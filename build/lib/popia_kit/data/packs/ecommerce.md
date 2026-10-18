> Engineering and compliance guidance, not legal advice. See DISCLAIMER.md.

# E-commerce pack

**Last reviewed:** 2026-10-18. **Checklist prefix:** `ECM-`.

Status key: **In force** · **Published, not in force** · **Draft** · **Disputed / in court** · **VERIFY** (no primary source confirmed)

## 1. Who it's for

Online stores (Shopify, WooCommerce, Takealot sellers with their own site, custom Next.js stores), marketplaces, subscription boxes, food and grocery delivery, digital product sellers, and agencies building checkout, CRM, email and loyalty flows for them.

Payment card handling is covered in more depth in `fintech.md`. Marketing rules are in `references/05-direct-marketing.md`. This pack adds the e-commerce specifics.

## 2. Laws beyond POPIA

| Law or instrument | What it means for builders | Status | Primary source |
|---|---|---|---|
| **ECTA 25 of 2002 s43(1)** | Suppliers selling goods or services by electronic transaction must show on the website: (a) full name and legal status; (b) physical address and phone number; (c) website and email address; (d) self-regulatory or accreditation memberships; (e) codes of conduct; (f) for legal persons, registration number, office bearers and place of registration; (g) physical address for service of legal documents; (h) main characteristics of the goods or services; (i) full price including transport, taxes and fees; (j) manner of payment; (k) terms and guarantees and how to access, store and reproduce them; (l) dispatch or delivery time frame; (m) how and how long the consumer can access a full record of the transaction; (n) return, exchange and refund policy; (o) any ADR code; (p) **security procedures and privacy policy for payment, payment information and personal information**; (q) minimum duration of recurring agreements; (r) consumer rights under s44. | In force | acts.co.za |
| **ECTA s43(2) to (4)** | Let the consumer review the whole transaction, correct mistakes and withdraw before the final order. If s43(1) or (2) is not met, the consumer may cancel within 14 days of receiving the goods or services. | In force | Act text |
| **ECTA s43(5) and (6)** | Use a payment system that is sufficiently secure by accepted technological standards. The supplier is liable for damage caused by failing to do so. | In force | Act text |
| **ECTA s44** | Cooling-off rights for electronic transactions (commonly cited as 7 days). | In force (period VERIFY) | Act text |
| **ECTA s45** | Unsolicited commercial communications must offer an opt-out and identify the source. POPIA s69 opt-in is stricter. | In force | Act text; `references/01-popia-legal-map.md` |
| **Consumer Protection Act 68 of 2008 s11** | Right to refuse, stop and pre-emptively block direct marketing; marketers must not contact people who asked to stop or registered a block; no fee. The 2026 block register applies (see regulatory watch). Registration on the register does not replace POPIA consent. | In force | acts.co.za |
| **CPA s12** | Regulation of time for contacting consumers (prescribed hours for direct marketing contact). | In force (hours VERIFY in CPA Regulations) | Act text |
| **CPA s16** | Cooling-off period after a transaction resulting from direct marketing. | In force (period VERIFY) | Act text |
| **CPA s20** | Consumer's right to return goods. | In force | Act text |
| **CPA s22** | Information in plain and understandable language. Applies to notices and consent wording. | In force | Act text |
| **CPA s35** | Customer loyalty programmes. | In force (detail VERIFY) | Act text |
| **CPA s36** | Promotional competitions. Entry data is PI. | In force | Act text |
| **CPA s41** | False, misleading or deceptive representations. Fake reviews and fake scarcity are a CPA risk. | In force | Act text |
| **PCI DSS v4.0.1** | Card data rules via your acquirer; SAQ A eligibility since January 2025 requires the whole site to be protected against malicious scripts. | In force (contractual) | pcisecuritystandards.org |
| **POPIA s69 and Reg 6 / Form 4** | Electronic marketing needs opt-in, or the s69(3) customer exception. Abandoned cart and "back in stock" messages are the grey zone (see below). | In force | Act text |

## 3. Data categories and risk

| Data | Examples | Risk | Why |
|---|---|---|---|
| Card and payment data | PAN, CVV, EFT proof, bank details for refunds | **Critical** | s105, s106; PCI DSS; ECTA s43(5) |
| Account credentials | Passwords, session tokens | **Critical** | s19 |
| Delivery data | Name, address, phone, delivery notes ("gate code 1234", "leave with domestic worker") | High | Physical security; shared with couriers |
| Order history | Products bought | Medium to high | Can reveal health, religion, sex life (pharmacy, adult, religious goods) |
| Marketing and behavioural data | Email opens, browsing, cart contents, segments | Medium | s69; profiling; s18 |
| Reviews | Name, photo, text, location | Medium | Published PI; s11 |
| Loyalty data | Points, tiers, linked cards, purchase profile | Medium | Profiling; s15 |
| ID numbers | For age-restricted goods or credit | High | Collect only where law requires (s10) |

