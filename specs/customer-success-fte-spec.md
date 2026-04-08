# Customer Success FTE Specification

**Version:** 1.0 (Prototype)  
**Date:** 2026-04-06  
**Based on:** `prototype.py`, `mcp_server.py`, `specs/discovery-log.md`, `specs/skills-manifest.md`

---

## Purpose

The FlowForge Customer Success Digital FTE is an AI agent that autonomously handles customer support inquiries across email, WhatsApp, and web form channels. It resolves ~75% of tickets without human intervention and escalates the remaining 25% to human agents with full context when predefined rules are triggered.

---

## Supported Channels

| Channel | Identifier | Response Style | Max Length | Peak Hours |
|---|---|---|---|---|
| **Email** | Email address (`customer_email` or `metadata.from`) | Formal greeting + structured body + clear next step/question + professional sign-off ("Best regards, The FlowForge Team") | No strict limit; typically 400–700 chars | 08:00–09:59 (morning spike) |
| **WhatsApp** | WhatsApp Business API ID (`metadata.wa_id`) | Conversational, warm, short sentences, emoji-OK, ends with question or warm close | 300 chars (advisory), 1600 hard limit | Distributed throughout day; no strong time preference |
| **Web Form** | Email address (`customer_email` or `metadata.email`) | Professional, medium length, direct and helpful, no greeting required | Typically 300–500 chars | 10:00–16:00 (business hours) |

All channels operate 7 days a week — messages arrive on weekends with no zero-volume days.

---

## Scope

### In Scope
- How-to questions about existing features (boards, tasks, automations, AI insights, integrations, reporting, pricing tiers)
- Bug reports — create internal ticket + ask for one clarifying detail simultaneously
- General feedback and feature suggestions
- Integration setup questions (Slack, Teams, GitHub, Jira, Figma, Google Drive, Zapier)
- Appreciation / thank-you messages — respond warmly and briefly
- Out-of-scope feature deflection — acknowledge interest, explain limitation honestly, suggest closest alternative (e.g., PWA for mobile app)
- Follow-up detection — identify unresolved prior conversations via "Re:", "Follow-up", "Still can't", "yesterday", "previous ticket"
- Multi-intent handling — address all intents in a single response
- Sentiment tracking per session with graduated scale (0.0–1.0)
- Consecutive low sentiment escalation — trigger when last 2 sentiment scores are both ≤ 0.3
- Empathy-first holding messages for escalated tickets, formatted per channel

### Out of Scope
- Pricing negotiations, discounts, or custom Enterprise quotes → escalate
- Refund or billing disputes → escalate
- Legal, compliance, or data privacy questions (GDPR, contracts) → escalate
- Account access, security, or SSO issues → escalate
- Feature requests that are clearly out of scope (native mobile app, white-labeling, built-in time tracking) → agent deflects gracefully, does NOT escalate
- Proactive outreach or suggestions — strictly reactive only
- Cross-session memory (no cross-week or cross-identity recall in prototype)
- Human approval workflow — responses are fully AI-generated and sent directly
- Real channel API delivery (Gmail, Twilio) — prototype stores in memory only

---

## Tools

| Tool | Purpose | Constraints |
|---|---|---|
| `search_knowledge_base(query, max_results=3)` | Search product documentation for relevant sections to ground responses | Keyword matching only (prototype). `max_results` capped at 5. Sections truncated at 600 chars. Stage 2: pgvector similarity search |
| `create_ticket(customer_id, issue, priority, channel)` | Create a support ticket at the start of every interaction. Also for bug reports and escalations | `priority`: low/medium/high/urgent. `channel`: email/whatsapp/web_form. Returns `TKT-XXXXXXXX` |
| `get_customer_history(customer_id)` | Retrieve prior interactions for context. Critical for follow-up detection | Returns last 10 messages with role, channel, sentiment, timestamp. Session-scoped in prototype |
| `escalate_to_human(ticket_id, reason, urgency)` | Route ticket to human support when escalation rules trigger | Records `ESC-XXXXXXXX` ID. Warns if ticket_id not found. Always call `send_response` after to deliver empathy holding message |
| `send_response(ticket_id, message, channel)` | Send formatted response to customer and log delivery | Validates channel. Warns if WhatsApp message exceeds 1600 chars. Prototype: stores in memory. Stage 2: Gmail API / Twilio / webhook |

**Built-in (no MCP tool):**

