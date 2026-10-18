# Direct marketing (s69, s11(3), Reg 6 / Form 4)

Roughly 10% of complaints to the Regulator concern direct marketing (Aug 2026 briefing). It is the easiest area to get wrong in a lead-gen build, and the first direct-marketing fine (FT Rams Consulting, R100 000) came from ignoring opt-outs.

## Decision flow for any marketing message

```
Is it direct marketing? (promoting goods/services, or requesting donations)
 └─ No → transactional/service message. No s69 consent needed. Don't sneak promos in.
 └─ Yes → Is it by electronic communication? (email, SMS, WhatsApp/IM, push, automated or live calls per Regulator, DMs)
      └─ No (post, in person) → s11 lawful basis (often legitimate interest) + right to object s11(3)(b) + respect objections.
      └─ Yes → s69 applies:
           ├─ Existing customer? (details obtained in context of a sale of a product/service)
           │    AND marketing your own similar products/services
           │    AND given opt-out at collection AND on every message
           │    AND hasn't opted out → ALLOWED
           └─ Otherwise → need prior OPT-IN consent (Form 4 or substantially similar).
                 Never asked before? → may ask ONCE.
                 Asked and refused/ignored? → may not ask again.
```

## What valid s69 consent looks like

- **Opt-in**, separate, unticked, specific to channel(s) and the kind of goods/services.
- Content "substantially similar" to **Form 4**: identity and contact details of the responsible party; the person signing on its behalf (in a web flow, the business identity); the goods/services to be marketed; the channels (SMS, email, fax, phone, other); data subject's choice to consent or not; signature/confirmation and date.
- Amended Regulations (2025): **an opt-out mechanism is not consent**.
- Recorded with wording version, timestamp, channel (see `consent_events` in 02-build-patterns.md).
- Purchased lists, scraped emails, LinkedIn exports, "business cards from the expo" for non-customers: **no consent**. Don't import into marketing tools.

**Web form wording (substantially similar to Form 4)**
> ☐ Yes, Venus One (Pty) Ltd may send me marketing about automation and Salesforce services by **email** and **WhatsApp**. I can withdraw at any time via the unsubscribe link or by emailing privacy@venusone.co.za.

Separate boxes per channel if you want granular consent.

## Every marketing message must include (s69(4))

- Identity of the sender (and on whose behalf).
- An address or contact details where the recipient can send a stop request.
- Practically: one-click unsubscribe (email `List-Unsubscribe` + `List-Unsubscribe-Post`), "Reply STOP" for SMS/WhatsApp, and opt-out honoured across all channels within a short period.

## Calls

The Regulator treats telephone calls (including live calls) as electronic communication. Industry disputes this; OUTsurance and MTN matters were referred to the Enforcement Committee in 2026 and the Regulator expects the question to reach court. **Default: treat calls as s69 until a court says otherwise.**

## CPA block register and ECTA

- **CPA s11** gives consumers the right to block direct marketing. The 2026 CPA amendment regulations introduced a pre-emptive block register. **Registration on that register does not replace POPIA consent** (Regulator, Aug 2026). Scrub against it *and* get consent.
- **ECTA s45** requires an opt-out and source disclosure on unsolicited commercial communications. POPIA's opt-in is stricter for natural persons.

## B2B

Juristic persons are data subjects, and work emails of individuals are personal information. B2B cold email to named individuals is s69 territory. Safer B2B routes: inbound (content, events with opt-in), existing-customer exception, a single Form 4-style consent request where lawful, or non-electronic outreach with a s11 basis.

## Lead generation and profiling

- Lead-gen partners must show you their consent evidence naming **your** business (or a clearly defined category) and channel. Generic "partners" consent is weak.
- Profiling for marketing is processing; disclose it in the notice (s18) and respect objections (s11(3)).
- Lookalike/custom audiences (uploading hashed customer emails to Meta/Google/LinkedIn): disclosure + basis needed; for non-customers or special PI, avoid.

## Checklist IDs (used in audits)

| ID | Check |
|---|---|
| DM-01 | Marketing consent is opt-in, unticked, separate from T&Cs |
| DM-02 | Consent wording substantially similar to Form 4 (identity, products, channels) |
| DM-03 | Consent evidence stored (who, what, when, how, version) |
| DM-04 | Existing-customer exception only used for own similar products, with opt-out at collection and each message |
| DM-05 | Non-customers approached for consent at most once |
| DM-06 | Every message identifies sender and has working opt-out |
| DM-07 | Opt-outs suppressed across all tools/channels promptly |
| DM-08 | No purchased/scraped lists for electronic marketing |
| DM-09 | Calls treated as s69 (or documented legal position) |
| DM-10 | CPA block register checked where applicable |
| DM-11 | Lead-gen partner consent evidence verified |
| DM-12 | Transactional messages don't carry promotional content without consent |
