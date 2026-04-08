# Skills Manifest — FlowForge Customer Success Digital FTE

**Version:** 1.0 (Prototype)  
**Date:** 2026-04-06  
**Based on:** `prototype.py` + `mcp_server.py`

---

## Overview

This document defines the 5 core skills that constitute the FlowForge Customer Success AI agent. Each skill is an autonomous capability that the agent invokes at decision points during customer interactions. Skills map to MCP tools where applicable and operate independently, allowing composition into multi-skill workflows (e.g., Knowledge Retrieval → Channel Adaptation → Escalation Decision).

---

## 1. Knowledge Retrieval Skill

**Purpose:** Search the FlowForge product knowledge base and return relevant documentation sections to ground agent responses.

**Trigger condition:**  
Invoked whenever a customer asks a question about product features, how-to steps, integrations, pricing tiers, limitations, or known issues. Always triggered before answering any product-related question.

**Inputs:**
| Parameter | Type | Source | Description |
|---|---|---|---|
| `query` | `str` | Customer message content | The customer's question or search keywords |
| `max_results` | `int` (default: 3) | Agent config | Maximum number of matching KB sections to return |

**Outputs:**
| Return | Type | Description |
|---|---|---|
| Success | `str` | Formatted string of top 3 matching KB sections, prefixed with `[Result N]`, separated by `---`. Sections truncated at 600 chars. |
| Not found | `str` | `"No relevant documentation found for your query. Consider escalating to human support if the question is outside the product scope."` |

**MCP tool:** `search_knowledge_base(query: str, max_results: int = 3) -> str`

**Current implementation:** Keyword frequency matching against sections split by `##` headings. Terms under 3 characters are ignored. Sections scored by term count across query terms.

**Constraints / edge cases:**
- `max_results` is capped at 5 to keep context size manageable
- Prototype uses keyword matching only — no semantic similarity. Multi-word phrases like "how to invite team" may miss sections that use "team invitation" phrasing
- No fuzzy matching — typos in customer queries reduce recall
- Sections longer than 600 chars are truncated, which may cut off step-by-step instructions mid-sentence
- Stage 2 will replace with pgvector cosine similarity search over embedded document chunks

---

## 2. Sentiment Analysis Skill

**Purpose:** Score each customer message on a graduated sentiment scale (0.0–1.0) and track sentiment trajectory across the session to detect deteriorating conversations.

**Trigger condition:**  
Runs automatically on **every incoming message** during the classification step. Not invokable as a tool — it is an intrinsic part of `classify()`.

**Inputs:**
| Parameter | Type | Source | Description |
|---|---|---|---|
| `content` | `str` | Customer message text | Full message body |
| `channel` | `str` | Ticket metadata | Used for context (WhatsApp messages tend to be more emotionally volatile) |
| `sentiment_history` | `list[float]` | SessionStore | Prior sentiment scores for this session |

**Outputs:**
| Return | Type | Description |
|---|---|---|
| `sentiment` | `float` (0.0–1.0) | Scored and attached to the Ticket object |
| Side effect | — | Appended to `Session.sentiment_history` |
| Trigger | — | If last 2 scores are both ≤ 0.3, sets `escalation_reason = "consecutive_low_sentiment"` |

**MCP tool:** None — built into `classify()`. Not externally callable.

**Sentiment scale:**

| Range | Interpretation | Example |
|---|---|---|
| 0.0–0.2 | Extremely negative | "worst ever!! nothing works 😡" |
| 0.2–0.4 | Negative / frustrated | "this is very frustrating", "still not working :(" |
| 0.4–0.6 | Neutral | "how do I connect Slack?", "does FlowForge support recurring tasks?" |
| 0.6–0.8 | Positive / pleased | "thanks for the help!", "great support" |
| 0.8–1.0 | Very positive / enthusiastic | "super fast reply as always! you guys rock ❤️" |

**Constraints / edge cases:**
- Threshold is **≤ 0.3** (not < 0.3) for consecutive low sentiment escalation — a score of exactly 0.3 counts as low
- Sentiment is context-dependent: "this is so frustrating" from WhatsApp is scored differently than the same phrase in a formal email
- The escalation rule requires **two consecutive** low scores — a single 0.1 score does not trigger escalation by itself
- The LLM classifier is asked to output sentiment as part of the same JSON response as intent classification, so parsing failures affect both
- Stage 2: could be replaced with a dedicated sentiment model (e.g., DistilBERT sentiment) for more consistent scoring without LLM variance

