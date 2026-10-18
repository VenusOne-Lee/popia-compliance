-- Rate limiting for the public site-check Edge Function.
-- Stores only a salted SHA-256 of the client IP bucket, a window start and a count.
-- No URLs, responses or findings are ever stored.

-- The function below is SECURITY DEFINER and the table has RLS forced with no policies,
-- so the function owner must bypass RLS (Supabase's postgres role does). Fail loudly here
-- rather than fail closed (429 for everyone) at runtime.
do $$
begin
  if not exists (
    select 1 from pg_roles where rolname = current_user and (rolsuper or rolbypassrls)
  ) then
    raise exception 'site_check_rate: run this migration as a role with BYPASSRLS (for example postgres)';
  end if;
end
$$;

create table if not exists public.site_check_rate (
  ip_hash      text        primary key check (ip_hash ~ '^[0-9a-f]{64}$'),
  window_start timestamptz not null default now(),
  count        int         not null default 0 check (count >= 0)
);

create index if not exists site_check_rate_window_start_idx on public.site_check_rate (window_start);

alter table public.site_check_rate enable row level security;
alter table public.site_check_rate force row level security;
-- Deliberately no policies. Only the SECURITY DEFINER function below touches this table.

revoke all on table public.site_check_rate from public, anon, authenticated, service_role;

-- Returns true when the call is within the limit for the current one hour window.
-- Atomic: a single INSERT ... ON CONFLICT DO UPDATE per call. Also prunes rows older than 2 hours.
create or replace function public.site_check_hit(p_ip_hash text, p_limit int)
returns boolean
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
  v_count int;
begin
  if p_ip_hash is null or p_ip_hash !~ '^[0-9a-f]{64}$' or p_limit is null or p_limit < 1 then
    return false;
  end if;

  delete from public.site_check_rate
   where window_start < now() - interval '2 hours';

  insert into public.site_check_rate as r (ip_hash, window_start, count)
  values (p_ip_hash, now(), 1)
  on conflict (ip_hash) do update
     set window_start = case when r.window_start <= now() - interval '1 hour' then now() else r.window_start end,
         count        = case when r.window_start <= now() - interval '1 hour' then 1 else r.count + 1 end
  returning r.count into v_count;

  return v_count <= p_limit;
end;
$$;

revoke all on function public.site_check_hit(text, int) from public, anon, authenticated;
grant execute on function public.site_check_hit(text, int) to service_role;
