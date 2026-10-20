---
name: popia-kit
description: POPIA privacy and security guardrails for South African apps, plus a read-only database check. Use when building or changing anything that handles personal information, before publishing, or when asked for a POPIA, privacy or security review.
---

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

## Lovable specifics

- Before publishing, run Lovable's security scan and check every Supabase table has RLS.
- Add the consent banner and privacy centre from the components registry instead of hand-rolling them.
- Lovable preview links are public. Never connect previews to production data.

## Database check (read-only)

Run this when asked for a POPIA, privacy or security review, before publishing, and after any migration that adds a table, view, function, policy or bucket.

1. Run the query below with your read-only SQL tool. Never run it as a migration. It reads the system catalogs only: no table data, no personal information, no changes.
2. Read the single JSON value it returns and apply the rules below. Skip tables, views, policies and functions in the platform schemas `extensions`, `graphql`, `graphql_public`, `realtime`, `storage`, `supabase_functions`, `vault`, but still check buckets. Use the severities below. Column names that suggest personal information (email, phone, ID number, address, date of birth, health, bank details and similar) raise some of them.
3. Report a table: severity, rule, object, evidence, POPIA section, fix. Say it is a lead to review, not a legal conclusion.
4. Propose the fixes as one migration and wait for the user to approve it. Never change policies, grants or buckets without approval. A critical finding may mean personal information was already exposed: tell the user that s22 may require notifying the Information Regulator and the people affected.
5. After the migration, run the query again and confirm the findings are gone.

Expected and fine: an anon insert policy on a sign-up or contact form table that anon cannot read (SB-005, low), and an extra exposed schema that only holds protected tables (SB-011, info).

| Rule | Finding | POPIA | Fix |
|---|---|---|---|
| SB-001 | Table open to anyone, row level security off | s19 | Enable row level security on the table and add policies for each role. Revoke anon grants it does not need. |
| SB-002 | Table open to every signed-in user, row level security off | s19 | Enable row level security and add policies that limit each user to their own rows. |
| SB-003 | Policy lets anyone read or change every row | s19 | Replace USING (true) with a condition, for example (select auth.uid()) = user_id, or limit the policy to authenticated. |
| SB-004 | Policy lets every signed-in user read or change every row | s19 | Limit the policy to the user's own rows, or to a role or team they belong to. |
| SB-005 | Anyone can insert rows | s19 | Fine for a sign-up or contact form if anon cannot read the table. Add rate limiting or a CAPTCHA, and validate input with a check constraint or trigger. |
| SB-006 | View bypasses row level security | s19 | Recreate the view WITH (security_invoker = true), or revoke select from anon and authenticated. |
| SB-007 | Materialized view readable through the API | s19 | Materialized views have no row level security. Revoke select from anon and authenticated, or move it to a schema the API does not expose. |
| SB-008 | Security definer function callable through the API | s19 | Revoke execute from public, anon and authenticated unless it must be called by them. If it must, set search_path = '' and check the caller inside the function. |
| SB-009 | Public storage bucket | s19 | Make the bucket private and serve files with short-lived signed URLs. Keep public only for files meant for everyone, such as logos. |
| SB-010 | Foreign table readable through the API | s19; s72 | Foreign tables have no row level security. Revoke select from anon and authenticated, or move it out of the exposed schemas. |
| SB-011 | Extra schema exposed through the API | s19 | Every table in an exposed schema is reachable with the anon key, subject to grants and row level security. Confirm each one is protected, or remove the schema from the exposed list. |

Severity: SB-001 critical. SB-002 high, critical with personal information. SB-003 high, critical for select with personal information. SB-004 medium, high with personal information. SB-005 low, high if anon can also read. SB-006 high, critical if it reads `auth.users` or anon can read personal information. SB-007 high, critical if anon can read personal information. SB-008 high for anon without a fixed search_path, medium for anon with one or authenticated without, low for authenticated with one. SB-009 high. SB-010 high. SB-011 info.