---

## 3. Escalation Decision Skill

**Purpose:** Evaluate incoming messages against a defined set of escalation rules and route to human support when criteria are met.

**Trigger condition:**  
Invoked during classification (LLM detects escalation triggers) and post-classification (rule-based overrides for consecutive low sentiment and known override patterns).

**Inputs:**
| Parameter | Type | Source | Description |
|---|---|---|---|
| `intents` | `list[str]` | Classification output | Detected intent labels (e.g., `refund`, `pricing`, `bug_report`) |
| `escalation_reason` | `str` | LLM classification | Raw escalation trigger text matched by classifier |
| `sentiment` | `float` | Sentiment Analysis Skill | Used for consecutive low sentiment check |
| `sentiment_history` | `list[float]` | SessionStore | Used for two-consecutive-low check |

**Outputs:**
| Return | Type | Description |
|---|---|---|
| `escalation_reason` | `str` or `""` | The matched escalation rule text, or empty string if no escalation needed |
| `status` | `str` | Set to `"escalated"` if any rule matches, otherwise unchanged |

**MCP tools:** 
- `escalate_to_human(ticket_id: str, reason: str, urgency: str) -> str` — called when escalation is confirmed
- `send_response(ticket_id: str, message: str, channel: str) -> str` — called after escalation to deliver empathy holding message

**Escalation rules (trigger immediately):**

| Rule | Example | Overrides? |
|---|---|---|
| Pricing negotiations / custom quotes | "can u give me a quote?" | No |
| Refund / billing dispute | "please refund my Pro subscription" | No |
| Legal, compliance, data privacy | "data export for compliance purposes" | No |
| Strong negative language | "worst product ever!!" | Yes — if intent is `bug_report`, `feedback`, or `integration_setup` and trigger is "strong negative language", agent handles it |
| Sentiment ≤ 0.3 for 2 consecutive messages | [0.3, 0.1] trajectory | No |
| Account access / security / SSO | "can't access my account", "SSO setup" | No |
| Explicit "human" / "manager" / "real person" request | "I want to speak to a real person" | No |
| Out-of-scope feature request | "does it have a mobile app?", "white-label?" | **Yes** — agent deflects gracefully per brand voice instead of escalating |

**Do NOT escalate (agent handles itself):**
- How-to questions about existing features
- Bug reports (create ticket + ask for clarifying detail)
- General feedback
- Integration setup questions (if covered in docs)

**Constraints / edge cases:**
- Out-of-scope feature requests are classified by the LLM as escalation triggers but **overridden** by the agent so it can respond with a graceful deflection (e.g., suggesting PWA for mobile app requests). This is intentional — we want the agent to handle these, not escalate them.
- The "strong negative language" rule is overridden for `bug_report`, `feedback`, and `integration_setup` intents — frustration with a bug is expected and should be handled empathetically, not escalated immediately
- Consecutive low sentiment check runs **after** classification, as a secondary pass — it catches deterioration that a single-message classifier might miss
- `escalate_to_human` warns if the ticket_id doesn't exist in `ticket_store` but still records the escalation
- Stage 2: escalation should write to a PostgreSQL `escalated_tickets` table with `status='escalated'` and notify via Slack webhook

---

## 4. Channel Adaptation Skill

**Purpose:** Format agent responses to match the linguistic conventions, length expectations, and tone norms of each communication channel.

**Trigger condition:**  
Invoked during response generation — both when the LLM generates a reply and when the empathy holding message is constructed for escalated tickets.

**Inputs:**
| Parameter | Type | Source | Description |
|---|---|---|---|
| `channel` | `str` | Ticket | One of: `email`, `whatsapp`, `web_form` |
| `response_content` | `str` | LLM output or empathy template | Raw response text |
| `customer_name` | `str` | Ticket | Used for personalization |

**Outputs:**
| Return | Type | Description |
|---|---|---|
| Formatted response | `str` | Channel-appropriate response ready for delivery |

