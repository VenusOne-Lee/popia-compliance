-- Test seed for popia-kit supabase. Builds a small Supabase-like database with known risks.
-- Run only against a throwaway Postgres. It drops and recreates the objects below.
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then create role anon nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'service_role') then create role service_role nologin bypassrls; end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticator') then create role authenticator noinherit login; end if;
end $$;
alter role authenticator set pgrst.db_schemas = 'public, storage, graphql_public';

drop schema if exists auth cascade;
drop schema if exists storage cascade;
drop materialized view if exists public.stats;
drop view if exists public.user_emails, public.safe_view;
drop table if exists public.profiles, public.notes, public.leads, public.orders, public.staff_only cascade;
drop function if exists public.wipe(uuid), public.guarded(), public.invoker(), public.trg();

create schema auth;
create table auth.users (id uuid primary key, email text);
create schema storage;
create table storage.buckets (id text primary key, name text, public boolean default false);
insert into storage.buckets values ('avatars', 'avatars', true), ('cvs', 'cvs', false);

-- RLS off and anon can read: critical.
create table public.profiles (id uuid primary key, email text, phone text);
grant select, insert on public.profiles to anon, authenticated;

-- RLS on, but the policy lets everyone read.
create table public.notes (id int primary key, body text);
alter table public.notes enable row level security;
create policy open_read on public.notes for select using (true);
grant select on public.notes to anon, authenticated;

-- Anon can insert only: a sign-up form.
create table public.leads (id int primary key, email text);
alter table public.leads enable row level security;
create policy lead_in on public.leads for insert to anon with check (true);
grant insert on public.leads to anon;

-- Good: own rows only.
create table public.orders (id int primary key, user_id uuid, total int);
alter table public.orders enable row level security;
create policy own on public.orders for select to authenticated using (user_id = gen_random_uuid());
grant select on public.orders to authenticated;

-- RLS off, signed-in users only.
create table public.staff_only (id int primary key, salary int);
grant select on public.staff_only to authenticated;
revoke all on public.staff_only from anon;

-- A view that exposes auth.users.
create view public.user_emails as select id, email from auth.users;
grant select on public.user_emails to anon;
create view public.safe_view with (security_invoker = true) as select id from public.orders;
grant select on public.safe_view to authenticated;
create materialized view public.stats as select count(*) n from public.orders;
grant select on public.stats to anon;

create function public.wipe(uid uuid) returns void language sql security definer
  as $f$ delete from public.orders where user_id = uid $f$;
create function public.guarded() returns int language sql security definer set search_path = '' as $f$ select 1 $f$;
create function public.invoker() returns int language sql as $f$ select 1 $f$;
create function public.trg() returns trigger language plpgsql security definer as $f$ begin return new; end $f$;
revoke all on function public.guarded() from public;
grant execute on function public.guarded() to authenticated;