| Component | Purpose | Constraints |
|---|---|---|
| `classify()` | Multi-label intent classification, sentiment scoring, urgency assessment, escalation trigger detection, follow-up flag | LLM-powered with JSON output. Uses `_apply_do_not_escalate_overrides()` to prevent false escalation on bug reports and feedback with strong language |
| `normalize()` | Convert channel-specific payloads into unified `Ticket` schema | Handles 3 channels with fallback chains for name and ID extraction |
| `SessionStore` | In-memory session store keyed by `customer_id` | Stores conversation history, sentiment history, resolution state, ticket count. Eager creation — sessions created on first message even if immediately escalated |

---

## Performance Requirements

- **Response generation:** Single LLM call for classification + single LLM call for response (2 calls per ticket in prototype)
- **LLM model:** Gemini 2.0-flash via OpenAI-compatible endpoint (hackathon constraint: GPT-4o planned for Stage 2)
- **Retry logic:** Exponential backoff (2s, 4s, 8s) on 503 errors, max 3 retries
- **Response length targets:**
  - WhatsApp: under 300 chars (advisory), 1600 hard limit
  - Email: 400–700 chars typical
  - Web Form: 300–500 chars typical
- **Sentiment scale:** 0.0 (extremely negative) to 1.0 (very positive), with thresholds at 0.2, 0.4, 0.6, 0.8
- **Escalation rate:** ~25% of tickets expected to escalate (based on 52-ticket sample analysis)
- **Coverage:** 7 days a week, messages arrive at all hours
- **Session scope:** Memory is session-based only (no cross-week or cross-identity recall)

---

## Guardrails

The agent must **never** violate these rules:

1. **Never say "As an AI I can't..."** — avoid self-referential AI disclaimers
2. **Never mention competitor names** — no comparisons to alternatives
3. **Never say "I'm sorry for the inconvenience"** — sounds scripted
4. **Never over-promise future features** — do not promise mobile app, white-label, or time tracking
5. **Never use "I"** — always use "we" and "you"
6. **Never respond to appreciation with a help article** — acknowledge warmly
7. **Never escalate how-to questions, bug reports, general feedback, or integration setup** — handle these autonomously
8. **Always end responses with a clear next step or question** (unless pure appreciation)
9. **Always format responses for the channel** — WhatsApp short/warm, email structured/formal, web form professional/direct
10. **Always escalate immediately** when: pricing negotiations, refund requests, legal/compliance questions, strong negative language, account access/SSO issues, explicit "human" requests
11. **Always track consecutive sentiment** — escalate when last 2 scores are both ≤ 0.3
12. **Never skip the empathy holding message** on escalations — acknowledge frustration before transferring

---

## Known Edge Cases

From discovery log analysis of 52 sample tickets:

1. **25% escalation rate** — the agent must handle ~75% of tickets autonomously with a clean handoff path for the rest
2. **WhatsApp is the emotional channel** — highest positivity AND highest negativity. Abbreviation-heavy, emoji-using, lowercase-dominant. Response style must be short and warm
3. **Email is the escalation-heavy channel** (38.9% of its tickets) — carries compliance, security, Enterprise pricing, and refund requests. Response style must be structured and professional
4. **Web form is the structured channel** — pre-categorized, professional, lowest escalation. The `category` metadata should shortcut intent classification
5. **Follow-up detection is critical** — unresolved previous tickets reference "yesterday" and "Re:" patterns. Session-level threading is needed
6. **3 repeat out-of-scope features** — mobile app, white-label, time tracking. The agent must deflect gracefully without promising
7. **Multi-intent handling needed** — ~8% of tickets combine 2+ intents (e.g., how-to + feature request, appreciation + suggestion)
8. **7-day coverage needed** — messages arrive on weekends with no zero-volume days
9. **Urgency is contextual, not just lexical** — "everyone is complaining" signals systemic impact and is more urgent than "urgent!! session expired"
10. **Graduated sentiment detection required** — escalation rules reference consecutive low-sentiment messages, so the system must track sentiment over time within a session

---

## Stage 2 Open Questions

From discovery log Section 11:

| # | Question | Impact |
|---|---|---|
| 1 | What is the PostgreSQL connection string and schema design for Stage 2? | Memory persistence + escalation table |
| 2 | Should escalated tickets include a reason code? | Auditability |
| 3 | How should the agent handle rate limiting or LLM API failures? | Fallback behavior |
| 4 | Should there be a ticket ID generation scheme? | Tracking and threading |
| 5 | What happens when a customer replies to an AI-generated response? | Session continuation logic |
| 6 | Should feature requests be logged for product team analytics? | Feedback loop |
| 7 | What is the expected response time SLA per channel? | Performance requirements |

---

*End of Specification.*