**MCP tool:** `send_response(ticket_id: str, message: str, channel: str) -> str` — validates channel and logs delivery

**Channel formatting rules:**

| Dimension | WhatsApp | Email | Web Form |
|---|---|---|---|
| **Max length** | Under 300 chars (advisory), 1600 hard limit | No strict limit, typically 400–700 chars | Professional, medium length, typically 300–500 chars |
| **Greeting** | "Hey {name}!" or "Hi {name}!" | "Hi {name},\n\n" | "Hi {name},\n\n" |
| **Structure** | Conversational, single paragraph | Structured with sections, formal sign-off | Direct, professional, no greeting required |
| **Emoji** | Acceptable (💙, 🛠️, 👋) | Minimal — only 👋 in greeting | None |
| **Sign-off** | Implicit (ends with question or warm close) | "Best regards,\nThe FlowForge Team" | "Best regards,\nThe FlowForge Team" |
| **Sentence length** | Short, fragmented OK | Full, compound sentences | Complete, professional sentences |

**Empathy holding messages for escalations:**
- **WhatsApp:** "Hey {name}! We hear your frustration... getting someone to look into this right away. 💙"
- **Email:** "Hi {name},\n\nWe hear you, and we understand this is frustrating. We've passed your request to our [appropriate team]..."
- **Web Form:** "Hi {name},\n\nWe've received your request and connected you with the appropriate team. Expect a response within 24 hours."

**Constraints / edge cases:**
- WhatsApp 300-char limit is **advisory**, not enforced — the LLM occasionally exceeds it (observed: 301 chars). The `send_response` tool only warns at 1600 chars
- Email responses must end with a clear next step or question (per brand voice) — the LLM is prompted but doesn't always comply
- The empathy holding messages are **templated** (not LLM-generated) — they ensure consistency but lack personalization beyond the customer name
- Cross-channel: a customer may start on WhatsApp and follow up via email — the system treats these as separate sessions (by customer_id). Stage 2 should unify
- Stage 2: `send_response` should route via real channel APIs (Gmail, Twilio, HTTP webhook) instead of in-memory storage

---

## 5. Customer Identification Skill

**Purpose:** Normalize incoming messages from any channel into a unified customer identity and session context, enabling consistent handling across channels.

**Trigger condition:**  
Runs as the **first step** of every `process_ticket()` call, before classification or response generation.

**Inputs:**
| Parameter | Type | Source | Description |
|---|---|---|---|
| `raw` | `dict` | Inbound message | Channel-specific payload structure |
| `customer_email` / `customer_phone` | `str` | Raw payload (email/whatsapp) | Direct customer identifier |
| `metadata.from` | `str` | Email metadata | Sender email address |
| `metadata.wa_id` | `str` | WhatsApp metadata | WhatsApp Business API ID |
| `metadata.email` | `str` | Web form metadata | Web form submitter email |
| `metadata.name` | `str` | Any channel metadata | Customer display name |

**Outputs:**
| Return | Type | Description |
|---|---|---|
| `Ticket` | `dataclass` | Normalized ticket with unified schema |
| `Session` | `Session` (via `SessionStore`) | Loaded existing or newly created session |

**MCP tool:** `get_customer_history(customer_id: str) -> str` — retrieves prior interactions for context

**Normalization logic per channel:**

| Channel | `customer_id` source | `customer_name` source |
|---|---|---|
| Email | `customer_email` → `metadata.from` | `customer_name` → `metadata.name` → email prefix |
| WhatsApp | `metadata.wa_id` → `customer_phone` | `customer_name` → `metadata.name` → wa_id |
| Web Form | `customer_email` → `metadata.email` | `customer_name` → `metadata.name` → email prefix |

**Session key:** `customer_id` (email address or WhatsApp wa_id)

**Session contents:**
- `conversation_history` — list of `{role, content, timestamp}` dicts
- `sentiment_history` — list of float scores
- `resolution_state` — `"open" | "escalated" | "resolved"`
- `ticket_count` — number of messages in this session
- `created_at` / `updated_at` — ISO timestamps

