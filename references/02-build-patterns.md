# Privacy-by-design build patterns

Copy-pasteable patterns. Each one names the POPIA section it satisfies so the reason travels with the code.

## Contents
1. Data inventory in the codebase (s17, s13)
2. Collection: forms, notices, minimisation (s10, s12, s18)
3. Consent records (s11, s69, s27, s35)
4. Cookie and tracker gating (s69 guidance, s18)
5. SA ID numbers and other high-risk identifiers (s19, s57, s105)
6. Access control (s19)
7. Encryption and tokenisation (s19)
8. Logging without leaking (s19, s14)
9. Retention and deletion (s14)
10. Data subject rights: access, correction, deletion, objection (s23, s24, s11(3))
11. Children and age gating (s34, s35)
12. Special personal information (s26, s27)
13. Testing and non-production data (s19, s15)
14. Third-party SDKs and webhooks (s20, s21, s72)

---

## 1. Data inventory in the codebase

Keep the inventory next to the schema so it can't drift. One row per PI-bearing table/collection.

```sql
-- s17 documentation / s13 purpose / s14 retention, as data
create table if not exists privacy.data_inventory (
  id                uuid primary key default gen_random_uuid(),
  data_store        text not null,          -- 'public.profiles'
  fields            text[] not null,        -- {'full_name','email','phone'}
  data_subjects     text not null,          -- 'customers', 'employees', 'leads', 'B2B contacts'
  purpose           text not null,          -- s13: specific and explicit
  lawful_basis      text not null check (lawful_basis in
                     ('consent','contract','legal_obligation','data_subject_interest','public_duty','legitimate_interest')),
  special_pi        boolean not null default false,  -- s26
  children          boolean not null default false,  -- s34
  retention         interval not null,      -- s14
  retention_trigger text not null,          -- 'account_closed', 'last_activity', 'created_at'
  operators         text[] not null default '{}',    -- s20/21: who else processes it
  cross_border      text[] not null default '{}',    -- s72: countries
  owner             text not null,
  reviewed_at       date not null default current_date
);
```

Or for non-SQL stacks, a `privacy/inventory.yaml` checked into the repo. The ROPA template (`templates/ropa.csv`) has the same columns.

## 2. Collection: forms, notices, minimisation

**Rules**
- Every field must map to a purpose in the inventory. If it doesn't, delete it (s10).
- Mark optional fields as optional, and say what happens if they're skipped (s18(1)(d)-(e)).
- Show a short notice at the point of collection and link the full privacy notice (s18).
- Don't pre-fill from third-party enrichment silently. If you enrich (e.g. company lookup), disclose the source (s12, s18(1)(a)).

**Pattern (React/TSX)**
```tsx
<form onSubmit={submit}>
  <Label htmlFor="email">Work email</Label>
  <Input id="email" name="email" type="email" required autoComplete="email" />

  <Label htmlFor="phone">Mobile <span className="text-muted">(optional)</span></Label>
  <Input id="phone" name="phone" type="tel" autoComplete="tel" />
  <p className="text-xs">Only used to confirm your appointment by SMS. Leave blank for email only.</p>

  {/* s69: marketing is separate, unticked, optional */}
  <Checkbox id="marketing" name="marketing_opt_in" defaultChecked={false} />
  <Label htmlFor="marketing">
    Send me product news and offers by email. I can unsubscribe at any time.
  </Label>

  {/* s18 notice at collection */}
  <p className="text-xs">
    Venus ARC (Pty) Ltd (trading as Venus One) processes these details to respond to your request.
    See our <a href="/privacy">Privacy Notice</a> for your rights, including the right to object
    and to complain to the Information Regulator.
  </p>
  <Button type="submit">Send</Button>
</form>
```

Anti-patterns to flag: `defaultChecked` on consent, one checkbox bundling T&Cs + marketing, "By continuing you agree to receive marketing", consent hidden in terms.

## 3. Consent records

Consent must be **voluntary, specific, informed** (s1) and the **burden of proof is yours** (s11(2)(a)). Store evidence, not just a boolean.

