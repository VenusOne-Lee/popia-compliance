-- POPIA privacy schema: function guards (defence in depth)
-- Engineering guidance, not legal advice.
--
-- Found in the end-to-end test on a fresh Lovable Cloud project (18 Oct 2026):
-- the migration tool there did not apply 0001's "revoke all on all functions",
-- so privacy.redact_consent_events stayed executable by PUBLIC. Any signed-in
-- user could then de-identify another person's consent evidence.
--
-- This migration:
--   1. Re-applies the revokes, one function at a time.
--   2. Makes redact_consent_events refuse callers that are not service_role,
--      even if a grant is later added by mistake.
--   3. Adds a check to privacy.security_report(): security definer functions in
--      public or privacy that anon or authenticated can execute.
--
-- After applying, run as postgres and expect no 'definer_function_exposed' rows:
--   select * from privacy.security_report();

-- 1. Revokes, function by function.
revoke all on function privacy.redact_consent_events(uuid) from public, anon, authenticated;
revoke all on function privacy.enforce_retention()         from public, anon, authenticated;
revoke all on function privacy.security_report()           from public, anon, authenticated;
grant execute on function privacy.redact_consent_events(uuid) to service_role;
grant execute on function privacy.enforce_retention()         to service_role;
grant execute on function privacy.security_report()           to service_role;

-- 2. Caller guard. A request through the API carries JWT claims; only the
-- service_role key may call this. Direct database sessions (SQL editor, cron)
-- have no claims and are allowed.
create or replace function privacy.redact_consent_events(p_subject uuid)
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  n integer;
  claims text := nullif(current_setting('request.jwt.claims', true), '');
begin
  if claims is not null and coalesce(claims::jsonb ->> 'role', '') <> 'service_role' then
    raise exception 'not allowed' using errcode = '42501';
  end if;
  perform set_config('privacy.allow_consent_redaction', 'on', true);
  update privacy.consent_events
     set ip_hash = null,
         user_agent = null,
         source_url = null,
         redacted_at = now()
   where subject_id = p_subject
     and redacted_at is null;
  get diagnostics n = row_count;
  perform set_config('privacy.allow_consent_redaction', 'off', true);
  return n;
end;
$$;

revoke all on function privacy.redact_consent_events(uuid) from public, anon, authenticated;
grant execute on function privacy.redact_consent_events(uuid) to service_role;

-- 3. security_report: add the exposed security definer check.
create or replace function privacy.security_report()
returns table (
  check_name  text,
  severity    text,
  object_name text,
  detail      text
)
language plpgsql
stable
security definer
set search_path = ''
as $$
begin
  return query
  select 'table_without_rls'::text,
         'critical'::text,
         format('%I.%I', t.schemaname, t.tablename),
         'Row level security is disabled. Anyone with the anon key may read or write, subject to grants.'::text
    from pg_catalog.pg_tables t
   where t.schemaname = 'public'
     and t.rowsecurity = false;

  return query
  select 'rls_not_forced'::text,
         'low'::text,
         format('%I.%I', n.nspname, c.relname),
         'RLS is enabled but not forced. The table owner bypasses policies.'::text
    from pg_catalog.pg_class c
    join pg_catalog.pg_namespace n on n.oid = c.relnamespace
   where n.nspname in ('public', 'privacy')
     and c.relkind = 'r'
     and c.relrowsecurity = true
     and c.relforcerowsecurity = false;

  return query
  select 'permissive_policy'::text,
         case
           when p.cmd in ('SELECT', 'ALL', 'UPDATE', 'DELETE')
                and (p.qual = 'true' or p.roles @> array['anon']::name[] or p.roles @> array['public']::name[])
             then 'high'
           else 'medium'
         end,
         format('%I.%I policy %I', p.schemaname, p.tablename, p.policyname),
         format('cmd=%s roles=%s using=%s with_check=%s',
                p.cmd, p.roles::text, coalesce(p.qual, 'null'), coalesce(p.with_check, 'null'))
    from pg_catalog.pg_policies p
   where p.schemaname in ('public', 'storage', 'privacy')
     and (p.qual = 'true'
          or p.with_check = 'true'
          or p.roles @> array['anon']::name[]);

  -- New: security definer functions callable from the browser roles. They run
  -- with the owner's rights, so an open grant can bypass RLS. Trigger functions
  -- can't be called directly and are skipped.
  return query
  select 'definer_function_exposed'::text,
         case when n.nspname = 'privacy' then 'high' else 'medium' end,
         format('%I.%I(%s)', n.nspname, p.proname, pg_catalog.pg_get_function_identity_arguments(p.oid)),
         format('Security definer function executable by %s. Revoke execute unless it is meant to be public and checks auth.uid() itself.',
                concat_ws(', ',
                  case when pg_catalog.has_function_privilege('anon', p.oid, 'EXECUTE') then 'anon' end,
                  case when pg_catalog.has_function_privilege('authenticated', p.oid, 'EXECUTE') then 'authenticated' end))
    from pg_catalog.pg_proc p
    join pg_catalog.pg_namespace n on n.oid = p.pronamespace
   where n.nspname in ('public', 'privacy')
     and p.prosecdef
     and p.prorettype <> 'pg_catalog.trigger'::pg_catalog.regtype
     and (pg_catalog.has_function_privilege('anon', p.oid, 'EXECUTE')
          or pg_catalog.has_function_privilege('authenticated', p.oid, 'EXECUTE'));

  if exists (select 1 from pg_catalog.pg_namespace where nspname = 'storage')
     and exists (select 1 from pg_catalog.pg_class c join pg_catalog.pg_namespace n on n.oid = c.relnamespace
                  where n.nspname = 'storage' and c.relname = 'buckets') then
    return query execute $q$
      select 'public_bucket'::text,
             'high'::text,
             b.id::text,
             format('Bucket %s is public. Make it private and serve files with short-lived signed URLs.', b.name)
        from storage.buckets b
       where b.public = true
    $q$;
  end if;
end;
$$;

revoke all on function privacy.security_report() from public, anon, authenticated;
grant execute on function privacy.security_report() to service_role;
