-- Deliberately non-compliant demo fixture.
create table public.profiles (
  id uuid primary key,
  full_name text,
  email text,
  id_number text,
  health_conditions text
);
create table public.leads (id uuid primary key default gen_random_uuid(), email text, phone text);
alter table public.leads enable row level security;
create policy "anyone can read leads" on public.leads for select to anon using (true);
insert into storage.buckets (id, name, public) values ('uploads', 'uploads', true);
