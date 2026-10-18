-- FAKE EVAL FIXTURE. Synthetic schema only.
create table public.audit_leads (
  id uuid primary key default gen_random_uuid(),
  full_name text not null,
  email text not null,
  phone text,
  company text,
  sa_id_number text,
  marketing_opt_in boolean default true,
  created_at timestamptz default now()
);
-- no row level security enabled
grant select, insert on public.audit_leads to anon;
