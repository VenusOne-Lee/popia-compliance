> Engineering and compliance guidance, not legal advice. See DISCLAIMER.md.

# Fintech pack

**Last reviewed:** 2026-10-18. **Checklist prefix:** `FIN-`.

Status key: **In force** · **Published, not in force** · **Draft** · **Disputed / in court** · **VERIFY** (no primary source confirmed)

## 1. Who it's for

Builders of lending, payments, wallets, banking-as-a-service, insurance, investment, crypto, buy-now-pay-later, debt collection, credit scoring and KYC onboarding products. Also agencies building apps for banks, insurers, FSPs and credit providers. If the product moves money, extends credit, verifies identity for a regulated client, or stores account or card numbers, use this pack.

Fintech is high-risk territory. `SKILL.md` lists credit, insurance and financial-services products as cases that need a POPIA attorney. Use this pack to build well, and still get legal review.

## 2. Laws beyond POPIA

| Law or instrument | What it means for builders | Status | Primary source |
|---|---|---|---|
| **Financial Intelligence Centre Act 38 of 2001 (FIC Act)**: s21 to s21H customer due diligence; s22 and s22A records; s23 retention; s24 electronic records and third-party storage; s42 Risk Management and Compliance Programme | Accountable institutions must identify and verify clients and keep CDD and transaction records. This is the s11(1)(c) "obligation imposed by law" that justifies collecting ID numbers and proof of address. | In force | Act text (acts.co.za, fic.gov.za) |
| FIC Act s23 | Records kept **at least five years**: CDD records from termination of the business relationship; transaction records from conclusion of the transaction; records behind a s29 report from submission of the report. | In force | FIC Act s23 |
| FIC Act s41A "Protection of personal information" | A FIC Act provision on personal information exists. Its content was not reviewed for this pack. | In force (content VERIFY) | FIC Act |
| FIC Revised Guidance Note 7A | Guidance on CDD and other FICA duties, revised in 2025 to align with the General Law Amendment Act 2022. | In force (guidance). Exact issue date VERIFY | fic.gov.za |
| **National Credit Act 34 of 2005 (NCA)**: s68 confidential treatment; s70 credit bureau information | Anyone who receives, compiles, retains or reports confidential consumer information may use it only for purposes the NCA or other legislation permits, and disclose it only to the consumer, as law requires, on the consumer's instruction, or by court or Tribunal order (s68). s70 limits what credit bureaus may hold and requires them to accept consumer challenges free of charge. | In force | Act text |
| NCA Regulations (GNR 489 of 2006): Reg 17 retention periods; Reg 18(4)(c) employment as a prescribed purpose; Reg 19(12) employer access | Reg 17 sets maximum periods credit bureaus may display and use each category (enquiries 1 year, payment profile 5 years, civil judgments up to 5 years, and so on). Employer access to credit records is limited to positions requiring honesty in handling cash or finances (NCR Circular 01 of 2019). | In force | acts.co.za; ncr.org.za Circular 01 of 2019 |
| **Code of Conduct: Credit Bureau Association (CBA)** under POPIA Chapter 7 | Approved 16 Sep 2022, effective 4 Nov 2022, review 4 Nov 2027. Under s57(3), s57 and s58 do not apply where a code has been issued and is in force for the sector. | In force | inforegulator.org.za (codes of conduct register) |
| **Code of Conduct: Banking Association South Africa (BASA)** | Approved 16 Sep 2022, effective 4 Nov 2022, review 4 Nov 2027. Members report annually to the Regulator. Relevant to s71(2)(b) (decisions governed by a code with appropriate measures). | In force | inforegulator.org.za; banking.org.za |
| **FSCA and PA Joint Standard 2 of 2024**: Cybersecurity and Cyber Resilience Requirements | Commenced **1 June 2025**, with 12 months to comply fully (so full compliance expected by about 1 June 2026). Applies to banks, mutual banks, insurers, market infrastructures, discretionary and administrative FSPs, Category I FSPs doing investment fund administration, retirement funds, OTC derivative providers, s13B administrators and credit rating agencies. Requires cyber governance, security controls, testing, and notifying the regulator of material cyber incidents. | In force | fsca.co.za, resbank.co.za (PA). Commencement confirmed via secondary source (Moonstone); primary notice link VERIFY |
| Joint Notice 2 of 2026 (notification template for Joint Standard 1 of 2023 and Joint Standard 2 of 2024) | Initial notification within **24 hours** of classifying an IT or cyber incident as material (calendar hours, weekends included); update within 14 calendar days; final report within an agreed period. Reported effective 1 Sep 2026. | In force (secondary source; VERIFY against FSCA/PA primary) | Moonstone (secondary) |
| Joint Standard 1 of 2023 (IT governance and risk management) | Companion standard on IT governance for the same institutions. | In force. Commencement date VERIFY | fsca.co.za |
| **SARB Directive No. 1 of 2024**: cybersecurity and cyber resilience within the national payment system | Issued 17 May 2024 under s12 of the National Payment System Act 78 of 1998; effective three months after publication. Applies to payment institutions, operators and payment system FMIs. Material cyber incidents reported to SARB within **24 hours**, full report within **48 hours**, then regular updates. | In force | resbank.co.za (directive PDF) |
| **PCI DSS v4.0.1** (industry standard, contractual via acquirer and card schemes) | Never store full PAN with CVV. Use the gateway's hosted fields or redirect and keep only tokens. Since the January 2025 SAQ A update, merchants on SAQ A must confirm the whole site is protected against malicious scripts. | In force (contractual, not law) | pcisecuritystandards.org |
| **ECTA 25 of 2002 s43(5) and (6)** | Online suppliers must use a payment system that is "sufficiently secure" and are liable for damage caused by failing to do so. | In force | Act text |
| **Cybercrimes Act 19 of 2020 s54** | Reporting duty for financial institutions and ECSPs (SAPS, 72 hours). | Published, not in force (VERIFY) | Act text; see `references/10-regulatory-watch.md` |
| **Tax Administration Act** and **Companies Act** | General record-keeping periods (see retention table). | In force | Act text |

