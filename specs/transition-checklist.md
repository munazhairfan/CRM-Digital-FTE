# Transition Checklist — FlowForge Customer Success FTE

**From:** Incubation Phase (prototype.py + mcp_server.py)  
**To:** Production Build  
**Date:** 2026-04-06

---

## 1. Discovered Requirements

From `specs/discovery-log.md` and `specs/skills-manifest.md`:

- [x] Agent must handle 3 channels: email, WhatsApp, web form
- [x] WhatsApp responses must be under 300 chars (advisory), 1600 hard limit
- [x] Email responses must include formal greeting, structured body, sign-off
- [x] Web form responses must use category metadata for routing
- [x] ~25% escalation rate expected (13 of 52 tickets in sample)
- [x] Sentiment must be graduated (0.0–1.0), not binary
- [x] Consecutive low sentiment (≤ 0.3 for 2 messages) must trigger escalation
- [x] Multi-intent tickets (~8%) must be addressed in a single response
- [x] Follow-up detection via "Re:", "Still can't", "yesterday", "previous ticket"
- [x] Agent must NEVER promise out-of-scope features (mobile app, white-label, time tracking)
- [x] Agent must NEVER say "As an AI I can't...", competitor names, "I'm sorry for the inconvenience"
- [x] Agent must use "we" and "you" — never "I"
- [x] All responses must end with a clear next step or question (except pure appreciation)
- [x] Bug reports must create a ticket AND ask for one clarifying detail simultaneously
- [x] Escalated tickets must receive empathy-first holding messages, channel-formatted
- [x] Session memory must track conversation history (last 5 messages passed to LLM)
- [x] Session memory must track sentiment history for consecutive-low detection
- [x] 7-day coverage required — messages arrive on weekends
- [x] Knowledge base currently in system prompt; RAG with pgvector in Stage 2
- [x] Human handoff writes to DB with status='escalated' (no Slack/dashboard in prototype)
- [x] Fully AI-generated responses, no human approval step
- [x] Strictly reactive — no proactive suggestions
- [x] Out-of-scope feature requests handled gracefully by agent (NOT escalated)
- [x] Strong negative language on bug_report/feedback/integration_setup intents should NOT auto-escalate
- [x] Customer identity resolution: email address or WhatsApp wa_id
- [x] Escalation store must persist ticket_id, reason, urgency, timestamp, status
- [x] LLM retry on 503 errors with exponential backoff (2s, 4s, 8s, max 3 retries)
- [ ] 2 LLM calls per ticket: classification + response generation
- [ ] WhatsApp is the most emotionally volatile channel (highest positive AND negative)
- [ ] Email carries 38.9% of escalations — highest business-critical channel
- [ ] Web form has pre-classified category metadata — should shortcut classification

---

## 2. Working Prompts

### 2.1 Classification Prompt (`CLASSIFY_PROMPT_TEMPLATE`)

```
You are a classification engine for a customer success AI agent.
Analyze the following customer message and return ONLY a valid JSON object
with these fields — no markdown, no explanation:

{
  "intents": ["list of applicable intent labels"],
  "sentiment": <float 0.0 to 1.0>,
  "urgency": "<normal|elevated|urgent>",
  "is_follow_up": <boolean>,
  "escalation_trigger": "<rule matched or empty>"
}

Allowed intent labels (use all that apply):
  how_to, bug_report, feature_request, pricing, refund, appreciation,
  feedback, integration_setup, account_access, compliance, escalation_request,
  general_inquiry

Escalation rules to check:
- Pricing negotiations, discounts, or custom Enterprise quotes
- Refund or billing dispute
- Legal, compliance, or data privacy (GDPR, contracts)
- Strong negative language (angry, swearing, "worst product ever")
- Account access / security / SSO / data export
- Customer explicitly asks for "human", "manager", or "real person"
- Feature request clearly out of scope (mobile app, white-label, time tracking)
If ANY rule matches, set escalation_trigger to the matched rule text.
Otherwise set it to "".

Follow-up detection hints:
- "Re:", "Follow-up", "Still can't", "previous ticket", "yesterday",
  "tried the steps you gave", "still no", "still not working"
If detected, set is_follow_up to true.

Sentiment scale:
  0.0-0.2  = extremely negative (rage, threats, swearing)
  0.2-0.4  = negative (frustrated, disappointed, annoyed)
  0.4-0.6  = neutral (informational, polite inquiry)
  0.6-0.8  = positive (grateful, pleased)
  0.8-1.0  = very positive (enthusiastic, appreciative)

Urgency:
  normal   = standard inquiry, no time pressure
  elevated = something is broken or blocked for one user
  urgent   = systemic issue, security concern, or explicit "urgent"

Customer message:
Channel: {channel}
Content: {content}
Metadata: {metadata}
```

