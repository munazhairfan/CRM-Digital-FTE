# Discovery Log — FlowForge Customer Success Digital FTE

**Date:** 2026-04-06  
**Phase:** Exploration & Analysis  
**Input:** `/context/` — company-profile.md, product-docs.md, sample-tickets.json (52 tickets), escalation-rules.md, brand-voice.md

---

## 1. Dataset Overview

| Metric | Value |
|---|---|
| Total tickets | 52 |
| Date range | 2026-04-05 to 2026-04-14 (10 days) |
| Channels | Email (18), WhatsApp (18), Web Form (18) |
| Channel split | Exactly 34.6% each |
| Weekend coverage | Messages arrive every day including weekends |
| Escalation rate | 13 of 52 (25%) require human handoff |

---

## 2. Topic / Intent Classification

| Category | Count | % |
|---|---|---|
| How-to | 14 | 26.9% |
| Bug report | 7 | 13.5% |
| Feature request | 6 | 11.5% |
| Pricing inquiry | 5 | 9.6% |
| Appreciation | 6 | 11.5% |
| Integration setup | 3 | 5.8% |
| Refund | 2 | 3.8% |
| Follow-up (unresolved) | 2 | 3.8% |
| Feedback | 3 | 5.8% |
| Account access / security | 2 | 3.8% |
| Escalation / compliance | 1 | 1.9% |
| General inquiry | 1 | 1.9% |

**Key finding:** How-to questions dominate (27%). Combined with bug reports (14%), these two categories represent ~41% of all traffic — the bot's primary workload.

---

## 3. Sentiment Analysis by Channel

### Email (18 tickets)
| Sentiment | Count | Notes |
|---|---|---|
| Positive | 4 | Appreciation, renewal, love for platform |
| Neutral | 10 | Polite, measured inquiries |
| Negative / Frustrated | 3 | "Very frustrating", refund request, urgent user removal |
| Urgent | 1 | Departed employee access removal |

### WhatsApp (18 tickets)
| Sentiment | Count | Notes |
|---|---|---|
| Positive | 5 | "thanks!", "you guys rock", "love the feature!!" |
| Neutral | 7 | Casual how-to questions |
| Negative / Frustrated | 4 | "worst ever!!", "task disappeared!!", "board crashing" |
| Urgent | 2 | "urgent!!" markers, double exclamation |

### Web Form (18 tickets)
| Sentiment | Count | Notes |
|---|---|---|
| Positive | 1 | "I love the AI insights!" |
| Neutral | 13 | Professional, measured |
| Negative | 3 | Understated frustration ("Very annoying", bug reports) |
| Urgent | 1 | Accidentally deleted important board |

**Key finding:** WhatsApp has the highest emotional amplitude — most positive AND most negative channel. Email carries the most business-critical escalations. Web form is the most stable and measured.

---

## 4. Channel-Specific Linguistic Patterns

### Email
- **Formality:** High — full sentences, proper capitalization, structured greetings
- **Sentence length:** 15-25 words average
- **Structure:** Greeting + context + request (+ implicit sign-off)
- **Subject lines:** Present in all metadata; "Re:" prefix signals follow-ups
- **Punctuation:** Proper — no emojis, no abbreviations
- **Follow-up markers:** "Follow-up:" and "Re:" patterns detected
- **Response style needed:** Structured, slightly longer, clear next step or question

### WhatsApp
- **Formality:** Very low — 78% all-lowercase messages
- **Abbreviations:** "pls" (3x), "u" (3x), "yo"
- **Emoji usage:** 5 of 18 messages (28%) — 😩, 😡, 👍, ❤️
- **Sentence length:** 8-12 words average
- **Sentence fragments:** No greetings or sign-offs; blunt and immediate
- **Urgency markers:** Double exclamation "!!" in 4 messages
- **Response style needed:** Short, warm, direct. Emoji-appropriate.

### Web Form
- **Formality:** Medium-high — full sentences, proper capitalization
- **Completeness:** Grammatically correct, professional tone even in complaints
- **No greetings/sign-offs:** Pure request content
- **Category metadata:** Every ticket has pre-classified `category` field
- **Specificity:** More detailed technical context than other channels
- **Response style needed:** Professional, structured, concise

### Cross-Channel Metadata Gap
- Email has `subject`, web form has `category`, WhatsApp has neither
- System must normalize into a unified schema

---

## 5. Escalation Trigger Analysis

Based on escalation-rules.md, here is every matching ticket:

| Trigger Rule | Count | Example Tickets |
|---|---|---|
| Pricing negotiations / custom quotes | 3 | Sana (custom pricing), Talha (Enterprise SLA), Daniyal (WA quote request) |
| Refund / billing disputes | 2 | Khalid (Pro refund), Anas (WA signed up by mistake) |
| Legal / compliance / data privacy | 1 | Shahid (data export for compliance) |
| Strong negative language | 1 | Rabia (WA: "worst ever!! nothing works") |
| Account access / security / SSO | 2 | Farah (SSO setup), Zara (WA: session expired) |
| Explicit "human/manager" requests | 0 | None in dataset |
| Out-of-scope feature requests | 3 | Imran (white-label), Hamza (time tracking), Fahad (mobile app) |
| Security — user removal | 1 | Shahzad (departed employee access) |
| **Total** | **13 / 52** | **25%** |

