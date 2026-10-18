# POPIA component registry

Drop-in privacy components for South African builders. They work with Lovable, Vite React and Next.js apps that use Tailwind and shadcn/ui, and with Supabase for the backend.

Every item cites the POPIA section it supports. The components handle the engineering. They do not make a product compliant on their own. You still need a privacy notice, a lawful basis for each purpose, operator agreements and a registered Information Officer.

> These components are engineering guidance, not legal advice. See [../DISCLAIMER.md](../DISCLAIMER.md).

## Contents

1. [Items](#items)
2. [Install with the shadcn CLI](#install-with-the-shadcn-cli)
3. [Manual copy](#manual-copy)
4. [Wire it up](#wire-it-up)
5. [Lovable prompt](#lovable-prompt)
6. [Supabase setup](#supabase-setup)
7. [Maintainers: building the registry](#maintainers-building-the-registry)

## Items

| Item | Type | What it does | POPIA |
|---|---|---|---|
| `consent-provider` | component | `ConsentProvider` and `useConsent`. Categories: necessary (always on), analytics, marketing. Versioned by `policyVersion`. Safe `localStorage` that works when storage throws. `onChange` callback to record consent server-side. `openPreferences()`. | s1 consent, s11(2), s69 |
| `consent-banner` | component | Banner with "Accept all" and "Reject all" equally prominent, plus "Choose" for per-category switches. Links to privacy and cookie notices. Keyboard accessible. Also exports `ConsentPreferencesLink` for the footer. | s18, s69, s11(2)(b) |
| `consent-gate` | component | `<ConsentGate category="marketing">` renders children or loads a script only after consent. `loadScript()`. Google Consent Mode v2: `initGoogleConsentMode()` sets everything to denied before tags, `GoogleConsentModeSync` updates on every change. | s69, Direct Marketing Guidance Note (Dec 2024) |
| `consent-system` | component | Provider, banner, gate and consent record helpers in one install. | as above |
| `consent-record` | lib | Types and `buildConsentEvent()` for `privacy.consent_events`. Hashes the exact wording with SHA-256 (SubtleCrypto). | s11(2)(a) burden of proof |
| `marketing-opt-in` | component | Opt-in substantially similar to Form 4. Unticked box per channel (email, SMS, WhatsApp, phone), business identity, what is marketed, how to withdraw. Emits a record with exact wording and wording hash. | s69(1)-(2), Reg 6 / Form 4 |
| `collection-notice` | component | Short notice at collection: who, why, optional or mandatory, cross-border, rights, link to the full notice. | s18 |
| `sa-id-input` | component | SA ID input. Luhn and date validation, masked after blur, a required "why we need it" helper, never logs the value. | s10, s18, s19 |
| `sa-id` | lib | `isValidSaId`, `parseSaId`, `maskSaId`. Port of `scripts/sa_id.py`. | s19, s57 |
| `redact` | lib | `redact()` and `createSafeLogger()`. Scrubs emails, SA ID numbers, SA phone numbers (+27 and 06x, 07x, 08x), card and account numbers, JWTs and API tokens from strings and objects. | s19, s14 |
| `privacy-centre` | component | Settings panel for signed-in users: download my data, delete my account (with confirmation and a note on legally retained data), marketing preferences, withdraw consent, object (Form 1), complain to the Information Regulator. Calls configurable endpoints. | s23, s24, s11(3), s69, s74 |
| `supabase-privacy-schema` | file | Four migrations. Schema `privacy` with `data_inventory`, append-only `consent_events`, `consent_current` view, `dsar_requests` (due 30 days after receipt), `retention_runs`, append-only `access_audit`. RLS enabled and forced on all tables. `enforce_retention()` with a guarded pg_cron schedule. `security_report()` for tables without RLS, permissive policies, exposed security definer functions and public buckets. | s11, s14, s17, s19, s23, s24 |
| `supabase-privacy-functions` | file | Deno edge functions: `dsar-export`, `dsar-delete`, `consent`, `unsubscribe`, plus `_shared/privacy-config.ts`. Identity from the JWT only. CORS allow-list. HMAC-signed unsubscribe tokens with one-click `List-Unsubscribe-Post`. IP hashed with a salt. | s11(2), s19, s23, s24, s69(4) |

Files install to `components/popia/*`, `lib/popia/*` and `supabase/*`.

## Install with the shadcn CLI

Base URL: `https://raw.githubusercontent.com/VenusOne-Lee/popia-compliance/main/registry/r`

```bash
# Consent system (provider, banner, gate, record helpers)
npx shadcn@latest add https://raw.githubusercontent.com/VenusOne-Lee/popia-compliance/main/registry/r/consent-system.json

# Forms
npx shadcn@latest add https://raw.githubusercontent.com/VenusOne-Lee/popia-compliance/main/registry/r/marketing-opt-in.json
npx shadcn@latest add https://raw.githubusercontent.com/VenusOne-Lee/popia-compliance/main/registry/r/collection-notice.json
npx shadcn@latest add https://raw.githubusercontent.com/VenusOne-Lee/popia-compliance/main/registry/r/sa-id-input.json

# Libraries
npx shadcn@latest add https://raw.githubusercontent.com/VenusOne-Lee/popia-compliance/main/registry/r/redact.json
npx shadcn@latest add https://raw.githubusercontent.com/VenusOne-Lee/popia-compliance/main/registry/r/sa-id.json

# Account
npx shadcn@latest add https://raw.githubusercontent.com/VenusOne-Lee/popia-compliance/main/registry/r/privacy-centre.json

# Supabase migrations and edge functions
npx shadcn@latest add https://raw.githubusercontent.com/VenusOne-Lee/popia-compliance/main/registry/r/supabase-privacy-schema.json
npx shadcn@latest add https://raw.githubusercontent.com/VenusOne-Lee/popia-compliance/main/registry/r/supabase-privacy-functions.json
```

Individual pieces are also available: `consent-provider.json`, `consent-banner.json`, `consent-gate.json`, `consent-record.json`.

The CLI installs the shadcn primitives each item needs (`button`, `checkbox`, `dialog`, `input`, `label`, `switch`). The Supabase items use `~/` targets so they land in your project root `supabase/` folder. Rename the migration files if your timestamps clash.

## Manual copy

If you cannot run the CLI:

1. Make sure these shadcn primitives exist under `src/components/ui/` (or `components/ui/`): `button`, `checkbox`, `dialog`, `input`, `label`, `switch`. Add any that are missing with `npx shadcn@latest add button checkbox dialog input label switch`.
2. Check that the `@/` alias points at your source root (`tsconfig.json` paths and the Vite or Next.js alias). Lovable and shadcn projects have this by default.
3. Copy the files:

| From `registry/popia/` | To your app |
|---|---|
| `consent/*.tsx` | `src/components/popia/` |
| `forms/*.tsx` | `src/components/popia/` |
| `account/privacy-centre.tsx` | `src/components/popia/` |
| `lib/*.ts` | `src/lib/popia/` |
| `supabase/migrations/*.sql` | `supabase/migrations/` (prefix with a timestamp, for example `20261018000001_`) |
| `supabase/functions/*` | `supabase/functions/` |

No npm dependencies are needed for the React components beyond React and your shadcn primitives. The edge functions import `npm:@supabase/supabase-js@2.45.4` through Deno.

## Wire it up

### Consent

```tsx
// main.tsx or app/layout.tsx
import { ConsentProvider } from "@/components/popia/consent-provider";
import { ConsentBanner, ConsentPreferencesLink } from "@/components/popia/consent-banner";
import { ConsentGate, GoogleConsentModeSync } from "@/components/popia/consent-gate";
import { buildConsentEvents } from "@/lib/popia/consent-record";
import { supabase } from "@/integrations/supabase/client";

const COOKIE_WORDING = "Analytics cookies: count visits. Marketing cookies: measure and show adverts.";

<ConsentProvider
  policyVersion="2026-10-18"
  onChange={async ({ changed, source }) => {
    // s11(2)(a): keep evidence server-side. Browser storage is not evidence.
    const events = await buildConsentEvents(
      changed.map((c) => ({
        purpose: `${c.category}_cookies`,
        action: c.granted ? "granted" : "withdrawn",
        wording: COOKIE_WORDING,
        channel: source === "withdraw" ? "privacy_centre" : "cookie_banner",
      })),
    );
    await supabase.functions.invoke("consent", { body: { events } });
  }}
>
  <App />
  <GoogleConsentModeSync />
  <ConsentGate category="analytics" src="https://plausible.io/js/script.js" scriptOptions={{ attributes: { "data-domain": "example.co.za" } }} />
  <ConsentBanner companyName="Example (Pty) Ltd" privacyNoticeUrl="/privacy" cookieNoticeUrl="/cookies" />
  <footer><ConsentPreferencesLink /></footer>
</ConsentProvider>
```

If you use the Google tag, put `GOOGLE_CONSENT_DEFAULTS_SNIPPET` (exported from `consent-gate.tsx`) in an inline script above the tag, or call `initGoogleConsentMode()` before any Google script loads.

The `consent` function needs a JWT. For visitors who are not signed in, enable Supabase anonymous sign-ins, or skip server recording for cookie choices and record only signed-in users.

### Forms

```tsx
<form onSubmit={submit}>
  {/* fields */}
  <MarketingOptIn
    business={{ legalName: "Example (Pty) Ltd", contact: "privacy@example.co.za" }}
    marketedGoods="our accounting software and training courses"
    channels={["email", "whatsapp"]}
    onChange={setMarketingRecord}
  />
  <CollectionNotice
    company="Example (Pty) Ltd"
    purpose="to reply to your enquiry"
    privacyNoticeUrl="/privacy"
    optionalMandatoryNote="Fields marked optional can be left blank. Without your email we cannot reply."
  />
  <Button type="submit">Send</Button>
</form>
```

On submit, send only the events where `action === "granted"` to the `consent` function. Offer only the channels you use. If the person is not a customer and declines, do not ask again (s69(2)).

### Privacy centre

```tsx
<PrivacyCentre
  baseUrl={import.meta.env.VITE_SUPABASE_URL}
  headers={{ apikey: import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY }}
  getAccessToken={async () => (await supabase.auth.getSession()).data.session?.access_token}
  companyName="Example (Pty) Ltd"
  privacyNoticeUrl="/privacy"
  objectionFormUrl="/privacy/objection"
  privacyContact="privacy@example.co.za"
  onDeleted={() => supabase.auth.signOut().then(() => (window.location.href = "/"))}
/>
```

Check the Information Regulator complaint link (`regulatorComplaintUrl`) against the Regulator's website before launch.

### Logging

```ts
import { createSafeLogger, redact } from "@/lib/popia/redact";
export const log = createSafeLogger(console);
Sentry.init({ dsn, sendDefaultPii: false, beforeSend: (event) => redact(event) });
```

`redact` is pattern-based. It reduces leakage. Log IDs and events, not values.

## Lovable prompt

Paste this into Lovable chat. It installs the consent system and the privacy centre and applies the database changes.

```text
Add POPIA (South Africa) privacy features to this app using the open-source registry at
https://raw.githubusercontent.com/VenusOne-Lee/popia-compliance/main/registry/r/

1. Fetch these registry item JSON files and create each file in "files" at its "target" path
   (under src/), using the "content" exactly as given. Do not rewrite the logic.
   - consent-system.json
   - privacy-centre.json
   - marketing-opt-in.json
   - collection-notice.json
   - redact.json
   Make sure the shadcn components button, checkbox, dialog, input, label and switch exist.

2. Wrap the app in <ConsentProvider policyVersion="2026-10-18"> in src/main.tsx (or App.tsx).
   Render <ConsentBanner companyName="[LEGAL NAME]" privacyNoticeUrl="/privacy" cookieNoticeUrl="/cookies" />
   and <GoogleConsentModeSync /> inside it. Add <ConsentPreferencesLink /> to the footer.
   Load every analytics or marketing script only through <ConsentGate>. Remove any tracking
   script that loads before consent. Accept all and Reject all must stay equally prominent.

3. Apply the migrations from supabase-privacy-schema.json (schema "privacy", in order 0001, 0002, 0003, 0004).
   Then run select * from privacy.security_report(); and show me any critical or high rows.
   Do not weaken any RLS policy or grant. Do not add update or delete policies to consent_events.

4. Create the endpoints from supabase-privacy-functions.json: dsar-export, dsar-delete,
   consent, unsubscribe and _shared/privacy-config.ts.
   If this project can't create Supabase Edge Functions (Lovable's TanStack Start stack can't),
   port them to server routes under /api/privacy/ instead: identity only from the verified access
   token, the service role client imported only inside server handlers, and every check in
   privacy-config.ts kept. Point PrivacyCentre's endpoints prop and the consent calls at them.
   Edit PRIVACY_TABLES to list this app's real tables that hold personal information, with the
   user id column and whether to delete, de-identify or retain each one. The unsubscribe endpoint
   must not require a login. If a secret is missing, the endpoints must refuse to run.
   Ask me for these secrets: ALLOWED_ORIGINS, CONSENT_IP_SALT, UNSUBSCRIBE_SECRET.

5. Add a /settings/privacy page for signed-in users that renders <PrivacyCentre> with the Supabase URL,
   the publishable key as the apikey header, getAccessToken from supabase.auth.getSession(),
   companyName "[LEGAL NAME]", privacyContact "[PRIVACY EMAIL]", objectionFormUrl "/privacy/objection",
   privacyNoticeUrl "/privacy", and sign the user out in onDeleted.

6. On every form that collects personal information, add <CollectionNotice> above the submit button.
   On sign-up and lead forms, add <MarketingOptIn> with the channels we actually use. All boxes unticked.
   Send only granted events to the consent function.

7. Never put the service role key in frontend code. Never trust a user id from a request body.
   Never log emails, phone numbers, ID numbers or tokens. Use createSafeLogger from src/lib/popia/redact.ts.

8. When done, run the security scan and list anything it flags.
```

Replace the bracketed values first. Lovable writes the files through its agent, so review the diff before publishing.

## Supabase setup

1. **Expose the schema** (only if you call `privacy` tables from the browser with `supabase.schema("privacy")`). Dashboard, Project Settings, API, Exposed schemas: add `privacy`. Grants and RLS still decide access. The edge functions use the service role and do not need this.

2. **Apply migrations**

   ```bash
   supabase link --project-ref <ref>
   supabase db push
   ```

   `0002_retention.sql` schedules `privacy.enforce_retention()` nightly at 02:15 UTC if `pg_cron` is installed. If it is not, the migration still succeeds and prints a notice. Enable pg_cron under Database, Extensions, then re-run the `do $$ ... $$` block. Edit the commented example rules to match your `data_inventory` before relying on it.

3. **Set secrets**

   ```bash
   supabase secrets set \
     ALLOWED_ORIGINS="https://example.co.za,https://www.example.co.za" \
     CONSENT_IP_SALT="$(openssl rand -hex 32)" \
     UNSUBSCRIBE_SECRET="$(openssl rand -hex 32)" \
     RECENT_AUTH_MINUTES="15" \
     EXPORTS_PER_HOUR="3"
   ```

   `RECENT_AUTH_MINUTES`: "Delete my account" needs a sign-in within this many minutes, so a stolen session cannot erase an account. When the function answers 401, ask the person to sign in again (password, magic link or OTP) and retry. `EXPORTS_PER_HOUR` limits "Download my data" per person.

   `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are provided to edge functions automatically. Never put the service role key in a `VITE_` or `NEXT_PUBLIC_` variable (s19).

4. **Deploy functions**

   ```bash
   supabase functions deploy dsar-export
   supabase functions deploy dsar-delete
   supabase functions deploy consent
   supabase functions deploy unsubscribe --no-verify-jwt
   ```

   `unsubscribe` must work without a login (s69(4), s11(2)(b)). The HMAC token is its authorisation.

5. **Configure** `supabase/functions/_shared/privacy-config.ts`. The shipped `PRIVACY_TABLES` is an example. List every table that holds a user's personal information, the column holding the user id, export columns, and the deletion strategy: `delete`, `deidentify` (s14(4)) or `retain` with a reason (s14(1)(a), s14(6)). Add storage buckets to `PRIVACY_BUCKETS` if files sit under `<user_id>/`.

6. **Unsubscribe links.** On your server, create a token with `signUnsubscribeToken({ s: userId, p: ["marketing_email"] }, UNSUBSCRIBE_SECRET)` and send these headers with every marketing email:

   ```text
   List-Unsubscribe: <https://<ref>.supabase.co/functions/v1/unsubscribe?t=TOKEN>, <mailto:privacy@example.co.za?subject=unsubscribe>
   List-Unsubscribe-Post: List-Unsubscribe=One-Click
   ```

   `GET` only validates the token, because mail scanners prefetch links. Your `/unsubscribe` page should call `GET`, show one "Unsubscribe" button, and `POST`. Mail providers `POST` directly. Check `privacy.consent_current` at send time and sync opt-outs to every sending tool.

7. **Run the security check** as the database owner in the SQL editor:

   ```sql
   select * from privacy.security_report();
   ```

   Treat each row as a lead. A lead-capture table may allow anon `insert` with check `true`, as long as anon cannot `select`.

8. **Fill `privacy.data_inventory`** with one row per table that holds personal information (s17). Keep it in step with `templates/ropa.csv`.

### What the schema enforces

- RLS enabled and forced on every `privacy` table. Anon has no access to the schema.
- Signed-in users can insert and read only their own consent events and DSAR requests. Column grants stop them setting `ip_hash`, `status` or `due_at`.
- `consent_events` and `access_audit` are append-only. A trigger blocks `update`, `delete` and `truncate`, even for the owner. The only exception is `privacy.redact_consent_events()`, which strips device and network details after an account deletion and keeps the fact of consent.
- `dsar_requests.due_at` defaults to 30 days after receipt.
- `security_report()` and `enforce_retention()` are executable by `service_role` only.

## Maintainers: building the registry

`registry.json` is the source. `r/` is generated and committed so the raw URLs work.

```bash
python3 registry/build.py          # regenerate r/
python3 registry/build.py --check  # CI: exits 1 if r/ is stale
```

Style for all copy and comments: South African English, short declarative sentences, cite POPIA sections, no manipulative UI copy. Mark anything uncertain with `VERIFY`.
