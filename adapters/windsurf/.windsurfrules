<!-- Generated from adapters/_core.md by scripts/build_adapters.py. Edit the core, not this file. -->
# POPIA privacy and security guardrails

These rules apply whenever you build, change or review anything that touches personal information of people in South Africa: forms, sign-ups, accounts, CRM, analytics, marketing, AI features, uploads, payments. They come from POPIA (Protection of Personal Information Act 4 of 2013) and its Regulations as amended 17 April 2025. Engineering guidance, not legal advice.

Full skill, scanner and references: https://github.com/VenusOne-Lee/popia-compliance

## Always apply when writing code

1. **Minimise (s10).** Every field needs a purpose. Don't collect SA ID numbers unless a law (FICA, tax, payroll, credit) or the core service requires it. Prefer date of birth or an age check.
2. **Lock down access (s19).** Enable row-level security on every Supabase/Postgres table holding personal information, with owner-scoped policies. Never `using (true)` for select/update/delete. Firebase rules compare `request.auth.uid` with the owner. Storage buckets with uploads are private; serve via short-lived signed URLs.
3. **Keep secrets server-side (s19).** No `service_role`, admin or secret keys in client code or in `VITE_`, `NEXT_PUBLIC_`, `EXPO_PUBLIC_`, `REACT_APP_` variables. Derive user identity from the verified session or JWT, never from the request body.
4. **Encrypt (s19).** HTTPS everywhere with HSTS. Field-level encryption or tokenisation for ID numbers, bank details, health data and biometrics. Passwords with argon2id, bcrypt or scrypt only.
5. **Real consent (s11, s69).** Consent checkboxes are unticked by default, separate per purpose and channel, never bundled into terms. Store a consent record: who, exact wording and version, when, how, and withdrawal. Electronic marketing (email, SMS, WhatsApp, push, calls) needs opt-in in a form substantially similar to Form 4, or the existing-customer exception for your own similar products. Opt-out is not consent.
6. **No trackers before consent.** Load analytics and advertising tags (GA4, GTM, Meta Pixel, TikTok, LinkedIn, Hotjar, Clarity) only after opt-in. Set Google Consent Mode defaults to denied.
7. **Notice at collection (s18).** Link the privacy notice beside every form that collects personal information. Say what is optional.
8. **Build in rights (s23, s24, s11(3)).** Export my data, delete my account, correct my details, marketing opt-out on every message, and a way to object.
9. **Retention (s14).** Every table with personal information has a retention period and a scheduled job that deletes or de-identifies it.
10. **No PI in logs, URLs or browser storage (s19).** Log IDs and events, not emails, phone numbers or ID numbers. Never put personal information in query strings. Don't keep tokens or personal information in localStorage.
11. **Third parties (s20, s21, s72).** Every SDK or API that receives personal information is an operator and usually a cross-border transfer. Send the minimum. Tell the user to record it with its hosting country and a written operator agreement. When asked, list every third-party API or SDK the code calls and the personal information each one receives (`python3 scripts/popia_operators.py <path>` if available).
12. **Test data is synthetic.** Never use production personal information in seeds, fixtures, previews, screenshots or prompts.

## Stop and ask the human before

- Collecting **special personal information** (race, religion, health, disability, sex life, trade union, political views, criminal records, **biometrics** such as face or voice matching). Needs a s27 ground, usually explicit consent.
- Processing **children's** information (under 18). Needs a competent person's consent (s35).
- **Automated decisions** about people with legal or significant effect (credit, hiring, eligibility, pricing, fraud blocks). s71 requires human review and an explanation.
- **Linking unique identifiers** with other organisations' data for a new purpose (may need s57 prior authorisation).
- Sending special or children's information **outside South Africa**.
- Anything that looks like a **security compromise** (exposed key, open table, misdirected data). s22 requires notifying the Information Regulator via its eServices portal and affected people as soon as reasonably possible.

## Refuse

Pre-ticked consent, backdating consent, hiding a breach, importing bought or scraped lists for electronic marketing, scraping personal data, or disabling security controls to "make it work". Explain the risk and offer the compliant alternative.

## When asked to audit

Run `python3 scripts/popia_scan.py <path> --format md` if available, triage every finding (confirmed, false positive, needs info), then check what a scanner can't see: Information Officer registration, privacy notice content, PAIA manual, operator agreements, retention, breach plan. Rate findings Critical (data exposed now), High (likely contravention), Medium (weak control), Low, Info. Cite the POPIA section for every finding.

## Style

Cite sections like s69(2). Use South African terms: responsible party, operator, data subject, Information Officer, Information Regulator. Don't claim anything makes a product "compliant". Recommend a POPIA attorney for high-risk processing.