### Escalation by Channel
| Channel | Escalation Tickets | % of Channel |
|---|---|---|
| Email | 7 | 38.9% |
| WhatsApp | 3 | 16.7% |
| Web Form | 3 | 16.7% |

Email is the escalation-heavy channel, aligning with its more formal, business-critical nature.

---

## 6. Hidden Requirements & Edge Cases

### 6.1 Follow-Up Detection
- **2 explicit follow-ups:** Ayesha Siddiqui ("Still can't invite team members. I tried the steps you gave yesterday"), Yousuf ("Still no AI insights showing up")
- Both reference unresolved previous tickets
- **Hidden need:** System must detect follow-ups via "Re:", "Follow-up:", "Still can't", "previous ticket" patterns
- **Implicit follow-ups:** Bilal (WA: "thanks! it worked"), Saima (WA: "thanks for the help earlier") — reference prior conversations positively

### 6.2 Multi-Intent Tickets
- **Usman (email):** CSV export + recurring tasks (2 how-tos)
- **Saad (web):** Appreciation + feature request in one message
- **Maira (web):** Positive feedback + feature suggestion
- **Hidden need:** Classifier must handle 2+ intents per ticket and respond to all

### 6.3 Positive Feedback Handling
- **6 appreciation messages** (12% of dataset)
- Bot must NOT respond to "thanks" with a help article
- Needs acknowledgment + relationship-building responses
- 3 from WhatsApp, 3 from email, 0 from web form

### 6.4 Urgency Detection
- **Explicit urgency:** Shahzad ("Urgent:"), Zara ("urgent!!")
- **Implicit urgency:** Omar ("task disappeared"), Ibrahim ("board keeps crashing"), Ali ("everyone is complaining" = systemic issue)
- **Hidden need:** Urgency is contextual, not just lexical. "Everyone is complaining" is more urgent than "urgent!! session expired" because it indicates multi-user impact

### 6.5 Graduated Sentiment
- "Very annoying" (Osama, web) — understated
- "This is very frustrating" (Hassan, email) — moderate
- "worst ever!! nothing works" (Rabia, WA) — extreme
- **Hidden need:** Sentiment analysis must detect graduated frustration levels, not binary positive/negative. Escalation rules reference "sentiment score below 0.3 for two consecutive messages"

### 6.6 Limitation Awareness
- Product docs explicitly list: no built-in time tracking, no native mobile app, no white-labeling in Pro
- Bot must NEVER promise these features
- Must deflect gracefully without sounding dismissive

### 6.7 Session / Context Management
- Follow-ups reference "yesterday" and "previous ticket"
- WhatsApp users reference prior help ("thanks for the help earlier")
- **Hidden need:** System needs conversation threading within a session

### 6.8 Domain-Tier Inference
- Email domains reveal company type: techcorp.com, startup.io, agency.com, corp.com, consulting.pk, freelance.dev, marketing.pk
- An Enterprise-domain email asking about Free plan = upsell opportunity
- **Hidden need:** Domain analysis can inform plan-tier awareness

---

## 7. Time Pattern Analysis

### Message Volume by Day
| Date (2026) | Day | Count |
|---|---|---|
| Apr 5 | Sunday | 3 |
| Apr 6 | Monday | 6 |
| Apr 7 | Tuesday | 6 |
| Apr 8 | Wednesday | 5 |
| Apr 9 | Thursday | 5 |
| Apr 10 | Friday | 6 |
| Apr 11 | Saturday | 5 |
| Apr 12 | Sunday | 5 |
| Apr 13 | Monday | 6 |
| Apr 14 | Tuesday | 5 |

**Key:** 7-day coverage required — no day has zero messages.

### Time-of-Day Distribution
| Time Window | Count | Pattern |
|---|---|---|
| 08:00–09:59 | 9 | Morning spike — email-dominant (8 of 18 emails) |
| 10:00–11:59 | 13 | Peak hours — all channels active |
| 12:00–13:59 | 6 | Lunch dip |
| 14:00–15:59 | 16 | Afternoon peak — busiest window |
| 16:00–17:00 | 5 | End-of-day wrap |

### Channel Timing Behavior
- **Email:** Concentrated at work-start (08:xx–09:xx) and mid-morning (13:xx–14:xx)
- **WhatsApp:** Distributed throughout the day — real-time, sporadic usage
- **Web Form:** Peaks 10:00–16:00 — business hours usage

### Follow-Up Gap
- Ayesha's follow-up: ~24 hours after original ticket
- Yousuf's follow-up: ~3 days after original ticket
- **Implication:** 1-3 day resolution expectation

---

## 8. Metadata Analysis

### Email Metadata
```json
{ "subject": "Team invitation question" }
{ "subject": "Re: Team invitation issue" }
```
- Subject line is a strong intent signal ("Pricing inquiry", "Refund request", "Thank you")
- "Re:" prefix signals conversation threading
- Customer email domain reveals company type — useful for plan-tier inference
- Full names consistently present — personalization possible

