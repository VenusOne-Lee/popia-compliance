# Stack playbooks

Stack-specific checks and fixes. Each section: **what goes wrong**, **check**, **fix**.

## Contents
1. Supabase and Lovable (Lovable Cloud)
2. Next.js / React / Vite frontends
3. Firebase
4. WordPress and WooCommerce
5. Salesforce
6. Mobile (React Native / Expo / Flutter / native)
7. No-code and automation (Zapier, Make, n8n, Airtable)
8. WhatsApp, SMS and email platforms
9. AI app builders and agent tools
10. Hosting regions in South Africa

---

## 1. Supabase and Lovable

Lovable projects typically use Supabase (directly or as Lovable Cloud). The anon key ships to the browser by design, so **row-level security is the only thing between the internet and your tables**.

**What goes wrong**
- Tables created without RLS → readable/writable by anyone with the anon key.
- Policies like `using (true)` added "to make it work".
- `service_role` key placed in frontend env (`VITE_SUPABASE_SERVICE_ROLE_KEY`).
- Public storage buckets holding uploads (CVs, ID copies, proof of address).
- Edge functions that trust a `user_id` from the request body instead of the JWT.
- Lead-capture tables (e.g. `audit_leads`) with `insert` open to anon **and** `select` open too.
- Database webhooks sending full rows (PI) to third parties.

**Check**
```sql
-- tables without RLS
select schemaname, tablename from pg_tables
where schemaname = 'public' and rowsecurity = false;

-- permissive policies
select schemaname, tablename, policyname, roles, cmd, qual, with_check
from pg_policies
where schemaname = 'public' and (qual = 'true' or with_check = 'true' or roles @> array['anon']::name[]);

-- public buckets
select id, name, public from storage.buckets where public = true;
```
Also run Supabase's **Security Advisor** (Dashboard → Advisors) and the scanner (`SEC-004`, `SEC-005`, `SEC-002`).

**Fix**
```sql
alter table public.profiles enable row level security;
alter table public.profiles force row level security;

create policy "own profile read" on public.profiles
  for select to authenticated using ((select auth.uid()) = id);
create policy "own profile update" on public.profiles
  for update to authenticated using ((select auth.uid()) = id) with check ((select auth.uid()) = id);

-- lead capture: anon may insert, nobody may read from the client
alter table public.leads enable row level security;
create policy "anon insert leads" on public.leads for insert to anon with check (true);
-- Public insert invites spam and abuse: add a CAPTCHA or Turnstile check in an edge function,
-- or insert through an edge function with rate limiting instead of directly from the browser.
-- Constrain what can be written:
alter table public.leads add constraint leads_email_len check (char_length(email) <= 254);
-- no select policy for anon/authenticated → reads only via service role on the server
```
- Storage: make PI buckets private; serve with `createSignedUrl(path, 60)`.
- Edge functions: derive identity from `supabase.auth.getUser(jwt)`; never from body.
- Put the service role key only in edge function secrets.
- Lovable: add POPIA rules to **project knowledge** (see `adapters/lovable/knowledge.md`) so the agent applies them on every change. Ask Lovable's agent to run its security scan before publishing.
- Region: check which region the Supabase project / Lovable Cloud backend runs in. If not SA, it's a **cross-border transfer** (s72). Record it in the ROPA and privacy notice.

## 2. Next.js / React / Vite frontends

**What goes wrong**: secrets in `NEXT_PUBLIC_*` / `VITE_*`; server actions without auth checks; PI in query strings (`/thank-you?email=`); analytics loaded in `_app`/`layout` before consent; API routes returning whole user objects; `dangerouslySetInnerHTML` with user content; missing security headers.

**Fix**
- Only non-secret config in public env prefixes.
- Every server action / route handler: `const user = await requireUser()` then authorise on the resource.
- Return DTOs, not ORM rows: `select: { id: true, displayName: true }`.
- Headers in `next.config.js`:
```js
async headers() {
  return [{ source: '/(.*)', headers: [
    { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
    { key: 'X-Content-Type-Options', value: 'nosniff' },
    { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
    { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
    { key: 'Content-Security-Policy', value: "default-src 'self'; frame-ancestors 'none'; ..." },
  ]}];
}
```
- Load analytics via a consent-aware wrapper component (see 02-build-patterns.md §4).
- Vite/Lovable static hosts: set headers at the host (Netlify `_headers`, Vercel `vercel.json`, Cloudflare). Lovable-hosted sites: check what headers the platform sets with `site_check.py`; use a custom domain via Cloudflare if you need to add headers.

## 3. Firebase

**What goes wrong**: test-mode rules (`allow read, write: if true;`) shipped to prod; rules checking `request.auth != null` only (any signed-in user reads everyone); Storage rules open; Analytics auto-collecting before consent.

**Fix**
```
rules_version = '2';
service cloud.firestore {
  match /databases/{db}/documents {
    match /users/{uid} {
      allow read, update: if request.auth != null && request.auth.uid == uid;
      allow create: if request.auth != null && request.auth.uid == uid;
      allow delete: if false; // via backend deletion pipeline
    }
  }
}
```
- `setAnalyticsCollectionEnabled(false)` until consent; set Consent Mode defaults.
- Use App Check. Firestore region: `africa-south1` (Johannesburg) is available for Google Cloud; confirm for Firebase products you use.

