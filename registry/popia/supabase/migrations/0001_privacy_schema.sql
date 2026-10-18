-- POPIA privacy schema for Supabase / Postgres 15+
-- Maintained by Venus One (Pty) Ltd. Engineering guidance, not legal advice.
--
-- Creates schema "privacy" with:
--   data_inventory   s17 documentation, s13 purpose, s14 retention, as data
--   consent_events   s11(2)(a) proof of consent. Append-only.
--   consent_current  latest event per subject and purpose (view)
--   dsar_requests    s23 access, s24 correction and deletion, s11(3) objection
--   retention_runs   evidence that the s14 retention job ran
--   access_audit     s19 who accessed or exported what. Append-only.
--
-- RLS is enabled and forced on every table. Anon gets nothing.
-- Authenticated users may insert and read only their own consent events and
-- their own DSAR requests. Everything else is service_role only (edge functions).
--
-- To call these tables from supabase-js (.schema('privacy')), add "privacy" to
-- Dashboard > Project Settings > API > Exposed schemas. That is safe because
-- the grants and RLS below decide access, not exposure.

create extension if not exists pgcrypto with schema extensions;

create schema if not exists privacy;

revoke all on schema privacy from public;
revoke all on schema privacy from anon;
grant usage on schema privacy to authenticated, service_role;

-- ---------------------------------------------------------------------------
-- Append-only guard (shared)
-- ---------------------------------------------------------------------------
-- Blocks UPDATE, DELETE and TRUNCATE. A narrow, audited escape hatch exists for
-- de-identifying consent evidence after an account deletion: see
-- privacy.redact_consent_events below. It sets a transaction-local flag.
create or replace function privacy.block_mutation()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if tg_table_name = 'consent_events'
     and tg_op = 'UPDATE'
     and coalesce(current_setting('privacy.allow_consent_redaction', true), '') = 'on' then
    return new;
  end if;
  raise exception 'privacy.%: % is not allowed. This table is append-only.', tg_table_name, tg_op
    using errcode = 'insufficient_privilege';
end;
$$;

-- ---------------------------------------------------------------------------
-- data_inventory  (s17, s13, s14, s26, s34, s20/21, s72)
-- ---------------------------------------------------------------------------
create table if not exists privacy.data_inventory (
  id                uuid primary key default gen_random_uuid(),
  data_store        text not null,                    -- 'public.profiles'
  fields            text[] not null,                  -- {'full_name','email','phone'}
  data_subjects     text not null,                    -- 'customers', 'employees', 'leads', 'B2B contacts'
  purpose           text not null,                    -- s13: specific and explicit
  lawful_basis      text not null check (lawful_basis in
                     ('consent','contract','legal_obligation','data_subject_interest','public_duty','legitimate_interest')),
  special_pi        boolean not null default false,   -- s26
  children          boolean not null default false,   -- s34
  retention         interval not null,                -- s14
  retention_trigger text not null,                    -- 'account_closed', 'last_activity', 'created_at'
  operators         text[] not null default '{}',     -- s20/21: who else processes it
  cross_border      text[] not null default '{}',     -- s72: countries
  owner             text not null,
  reviewed_at       date not null default current_date
);

-- ---------------------------------------------------------------------------
-- consent_events  (s11(2)(a) burden of proof, s69 direct marketing, s27, s35)
-- ---------------------------------------------------------------------------
create table if not exists privacy.consent_events (
  id                  uuid primary key default gen_random_uuid(),
  subject_id          uuid not null default auth.uid(),  -- user or lead id
  purpose             text not null check (char_length(purpose) between 1 and 100),
  action              text not null check (action in ('granted','withdrawn')),
  notice_version      text not null check (char_length(notice_version) between 1 and 200),
  wording             text not null check (char_length(wording) between 1 and 5000),
  channel             text not null check (char_length(channel) between 1 and 50),
  source_url          text check (source_url is null or char_length(source_url) <= 2000),
  ip_hash             text,                              -- salted hash, never the raw IP
  user_agent          text check (user_agent is null or char_length(user_agent) <= 500),
  competent_person_id uuid,                              -- s35: parent or guardian for a child
  redacted_at         timestamptz,                       -- set only by redact_consent_events
  created_at          timestamptz not null default now()
);

create index if not exists consent_events_subject_purpose_idx
  on privacy.consent_events (subject_id, purpose, created_at desc);

drop trigger if exists consent_events_append_only on privacy.consent_events;
create trigger consent_events_append_only
  before update or delete on privacy.consent_events
  for each row execute function privacy.block_mutation();

drop trigger if exists consent_events_no_truncate on privacy.consent_events;
create trigger consent_events_no_truncate
  before truncate on privacy.consent_events
  for each statement execute function privacy.block_mutation();

-- Current state: latest event per subject and purpose wins.
-- Check this at send time, not at list-build time.
-- security_invoker makes the caller's RLS apply through the view.
create or replace view privacy.consent_current
with (security_invoker = true) as
select distinct on (subject_id, purpose)
  subject_id, purpose, action, notice_version, channel, created_at
from privacy.consent_events
order by subject_id, purpose, created_at desc;

-- De-identify consent evidence for a deleted subject. Keeps the fact and time
-- of consent and withdrawal, drops device and network details.
-- VERIFY with your attorney how long consent evidence must be kept after an
-- account is deleted. Burden of proof (s11(2)(a)) argues for keeping the
-- event itself; s14 argues for keeping no more than needed.
create or replace function privacy.redact_consent_events(p_subject uuid)
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  n integer;
begin
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

