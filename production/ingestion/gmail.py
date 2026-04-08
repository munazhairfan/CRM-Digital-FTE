"""
production/ingestion/gmail.py
Gmail ingestion handler with filtering for non-actionable messages.
"""

import base64
import json
import os
import re
from email.mime.text import MIMEText
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from production.clients.kafka_client import kafka_producer


# ---------------------------------------------------------------------------
# Auto-reply / skip patterns
# ---------------------------------------------------------------------------
SKIP_SUBJECT_PREFIXES = (
    "auto:",
    "automatic reply:",
    "out of office:",
    "delivery status",
    "undeliverable:",
    "mail delivery",
    "ndr:",                     # Non-delivery report
    "failure notice",
    "returned mail:",
    "mailer-daemon",
)

SKIP_LABELS = {"SENT", "DRAFT", "SPAM", "TRASH"}
REQUIRED_LABEL = "INBOX"

# Standard RFC headers that indicate automated messages
AUTORESPONSE_HEADERS = ("x-autoreply", "auto-submitted", "x-autorespond")


class GmailIngestion:
    def __init__(self):
        token_path = os.getenv("GMAIL_TOKEN_PATH", "token.json")
        self.support_email = os.getenv(
            "GMAIL_FROM_EMAIL", "support@flowforge.com"
        ).lower()

        self.service = None
        self._connected = False

        try:
            self.credentials = Credentials.from_authorized_user_file(token_path)
            self.service = build("gmail", "v1", credentials=self.credentials)
            self._connected = True
        except Exception as e:
            print(f"⚠️ Gmail credentials unavailable (using simulation mode): {e}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse_pubsub_message(self, pubsub_payload: dict) -> dict:
        """Decode the Pub/Sub push notification payload."""
        message_data = pubsub_payload.get("message", {})
        raw_data = message_data.get("data", "")
        decoded = (
            base64.b64decode(raw_data).decode("utf-8") if raw_data else "{}"
        )
        try:
            attrs = json.loads(decoded)
        except json.JSONDecodeError:
            attrs = message_data.get("attributes", {})
        return attrs

    async def process_notification(self, pubsub_message: dict) -> list:
        """
        Process a Gmail Pub/Sub notification and return messages that
        need a reply. Filters out sent mail, drafts, spam, auto-replies,
        and system notifications before returning.
        """
        if not self._connected:
            print("⚠️ Gmail API not connected — returning empty list")
            return []

        attrs = self.parse_pubsub_message(pubsub_message)
        history_id = attrs.get("historyId")
        if not history_id:
            return []

        try:
            history = (
                self.service.users()
                .history()
                .list(
                    userId="me",
                    startHistoryId=history_id,
                    historyTypes=["messageAdded"],
                )
                .execute()
            )
        except Exception as e:
            print(f"⚠️ Gmail history fetch failed: {e}")
            return []

        messages = []
        for record in history.get("history", []):
            for msg_added in record.get("messagesAdded", []):
                raw_msg = msg_added["message"]
                msg_id = raw_msg["id"]
                labels = raw_msg.get("labelIds", [])

                # Fast label check before fetching full message
                if not self._labels_ok(msg_id, labels):
                    continue

                message = await self.get_message(msg_id)
                if message:
                    messages.append(message)

        return messages

    async def get_message(self, message_id: str) -> Optional[dict]:
        """
        Fetch, parse, and filter a single Gmail message.
        Returns None for messages that should not receive a reply.
        """
        try:
            msg = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
        except Exception as e:
            print(f"⚠️ Failed to fetch message {message_id}: {e}")
            return None

        headers = {
            h["name"].lower(): h["value"]
            for h in msg["payload"]["headers"]
        }
        labels = msg.get("labelIds", [])
        body = self._extract_body(msg["payload"])

        # Central skip check
        skip, reason = self._should_skip_message(headers, labels, body, message_id)
        if skip:
            print(f"⏭️  Skipping message {message_id}: {reason}")
            return None

        # Truncate very long emails
        if len(body) > 4000:
            body = body[:3997] + "...\n[Email truncated for processing]"

        from_raw = headers.get("from", "")
        from_email = self._extract_email(from_raw)
        from_name = from_raw.split("<")[0].strip().replace('"', "")

        return {
            "channel": "email",
            "channel_message_id": message_id,
            "customer_email": from_email,
            "customer_name": from_name,
            "subject": headers.get("subject", "No Subject"),
            "content": body,
            "thread_id": msg.get("threadId"),
            "metadata": {
                "from": from_email,
                "name": from_name,
                "subject": headers.get("subject", "No Subject"),
                "labels": labels,
            },
        }

    async def send_reply(
        self,
        to_email: str,
        subject: str,
        body: str,
        thread_id: str = None,
        is_html: bool = False,
    ) -> dict:
        """Send a reply via Gmail API."""
        if not self._connected:
            print(
                f"⚠️ Gmail send simulated → To: {to_email} | Subject: {subject}"
            )
            return {"channel_message_id": "simulated", "delivery_status": "simulated"}

        if is_html:
            from email.mime.multipart import MIMEMultipart
            message = MIMEMultipart("alternative")
            message.attach(MIMEText(body, "html"))
        else:
            message = MIMEText(body)
        message["to"] = to_email
        message["subject"] = (
            subject if subject.startswith("Re:") else f"Re: {subject}"
        )
        message["from"] = self.support_email

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        send_request = {"raw": raw}
        if thread_id:
            send_request["threadId"] = thread_id

        result = (
            self.service.users()
            .messages()
            .send(userId="me", body=send_request)
            .execute()
        )
        return {"channel_message_id": result["id"], "delivery_status": "sent"}

    # ------------------------------------------------------------------
    # Filter helpers
    # ------------------------------------------------------------------

    def _should_skip_message(
        self,
        headers: dict,
        labels: list,
        body: str,
        message_id: str = "",
    ) -> tuple[bool, str]:
        """
        Central skip-decision method. Returns (should_skip: bool, reason: str).

        Checks (in order):
        1. Label-based: SENT, DRAFT, SPAM, TRASH, or missing INBOX
        2. Sender is our own support address
        3. Subject matches auto-reply / delivery-failure patterns
        4. RFC auto-reply headers present (X-Autoreply, Auto-Submitted, etc.)
        5. Empty body after stripping whitespace
        """
        # 1. Label check
        label_ok, label_reason = self._labels_ok(message_id, labels, detailed=True)
        if not label_ok:
            return True, label_reason

        # 2. Our own outbound mail
        from_email = self._extract_email(headers.get("from", "")).lower()
        if from_email == self.support_email:
            return True, f"outbound — sender is our own support address ({from_email})"

        # 3. Subject pattern match
        subject = headers.get("subject", "").lower().strip()
        for prefix in SKIP_SUBJECT_PREFIXES:
            if subject.startswith(prefix) or prefix in subject:
                return True, f"auto-reply subject pattern matched: '{prefix}'"

        # 4. RFC auto-response headers
        for header in AUTORESPONSE_HEADERS:
            value = headers.get(header, "").lower()
            if value and value not in ("no", ""):
                return True, f"auto-response header detected: {header}={value}"

        # 5. Empty body
        if not body.strip():
            return True, "empty body"

        return False, ""

    def _labels_ok(
        self,
        message_id: str,
        labels: list,
        detailed: bool = False,
    ) -> tuple[bool, str] | bool:
        """
        Returns True if the message labels indicate it should be processed.
        Pass detailed=True to get a (bool, reason) tuple.
        """
        label_set = set(labels)

        if label_set & SKIP_LABELS:
            matched = label_set & SKIP_LABELS
            reason = f"message has skip label(s): {matched}"
            return (False, reason) if detailed else False

        if REQUIRED_LABEL not in label_set:
            reason = f"message not in INBOX (labels: {label_set})"
            return (False, reason) if detailed else False

        return (True, "") if detailed else True

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    def _extract_body(self, payload: dict) -> str:
        """Extract plain text body from email payload, falling back to HTML."""
        if "parts" in payload:
            # Prefer plain text
            for part in payload["parts"]:
                if (
                    part.get("mimeType") == "text/plain"
                    and part.get("body", {}).get("data")
                ):
                    return base64.urlsafe_b64decode(
                        part["body"]["data"]
                    ).decode("utf-8")
            # Fall back to HTML with tag stripping
            for part in payload["parts"]:
                if (
                    part.get("mimeType") == "text/html"
                    and part.get("body", {}).get("data")
                ):
                    html = base64.urlsafe_b64decode(
                        part["body"]["data"]
                    ).decode("utf-8")
                    return re.sub(r"<[^<]+?>", "", html)

        # Direct body
        if payload.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(
                payload["body"]["data"]
            ).decode("utf-8")

        return ""

    def _extract_email(self, from_header: str) -> str:
        """Extract clean email address from a From header value."""
        match = re.search(r"<(.+?)>", from_header)
        return match.group(1).strip() if match else from_header.strip()


# ---------------------------------------------------------------------------
# Standalone filter tests
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    handler = GmailIngestion()

    cases = [
        # (description, headers, labels, body, expect_skip)
        (
            "Our own sent email",
            {"from": "support@flowforge.com", "subject": "Re: your ticket"},
            ["INBOX"],
            "Here is your answer.",
            True,
        ),
        (
            "Out-of-office auto-reply",
            {"from": "customer@corp.com", "subject": "Out of Office: Re: ticket"},
            ["INBOX"],
            "I am out of the office until Monday.",
            True,
        ),
        (
            "Auto-Submitted header",
            {
                "from": "noreply@someservice.com",
                "subject": "Notification",
                "auto-submitted": "auto-generated",
            },
            ["INBOX"],
            "Your weekly summary is ready.",
            True,
        ),
        (
            "Message in SENT label",
            {"from": "customer@example.com", "subject": "How do I export?"},
            ["SENT"],
            "Just following up on my question.",
            True,
        ),
        (
            "Message not in INBOX",
            {"from": "customer@example.com", "subject": "Help needed"},
            ["CATEGORY_PROMOTIONS"],
            "Can you help me with the API?",
            True,
        ),
        (
            "Empty body",
            {"from": "customer@example.com", "subject": "Hello"},
            ["INBOX"],
            "   ",
            True,
        ),
        (
            "Genuine customer inquiry — should NOT skip",
            {"from": "customer@corp.com", "subject": "How do I export CSV?"},
            ["INBOX"],
            "Hi, I need help exporting my project data as CSV.",
            False,
        ),
        (
            "Genuine follow-up — should NOT skip",
            {"from": "ayesha@startup.io", "subject": "Re: Team invitation issue"},
            ["INBOX"],
            "Still can't invite my team. I tried the steps you gave yesterday.",
            False,
        ),
    ]

    print("=" * 60)
    print("GMAIL FILTER TESTS")
    print("=" * 60)

    all_passed = True
    for desc, headers, labels, body, expect_skip in cases:
        skip, reason = handler._should_skip_message(headers, labels, body)
        status = "✅" if skip == expect_skip else "❌"
        if skip != expect_skip:
            all_passed = False
        skip_label = "SKIP" if skip else "PROCESS"
        print(f"\n{status} {desc}")
        print(f"   Expected: {'SKIP' if expect_skip else 'PROCESS'} | Got: {skip_label}")
        if reason:
            print(f"   Reason: {reason}")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✅" if all_passed else "SOME TESTS FAILED ❌")
    print("=" * 60)