## 4. WordPress and WooCommerce

**What goes wrong**: form plugins storing submissions forever in `wp_posts`/plugin tables; outdated plugins; admin without MFA; cookie banner plugin that doesn't actually block scripts; WooCommerce orders retained indefinitely; backups on shared hosting in plain zip files in web root.

**Fix**
- WordPress has built-in privacy tools (Tools → Export/Erase Personal Data). Make sure form and CRM plugins register exporters/erasers.
- WooCommerce: Settings → Accounts & Privacy → set retention for inactive accounts, cancelled/failed/completed orders.
- Form plugins: disable "store entries" when the email/CRM handoff is enough; or set auto-delete.
- Cookie consent: use a plugin that **blocks** scripts until consent (test with `site_check.py`: no tracking cookies on first load).
- MFA plugin + limit login attempts; auto-updates for minor/security releases; remove unused plugins/themes.
- Host with SA providers or document s72 basis.

## 5. Salesforce

**What goes wrong**: org-wide defaults Public Read/Write on Contacts/Leads; profiles with View All Data; ID numbers in plain text fields visible to all; Web-to-Lead without consent capture; marketing sends ignoring opt-outs across Account Engagement / Marketing Cloud; sandboxes refreshed with full prod PI; data exports by reports.

**Fix**
- OWD Private for objects with PI; sharing rules and permission sets on least privilege.
- Use **Consent Data Model** (Individual, Contact Point Type Consent, Data Use Purpose) to store s11/s69 consent per channel and purpose.
- **Shield Platform Encryption** or classic encrypted fields for ID numbers; Field-Level Security; mask in list views.
- Data Classification metadata on fields (Compliance Categorization: e.g. tag POPIA).
- Event Monitoring / Field Audit Trail for access to sensitive fields (if licensed).
- Sandboxes: Data Mask before use.
- Retention: scheduled flows or batch Apex to delete/anonymise stale leads.
- Web-to-Lead: add separate marketing opt-in field mapped to consent records; capture notice version.
- Hyperforce region: confirm org location; record s72 basis.

## 6. Mobile (React Native / Expo / Flutter / native)

**What goes wrong**: secrets in the bundle; PI in AsyncStorage/SharedPreferences unencrypted; third-party SDKs (ads, attribution, crash) collecting device IDs and location before consent; over-broad permissions (contacts, location always); screenshots of sensitive screens in app switcher.

**Fix**
- Secure storage: Keychain / Keystore (`expo-secure-store`, `flutter_secure_storage`).
- Request permissions just-in-time with a purpose string; drop unused permissions.
- Initialise analytics/attribution SDKs only after consent; disable IDFA/AAID collection unless needed.
- Certificate pinning for high-risk apps; disable ATS exceptions / cleartext.
- Hide sensitive screens in task switcher (`FLAG_SECURE` on Android).
- App store privacy labels must match actual SDK behaviour.

## 7. No-code and automation (Zapier, Make, n8n, Airtable)

**What goes wrong**: every Zap step copies full PI to another offshore vendor; task history retains PI for months; shared Airtable views are public links; n8n self-hosted with no auth; webhooks unauthenticated.

**Fix**
- Map each automation in the ROPA (source → steps → destinations).
- Pass only required fields; set task history retention to the minimum.
- Airtable: no public shared views of PI; restrict base access.
- n8n: auth on, HTTPS, secrets in credentials store, execution data pruning on.
- Sign or secret-protect webhooks.

## 8. WhatsApp, SMS and email platforms

- WhatsApp Business: template messages for marketing need **s69 consent** (Meta's own opt-in policy is not POPIA consent); store the opt-in with wording and timestamp; honour "STOP".
- SMS (BulkSMS, Clickatell, Twilio): include sender identity and opt-out in every marketing SMS (s69(4)); suppress opted-out numbers globally; WASPA code applies to SA mobile marketing.
- Email (Mailchimp, Brevo, HubSpot, Resend): double opt-in for non-customers; one-click unsubscribe (List-Unsubscribe header); physical/contact address in footer; don't import purchased or scraped lists.
- Transactional vs marketing: keep separate streams and lists. A receipt with a promo banner becomes marketing.

## 9. AI app builders and agent tools

See `08-ai-and-automated-decisions.md`. Short version: don't paste production PI into prompts, set the provider to zero/limited retention where offered, record the provider as an operator and a cross-border transfer, and keep humans in loop for decisions about people.

## 10. Hosting regions in South Africa

Keeping data in SA avoids s72 analysis for that store (operators still need s21 contracts). Commonly available SA regions (verify current availability for each service you use):

| Provider | SA region(s) |
|---|---|
| AWS | `af-south-1` (Cape Town) |
| Microsoft Azure | South Africa North (Johannesburg), South Africa West (Cape Town) |
| Google Cloud | `africa-south1` (Johannesburg) |
| Oracle Cloud | Johannesburg |
| Huawei Cloud | Johannesburg |
| Local providers | Teraco-hosted providers, Afrihost, Hetzner SA, xneelo and others |

Not every managed service (Supabase, Vercel functions, Netlify, PlanetScale, Neon, OpenAI, Anthropic, etc.) offers an SA region. Check the vendor's current region list. If none, it's a transfer: document it.