-- ---------------------------------------------------------------------------
-- dsar_requests  (s23 access, s24 correction/deletion, s11(3) objection)
-- ---------------------------------------------------------------------------
-- Target turnaround is 30 days or less, aligned with PAIA timelines.
create table if not exists privacy.dsar_requests (
  id            uuid primary key default gen_random_uuid(),
  subject_id    uuid not null default auth.uid(),
  type          text not null check (type in ('access','correction','deletion','objection')),
  status        text not null default 'received'
                 check (status in ('received','verifying','in_progress','completed','rejected')),
  details       text check (details is null or char_length(details) <= 5000),
  channel       text not null default 'privacy_centre',
  received_at   timestamptz not null default now(),
  due_at        timestamptz not null default (now() + interval '30 days'),
  completed_at  timestamptz,
  outcome       text,                                  -- what was done, told to the data subject (s24(3))
  handled_by    text
);

create index if not exists dsar_requests_subject_idx on privacy.dsar_requests (subject_id, received_at desc);
create index if not exists dsar_requests_open_idx on privacy.dsar_requests (due_at) where status not in ('completed','rejected');

-- ---------------------------------------------------------------------------
-- retention_runs  (s14 evidence)
-- ---------------------------------------------------------------------------
create table if not exists privacy.retention_runs (
  id            bigint generated always as identity primary key,
  ran_at        timestamptz not null default now(),
  rule          text,
  rows_affected integer,
  details       jsonb not null default '{}'::jsonb
);

-- ---------------------------------------------------------------------------
-- access_audit  (s19: who viewed or exported sensitive data). Append-only.
-- ---------------------------------------------------------------------------
create table if not exists privacy.access_audit (
  id          bigint generated always as identity primary key,
  occurred_at timestamptz not null default now(),
  actor_id    uuid,                 -- staff user or the data subject
  actor_role  text,                 -- 'support', 'compliance', 'data_subject', 'system'
  action      text not null,        -- 'view', 'export', 'delete', 'deidentify', 'unmask'
  data_store  text not null,        -- 'public.profiles'
  subject_id  uuid,                 -- whose data
  record_id   text,
  reason      text,
  details     jsonb not null default '{}'::jsonb  -- never put the personal information itself here
);

create index if not exists access_audit_subject_idx on privacy.access_audit (subject_id, occurred_at desc);

drop trigger if exists access_audit_append_only on privacy.access_audit;
create trigger access_audit_append_only
  before update or delete on privacy.access_audit
  for each row execute function privacy.block_mutation();

drop trigger if exists access_audit_no_truncate on privacy.access_audit;
create trigger access_audit_no_truncate
  before truncate on privacy.access_audit
  for each statement execute function privacy.block_mutation();

-- ---------------------------------------------------------------------------
-- Row level security: enabled and forced everywhere (s19)
-- ---------------------------------------------------------------------------
alter table privacy.data_inventory enable row level security;
alter table privacy.data_inventory force row level security;
alter table privacy.consent_events enable row level security;
alter table privacy.consent_events force row level security;
alter table privacy.dsar_requests  enable row level security;
alter table privacy.dsar_requests  force row level security;
alter table privacy.retention_runs enable row level security;
alter table privacy.retention_runs force row level security;
alter table privacy.access_audit   enable row level security;
alter table privacy.access_audit   force row level security;

-- consent_events: own rows only. No update or delete policies exist.
drop policy if exists "consent: insert own" on privacy.consent_events;
create policy "consent: insert own" on privacy.consent_events
  for insert to authenticated
  with check ((select auth.uid()) = subject_id);

drop policy if exists "consent: read own" on privacy.consent_events;
create policy "consent: read own" on privacy.consent_events
  for select to authenticated
  using ((select auth.uid()) = subject_id);

-- dsar_requests: own rows only, and only as a new 'received' request.
drop policy if exists "dsar: insert own" on privacy.dsar_requests;
create policy "dsar: insert own" on privacy.dsar_requests
  for insert to authenticated
  with check ((select auth.uid()) = subject_id and status = 'received');

drop policy if exists "dsar: read own" on privacy.dsar_requests;
create policy "dsar: read own" on privacy.dsar_requests
  for select to authenticated
  using ((select auth.uid()) = subject_id);

-- data_inventory, retention_runs, access_audit: no client policies.
-- service_role bypasses RLS in Supabase and is used only in edge functions.

-- ---------------------------------------------------------------------------
-- Grants: explicit, least privilege
-- ---------------------------------------------------------------------------
revoke all on all tables    in schema privacy from public, anon, authenticated;
revoke all on all sequences in schema privacy from public, anon, authenticated;
revoke all on all functions in schema privacy from public, anon, authenticated;

alter default privileges in schema privacy revoke all on tables    from public, anon, authenticated;
alter default privileges in schema privacy revoke all on sequences from public, anon, authenticated;
alter default privileges in schema privacy revoke all on functions from public, anon, authenticated;

-- authenticated: column-scoped inserts, so clients cannot set ip_hash,
-- redacted_at, status, due_at or created_at themselves.
grant select on privacy.consent_events to authenticated;
grant insert (subject_id, purpose, action, notice_version, wording, channel, source_url, user_agent, competent_person_id)
  on privacy.consent_events to authenticated;
grant select on privacy.consent_current to authenticated;

grant select on privacy.dsar_requests to authenticated;
grant insert (subject_id, type, details) on privacy.dsar_requests to authenticated;

-- service_role: what the edge functions need. Still no update or delete on
-- append-only tables (the triggers block them regardless).
grant select, insert, update, delete on privacy.data_inventory to service_role;
grant select, insert on privacy.consent_events to service_role;
grant select on privacy.consent_current to service_role;
grant select, insert, update on privacy.dsar_requests to service_role;
grant select, insert on privacy.retention_runs to service_role;
grant select, insert on privacy.access_audit to service_role;
grant usage on all sequences in schema privacy to service_role;

grant execute on function privacy.redact_consent_events(uuid) to service_role;