## 4. Top 10 risky patterns builders ship

1. **Abandoned cart emails to people who never opted in.** A visitor who typed an email but did not buy is not a "customer" under s69(3), because the details were not obtained "in the context of the sale". Treat the email as a prospect: you need consent. VERIFY whether a started checkout counts as "in the context of the sale". Default to consent.
2. **Pre-ticked "send me offers" at checkout** or "by placing an order you agree to receive marketing" (s69; Reg 6; CON-002, CON-003).
3. **Meta Pixel, TikTok Pixel and Google Ads tags firing before consent**, often with enhanced matching that sends hashed email and phone (s69 guidance; s72; CON-001).
4. **Server-side tracking (Meta CAPI, GTM server)** sending purchase data with email and phone to ad platforms with no consent check. Hashing is not anonymisation.
5. **ECTA s43 page missing** or incomplete: no physical address, no registration number, no security and privacy statement. The consumer may cancel within 14 days (s43(3)).
6. **Courier integrations that send more than needed:** full order contents, customer ID number, or email address to every courier (s10, s20, s21).
7. **Order data from pharmacy, adult or religious products used for ad audiences** (s26 special PI by inference, s15).
8. **Reviews published with full names and photos** without telling the reviewer, or reviews imported from another platform (s11, s12, s18; CPA s41 if faked).
9. **Loyalty programme T&Cs that bundle marketing consent** and data sharing with "partners" (s11, s69).
10. **Refund bank details collected by email** and kept in the support desk forever (s19, s14, s105).

## 5. Abandoned cart, back in stock and other grey zones

| Message | Who | Default |
|---|---|---|
| Order confirmation, shipping update, delivery notice | Customer | Transactional. No s69 consent needed. Do not add promotions (DM-12). |
| Abandoned cart reminder | Logged-in past customer with s69(3) opt-out given and not used | Allowed as marketing of own similar products under s69(3), with opt-out in the message |
| Abandoned cart reminder | First-time visitor who typed an email and left | **Needs consent.** Show an unticked opt-in next to the email field, or do not send |
| Back-in-stock alert | Person who asked for it | Allowed for that product (they requested it). Do not reuse the address for general marketing without consent |
| Review request after delivery | Customer | Generally a service message; keep it free of promotions |
| Win-back and birthday offers | Customer | s69(3) only for own similar products, with opt-out on every message; otherwise consent |
| WhatsApp marketing | Anyone | Same s69 rules plus WhatsApp's own opt-in policy |

## 6. Checklist

| ID | Control | POPIA | Evidence |
|---|---|---|---|
| ECM-01 | ECTA s43(1) information published and linked from footer and checkout, including (p) payment security and privacy policy | s18; ECTA s43 | Page URL; screenshot |
| ECM-02 | Checkout lets the customer review, correct and withdraw before final order | ECTA s43(2) | Checkout flow recording |
| ECM-03 | Card data captured by gateway hosted fields, iframe or redirect; no PAN or CVV touches our servers or logs; SAQ type recorded | s19; ECTA s43(5) | Gateway config; SAQ |
| ECM-04 | Marketing opt-in at checkout and sign-up is unticked, separate, and names channels; consent event stored | s69; Reg 6 | Form; consent_events |
| ECM-05 | s69(3) customer exception applied only to own similar products, with opt-out at collection and on every message | s69(3) | Email templates; suppression list |
| ECM-06 | Abandoned cart messages only to consented subscribers or s69(3) customers | s69 | Flow rules in ESP |
| ECM-07 | Ad pixels and server-side conversion APIs gated on marketing consent; no enhanced matching without consent | s69 guidance; s72 | site_check; GTM consent config; CAPI code |
| ECM-08 | Courier and fulfilment partners get only name, address, phone and parcel details; written operator terms | s10, s20, s21 | API payloads; courier DPA |
| ECM-09 | Sensitive product categories excluded from ad audiences and recommendation sharing | s26, s15 | Audience rules |
| ECM-10 | Reviews: reviewer told how review is shown; display first name and initial by default; removal on request | s18, s24 | Review form; moderation runbook |
| ECM-11 | Loyalty programme consent separate from programme terms; partner sharing disclosed and opt-in | s11, s15, s69 | Loyalty sign-up flow |
| ECM-12 | Refund banking details collected through a secure form, not email; deleted after refund | s19, s14, s105 | Refund flow; retention job |
| ECM-13 | Guest checkout available where an account is not needed | s10 | Checkout options |
| ECM-14 | CPA block register and s11 stop requests suppressed across all channels | CPA s11; s11(3) | Suppression process |
| ECM-15 | Delivery notes field warns against entering alarm codes or gate codes, or encrypts and purges after delivery | s19, s14 | Field microcopy; retention |

