# AI features and automated decisions

POPIA doesn't mention "AI", but every condition applies to AI features. The Regulator's chairperson has framed POPIA and AI as "frenemies": AI wants large datasets, opaque logic and automated decisions; POPIA requires minimality, openness and limits on solely automated decisions (s71). Watch `10-regulatory-watch.md` for any AI-specific guidance before relying on this file alone.

## Map of risks

| AI pattern | POPIA hooks | Default control |
|---|---|---|
| Chatbot / support agent receiving user messages | s18 notice, s20/21 operator, s72 transfer, s14 retention | Notice that an AI processes messages; provider DPA; zero/limited retention where available; transcript retention policy |
| Sending user records to an LLM for summarising/enrichment | s10 minimality, s15 further processing, s72 | Send minimum fields; pseudonymise IDs; no special PI unless s27 ground |
| RAG over internal docs containing PI | s19 access control, s14 | Index respects source permissions; delete from vector store when source deleted |
| Training/fine-tuning on customer data | **s15** (compatible purpose?), s13, s18, s26 | Separate consent or robust compatibility assessment; de-identify; exclude special PI and children |
| Scoring/ranking people (leads, credit, hiring, fraud, pricing) | **s71**, s11, s18 | Human review before decisions with legal/substantial effect; explain logic; route to object/represent |
| Voice agents / call recording / voice cloning | s18, s69 (outbound calls), **biometrics** (voice prints) | Disclosure at call start; consent for recording; don't create voiceprints without s27 ground |
| Face detection / recognition / liveness | **Biometrics (special PI)**, s57 | Explicit consent, vendor no-retention, PIA, attorney review |
| AI-generated outbound marketing (email/WhatsApp/calls) | **s69** | Same consent rules as human-sent marketing |
| Agents with tool access to CRM/DB | s19, s20 | Least-privilege tokens, read-only by default, audit logs, human approval for exports/sends |
| Prompt logs and observability (Langfuse, Helicone) | s14, s19, s72 | Redact PI; retention limits; access control |

## s71 automated decisions (detail)

Applies when **all** are true: a **decision** is made about a person; it has **legal consequences** or **affects them to a substantial degree**; it's based **solely** on automated processing; that processing builds a **profile** (work performance, creditworthiness, reliability, location, health, preferences, conduct).

Permitted only if (s71(2)):
- it's taken in connection with a **contract** and either the data subject's request was met, or **appropriate measures** protect their legitimate interests; or
- it's governed by a **law or code of conduct** with appropriate measures.

"Appropriate measures" must include (s71(3)): an **opportunity to make representations** about the decision, and **sufficient information about the underlying logic** of the processing.

**Build pattern**
- Add `decision_mode: 'automated'|'human_reviewed'` to decision records.
- For adverse outcomes, route to a human queue before finalising, or provide a "request human review" path.
- Store the main factors behind each decision in plain language (for the explanation duty).
- "Human in the loop" must be meaningful: reviewer can see the inputs and override. Rubber-stamping risks being "solely automated".

## Provider settings checklist

| ID | Check |
|---|---|
| AI-01 | Each AI provider listed as operator; DPA accepted/signed |
| AI-02 | Provider data use for training disabled (API defaults vary; check enterprise/zero-retention options) |
| AI-03 | Region and retention recorded; s72 basis documented |
| AI-04 | Prompts minimised; no ID numbers, account numbers, special PI unless justified |
| AI-05 | Users told when they interact with AI and how their data is used |
| AI-06 | Outputs about people reviewed for accuracy (s16) before use |
| AI-07 | s71 assessment for any scoring/eligibility/ranking feature |
| AI-08 | Model training on customer data has documented s15 compatibility or consent |
| AI-09 | Vector stores and caches follow deletion requests |
| AI-10 | Agent/tool tokens least-privilege; actions logged; human approval for bulk exports and outbound sends |
| AI-11 | Prompt/trace logs redacted and retention-limited |
| AI-12 | Biometric features (face, voice) have s27 ground and attorney review |

## Using AI coding assistants on client projects

When you (or this skill) work on a codebase:
- Don't paste production data, real ID numbers or customer exports into the chat. Use synthetic samples.
- Treat database query tools (MCP connectors to prod DBs) as PI access: read-only, scoped, logged.
- Screenshots of admin panels with real customer data are PI transfers to the AI provider.
