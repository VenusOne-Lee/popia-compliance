-- FAKE EVAL FIXTURE.
create table public.players (
  id uuid primary key default gen_random_uuid(),
  username text not null,
  date_of_birth date not null,
  school text,
  grade text,
  city text,
  avatar_url text,
  is_public boolean default true
);
