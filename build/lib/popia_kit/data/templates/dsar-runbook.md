> Draft template. Engineering and compliance guidance, not legal advice. Have it reviewed by a qualified South African privacy attorney before use. See DISCLAIMER.md.

# Data subject request runbook: {{display_name}}

How {{company_legal_name}} handles requests from data subjects to access, correct, delete, object to processing of, or stop marketing with, their personal information.

| Field | Value |
|---|---|
| Request inbox | {{dsar_email}} |
| Owner | {{io_name}} (Information Officer) |
| Backup | {{dsar_backup_owner}} |
| Target response time | {{dsar_sla_days}} days (aim for 30 days or less, aligned with PAIA timelines) |
| Request log | {{dsar_log_location}} |

## Request types

| Request | Section | Form | Fee |
|---|---|---|---|
| Confirm whether we hold PI | s23(1)(a) | None needed | Free |
| Access a copy or description, incl. third parties who had access | s23(1)(b) | None needed (PAIA process may apply) | A fee may apply per PAIA. Give a written fee estimate first. VERIFY current PAIA fees. |
| Correction or deletion | s24 | Form 2 accepted, not required | Free |
| Objection to processing | s11(3) | Form 1 accepted, not required | Free |
| Stop marketing | s11(3)(b), s69(4) | None needed | Free |
| Withdraw consent | s11(2)(b) | None needed | Free |
| Representations on an automated decision | s71(3) | None needed | Free |

Accept requests through any reasonable channel: email, web form, letter, phone, in person. Do not insist on a specific form.

## 1. Intake (day 0)

1. Log the request: date received, channel, requester, request type, systems likely involved.
2. Send an acknowledgement within {{dsar_ack_days}} business days (template A).
3. If the request is unclear, ask for clarification. Log when you asked and when the requester replied.

## 2. Identity verification

- Verify proportionately. Re-authenticate logged-in users.
- For others, match on two data points you already hold (for example: email plus last order number).
- **Never ask for more personal information than you already hold** to verify someone.
- For a request on behalf of someone else, get proof of authority (for example: a signed mandate, or proof of being a competent person for a child).
- Do not ask for ID copies unless you already hold the ID number and need it to match.

## 3. Search

Search every system in the ROPA, including:

- Production databases, replicas and search indexes
- CRM, email platform, support desk, analytics
- File storage, spreadsheets, shared drives, inboxes
- AI tools, vector stores, prompt logs
- Operators who hold the data (ask them under the operator agreement)

## 4. Respond by request type

### Access (s23)
- Confirm, free of charge, whether we hold PI.
- Provide a copy or description in a generally understandable form, plus the identities or categories of third parties who had access.
- Export in a usable format (JSON or CSV) where practical.
- Remove PI of other people before release. Some grounds for refusal under PAIA may apply: get advice before refusing.

### Correction (s24)
- Correct inaccurate, incomplete or misleading PI.
- If you do not agree a correction is due, attach an indication that a correction was requested but not made, where the data subject asks.
- Tell the data subject what action was taken.
- Tell third parties who received the PI, where reasonably practicable and the change affects decisions.

### Deletion (s24)
- Delete or destroy PI that is irrelevant, excessive, out of date, unlawfully obtained, or no longer authorised to be kept.
- Delete from primary systems, replicas, search indexes, caches, analytics, warehouses and operators. Backups age out on their cycle.
- Where a law requires retention (for example tax or FICA records), restrict and minimise instead (s14(6)), and tell the data subject what is kept, why and for how long.

### Objection (s11(3))
- For processing based on s11(1)(d) or (f): stop unless you can show reasonable grounds to continue. Record the reasoning.
- For direct marketing: stop. No balancing.

### Marketing stop (s11(3)(b), s69(4))
- Add to suppression lists in **every** tool and channel promptly.
- Do not send a "sorry to see you go" marketing message.
- Keep only the minimum needed to honour the opt-out.

## 5. Close

- Send the response (templates B to E).
- Log the outcome, date and who handled it (DSP-04).
- Diary a check that deletions or suppressions took effect.

## Response templates

### A. Acknowledgement

> Subject: We received your request
>
> Dear [name],
>
> We received your request on [date] to [access / correct / delete / object to / stop marketing using] your personal information. Our reference is [ref]. To protect your information, we need to confirm your identity: [verification step]. We aim to respond by [date].
>
> {{io_name}}, Information Officer, {{company_legal_name}}, {{io_email}}

### B. Access response

> Dear [name],
>
> We confirm that we hold personal information about you. Attached is [a copy / a description] of it, including the categories of third parties who have had access. [If a fee applies: as set out in our fee estimate of [date].]
>
> If you think any of it is wrong, you can ask us to correct it.
>
> {{io_name}}, Information Officer

### C. Correction or deletion response

> Dear [name],
>
> We have [corrected / deleted] the following information: [list]. [We have kept [records] because [law] requires us to keep them until [date]. We have restricted access to them.] [We have told [recipients] about the change.]
>
> {{io_name}}, Information Officer

### D. Objection response

> Dear [name],
>
> We have stopped processing your personal information for [purpose]. [Or: We have considered your objection. We will continue processing for [purpose] because [reasonable grounds]. You may complain to the Information Regulator.]
>
> {{io_name}}, Information Officer

### E. Marketing stop confirmation

> Dear [name],
>
> We have removed you from all our marketing lists on [date]. You will not receive further marketing from {{company_legal_name}}. You may still receive service messages about your account.
>
> {{io_name}}, Information Officer

Every refusal or partial response must tell the data subject they may complain to the Information Regulator. {{regulator_contact}} Verify current contact details on https://inforegulator.org.za.