### 2.2 System Prompt Builder (`build_system_prompt()`)

Dynamic template with these sections:
1. **Role:** "You are the FlowForge Customer Success AI agent."
2. **Company Context:** FlowForge overview (12,400+ teams, pricing tiers, mission)
3. **Product Knowledge:** Full `PRODUCT_DOCS` embedded (features, how-tos, pricing, limitations)
4. **Escalation Rules:** Full `ESCALATION_RULES` embedded
5. **Brand Voice & Tone:** Full `BRAND_VOICE` embedded
6. **Recent Conversation History** (conditional, only when history > 1 message): Last 5 messages formatted as `Customer:` / `You (Agent):` lines
7. **Current Customer Message:** Channel, name, content, detected intents, sentiment, urgency, follow-up flag, escalation reason
8. **10 Instructions:** Escalation shortcut, appreciation handling, bug report flow, how-to flow, multi-intent, out-of-scope deflection, channel formatting, end with question, guardrails, pronoun rules

### 2.3 Tool Docstrings That Worked Well

**`search_knowledge_base`** — Keyword section matching with term frequency scoring. Returns top N sections from markdown, truncated at 600 chars. "No relevant documentation found" fallback.

**`create_ticket`** — Validates channel (email/whatsapp/web_form) and priority (low/medium/high/urgent). Returns `TKT-XXXXXXXX` format ID. Stores in dict with timestamp.

**`get_customer_history`** — Returns last 10 messages with role, channel, sentiment, timestamp. Session-scoped. "No previous interactions found" fallback.

**`escalate_to_human`** — Validates urgency (normal/elevated/urgent). Updates ticket status to "escalated". Writes to escalation_store. Returns `ESC-XXXXXXXX` confirmation. Warns if ticket_id not found.

**`send_response`** — Validates channel. Stores response against ticket with delivery timestamp. Warns if WhatsApp exceeds 1600 chars. Returns delivery confirmation string.

---

## 3. Edge Cases Found

From discovery-log.md Section 6:

| Edge Case | How It Was Handled | Test Case Needed |
|---|---|---|
| **Follow-up handling** | LLM classifier detects "Re:", "Follow-up", "Still can't", "yesterday", "previous ticket" → sets `is_follow_up=True`. Conversation history (last 5 messages) passed to LLM for context. | ✅ Tested: "Follow-up: Still can't invite team members. I tried the steps you gave yesterday." — detected correctly |
| **Multi-intent tickets** | LLM classifier returns multiple intents in `intents` array. System prompt instructs: "If the message has MULTIPLE intents, address ALL of them in one response." | ✅ Tested: "Can I export all my tasks as CSV? Also, is there a way to schedule recurring tasks?" — both addressed |
| **Positive feedback handling** | Intent `appreciation` detected. System prompt: "If the message is primarily an appreciation/thanks, respond warmly and briefly." LLM generates short warm response, no KB article served. | ✅ Tested: "thanks for the help earlier. everything is good now ❤️" — warm 72-char response |
| **Urgency detection (contextual)** | LLM classifier assigns urgency: normal/elevated/urgent. "Everyone is complaining" → urgent. "urgent!! session expired" → urgent. Context matters, not just keywords. | ❌ No dedicated test for contextual urgency |
| **Graduated sentiment** | LLM scores 0.0–1.0. Escalation triggers when last 2 consecutive scores are both ≤ 0.3. `_apply_do_not_escalate_overrides()` prevents false escalation on bug reports with strong language. | ✅ Tested: [0.5, 0.3, 0.1] trajectory → escalated at turn 3 |
| **Session/context management** | `SessionStore` keyed by `customer_id`. Conversation history appended with role/content/timestamp. Sentiment history tracked as list of floats. | ✅ Tested: 3-turn conversation with full history persistence |
| **"Silent frustration" pattern** | "Very annoying" (understated) vs "worst ever!!" (extreme). LLM classifier scores these differently — understated ~0.4, extreme ~0.1. | ❌ No dedicated test for understated frustration |
| **Limitation awareness** | Out-of-scope feature requests (`feature_request` + "out of scope") trigger override in `_apply_do_not_escalate_overrides()`. Agent deflects gracefully via system prompt instructions. | ✅ Tested: "Does FlowForge have a mobile app?" — PWA alternative suggested, no false escalation |
| **Domain-tier inference** | Customer email domain (techcorp.com, startup.io, corp.com) available in metadata. Not currently used for plan-tier inference. | ❌ No test — capability exists but unused |
| **Cross-channel session gap** | Customer emailing from one address and WhatsApping from another creates two separate sessions. Not currently resolved. | ❌ No test — known Stage 2 gap |