```sql
create table privacy.consent_events (
  id              uuid primary key default gen_random_uuid(),
  subject_id      uuid not null,                 -- user/lead id
  purpose         text not null,                 -- 'marketing_email','marketing_whatsapp','special_pi_health','analytics_cookies'
  action          text not null check (action in ('granted','withdrawn')),
  notice_version  text not null,                 -- hash or semver of the exact wording shown
  wording         text not null,                 -- the literal text shown
  channel         text not null,                 -- 'web_form','app','form4_email','call_recording'
  source_url      text,
  ip_hash         text,                          -- hashed, not raw, unless you need it
  user_agent      text,
  competent_person_id uuid,                      -- s35: parent/guardian for minors
  created_at      timestamptz not null default now()
);
-- current state view: latest event per subject/purpose wins
create view privacy.consent_current as
select distinct on (subject_id, purpose) subject_id, purpose, action, created_at
from privacy.consent_events
order by subject_id, purpose, created_at desc;
```

Rules:
- Append-only. Never update a consent row. Withdrawal is a new event.
- Withdrawal must be as easy as giving consent (one click, no login wall for unsubscribe).
- Check `consent_current` **at send time**, not at list-build time.
- For s69 non-customers: you may ask **once**. Record `form4_request_sent` and never ask again if refused.

## 4. Cookie and tracker gating

The Regulator's Direct Marketing Guidance Note (Dec 2024) is read by practitioners as bringing cookies and similar tracking used for marketing into the electronic-communications frame. Treat marketing/advertising pixels as needing opt-in, and analytics as needing at least notice plus a choice. Strictly necessary cookies (session, CSRF, load balancing) don't need consent but must be disclosed.

**Pattern: load nothing until consent (vanilla JS)**
```html
<script>
  // categories: necessary (always), analytics, marketing
  function getConsent() {
    try { return JSON.parse(localStorage.getItem('consent_v2')) || null; } catch { return null; }
  }
  function loadScript(src) { const s = document.createElement('script'); s.src = src; s.async = true; document.head.appendChild(s); }
  function applyConsent(c) {
    if (c?.analytics) loadScript('https://plausible.io/js/script.js');            // or GA4 with consent mode
    if (c?.marketing) { /* load Meta pixel, LinkedIn Insight, TikTok here, never before */ }
  }
  const c = getConsent();
  if (c) applyConsent(c); else showBanner(); // banner: "Accept all" and "Reject all" equally prominent + "Choose"
</script>
```

**GA4 / Google tag:** set Consent Mode defaults to `denied` **before** the tag loads:
```js
gtag('consent', 'default', { ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied', analytics_storage: 'denied' });
```

**Server-side tracking (Meta CAPI, GTM server)** is still processing of PI. Same consent applies. Hash isn't anonymisation.

Prefer privacy-friendly analytics (cookieless, EU/SA-hosted, no cross-site tracking) where marketing attribution isn't essential.

## 5. SA ID numbers and other high-risk identifiers

The 13-digit SA ID (`YYMMDD SSSS C A Z`) encodes **date of birth**, **gender** (SSSS < 5000 female), **citizenship status** (C: 0 citizen, 1 permanent resident) and a Luhn check digit. It is a **unique identifier** and enables identity fraud. Treat as high-risk.

**Decision tree**
1. Do you have a legal obligation (FICA, tax, payroll, credit) or is ID verification the service? If no: **don't collect it**. Use email + phone verification, or DOB if age matters.
2. If yes: collect, validate (Luhn + date), **encrypt or tokenise at field level**, show **masked** (`******1234***` or last 4), restrict access to named roles, log every read.
3. Never use ID number as a primary key, a URL parameter, a username, or a join key across systems.
4. Linking ID numbers with other organisations' data for a new purpose may need **s57 prior authorisation**.

Validator + masker: `scripts/sa_id.py` (Python) and the TS port below.

```ts
export function isValidSaId(id: string): boolean {
  if (!/^\d{13}$/.test(id)) return false;
  const yy = +id.slice(0, 2), mm = +id.slice(2, 4), dd = +id.slice(4, 6);
  if (mm < 1 || mm > 12 || dd < 1 || dd > 31) return false;
  const now = new Date().getFullYear() % 100;
  const year = (yy <= now ? 2000 : 1900) + yy;
  const d = new Date(year, mm - 1, dd);
  if (d.getMonth() !== mm - 1 || d.getDate() !== dd) return false;
  if (!['0', '1', '2'].includes(id[10])) return false;
  // Luhn
  let sum = 0;
  for (let i = 0; i < 13; i++) {
    let n = +id[12 - i];
    if (i % 2 === 1) { n *= 2; if (n > 9) n -= 9; }
    sum += n;
  }
  return sum % 10 === 0;
}
export const maskSaId = (id: string) => id.replace(/^(\d{6})\d{4}(\d{3})$/, '******$2'.padStart(10, '*')) // shows last 3
```

