-- POPIA Kit: Supabase inventory (read-only).
-- Run in the Supabase SQL editor, or with popia-kit supabase run. It reads the system
-- catalogs only: no table data, no personal information, no changes. Save the single
-- JSON value it returns and run: popia-kit supabase check result.json
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