**Constraints / edge cases:**
- Session is keyed by a single identifier — a customer who emails from `personal@gmail.com` and WhatsApps from `+92300...` gets **two separate sessions**. Stage 2 should support customer identity resolution (email-to-phone linking)
- The `normalize()` function does not validate email format or phone number format — malformed inputs produce malformed `customer_id` values
- `customer_name` fallback chain: explicit name → metadata name → email prefix → raw ID. The last fallback (`"923001234567"` as a name) is undesirable but prevented by the metadata checks
- Session creation is **eager** — a session is created on the first message even if it immediately escalates. Orphaned sessions (escalated, no further messages) accumulate in memory
- Stage 2: sessions should be persisted to PostgreSQL with customer profiles, and `get_customer_history` should query across unified customer identity (email + phone linked)

---

## Stage 2 Gaps

The following items are implemented in-memory in the prototype and require real implementations in Stage 2:

### Data Persistence
| Current (Prototype) | Stage 2 Requirement |
|---|---|
| `SessionStore` — in-memory dict | PostgreSQL `sessions` table with `customer_id`, `history` (JSONB), `sentiment_history` (float array), `resolution_state`, `ticket_count` |
| `escalation_store` — in-memory list | PostgreSQL `escalated_tickets` table with `escalation_id`, `ticket_id`, `reason`, `urgency`, `status`, `created_at`, `assigned_to` |
| `ticket_store` — in-memory dict | PostgreSQL `tickets` table with full ticket lifecycle tracking |
| Session loss on process restart | Persistent sessions survive restarts, support concurrent workers |

### Knowledge Retrieval
| Current (Prototype) | Stage 2 Requirement |
|---|---|
| Keyword frequency matching against markdown sections | pgvector cosine similarity search over embedded document chunks |
| Single `PRODUCT_DOCS` string embedded in code | Document ingestion pipeline: parse markdown, chunk by heading, embed with OpenAI `text-embedding-3-small`, store in `document_chunks` table |
| No semantic understanding | Semantic search handles paraphrases, typos, and indirect queries |
| No versioning of docs | Document version tracking with re-embedding on update |

### Channel Integration
| Current (Prototype) | Stage 2 Requirement |
|---|---|
| `send_response` stores response in `ticket_store` | Real channel APIs: Gmail API (email), Twilio WhatsApp Business API (WhatsApp), HTTP POST webhook (web form) |
| No inbound message ingestion | Webhook endpoints: Gmail push notifications, Twilio incoming WhatsApp, web form POST handler |
| No delivery confirmation | Delivery status tracking per channel (sent, delivered, read) |
| No rate limiting | Per-channel rate limiting (WhatsApp: 800 msg/24h, Gmail: 250 msg/day free tier) |

### Session & Identity
| Current (Prototype) | Stage 2 Requirement |
|---|---|
| Single identifier per session (email OR wa_id) | Unified customer identity: link email, phone, name across channels |
| No cross-channel session continuity | Customer starting on WhatsApp and following up via email sees unified history |
| No session expiration | Session TTL (e.g., 7 days of inactivity = archive) |
| `SessionStore` is process-local | Shared session store for distributed deployment (PostgreSQL or Redis) |

### Observability & Analytics
| Current (Prototype) | Stage 2 Requirement |
|---|---|
| `print()` statements for logging | Structured logging (JSON) with correlation IDs |
| No metrics | Prometheus/Grafana dashboards: avg response time, escalation rate, sentiment trends, channel distribution |
| No audit trail | Full audit log: every tool call, classification result, and response stored for compliance |

### Error Handling & Resilience
| Current (Prototype) | Stage 2 Requirement |
|---|---|
| No retry on LLM API failure | Exponential backoff with circuit breaker for OpenAI API |
| No fallback if LLM returns malformed JSON | JSON parsing fallback: re-prompt or use rule-based classification |
| No input validation on raw messages | Schema validation (Pydantic) on all inbound messages |
| No timeout on LLM calls | Request timeout (30s) with graceful degradation |

### Security
| Current (Prototype) | Stage 2 Requirement |
|---|---|
| API key in `.env` file | Secret management (AWS Secrets Manager, HashiCorp Vault, or GitHub Secrets) |
| No data encryption | PII encryption at rest (customer emails, phone numbers) |
| No access control | Role-based access for human agents reviewing escalated tickets |

---

*End of Skills Manifest. Next: Stage 2 architecture design.*
