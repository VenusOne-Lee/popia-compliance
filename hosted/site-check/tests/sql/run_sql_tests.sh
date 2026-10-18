#!/usr/bin/env bash
# Runs the migration against a throwaway local Postgres cluster with Supabase-like roles
# (anon, authenticated, service_role, and a non-superuser owner with BYPASSRLS like Supabase's postgres).
# Usage: tests/sql/run_sql_tests.sh   (needs Postgres 14+ server binaries; runs as the postgres OS user if root)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
MIGRATION="$HERE/../../supabase/migrations/site_check_rate.sql"
PGBIN="${PGBIN:-$(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | sort -V | tail -1)}"
WORK="$(mktemp -d)"
PORT="${PGPORT_TEST:-54329}"
RUNAS=()
if [ "$(id -u)" = "0" ]; then RUNAS=(runuser -u postgres --); chown postgres "$WORK"; fi
cp "$MIGRATION" "$WORK/migration.sql"; chmod 644 "$WORK/migration.sql"
cleanup() { "${RUNAS[@]}" "$PGBIN/pg_ctl" -D "$WORK/data" -m immediate stop >/dev/null 2>&1 || true; rm -rf "$WORK"; }
trap cleanup EXIT

"${RUNAS[@]}" "$PGBIN/initdb" -D "$WORK/data" -U postgres -A trust >/dev/null
"${RUNAS[@]}" "$PGBIN/pg_ctl" -D "$WORK/data" -o "-p $PORT -k $WORK -c listen_addresses=''" -l "$WORK/log" -w start >/dev/null

PASS=0; FAIL=0
q() { "${RUNAS[@]}" "$PGBIN/psql" -h "$WORK" -p "$PORT" -X -q -t -A -v ON_ERROR_STOP=1 "$@"; }
ok() { PASS=$((PASS+1)); echo "ok   $1"; }
bad() { FAIL=$((FAIL+1)); echo "FAIL $1"; }
expect() { # name expected actual
  if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (expected '$2', got '$3')"; fi
}

q -U postgres -d postgres <<'SQL'
create role anon nologin;
create role authenticated nologin;
create role service_role nologin bypassrls;
create role owner_ok login bypassrls;
create role owner_norls login;
grant create on schema public to owner_ok, owner_norls;
grant anon, authenticated, service_role to postgres;
-- Mimic Supabase: new objects in public are granted to the API roles by default.
alter default privileges for role owner_ok in schema public grant all on tables to anon, authenticated, service_role;
alter default privileges for role owner_ok in schema public grant all on functions to anon, authenticated, service_role;
SQL

# Migration refuses an owner that cannot bypass RLS.
if q -U owner_norls -d postgres -f "$WORK/migration.sql" >/dev/null 2>&1; then
  bad "migration refuses owner without BYPASSRLS"
else ok "migration refuses owner without BYPASSRLS"; fi

q -U owner_ok -d postgres -f "$WORK/migration.sql" >/dev/null && ok "migration applies as BYPASSRLS owner"
q -U owner_ok -d postgres -f "$WORK/migration.sql" >/dev/null 2>&1 && ok "migration is re-runnable"

H1=$(printf 'a%.0s' {1..64}); H2=$(printf 'b%.0s' {1..64}); H3=$(printf 'c%.0s' {1..64})
call() { { q -U postgres -d postgres -c "set role $1; select public.site_check_hit('$2', $3);" 2>&1 || true; } | tail -1; }

expect "rls enabled" "t" "$(q -U postgres -d postgres -c "select relrowsecurity from pg_class where oid='public.site_check_rate'::regclass")"
expect "rls forced" "t" "$(q -U postgres -d postgres -c "select relforcerowsecurity from pg_class where oid='public.site_check_rate'::regclass")"
expect "no policies" "0" "$(q -U postgres -d postgres -c "select count(*) from pg_policies where tablename='site_check_rate'")"
expect "security definer" "t" "$(q -U postgres -d postgres -c "select prosecdef from pg_proc where proname='site_check_hit'")"
expect "search_path pinned" "{\"search_path=\\\"\\\"\"}" "$(q -U postgres -d postgres -c "select proconfig from pg_proc where proname='site_check_hit'")"

for r in anon authenticated; do
  out=$(call $r "$H1" 10)
  case "$out" in *"permission denied"*) ok "$r cannot execute function";; *) bad "$r cannot execute function ($out)";; esac
  out=$({ q -U postgres -d postgres -c "set role $r; select count(*) from public.site_check_rate;" 2>&1 || true; } | tail -1)
  case "$out" in *"permission denied"*) ok "$r cannot read table";; *) bad "$r cannot read table ($out)";; esac
done
out=$({ q -U postgres -d postgres -c "set role service_role; select count(*) from public.site_check_rate;" 2>&1 || true; } | tail -1)
case "$out" in *"permission denied"*) ok "service_role has no direct table access";; *) bad "service_role table access ($out)";; esac
expect "public has no execute" "f" "$(q -U postgres -d postgres -c "select has_function_privilege('public', 'public.site_check_hit(text,int)', 'execute')")"

expect "hit 1 of 3" "t" "$(call service_role "$H1" 3)"
expect "hit 2 of 3" "t" "$(call service_role "$H1" 3)"
expect "hit 3 of 3" "t" "$(call service_role "$H1" 3)"
expect "hit 4 of 3 refused" "f" "$(call service_role "$H1" 3)"
expect "other client unaffected" "t" "$(call service_role "$H2" 3)"
expect "count stored" "4" "$(q -U postgres -d postgres -c "select count from public.site_check_rate where ip_hash='$H1'")"

q -U postgres -d postgres -c "update public.site_check_rate set window_start = now() - interval '61 minutes' where ip_hash='$H1'"
expect "window resets after 1 hour" "t" "$(call service_role "$H1" 3)"
expect "count reset to 1" "1" "$(q -U postgres -d postgres -c "select count from public.site_check_rate where ip_hash='$H1'")"

q -U postgres -d postgres -c "insert into public.site_check_rate values ('$H3', now() - interval '3 hours', 99)"
call service_role "$H2" 3 >/dev/null
expect "rows older than 2 hours pruned" "0" "$(q -U postgres -d postgres -c "select count(*) from public.site_check_rate where ip_hash='$H3'")"

expect "invalid hash refused" "f" "$(call service_role "not-a-hash" 3)"
expect "zero limit refused" "f" "$(call service_role "$H2" 0)"
expect "null limit refused" "f" "$(call service_role "$H2" null)"

# Concurrency: 30 parallel calls with limit 10 must allow exactly 10.
HC=$(printf 'd%.0s' {1..64})
for i in $(seq 1 30); do (call service_role "$HC" 10 > "$WORK/c$i") & done; wait
allowed=$(cat "$WORK"/c* | grep -c '^t$' || true)
expect "atomic under 30 concurrent calls (limit 10)" "10" "$allowed"

echo "sql tests: $PASS passed, $FAIL failed"
[ "$FAIL" = "0" ]