### POPIA sections that bite hardest in fintech

- **s11(1)(c)**: FICA and NCA duties are lawful grounds, but only for what those laws require. Extra fields still need a basis (s10).
- **s15**: KYC data reused for marketing, cross-selling or model training is further processing. Assess compatibility.
- **s57(1)(a)**: Linking ID numbers or account numbers with other organisations' data for a new purpose needs prior authorisation.
- **s57(1)(c)**: Processing for **credit reporting** needs prior authorisation, unless a code of conduct applies under s57(3). The CBA code covers its members. Whether a fintech that shares repayment data with bureaus, or builds its own "alternative data" score sold to others, is doing credit reporting is a legal question: **VERIFY with an attorney** before launch.
- **s71**: Automated credit, fraud and affordability decisions.
- **s72**: KYC vendors, card processors and cloud hosting abroad.
- **s105 and s106**: Offences linked to **account numbers**. s105(5) defines "account number" as a unique identifier assigned by a financial or other institution that lets the data subject access their own funds or credit facilities (or joint funds or credit). s105 applies where the s8 failure is serious or persistent and likely to cause substantial damage or distress, and the responsible party knew or ought to have known of the risk and failed to take reasonable steps. All reasonable steps to comply with s8 is a defence (s105(4)). s106 makes it an offence to knowingly or recklessly obtain, disclose or procure disclosure of an account number without the responsible party's consent, and to sell or offer to sell one. Penalty for s105(1) and s106(1), (3), (4): up to 10 years' imprisonment, a fine, or both (s107(a)).
- **s22**: A breach may need to be reported to the Information Regulator (eServices portal) **and** the FSCA, PA or SARB under their own rules and timelines. These run in parallel.

## 3. Data categories and risk

| Data | Examples | Risk | Why |
|---|---|---|---|
| Account numbers | Bank account, card PAN, wallet ID that accesses funds, loan account | **Critical** | s105, s106 offences; fraud |
| Card data | PAN, expiry, CVV, track data | **Critical** | PCI DSS; ECTA s43(5) |
| Credentials and secrets | Banking API keys, open-banking tokens, PINs, OTPs | **Critical** | s19; account takeover |
| Identity documents | SA ID number, passport, ID copy, proof of address | **High** | Unique identifier; s57(1)(a); identity fraud |
| Biometrics | Selfie liveness, face match, voice ID | **High (special PI)** | s26, s27, s33; non-negotiable in `SKILL.md` |
| Credit information | Bureau reports, scores, judgments, debt review status | **High** | NCA s68, s70; s71 |
| Financial history | Bank statements, income, payslips, transactions | **High** | Profiling; s71; s10 |
| Beneficial ownership and PEP status | Directors, shareholders, PEP flags | **High** | FICA; juristic persons are data subjects |
| Transaction metadata | Merchant, location, device, IP | Medium | Location is PI (s1); fraud models |
| Marketing preferences | Opt-ins, segments | Medium | s69 |

