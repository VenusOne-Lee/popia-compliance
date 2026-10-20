# Operators and cross-border transfers (s20, s21, s72)

Most South African apps run on offshore infrastructure. That's legal, but it has to be **documented, contracted and disclosed**.

## Operators (s20, s21)

An **operator** processes PI for you under contract: hosting, database, email, CRM, analytics, payment, support desk, AI APIs, agencies, freelancers.

Requirements:
1. Operator processes only with your **knowledge or authorisation** and treats PI as confidential (s20).
2. **Written contract** requiring the operator to establish and maintain **s19 security measures** (s21(1)).
3. Operator must **notify you immediately** when there are reasonable grounds to believe PI was accessed or acquired by an unauthorised person (s21(2)).
4. You remain accountable. Their breach is your s22 notification.

If you are the agency/builder: for client projects you are often the **operator**, and the client is the responsible party. Put that in your contract, and push the same terms down to your sub-operators (hosting, tools).

Operator agreement checklist: `templates/operator-agreement-checklist.md`.

## Cross-border (s72)

Sending PI to a third party in another country (including storing it on a server abroad operated by someone else) needs one of:

| Ground | Use when | Notes |
|---|---|---|
| s72(1)(a) adequate protection via law / BCRs / **binding agreement** | Default for SaaS vendors | DPA with POPIA-equivalent terms incl. onward transfer. EU GDPR SCCs help but don't cover juristic persons: add a POPIA addendum. |
| (b) **consent** | Small user bases, specific transfers | Must be informed (where, why, risks). Withdrawal breaks it. Not ideal as sole basis. |
| (c) necessary for **contract** with data subject | e.g. booking an overseas hotel for the customer | Narrow: necessity, not convenience. |
| (d) contract in data subject's interest with third party | e.g. international shipping | |
| (e) **benefit** of data subject, impracticable to get consent, likely would consent | Rare | |

Also:
- **Special PI or children's PI** to a country **without adequate protection** → **prior authorisation** under s57(1)(d).
- Disclose transfers in the privacy notice (s18(1)(g)).
- The Regulator has **not** published an adequacy list (as at Oct 2026). Don't assume any country is "adequate" without analysis.

## Common vendors: what to record

Hosting locations change. Treat this as a starting point and confirm each vendor's current region options and DPA.

| Category | Examples | Typical location | Record |
|---|---|---|---|
| Backend / DB | Supabase, Firebase, Neon, PlanetScale, MongoDB Atlas | Region you choose; SA not always available | Region, DPA, s72(a) |
| Hosting / edge | Vercel, Netlify, Cloudflare, Lovable hosting | Global edge + US/EU origin | DPA, logs retention |
| AI APIs | OpenAI, Anthropic, Google Gemini, Mistral, ElevenLabs | Mostly US/EU | Zero/limited retention setting, training opt-out, DPA |
| Email | Resend, SendGrid, Mailchimp, Brevo, Postmark | US/EU | DPA, s69 consent flow |
| CRM | Salesforce, HubSpot, Zoho, Pipedrive | Region per org | DPA, region |
| Analytics | GA4, Meta Pixel, PostHog, Mixpanel, Plausible, Hotjar, Clarity | US/EU | Consent gating, IP handling |
| Errors / logs | Sentry, Datadog, Logtail | US/EU | PI scrubbing |
| Payments | Paystack, PayFast, Yoco, Peach, Stripe | SA or abroad | PCI, DPA |
| Messaging | Twilio, Clickatell, BulkSMS, WhatsApp Cloud API (Meta) | Varies | Consent, DPA |
| Support | Intercom, Zendesk, Freshdesk, Crisp | US/EU | DPA, retention |
| Automation | Zapier, Make, n8n cloud | US/EU | Task history retention |

## Audit checks

| ID | Check |
|---|---|
| XB-01 | Operator register complete (every vendor that touches PI). Start it with `popia-kit operators <path> --format csv` |
| XB-02 | Written s21 terms in place for each operator |
| XB-03 | Operator breach notification duty is "immediately" or a defined short window |
| XB-04 | Hosting country recorded per data store/vendor |
| XB-05 | s72 ground documented per cross-border vendor |
| XB-06 | No special/children's PI to non-adequate countries without s57 authorisation |
| XB-07 | Privacy notice discloses cross-border transfers and protection level |
| XB-08 | Sub-operator (onward transfer) controls in contracts |
| XB-09 | Vendor offboarding: data return/deletion confirmed |