```sql
with cfg as (
  select coalesce(
           (select string_to_array(replace(split_part(c, '=', 2), ' ', ''), ',')
              from pg_catalog.pg_roles r, unnest(r.rolconfig) c
             where r.rolname = 'authenticator' and c like 'pgrst.db_schemas=%'
             limit 1),
           array['public', 'graphql_public']) as schemas
),
roles as (
  select exists (select 1 from pg_catalog.pg_roles where rolname = 'anon') as has_anon,
         exists (select 1 from pg_catalog.pg_roles where rolname = 'authenticated') as has_auth
),
rels as (
  select c.oid, n.nspname as schema, c.relname as name, c.relkind as kind,
         c.relrowsecurity as rls, c.relforcerowsecurity as rls_forced,
         coalesce(c.reloptions::text[] && array['security_invoker=true', 'security_invoker=on', 'security_invoker=1'], false) as security_invoker
    from pg_catalog.pg_class c
    join pg_catalog.pg_namespace n on n.oid = c.relnamespace, cfg
   where n.nspname = any (cfg.schemas)
     and c.relkind in ('r', 'p', 'v', 'm', 'f')
     and not exists (select 1 from pg_catalog.pg_depend d
                      where d.classid = 'pg_catalog.pg_class'::regclass and d.objid = c.oid and d.deptype = 'e')
),
priv as (
  select r.*,
         case when ro.has_anon then has_table_privilege('anon', r.oid, 'SELECT') else false end as anon_select,
         case when ro.has_anon then has_table_privilege('anon', r.oid, 'INSERT') or has_table_privilege('anon', r.oid, 'UPDATE') or has_table_privilege('anon', r.oid, 'DELETE') else false end as anon_write,
         case when ro.has_auth then has_table_privilege('authenticated', r.oid, 'SELECT') else false end as auth_select,
         case when ro.has_auth then has_table_privilege('authenticated', r.oid, 'INSERT') or has_table_privilege('authenticated', r.oid, 'UPDATE') or has_table_privilege('authenticated', r.oid, 'DELETE') else false end as auth_write,
         (select coalesce(json_agg(a.attname order by a.attnum), '[]'::json)
            from pg_catalog.pg_attribute a
           where a.attrelid = r.oid and a.attnum > 0 and not a.attisdropped) as columns,
         case when r.kind in ('v', 'm') then pg_catalog.pg_get_viewdef(r.oid) ~* '\mauth\s*\.\s*users\M' else false end as reads_auth_users
    from rels r, roles ro
),
funcs as (
  select n.nspname as schema, p.proname as name, pg_catalog.pg_get_function_identity_arguments(p.oid) as args,
         p.prosecdef as security_definer,
         coalesce(exists (select 1 from unnest(p.proconfig) c where c like 'search_path=%'), false) as fixed_search_path,
         case when ro.has_anon then has_function_privilege('anon', p.oid, 'EXECUTE') else false end as anon_execute,
         case when ro.has_auth then has_function_privilege('authenticated', p.oid, 'EXECUTE') else false end as auth_execute
    from pg_catalog.pg_proc p
    join pg_catalog.pg_namespace n on n.oid = p.pronamespace, cfg, roles ro
   where n.nspname = any (cfg.schemas)
     and p.prokind = 'f'
     and p.prorettype <> 'pg_catalog.trigger'::pg_catalog.regtype
     and p.prorettype <> 'pg_catalog.event_trigger'::pg_catalog.regtype
     and not exists (select 1 from pg_catalog.pg_depend d
                      where d.classid = 'pg_catalog.pg_proc'::regclass and d.objid = p.oid and d.deptype = 'e')
),
pols as (
  select p.schemaname as schema, p.tablename as "table", p.policyname as name, p.permissive, p.roles::text[] as roles,
         p.cmd, p.qual, p.with_check
    from pg_catalog.pg_policies p, cfg
   where p.schemaname = any (cfg.schemas) or p.schemaname = 'storage'
),
buckets as (
  select case when to_regclass('storage.buckets') is null then '[]'::json else (
    select coalesce(json_agg(json_build_object(
             'id', (xpath('/row/id/text()', x))[1]::text,
             'public', (xpath('/row/public/text()', x))[1]::text = 'true')), '[]'::json)
      from unnest(xpath('/table/row', query_to_xml('select id, public from storage.buckets', false, false, ''))) x
  ) end as list
)
select json_build_object(
  'tool', 'popia-kit supabase inventory',
  'version', 1,
  'postgres', current_setting('server_version'),
  'exposed_schemas', (select to_json(schemas) from cfg),
  'relations', (select coalesce(json_agg(json_build_object(
      'schema', schema, 'name', name, 'kind', kind, 'rls', rls, 'rls_forced', rls_forced,
      'security_invoker', security_invoker, 'anon_select', anon_select, 'anon_write', anon_write,
      'auth_select', auth_select, 'auth_write', auth_write, 'columns', columns,
      'reads_auth_users', reads_auth_users) order by schema, name), '[]'::json) from priv),
  'functions', (select coalesce(json_agg(json_build_object(
      'schema', schema, 'name', name, 'args', args, 'security_definer', security_definer,
      'fixed_search_path', fixed_search_path, 'anon_execute', anon_execute, 'auth_execute', auth_execute)
      order by schema, name), '[]'::json) from funcs),
  'policies', (select coalesce(json_agg(json_build_object(
      'schema', schema, 'table', "table", 'name', name, 'permissive', permissive, 'roles', roles,
      'cmd', cmd, 'using', qual, 'with_check', with_check) order by schema, "table", name), '[]'::json) from pols),
  'buckets', (select list from buckets)
) as popia_kit_inventory;
```

The same query and rules ship as `uvx popia-kit supabase sql` and `uvx popia-kit supabase check result.json`. For the live site, use the free passive check at https://popiakit.co.za/check.
