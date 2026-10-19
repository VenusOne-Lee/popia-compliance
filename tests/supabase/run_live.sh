#!/usr/bin/env bash
# Runs the Supabase inventory query against a throwaway local Postgres seeded with known risks.
# Usage: bash tests/supabase/run_live.sh   (needs Postgres 14+ server binaries and psql; if root, the
# cluster runs as the postgres OS user)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PGBIN="${PGBIN:-$(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | sort -V | tail -1)}"
WORK="$(mktemp -d)"
PORT="${PGPORT_TEST:-54332}"
RUNAS=()
if [ "$(id -u)" = "0" ]; then RUNAS=(runuser -u postgres --); chown postgres "$WORK"; fi
cleanup() { "${RUNAS[@]}" "$PGBIN/pg_ctl" -D "$WORK/data" -m immediate stop >/dev/null 2>&1 || true; rm -rf "$WORK"; }
trap cleanup EXIT

"${RUNAS[@]}" "$PGBIN/initdb" -D "$WORK/data" -U postgres -A trust >/dev/null
"${RUNAS[@]}" "$PGBIN/pg_ctl" -D "$WORK/data" -o "-p $PORT -k $WORK -c listen_addresses=127.0.0.1" -l "$WORK/log" -w start >/dev/null

export POPIA_TEST_PG_URL="postgresql://postgres@127.0.0.1:$PORT/postgres?sslmode=disable"
cd "$ROOT"
python3 -m unittest tests.supabase.test_supabase_check -v 2>&1 | tee "$WORK/out.txt"
if grep -q "^test_query_runs_read_only.* skipped" "$WORK/out.txt"; then echo "live SQL test was skipped"; exit 1; fi