---

## 4. Response Patterns That Worked

From skills-manifest.md Skill 4 (Channel Adaptation):

### WhatsApp
- Short, conversational, single paragraph
- Greeting: "Hey {name}!" or "Hi {name}! 👋"
- Emoji-OK: 💙, 🛠️, ❤️, 👋 used naturally
- Max 300 chars (advisory), 1600 hard limit
- Ends with question or warm close
- No sign-off required
- Example: *"Hey Sara! We hear your frustration and we're really sorry about this. We're getting someone from our team to look into this right away. 💙"*

### Email
- Formal greeting: "Hi {name},\n\n"
- Structured body with sections (bold headings OK)
- Clear next step or question before sign-off
- Sign-off: "Best regards,\nThe FlowForge Team"
- Typically 400–700 chars
- Minimal emoji (only 👋 in greeting per brand voice example)
- Example: *"Hi Usman,\n\nThanks for reaching out! We are happy to help...\n\n**Exporting Data:**\n...\n\n**Recurring Tasks:**\n...\n\nDo those instructions help...?\n\nBest regards,\nThe FlowForge Team"*

### Web Form
- Professional, medium length
- Direct and helpful
- "Hi {name},\n\n" greeting
- Sign-off: "Best regards,\nThe FlowForge Team"
- Typically 300–500 chars
- No emoji
- Category metadata can shortcut classification

### Empathy Holding Messages (Escalations)
- **WhatsApp:** "Hey {name}! We hear your frustration... getting someone to look into this right away. 💙"
- **Email:** "Hi {name},\n\nWe hear you, and we understand this is frustrating. We've passed your request to our [appropriate team], and they'll be in touch within 24 hours.\n\nBest regards,\nThe FlowForge Team"
- **Web Form:** "Hi {name},\n\nWe've received your request and connected you with the appropriate team. Expect a response within 24 hours.\n\nBest regards,\nThe FlowForge Team"

---

## 5. Escalation Rules (Finalized)

From skills-manifest.md Skill 3:

### Immediate Escalation Triggers

| Rule | Example | Overrides? |
|---|---|---|
| Pricing negotiations, discounts, custom Enterprise quotes | "can u give me a quote?" | No |
| Refund or billing dispute | "please refund my Pro subscription" | No |
| Legal, compliance, data privacy (GDPR, contracts) | "data export for compliance purposes" | No |
| Strong negative language (angry, swearing, "worst product ever") | "worst ever!! nothing works 😡" | **Yes** — if intent is `bug_report`, `feedback`, or `integration_setup` and trigger is "strong negative language", agent handles it |
| Sentiment ≤ 0.3 for 2 consecutive messages | [0.3, 0.1] trajectory | No |
| Account access / security / SSO / data export | "can't access my account", "SSO setup" | No |
| Customer explicitly asks for "human", "manager", "real person" | "I want to speak to a real person" | No |
| Technical issue cannot be solved after 2 KB searches | (Not yet implemented) | No |

### Do NOT Escalate (Agent Handles Itself)

| Category | Examples |
|---|---|
| How-to questions about existing features | "how do I invite team members?", "how do I set up automations?" |
| Bug reports | "board is stuck loading", "AI insights not showing predictions" |
| General feedback | "platform is amazing but I wish it had a dark mode" |
| Integration setup questions (if covered in docs) | "how do I connect Slack?", "Figma integration error" |

### Override Rules (Implemented in `_apply_do_not_escalate_overrides()`)

1. **Bug report + strong language** → Don't escalate. Frustration with bugs is expected; handle empathetically.
2. **Bug report + sentiment < 0.3** → Don't escalate on a single low score. Only escalate if 2 consecutive.
3. **Integration setup + strong language** → Don't escalate. Handle with patience.
4. **Feedback + strong language** → Don't escalate. Acknowledge and log.
5. **Feature request + out of scope** → Don't escalate. Agent deflects gracefully (suggests PWA for mobile app, etc.).

---

## 6. Performance Baseline

From actual test runs:

| Metric | Value |
|---|---|
| LLM calls per ticket | 2 (classify + respond) |
| WhatsApp response length | 72–301 chars (mostly under 300) |
| Email response length | ~570 chars average |
| Escalation holding message (WhatsApp) | ~139–163 chars |
| Escalation holding message (Email) | ~185 chars |
| Escalation rate on test set | 3 of 4 forced tests escalated correctly (75% on small sample) |
| Consecutive sentiment detection | ✅ Verified: [0.5, 0.3, 0.1] → escalated at turn 3 |
| Classification accuracy | 10/10 test tickets classified with correct intents |
| Follow-up detection | ✅ Verified: "Follow-up:", "Still can't", "tried the steps you gave" all detected |
| Multi-intent handling | ✅ Verified: CSV export + recurring tasks both addressed in one response |
| Appreciation handling | ✅ Verified: "thanks" → warm 72-char response, no KB article |
| Out-of-scope deflection | ✅ Verified: "mobile app?" → PWA suggested, no false escalation |
| Refund escalation | ✅ Verified: "refund" → escalated with empathy holding message |
| LLM retry on 503 | ✅ Implemented: exponential backoff 2s/4s/8s, max 3 retries |

---

## 7. Code Mapping Table

| Prototype Component | File | Production Equivalent | Production Location |
|---|---|---|---|
| `Ticket` dataclass | `prototype.py` | Pydantic `TicketCreate`, `TicketResponse` models | `production/models/` |
| `Session` + `SessionStore` | `prototype.py` | PostgreSQL-backed session service with Redis cache | `production/services/session_service.py` |
| `normalize()` | `prototype.py` | Ingestion adapter per channel | `production/ingestion/` |
| `classify()` + `CLASSIFY_PROMPT_TEMPLATE` | `prototype.py` | Classification agent with structured output | `production/agents/classifier.py` |
| `_apply_do_not_escalate_overrides()` | `prototype.py` | Override rules engine | `production/services/escalation_engine.py` |
| `build_system_prompt()` | `prototype.py` | Prompt template manager with RAG context | `production/services/prompt_builder.py` |
| `generate_response()` | `prototype.py` | Response generation agent | `production/agents/responder.py` |
| `generate_empathy_holding()` | `prototype.py` | Templated holding message service | `production/services/response_formatter.py` |
| `_llm_with_retry()` | `prototype.py` | Shared LLM client with circuit breaker | `production/clients/llm_client.py` |
| `escalation_store` (in-memory list) | `prototype.py` | PostgreSQL `escalated_tickets` table | `production/models/` + DB migrations |
| `escalation_record()` | `prototype.py` | Escalation repository layer | `production/repositories/escalation_repo.py` |
| `search_knowledge_base` | `mcp_server.py` | pgvector similarity search service | `production/services/knowledge_base.py` |
| `create_ticket` | `mcp_server.py` | Ticket management service | `production/services/ticket_service.py` |
| `get_customer_history` | `mcp_server.py` | Customer history repository | `production/repositories/customer_repo.py` |
| `escalate_to_human` | `mcp_server.py` | Escalation workflow (DB + notification) | `production/workflows/escalation.py` |
| `send_response` | `mcp_server.py` | Channel delivery service (Gmail/Twilio/Webhook) | `production/services/channel_delivery.py` |
| `PRODUCT_DOCS` (embedded string) | `prototype.py` | Document ingestion pipeline + pgvector chunks | `production/ingestion/docs_loader.py` |
| `ESCALATION_RULES` (embedded string) | `prototype.py` | Config-driven rules engine | `production/config/escalation_rules.yaml` |
| `BRAND_VOICE` (embedded string) | `prototype.py` | Prompt template partial | `production/config/brand_voice.md` |
| `run_conversation()` | `prototype.py` | Integration test harness | `tests/integration/test_conversations.py` |
| Individual test files | `test_*.py` | pytest suite with fixtures | `tests/unit/`, `tests/integration/` |

---

## 8. Production Folder Structure

```
production/
├── __init__.py
├── agents/
│   ├── __init__.py
│   ├── classifier.py
│   └── responder.py
├── clients/
│   ├── __init__.py
│   └── llm_client.py
├── config/
│   ├── __init__.py
│   └── brand_voice.md
├── ingestion/
│   ├── __init__.py
│   ├── email.py
│   ├── whatsapp.py
│   └── web_form.py
├── models/
│   ├── __init__.py
│   └── schemas.py
├── repositories/
│   ├── __init__.py
│   ├── customer_repo.py
│   ├── escalation_repo.py
│   └── ticket_repo.py
├── services/
│   ├── __init__.py
│   ├── channel_delivery.py
│   ├── escalation_engine.py
│   ├── knowledge_base.py
│   ├── prompt_builder.py
│   ├── response_formatter.py
│   ├── session_service.py
│   └── ticket_service.py
├── workflows/
│   ├── __init__.py
│   └── escalation.py
└── main.py
```

*Files not yet created — structure only. Ready for implementation in Stage 2.*

---

*End of Transition Checklist.*