Same high-risk treatment for: **bank account numbers and card data** (s105/106 offences; card data also PCI DSS: never store PAN/CVV, use the payment provider's tokens), passport numbers, tax numbers, medical aid numbers, biometric templates.

## 6. Access control

- **Deny by default.** Every table has row-level security (Postgres/Supabase) or rules (Firebase) with an explicit owner policy.
- **Server enforces, client only displays.** Hiding a button is not access control.
- **Least privilege** for staff: role-based, with separate roles for support (masked view) vs compliance (full view, audited).
- **Admin and service keys** live only in server environments (edge functions, backend). Never in `NEXT_PUBLIC_*`, `VITE_*`, `EXPO_PUBLIC_*`, mobile bundles, or browser code.
- **MFA** for every admin, database, cloud, CRM and email account. SSO where possible.
- **Session hygiene:** short-lived access tokens, rotation, HttpOnly + Secure + SameSite cookies, logout invalidates server-side.
- **Rate limit** auth and lookup endpoints (enumeration of emails/IDs is a breach vector).

Supabase specifics in `04-stack-playbooks.md`.

## 7. Encryption and tokenisation

| Layer | Default |
|---|---|
| In transit | TLS 1.2+ everywhere, HSTS with `includeSubDomains`, no mixed content, internal service calls too. |
| At rest | Provider disk encryption (on by default for AWS RDS, Supabase, Azure SQL, GCP). Check backups and object storage too. |
| Field level | High-risk fields (ID numbers, account numbers, health, biometrics) encrypted with app-held keys or KMS envelope encryption; or replaced with tokens from a vault. |
| Search on encrypted fields | Store a keyed HMAC (blind index) for equality lookups, never the plaintext. |
| Passwords | argon2id (preferred), bcrypt (cost ≥ 12), scrypt. Never MD5, SHA-1, unsalted SHA-256. |
| Keys | KMS / secret manager, rotated, never in repo, separate per environment. |

```ts
// Node: AES-256-GCM envelope with a KMS-provided data key
import { createCipheriv, randomBytes } from 'crypto';
export function encryptField(plain: string, key: Buffer) {
  const iv = randomBytes(12);
  const c = createCipheriv('aes-256-gcm', key, iv);
  const ct = Buffer.concat([c.update(plain, 'utf8'), c.final()]);
  return Buffer.concat([iv, c.getAuthTag(), ct]).toString('base64'); // store with key_version
}
```

## 8. Logging without leaking

PI in logs is PI in a second, less-protected database that usually sits with an offshore operator (Datadog, Sentry, Logtail). It also outlives your retention policy.

- Log **IDs and events**, not values: `user 8f2c… updated phone`, not the phone number.
- Redact at the logger, not at each call site:
```ts
const REDACT = /("?(email|phone|mobile|id_?number|idNumber|sa_?id|password|token|authorization|dob|account_?number)"?\s*[:=]\s*)"[^"]*"/gi;
export const safe = (s: string) => s.replace(REDACT, '$1"[REDACTED]"');
```
- Sentry: `sendDefaultPii: false`, `beforeSend` scrubber, disable request body capture on forms.
- Session replay tools (Hotjar, Clarity, LogRocket, PostHog replay): mask all inputs by default, block pages with forms, and gate behind consent.
- Keep a separate **access audit log** for sensitive data (who viewed/exported what, when) with tamper resistance and its own retention.

## 9. Retention and deletion

- Each inventory row has a retention period and a trigger. A scheduled job enforces it.
- Delete means **gone from primary + replicas + search indexes + caches + analytics + data warehouse + backups (on their natural expiry)**. Document the backup expiry window in the privacy notice.
- Where you must keep records (tax, FICA), **restrict and minimise** (s14(6)): strip what isn't legally required.
- De-identification must be robust: remove direct identifiers *and* quasi-identifiers that enable re-identification (DOB + postcode + gender).

```sql
-- Supabase/Postgres: nightly retention with pg_cron
create or replace function privacy.enforce_retention() returns void language plpgsql security definer as $$
begin
  -- leads with no conversion after 12 months
  delete from public.leads where converted = false and created_at < now() - interval '12 months';
  -- closed accounts: de-identify after 90 days, keep invoice totals for tax
  update public.profiles
     set full_name = null, email = null, phone = null, id_number_enc = null, deidentified_at = now()
   where closed_at < now() - interval '90 days' and deidentified_at is null;
  insert into privacy.retention_runs(ran_at) values (now());
end $$;
select cron.schedule('popia-retention', '15 2 * * *', 'select privacy.enforce_retention()');
```

## 10. Data subject rights

Build these into the product, or document a manual process with a target turnaround (aim for 30 days or less, align with PAIA timelines).

| Right | Section | Minimum build |
|---|---|---|
| Confirm whether you hold data | s23(1)(a) | Free. Support inbox + verification step. |
| Access a copy | s23(1)(b) | "Download my data" (JSON/CSV) or manual export. Verify identity first. |
| Correct | s24 | Profile edit + request path for fields the user can't edit. Form 2 accepted. |
| Delete | s24 | "Delete my account" that triggers the deletion pipeline; tell the user what's retained by law and for how long. |
| Object | s11(3) | Objection route (Form 1 accepted, free); stop processing based on (d)/(e)/(f) unless you can justify continuing. |
| Stop marketing | s11(3)(b), s69(4) | One-click unsubscribe in every message; honour across channels. |
| Withdraw consent | s11(2)(b) | Settings toggle per purpose. |
| Complain | s18(1)(h), s74 | Regulator contact details in the notice. |

Identity verification: proportionate. Re-authenticate logged-in users; for others, match on two data points you already hold. **Never** ask for more PI than you hold to verify.

## 11. Children and age gating

- If the service isn't for children: state 18+ in terms, add a neutral age gate (DOB entry without a hint of the threshold), and delete data if you learn a user is a child without consent.
- If it is for children: verifiable parental consent before collection (s35(1)(a)), minimal profile data, no behavioural advertising, no public profiles by default, no direct messaging from strangers, consider prior authorisation for any cross-border transfer of children's data to non-adequate countries (s57(1)(d)).
- Schools, edtech and sports clubs: record the competent person in `consent_events.competent_person_id`.

## 12. Special personal information

Before adding a field for race, religion, health, disability, biometrics, union membership, political views, sex life or criminal record:
1. Identify the s27 ground (usually explicit consent, or a specific authorisation like s29 for EE/B-BBEE reporting or s32 for health practitioners).
2. Make it optional unless the ground makes it necessary.
3. Separate consent checkbox with plain wording of the exact use.
4. Store in a separate table with stricter RLS and field encryption.
5. Exclude from analytics, marketing segmentation and AI training by default.
6. Do a PIA (`templates/pia-template.md`).

Biometrics: selfie liveness and face match are biometric processing. Prefer vendors that don't retain templates, store only the verification result, and contract that the vendor deletes images.

## 13. Testing and non-production data

- **No production PI in dev, staging, preview deployments, demos, fixtures, seed files, screenshots, Loom videos or LLM prompts.**
- Use synthetic data. For SA IDs, generate fake ones that pass Luhn but use an obviously fake date range or mark them in a fixtures folder the scanner ignores.
- If you must use prod-like data, mask it with a one-way pipeline and treat staging with prod-level controls.
- Preview environments (Vercel, Netlify, Lovable previews) are public by default. Don't point them at prod databases.

## 14. Third-party SDKs and webhooks

Every SDK that receives PI makes its vendor an **operator** (s20/21) and usually triggers **s72** (cross-border).
- Add it to the inventory with: purpose, data sent, hosting region, DPA signed (y/n), s72 basis.
- Send the minimum (e.g. user ID not email to analytics).
- Verify webhook signatures; don't put PI in webhook URLs or query strings.
- Review SDK defaults: many auto-capture IPs, device IDs, form fields, or console logs.
- Remove unused SDKs. Every dormant pixel is an ongoing transfer.