## 4. Top 10 risky patterns builders ship

1. **Full card numbers in the database or logs.** Card fields posted to your own API "to save the card". Use gateway tokens. Never touch CVV (PCI DSS; s19; s105).
2. **Bank account numbers in plaintext columns,** shown in full to support staff and exported to spreadsheets. Encrypt at field level, mask, log every reveal (s19; s105).
3. **ID copies in a public storage bucket,** or uploaded to a bucket with a guessable path. Make it private and serve with short signed URLs (s19).
4. **KYC data reused for marketing** or lookalike audiences without a compatibility assessment or consent (s15, s69).
5. **Auto-decline on a score** with no human review, no explanation and no way to make representations (s71).
6. **Bank statement parsing with an LLM** that sends full statements offshore with default retention (s10, s15, s72; AI-04 in `references/08-ai-and-automated-decisions.md`).
7. **Selfie KYC vendor chosen on price,** with no DPA, unknown template retention and hosting abroad (s27, s33, s21, s57(1)(d) if not adequate).
8. **Credit bureau or KYC API keys in the frontend** or in a no-code automation that anyone in the workspace can see (s19; SEC-002, SEC-003).
9. **Collecting more than FICA needs** "because FICA". Employer, marital status, race, next of kin and full transaction history for a simple wallet (s10). FICA justifies the required CDD fields, not everything.
10. **Breach handled only one way.** The team notifies the Regulator but forgets the FSCA, PA or SARB 24-hour clock, or the reverse (s22; Joint Standard 2 of 2024; SARB Directive 1 of 2024).

## 5. Checklist