## 7. Build patterns

### Checkout consent

```tsx
{/* s69 + Reg 6: unticked, separate, names channels. Not tied to placing the order. */}
<Checkbox id="mkt_email" name="marketing_email" defaultChecked={false} />
<Label htmlFor="mkt_email">
  Email me offers and new arrivals from Example Store (Pty) Ltd. I can unsubscribe at any time.
</Label>
<Checkbox id="mkt_wa" name="marketing_whatsapp" defaultChecked={false} />
<Label htmlFor="mkt_wa">Send me offers on WhatsApp.</Label>
```

### Abandoned cart guard

```ts
// s69: decide at send time, not at list-build time.
export async function canSendCartReminder(email: string): Promise<boolean> {
  const consent = await db.consentCurrent(email, 'marketing_email');      // latest event wins
  if (consent?.action === 'granted') return true;
  const customer = await db.customerByEmail(email);                       // s69(3): obtained in context of a sale
  return Boolean(customer?.firstOrderAt && !customer.optedOutAt && customer.optOutOfferedAtCollection);
}
```

### Server-side conversion API with consent

```ts
// Meta CAPI / Google Enhanced Conversions are still processing of PI. Hashing is not anonymisation.
if (order.consent.marketing === true) {
  await sendConversion({ event: 'Purchase', value: order.total, user: { em: sha256(order.email) } });
}
// no consent: send nothing, or an aggregate count with no identifiers
```

### Courier payload

```ts
// s10/s21: minimum fields only
const shipment = {
  recipientName: order.shippingName,
  phone: order.shippingPhone,
  address: order.shippingAddress,
  parcel: { weightKg: order.weightKg, reference: order.shortRef },  // not the product list
};
```

## 8. Retention (verify for your sector)

| Record | Period | Source | Status |
|---|---|---|---|
| Invoices and accounting records | Generally 5 years (tax), 7 years (Companies Act) | Tax Administration Act; Companies Act | Commonly cited norms |
| Transaction record available to the consumer | State how and for how long in the s43(1)(m) notice | ECTA s43(1)(m) | In force (you set the period) |
| Abandoned cart data for non-consented visitors | Delete within days | s14 | Recommended practice |
| Delivery notes and gate codes | Delete after delivery | s14 | Recommended practice |
| Refund bank details | Delete after refund confirmed | s14 | Recommended practice |
| Marketing consent records | While marketing continues plus a proof period | s11(2)(a) | Recommended practice |
| Dormant customer accounts | Define a period (for example 24 months inactive), then notify and delete | s14 | Recommended practice |
| Reviews | While published; delete on request unless a legal reason applies | s14, s24 | Recommended practice |

## 9. Scanner rule ideas

Existing rules cover pre-ticked consent (CON-002), bundled wording (CON-003), trackers without consent (CON-001) and unsubscribe handling (DM-001). Ideas to add:

| Idea | Detects | Severity | Section |
|---|---|---|---|
| No ECTA s43 page | Store repo (Shopify theme, WooCommerce, `/checkout`) with no page containing a registration number pattern and physical address | Medium | ECTA s43 |
| Abandoned cart without consent check | Klaviyo/Mailchimp/Omnisend abandoned checkout flow code with no consent field reference | Medium | s69 |
| CAPI without consent | `graph.facebook.com/.../events` or `fbq('init'` with `em`/`ph` fields and no consent condition nearby | High | s69 guidance; s72 |
| Product list sent to courier | Courier API payloads (`courierguy`, `bobgo`, `shiplogic`, `dawnwing`) including `line_items` | Low | s10 |
| Refund bank details via email | Templates asking customers to "email your bank details" | Low | s19, s105 |

## 10. Sources

Primary:
- ECTA 25 of 2002, s43 (acts.co.za).
- Consumer Protection Act 68 of 2008, ss 11, 12, 16, 20, 22, 35, 36, 41 (acts.co.za).
- POPIA Act 4 of 2013, ss 10, 11, 15, 18, 19, 26, 69, 72, 105 (gov.za).
- Information Regulator, Guidance Note on Direct Marketing (Dec 2024).
- PCI Security Standards Council, PCI DSS v4.0.1 and SAQ A.

Secondary:
- `references/05-direct-marketing.md` and `references/10-regulatory-watch.md` (CPA block register status).

## 11. Open VERIFY items

- ECTA s44 cooling-off period and scope.
- CPA s16 cooling-off period and CPA Regulations contact hours (s12).
- CPA s35 loyalty programme requirements.
- Whether an abandoned checkout counts as details obtained "in the context of the sale" under s69(3)(a).
