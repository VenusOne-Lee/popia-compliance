# Start here

Three paths. Pick the one that matches where you are. Each one takes under an hour for a small app.

Engineering guidance, not legal advice. A clean scan is not a compliance certificate. See [DISCLAIMER.md](../DISCLAIMER.md).

| You have | Path |
|---|---|
| A new React, Vite or Next.js app on Supabase | [1. New project](#1-new-project) |
| An existing codebase in any language | [2. Existing project](#2-existing-project) |
| A Lovable project | [3. Lovable](#3-lovable) |

All you need is Python 3.8 or newer. Node is only needed for the components.

Only want to check a live site? Use [popiakit.co.za/check](https://popiakit.co.za/check) in your browser. Nothing to install.

---

## 1. New project

**1. Teach your AI tool the rules.** Copy the matching file from [`adapters/`](../adapters) into your project: `CLAUDE.md`, `.cursor/rules/popia.mdc`, `.github/copilot-instructions.md`, `.windsurf/rules/popia.md`, `GEMINI.md` or `AGENTS.md`. From then on your assistant applies the guardrails without being asked.

**2. Add the components.** They install with the shadcn CLI and compile under strict TypeScript.

```bash
R=https://raw.githubusercontent.com/VenusOne-Lee/popia-compliance/main/registry/r
npx shadcn@latest add $R/consent-system.json $R/marketing-opt-in.json $R/collection-notice.json $R/privacy-centre.json $R/redact.json
```

Wrap your app in `<ConsentProvider policyVersion="...">`, render `<ConsentBanner />`, and load every analytics or marketing script through `<ConsentGate>`. Details: [registry/README.md](../registry/README.md#wire-it-up).

**3. Add the database layer.**

```bash
npx shadcn@latest add $R/supabase-privacy-schema.json $R/supabase-privacy-functions.json
supabase db push
```

Then check it, as `postgres` in the SQL editor:

```sql
select * from privacy.security_report();
```

Fix anything rated critical or high. A lead-capture table that allows anonymous insert, with no anonymous select, is expected.

**4. Deploy the functions** and set their secrets: [registry/README.md, Supabase setup](../registry/README.md#supabase-setup).

**5. Scan before every merge.** Add the GitHub Action:

```yaml
- uses: VenusOne-Lee/popia-compliance@0192dd213a41c62c2cfeb9e11221bad4af7bc729 # v1.0.0
  with: { fail-on: high }
```

**6. Draft the paperwork.**

```bash
uvx popia-kit pack --interactive --out ./compliance-pack
```

Have someone qualified review the drafts before you publish them.

---

## 2. Existing project

**1. Scan.** No install needed:

```bash
uvx popia-kit scan . --format md --out popia-scan.md
```

No `uv`? Use `pipx run popia-kit scan .` or `npx -y github:VenusOne-Lee/popia-compliance scan .`.

**2. Triage.** Every finding is a lead, not a verdict. Mark each one confirmed, false positive or needs info. Silence a confirmed false positive with `popia-ignore: RULE-ID` on the line, or a path in `.popiaignore`.

**3. Fix in this order.**

1. **Critical:** leaked keys (rotate them first), tables without row-level security, open storage buckets. If personal information may already have been exposed, read [references/07-breach-response.md](../references/07-breach-response.md) now. Section 22 may require you to notify the Information Regulator and the people affected.
2. **High:** trackers before consent, pre-ticked boxes, real ID numbers in test data, no privacy notice.
3. **Medium and below:** in your normal backlog.

**4. Check the live site** you own:

```bash
uvx popia-kit site-check https://your-site.co.za --out site-check.md
```

**5. Check the database** if you use Supabase. The scanner reads your migrations. This reads the live settings: tables open to the anon key, policies that let everyone in, views over `auth.users`, exposed functions and public buckets. It reads the system catalogs only, never your data, and changes nothing.

```bash
uvx popia-kit supabase sql > inventory.sql
```

Paste `inventory.sql` into the Supabase SQL editor and run it. Save the single value it returns as `result.json` (a CSV download works too), then:

```bash
uvx popia-kit supabase check result.json --format md --out supabase-check.md
```

With `psql` installed you can skip the copy and paste: set `SUPABASE_DB_URL` to the connection string from Project settings, Database, then run `uvx popia-kit supabase run`. The session is read-only.

**6. Stop it coming back.** Add the GitHub Action from path 1, step 5, or the pre-commit hook in [docs/automation.md](automation.md).

**7. Fill the gaps the scanner can't see:** Information Officer registration, privacy notice content, PAIA manual, operator agreements, retention, breach plan. The compliance pack drafts most of them: path 1, step 6.

---

## 3. Lovable

Tested on 18 October 2026 in a fresh Lovable project with Lovable Cloud: the database rules on the live database, the privacy endpoints and the component tests.

**1. Add the knowledge.** Paste [`adapters/lovable/knowledge.md`](../adapters/lovable/knowledge.md) into Project settings, Knowledge. Lovable then applies the rules on every change.

Workspace admins can add it once for every project instead: create a workspace skill named `popia-kit` from [`adapters/lovable/skill/SKILL.md`](../adapters/lovable/skill/SKILL.md). It has the same rules plus the read-only database check, so you can ask Lovable "run the POPIA database check".

**2. Install the components and database layer.** Paste the [Lovable prompt](../registry/README.md#lovable-prompt) into chat. Approve the database migrations when Lovable asks.

**3. Check the database.** Ask Lovable to run this, or run it in the Cloud SQL editor:

```sql
select * from privacy.security_report();
```

You should see no critical or high rows. If you see `definer_function_exposed`, the migration step skipped a revoke: apply `0004_function_guards.sql` from the registry again.

That report covers the privacy schema. To check every table Lovable made, ask Lovable to "run the POPIA database check" if you added the workspace skill. Without it, ask Lovable to run the query from `uvx popia-kit supabase sql` and give you the result, then run `uvx popia-kit supabase check result.json`. On our test app it found only the expected newsletter sign-up insert.

**4. Privacy centre endpoints.** Lovable's current default stack (TanStack Start) does not create Supabase Edge Functions. The prompt asks Lovable to create the same four endpoints as server routes under `/api/privacy/`. Add the secrets it asks for (`ALLOWED_ORIGINS`, `CONSENT_IP_SALT`, `UNSUBSCRIBE_SECRET`) in the Lovable editor.

**5. Click through it yourself** in the preview, signed in as a test user:

- Reject all: no analytics cookies appear.
- Sign up with the marketing box unticked: no consent event is recorded.
- Privacy centre, Download my data: you get a file with your profile.
- Privacy centre, Delete my account: it asks you to sign in again first.

**6. Before you publish,** run Lovable's security scan, then scan the code (connect the project to GitHub, then path 2, step 1).

Preview links are public. Never connect a preview to production data.