| ID | Control | POPIA | Evidence |
|---|---|---|---|
| FIN-01 | Accountable institution status known (FIC Act Schedule 1 or client's status). CDD fields map to FICA duties; extra fields have their own basis | s10, s11(1)(c) | Data inventory with lawful basis per field; FICA RMCP reference |
| FIN-02 | ID numbers, passport numbers and account numbers encrypted or tokenised at field level; masked in UI; reveal is role-limited and logged | s19, s105 | Schema, key management config, access log sample |
| FIN-03 | No PAN, CVV or track data stored or logged. Card capture via gateway hosted fields, iframe or redirect. SAQ type documented | s19; ECTA s43(5) | PCI SAQ or AOC; network capture showing PAN goes to gateway only; scanner PII-003 clean |
| FIN-04 | KYC documents in private storage, short-lived signed URLs, virus scan, no public links | s19 | Bucket policy; storage config |
| FIN-05 | FICA retention runs from relationship end or transaction date (FIC Act s23), then deletion or de-identification job runs | s14 | Retention schedule; job code; run logs |
| FIN-06 | Credit decisions record decision mode, main factors in plain language, and a route to make representations and request human review | s71(2), s71(3) | Decision table; adverse action notice; review queue |
| FIN-07 | Credit reporting assessment done: does the product report to bureaus or sell scores? Prior authorisation or code of conduct position documented | s57(1)(c), s57(3) | Legal memo; Regulator authorisation or code membership |
| FIN-08 | Unique identifier linking across organisations (e.g. matching ID numbers with partners' data for a new purpose) assessed for prior authorisation | s57(1)(a) | PIA; authorisation if needed |
| FIN-09 | Biometric KYC has a s27 ground (usually consent), explicit separate consent, vendor DPA, template and image deletion terms, hosting country and s72 basis | s26, s27, s33, s72 | Vendor DPA; consent record; PIA |
| FIN-10 | Bureau data used only for NCA-permitted purposes, never for marketing; employer checks limited to cash or finance roles | NCA s68; Reg 19(12); s15 | Purpose register; access controls on bureau responses |
| FIN-11 | Incident plan covers Information Regulator (eServices), FSCA/PA (24 hours from classification as material), SARB (24 hours, full report 48 hours) where applicable, card schemes and acquirer | s22 | Incident runbook with all regulators and clocks |
| FIN-12 | Joint Standard 2 of 2024 controls mapped for in-scope clients (governance, testing, third-party risk) | s19(3) | Mapping to `references/03-security-controls.md` IDs |
| FIN-13 | AI or LLM processing of statements, payslips or IDs: minimised fields, zero or limited retention, no training on data, region recorded | s10, s15, s72 | Provider settings; prompt redaction code |
| FIN-14 | Marketing to customers uses s69(3) only for own similar products, with opt-out at collection and on every message; prospects need Form 4-style consent | s69 | Consent records; message templates |
| FIN-15 | Account numbers never in URLs, analytics events, push notification text or SMS bodies beyond last 4 digits | s19, s105 | Code review; analytics event schema |

## 6. Build patterns

### KYC table with field-level encryption

```sql
-- s11(1)(c) FICA CDD; s19 field encryption; s14 retention from relationship end (FIC Act s23)
create table kyc.customer_identity (
  customer_id        uuid primary key references public.customers(id),
  id_type            text not null check (id_type in ('sa_id','passport','asylum_permit')),
  id_number_enc      bytea not null,          -- AES-256-GCM ciphertext, app or KMS key
  id_number_hmac     text  not null unique,   -- keyed HMAC blind index for duplicate checks
  id_last3           text  not null,          -- for masked display only
  id_doc_path        text,                    -- private bucket object key, never a public URL
  verified_at        timestamptz,
  verified_by        text,                    -- vendor or staff id
  relationship_ended_at timestamptz,          -- starts the 5-year FICA clock
  key_version        int not null default 1
);
alter table kyc.customer_identity enable row level security;
alter table kyc.customer_identity force row level security;
-- no client policies: only server-side code with a compliance role reads this table
```

### Account number handling

```ts
// s105: treat account numbers as the highest-risk class. Store token + last4, not the number.
type StoredBankAccount = {
  id: string;
  customerId: string;
  bankCode: string;
  accountLast4: string;      // display: "**** 1234"
  accountToken: string;      // vault or PSP token; plaintext never at rest in app DB
  verifiedVia: 'avs' | 'manual';
};

export const maskAccount = (last4: string) => `**** ${last4}`;
```

### Card capture

```tsx
{/* PCI DSS: card fields are the gateway's iframe. Our server only sees a token. ECTA s43(5). */}
<PaymentElement options={{ layout: 'tabs' }} />
{/* Never: <input name="card_number" /> posted to our own API */}
```

### Credit decision record (s71)

```sql
create table credit.decisions (
  id               uuid primary key default gen_random_uuid(),
  application_id   uuid not null,
  outcome          text not null check (outcome in ('approved','declined','referred')),
  decision_mode    text not null check (decision_mode in ('automated','human_reviewed')),
  model_version    text not null,
  main_factors     text[] not null,      -- plain language, e.g. '{"Income below affordability threshold"}'
  bureau_used      text,
  reviewer_id      uuid,                 -- set when a human reviews
  representations  text,                 -- s71(3)(a): what the applicant said
  created_at       timestamptz not null default now()
);
-- Rule: an automated 'declined' must offer "Ask for a person to review" before it is final (s71(2), s71(3)).
```

Adverse outcome copy (plain language, s71(3)(b)):
> We could not approve your application today. The main reasons were: your monthly income is below what we need for this amount, and your existing repayments are high. You can ask a person to review this decision and tell us anything we should consider. Reply within 30 days or use the "Request review" button.

### Breach routing

```yaml
# incident-routing.yaml - check each that applies. Clocks run in parallel.
information_regulator: { when: "reasonable grounds PI accessed by unauthorised person", how: "eServices portal", clock: "as soon as reasonably possible", ref: "POPIA s22" }
fsca_pa:               { when: "material cyber incident at in-scope FI", clock: "24h from classification as material; update 14 days", ref: "Joint Standard 2 of 2024; Joint Notice 2 of 2026 (VERIFY)" }
sarb:                  { when: "material cyber incident at payment institution, operator or FMI", clock: "24h initial; full report 48h", ref: "SARB Directive 1 of 2024" }
card_schemes:          { when: "suspected card data compromise", how: "acquirer incident process", ref: "PCI DSS" }
```

## 7. Retention (verify for your sector)

| Record | Period | Source | Status |
|---|---|---|---|
| CDD records (ID, verification, business relationship) | At least 5 years from termination of the business relationship | FIC Act s23(a) | In force |
| Transaction records | At least 5 years from conclusion of the transaction | FIC Act s23(b) | In force |
| Records behind a suspicious or unusual transaction report | At least 5 years from submission of the report | FIC Act s23(c) | In force |
| Credit bureau display periods | Enquiries 1 year; payment profile 5 years; civil judgments the earlier of 5 years or rescission; sequestration 5 years or rehabilitation | NCA Reg 17 | In force (applies to bureaus) |
| Credit agreement and application records at the credit provider | Prescribed by NCA regulations | NCA Regulations | VERIFY exact period |
| Tax records | Generally 5 years from submission of return | Tax Administration Act | Commonly cited norm (see `references/01-popia-legal-map.md`) |
| Company accounting records | Generally 7 years | Companies Act | Commonly cited norm |
| Declined applications (no relationship formed) | Shortest period you can justify; VERIFY whether FICA applies to the attempt | s14; FIC Act | VERIFY |
| Biometric images | Delete after verification; keep only result and vendor reference | s10, s14 | Recommended practice |
| Card data | Never store PAN with CVV; keep tokens only | PCI DSS | Contractual |

FICA sets a minimum. After it ends, s14 requires deletion or de-identification unless another ground applies.

## 8. Scanner rule ideas

Existing rules already cover card numbers (PII-003), SA IDs (PII-001), plain high-risk columns (PII-005), service keys (SEC-002) and automated decisions (AI-002). Ideas to add:

| Idea | Detects | Severity | Section |
|---|---|---|---|
| Account number column | `account_number`, `acc_no`, `iban`, `bank_account` columns typed `text`/`varchar` without `_enc`/`_token` suffix | High | s19, s105 |
| CVV persistence | `cvv`, `cvc`, `card_security_code` in schemas, models or logs | Critical | s19; PCI DSS |
| Raw card input posted to own API | `<input name="card_number">` or `cardNumber` in a form that posts to `/api/` | High | s19; ECTA s43(5) |
| Bureau API keys client-side | `TRANSUNION`, `EXPERIAN`, `XDS`, `VERIFYID`, `SMILE_ID` keys with `NEXT_PUBLIC_`/`VITE_` prefix | Critical | s19 |
| Statement upload to LLM | Bank statement or payslip file passed directly to an LLM SDK call | Medium | s10, s15, s72 |
| Decline without review path | `status = 'declined'` set in code with no reference to review, appeal or representations | Low (heuristic) | s71 |

## 9. Sources

Primary:
- POPIA Act 4 of 2013, ss 8, 11, 15, 22, 57, 69, 71, 72, 105, 106, 107 (Government Gazette 37067, gov.za).
- FIC Act 38 of 2001, ss 21 to 24, 41A, 42 (acts.co.za; fic.gov.za).
- National Credit Act 34 of 2005, ss 68, 70; Regulations GNR 489 Reg 17, 18, 19 (acts.co.za); NCR Circular 01 of 2019 (ncr.org.za).
- Information Regulator, Codes of Conduct register: CBA and BASA codes (inforegulator.org.za/codes-of-conducts/).
- SARB, Directive No. 1 of 2024: Cybersecurity and cyber resilience within the national payment system (resbank.co.za).
- FSCA and PA, Joint Standard 2 of 2024 (fsca.co.za).
- ECTA 25 of 2002 s43 (acts.co.za).
- PCI Security Standards Council, PCI DSS v4.0.1 and SAQ A (pcisecuritystandards.org).

Secondary (context only):
- Moonstone: Joint Standard commencement confirmed (1 June 2025); Joint Notice 2 of 2026 incident reporting template.
- Akamai: PCI DSS v4.0.1 SAQ A changes (January 2025).
- Accounting Academy and Acts Online blog: Revised Guidance Note 7A (2025).

## 10. Open VERIFY items

- Primary FSCA/PA notice confirming the Joint Standard 2 of 2024 commencement and Joint Notice 2 of 2026 timelines.
- Joint Standard 1 of 2023 commencement date.
- FIC Act s41A content.
- Revised Guidance Note 7A issue date.
- NCA retention periods for credit provider records.
- Whether a non-bureau fintech's data sharing or scoring is "credit reporting" under s57(1)(c).
- Cybercrimes Act s54 commencement.
