-- POPIA security self-check (s19(2)(c): regularly verify that safeguards work)
-- Engineering guidance, not legal advice.
--
-- privacy.security_report() is read-only. It lists:
--   - tables in public without row level security
--   - permissive policies: qual or with_check is literally 'true', or the policy applies to anon
--   - public storage buckets
--
-- Callable only by service_role. Run it from the SQL editor (as postgres) or
-- from a scheduled edge function, and treat each row as a lead to confirm.
-- A lead-capture table may legitimately allow anon INSERT with check (true),
-- as long as there is no anon SELECT.
--
--   select * from privacy.security_report();

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
  -- 1. Tables in public without RLS. Critical: the anon key ships to the browser.
  return query
  select 'table_without_rls'::text,
         'critical'::text,
         format('%I.%I', t.schemaname, t.tablename),
         'Row level security is disabled. Anyone with the anon key may read or write, subject to grants.'::text
    from pg_catalog.pg_tables t
   where t.schemaname = 'public'
     and t.rowsecurity = false;

  -- 2. RLS enabled but not forced (table owner bypasses policies). Low.
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

  -- 3. Permissive policies.
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

  -- 4. Public storage buckets. Uploads such as CVs, ID copies and proof of address must be private.
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