### WhatsApp Metadata
```json
{ "wa_id": "923001234567" }
```
- Consistent Pakistani phone format (+92 prefix)
- Persistent identifier for repeat contacts
- No category or subject — all classification must be inferred from message text
- First names mostly — less formal

### Web Form Metadata
```json
{ "category": "technical" }
{ "category": "bug_report" }
{ "category": "feature_request" }
{ "category": "general" }
{ "category": "feedback" }
{ "category": "integration" }
```
- **Only channel with pre-classified intent**
- Categories used: technical (4), bug_report (4), general (4), feature_request (2), feedback (2), integration (1)
- Category field should be the PRIMARY routing signal for web_form tickets
- Customer email present — allows follow-up via email if needed

---

## 9. Recommended Architecture

```
┌─────────────────────────────────────────────────────┐
│                  INGESTION LAYER                     │
│  Email API │ WhatsApp API │ Web Form Webhook         │
└──────────┬──────────┬──────────────┬────────────────┘
           │          │              │
           ▼          ▼              ▼
┌─────────────────────────────────────────────────────┐
│              NORMALIZATION LAYER                     │
│  • Unified ticket schema                           │
│  • Channel metadata mapping                         │
│  • Customer identity resolution (email/wa_id)       │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│           CLASSIFICATION & ROUTING LAYER             │
│  • Intent classification (multi-label)              │
│  • Sentiment analysis (graduated, not binary)       │
│  • Urgency scoring (contextual)                     │
│  • Escalation rule engine                           │
│  • Conversation thread detection (session-only)     │
└──────┬───────────────────────┬──────────────────────┘
       │                       │
       ▼ (handle)              ▼ (escalate)
┌──────────────────┐   ┌──────────────────────────────┐
│ RESPONSE ENGINE  │   │   HUMAN HANDOFF              │
│ • KB lookup      │   │   • Write to DB              │
│ • Step-by-step   │   │     status='escalated'       │
│ • Bug ticketing  │   │   • No Slack/dashboard       │
│ • Feature logging │   │     (prototype scope)         │
│ • Appreciation   │   │                              │
│ • Limitation deflection                          │
└────────┬─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│              RESPONSE DELIVERY LAYER                 │
│  • Channel-specific formatting (Email vs WhatsApp)  │
│  • Brand voice injection                            │
│  • Next-step/question append                        │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│              MEMORY & CONTEXT STORE                  │
│  • Session-based conversation history               │
│  • Resolution state tracking                        │
│  • Follow-up detection                              │
│  • Customer profile (plan tier, company, history)   │
│  • Stage 2: PostgreSQL persistence                  │
└─────────────────────────────────────────────────────┘
```

---

## 10. Architectural Decisions (Locked)

| Decision | Choice | Rationale |
|---|---|---|
| **LLM** | OpenAI GPT-4o | Hackathon requirement |
| **Framework** | OpenAI Agents SDK | Minimal dependencies |
| **Knowledge Base** | System prompt (prototype) | Product docs + escalation rules loaded into prompt. RAG with pgvector in Stage 2 |
| **Brand Voice** | System prompt (always) | Non-negotiable, must be in every call |
| **Conversation Memory** | Session-only (prototype) | PostgreSQL persistence in Stage 2 |
| **Human Handoff** | DB write, status='escalated' | No Slack, no dashboard — prototype scope |
| **Response Generation** | Fully AI-generated, direct send | No human approval step |
| **Multi-Intent** | Single response covering all intents | Keep it simple |
| **Bug Report Flow** | Clarify + create ticket simultaneously | Both actions |
| **Proactive Features** | None — strictly reactive | Scope control |

---

## 11. Open Questions for Stage 2

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

## 12. Summary of Key Findings

1. **25% escalation rate** — the bot must handle ~75% of tickets autonomously with a clean handoff path for the rest.
2. **WhatsApp is the emotional channel** — highest positivity AND highest negativity. Abbreviation-heavy, emoji-using, lowercase-dominant. Response style must be short and warm.
3. **Email is the escalation-heavy channel** (38.9% of its tickets) — carries compliance, security, Enterprise pricing, and refund requests. Response style must be structured and professional.
4. **Web form is the structured channel** — pre-categorized, professional, lowest escalation. The `category` metadata should shortcut intent classification.
5. **Follow-up detection is critical** — unresolved previous tickets reference "yesterday" and "Re:" patterns. Session-level threading is needed.
6. **3 repeat out-of-scope features** — mobile app, white-label, time tracking. The bot must deflect gracefully without promising.
7. **Multi-intent handling needed** — ~8% of tickets combine 2+ intents.
8. **7-day coverage needed** — messages arrive on weekends with no zero-volume days.
9. **Urgency is contextual, not just lexical** — "everyone is complaining" signals systemic impact and is more urgent than "urgent!! session expired".
10. **Graduated sentiment detection required** — escalation rules reference consecutive low-sentiment messages, so the system must track sentiment over time within a session.

---

*End of Discovery Log. Next phase: Prototype build upon user signal.*
