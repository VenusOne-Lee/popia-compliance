#!/usr/bin/env python3
"""
supabase_check: find database exposures in a Supabase project, read-only.

    popia-kit supabase sql                     print the read-only inventory query
    popia-kit supabase check result.json       turn its result into findings
    popia-kit supabase run                     run the query with psql, then check

The query reads the system catalogs only: table and column names, row level
security settings, policies, grants, functions and bucket settings. It never reads
table data or personal information, and it changes nothing.

Two ways to run it:
  1. No install: paste `popia-kit supabase sql` into the Supabase SQL editor, copy the
     single JSON value it returns into result.json, then `popia-kit supabase check result.json`.
     A CSV download of the result works too.
  2. With psql installed: set SUPABASE_DB_URL to the connection string (Project settings,
     Database) and run `popia-kit supabase run`. The URL is read from the environment and
     passed to psql through environment variables, never on the command line. The session
     is read-only.

Findings are leads to review, not legal conclusions. Engineering guidance only, not legal
advice. Stdlib only. Python 3.8+.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import shutil
import subprocess  # nosec B404: runs the user's own psql, see run_psql
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, unquote, urlsplit

__version__ = "1.0.0"
SEVERITIES = ["critical", "high", "medium", "low", "info"]
SQL_PATH = Path(__file__).resolve().parent / "sql" / "supabase_inventory.sql"

# Schemas Supabase manages itself. Their tables and functions are not the project's to fix.
PLATFORM_SCHEMAS = {"storage", "graphql_public", "graphql", "realtime", "supabase_functions", "extensions", "vault"}
DEFAULT_SCHEMAS = {"public", "graphql_public", "storage"}

# Column names that usually hold personal information. A hit raises the severity of an exposure.
PI_COLUMN = re.compile(
    r"(^|_)(e_?mail|phone|mobile|cell|msisdn|whatsapp|id_?num(ber)?|sa_?id|identity|national_?id|passport|"
    r"address|street|postal|suburb|dob|birth|age|gender|race|religion|health|medical|diagnos\w*|disab\w*|"
    r"salary|income|bank|account_?(no|num(ber)?)|iban|card|tax_?(no|num(ber)?)|biometric|face|fingerprint|"
    r"location|lat|lng|longitude|latitude|ip_?address|first_?name|last_?name|surname|full_?name)($|_)",
    re.I,
)

RULES: Dict[str, Dict[str, str]] = {
    "SB-001": {"title": "Table open to anyone, row level security off", "popia": "s19",
               "fix": "Enable row level security on the table and add policies for each role. Revoke anon grants it does not need."},
    "SB-002": {"title": "Table open to every signed-in user, row level security off", "popia": "s19",
               "fix": "Enable row level security and add policies that limit each user to their own rows."},
    "SB-003": {"title": "Policy lets anyone read or change every row", "popia": "s19",
               "fix": "Replace USING (true) with a condition, for example (select auth.uid()) = user_id, or limit the policy to authenticated."},
    "SB-004": {"title": "Policy lets every signed-in user read or change every row", "popia": "s19",
               "fix": "Limit the policy to the user's own rows, or to a role or team they belong to."},
    "SB-005": {"title": "Anyone can insert rows", "popia": "s19",
               "fix": "Fine for a sign-up or contact form if anon cannot read the table. Add rate limiting or a CAPTCHA, and validate input with a check constraint or trigger."},
    "SB-006": {"title": "View bypasses row level security", "popia": "s19",
               "fix": "Recreate the view WITH (security_invoker = true), or revoke select from anon and authenticated."},
    "SB-007": {"title": "Materialized view readable through the API", "popia": "s19",
               "fix": "Materialized views have no row level security. Revoke select from anon and authenticated, or move it to a schema the API does not expose."},
    "SB-008": {"title": "Security definer function callable through the API", "popia": "s19",
               "fix": "Revoke execute from public, anon and authenticated unless it must be called by them. If it must, set search_path = '' and check the caller inside the function."},
    "SB-009": {"title": "Public storage bucket", "popia": "s19",
               "fix": "Make the bucket private and serve files with short-lived signed URLs. Keep public only for files meant for everyone, such as logos."},
    "SB-010": {"title": "Foreign table readable through the API", "popia": "s19; s72",
               "fix": "Foreign tables have no row level security. Revoke select from anon and authenticated, or move it out of the exposed schemas."},
    "SB-011": {"title": "Extra schema exposed through the API", "popia": "s19",
               "fix": "Every table in an exposed schema is reachable with the anon key, subject to grants and row level security. Confirm each one is protected, or remove the schema from the exposed list."},
}


def _f(rule_id: str, severity: str, obj: str, evidence: str, note: str = "") -> Dict[str, str]:
    r = RULES[rule_id]
    return {"rule_id": rule_id, "title": r["title"], "severity": severity, "popia": r["popia"],
            "object": obj, "evidence": evidence, "fix": r["fix"] + (f" {note}" if note else "")}


def _is_true(expr: Optional[str]) -> bool:
    if expr is None:
        return False
    e = re.sub(r"\s+", "", expr).lower()
    while e.startswith("(") and e.endswith(")"):
        e = e[1:-1]
    return e == "true"


def _pi_columns(columns: List[str]) -> List[str]:
    return [c for c in columns if PI_COLUMN.search(c or "")]


def _name(schema: str, name: str) -> str:
    return f"{schema}.{name}"


def analyse(inv: Dict[str, Any]) -> Dict[str, Any]:
    """Turn an inventory (the query's JSON value) into findings. Pure function."""
    if not isinstance(inv, dict) or not isinstance(inv.get("relations"), list):
        raise ValueError("not a POPIA Kit Supabase inventory")
    findings: List[Dict[str, str]] = []
    rels = {(r["schema"], r["name"]): r for r in inv.get("relations", [])}
    exposed = [s for s in inv.get("exposed_schemas", []) if isinstance(s, str)]

    def project_owned(schema: str) -> bool:
        return schema not in PLATFORM_SCHEMAS

    for (schema, name), r in sorted(rels.items()):
        if not project_owned(schema):
            continue
        obj = _name(schema, name)
        pi = _pi_columns(r.get("columns") or [])
        pi_note = f"Columns that look like personal information: {', '.join(pi[:8])}." if pi else ""
        kind = r.get("kind")
        if kind in ("r", "p") and not r.get("rls"):
            if r.get("anon_select") or r.get("anon_write"):
                ops = " and ".join(x for x, on in (("read", r.get("anon_select")), ("write", r.get("anon_write"))) if on)
                findings.append(_f("SB-001", "critical", obj, f"anon can {ops}; rls off", pi_note))
            elif r.get("auth_select") or r.get("auth_write"):
                findings.append(_f("SB-002", "critical" if pi else "high", obj, "authenticated has grants; rls off", pi_note))
        elif kind == "v" and not r.get("security_invoker") and (r.get("anon_select") or r.get("auth_select")):
            who = "anon" if r.get("anon_select") else "authenticated"
            if r.get("reads_auth_users"):
                findings.append(_f("SB-006", "critical", obj, f"{who} can select; view reads auth.users",
                                   "It exposes data from auth.users, such as email addresses."))
            else:
                findings.append(_f("SB-006", "critical" if (pi and r.get("anon_select")) else "high", obj,
                                   f"{who} can select; no security_invoker", pi_note))
        elif kind == "m" and (r.get("anon_select") or r.get("auth_select")):
            who = "anon" if r.get("anon_select") else "authenticated"
            findings.append(_f("SB-007", "critical" if (pi and r.get("anon_select")) else "high", obj, f"{who} can select", pi_note))
        elif kind == "f" and (r.get("anon_select") or r.get("auth_select")):
            findings.append(_f("SB-010", "high", obj, "readable by API roles", pi_note))

    for p in inv.get("policies", []):
        schema, table = p.get("schema", ""), p.get("table", "")
        if schema == "storage" or not project_owned(schema):
            continue
        roles = set(p.get("roles") or [])
        cmd = (p.get("cmd") or "").upper()
        obj = f"{_name(schema, table)} policy \"{p.get('name')}\""
        r = rels.get((schema, table), {})
        pi = _pi_columns(r.get("columns") or [])
        pi_note = f"Columns that look like personal information: {', '.join(pi[:8])}." if pi else ""
        open_to_anyone = bool(roles & {"anon", "public"})
        if cmd in ("SELECT", "ALL", "UPDATE", "DELETE") and _is_true(p.get("using")):
            if open_to_anyone:
                sev = "critical" if (pi and cmd in ("SELECT", "ALL")) else "high"
                findings.append(_f("SB-003", sev, obj, f"{cmd} for {', '.join(sorted(roles))} using (true)", pi_note))
            elif "authenticated" in roles:
                findings.append(_f("SB-004", "high" if pi else "medium", obj, f"{cmd} for authenticated using (true)", pi_note))
        if cmd in ("INSERT", "ALL") and open_to_anyone and _is_true(p.get("with_check")):
            readable = bool(r.get("anon_select")) and any(
                q for q in inv.get("policies", [])
                if q.get("schema") == schema and q.get("table") == table
                and (q.get("cmd") or "").upper() in ("SELECT", "ALL") and set(q.get("roles") or []) & {"anon", "public"})
            findings.append(_f("SB-005", "high" if readable else "low", obj,
                               "anon insert with check (true)" + ("; anon can also read" if readable else "")))

    for fn in inv.get("functions", []):
        schema = fn.get("schema", "")
        if not project_owned(schema) or not fn.get("security_definer"):
            continue
        anon, auth = fn.get("anon_execute"), fn.get("auth_execute")
        if not (anon or auth):
            continue
        fixed = fn.get("fixed_search_path")
        if anon:
            sev = "medium" if fixed else "high"
        else:
            sev = "low" if fixed else "medium"
        who = "anon" if anon else "authenticated"
        obj = f"{_name(schema, fn.get('name', ''))}({fn.get('args', '')})"
        findings.append(_f("SB-008", sev, obj, f"{who} can execute; search_path {'fixed' if fixed else 'not set'}"))

    for b in inv.get("buckets", []):
        if b.get("public"):
            findings.append(_f("SB-009", "high", f"storage bucket {b.get('id')}", "public = true"))

    for s in exposed:
        if s not in DEFAULT_SCHEMAS:
            findings.append(_f("SB-011", "info", f"schema {s}", "in pgrst.db_schemas"))

    findings.sort(key=lambda f: (SEVERITIES.index(f["severity"]), f["rule_id"], f["object"]))
    summary = {s: sum(1 for f in findings if f["severity"] == s) for s in SEVERITIES}
    return {
        "tool": "supabase_check", "version": __version__,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "postgres": inv.get("postgres"), "exposed_schemas": exposed,
        "counts": {"relations": len([1 for k in rels if project_owned(k[0])]),
                   "policies": len(inv.get("policies", [])), "functions": len(inv.get("functions", []))},
        "summary": summary, "findings": findings,
        "disclaimer": "Read-only check of database settings, not of data. Leads for review, not legal "
                      "conclusions. Engineering guidance only, not legal advice.",
    }


def parse_inventory(text: str) -> Dict[str, Any]:
    """Accept the raw JSON value, a JSON row or list of rows, or a CSV download from the SQL editor."""
    t = text.strip().lstrip("\ufeff")
    candidates: List[Any] = []
    try:
        candidates.append(json.loads(t))
    except ValueError:
        try:
            rows = list(csv.reader(io.StringIO(t)))
            for row in rows[1:] if rows and rows[0] and rows[0][0].strip() == "popia_kit_inventory" else rows:
                for cell in row:
                    try:
                        candidates.append(json.loads(cell))
                    except ValueError:
                        continue
        except csv.Error:
            pass
    for c in candidates:
        while True:
            if isinstance(c, list) and c:
                c = c[0]
            elif isinstance(c, dict) and "popia_kit_inventory" in c:
                c = c["popia_kit_inventory"]
                if isinstance(c, str):
                    c = json.loads(c)
            else:
                break
        if isinstance(c, dict) and isinstance(c.get("relations"), list):
            return c
    raise ValueError("could not find the inventory. Paste the single JSON value the query returns.")


def run_psql(env_var: str = "SUPABASE_DB_URL", timeout: int = 60) -> str:
    url = os.environ.get(env_var, "")
    if not url:
        raise RuntimeError(f"set {env_var} to your database connection string (Project settings, Database)")
    psql = shutil.which("psql")
    if not psql:
        raise RuntimeError("psql is not installed. Use `popia-kit supabase sql` in the SQL editor instead.")
    u = urlsplit(url)
    sslmode = dict(parse_qsl(u.query)).get("sslmode", "require")
    if u.scheme not in ("postgres", "postgresql") or not u.hostname:
        raise RuntimeError(f"{env_var} must be a postgresql:// connection string")
    env = {k: v for k, v in os.environ.items() if not k.startswith("PG")}
    env.update({
        "PGHOST": u.hostname, "PGPORT": str(u.port or 5432), "PGDATABASE": unquote(u.path.lstrip("/") or "postgres"),
        "PGUSER": unquote(u.username or "postgres"), "PGPASSWORD": unquote(u.password or ""),
        "PGSSLMODE": sslmode, "PGCONNECT_TIMEOUT": "15", "PGAPPNAME": "popia-kit supabase",
        "PGOPTIONS": "-c default_transaction_read_only=on -c statement_timeout=30000",
    })
    env.pop(env_var, None)
    proc = subprocess.run(  # nosec B603: fixed argv, no shell, no user input in arguments
        [psql, "-X", "-q", "-t", "-A", "-v", "ON_ERROR_STOP=1", "-f", str(SQL_PATH)],
        env=env, capture_output=True, text=True, timeout=timeout, check=False)
    if proc.returncode != 0:
        # Never echo the connection string; psql errors do not contain the password.
        raise RuntimeError("psql failed: " + (proc.stderr.strip().splitlines() or ["unknown error"])[-1][:300])
    return proc.stdout


def fmt_md(res: Dict[str, Any]) -> str:
    s = res["summary"]
    md = ["# POPIA Supabase check", "",
          f"- **Checked:** {res['checked_at']} · supabase_check {res['version']} · read-only, settings only",
          f"- **Postgres:** {res.get('postgres') or 'unknown'} · **Exposed schemas:** {', '.join(res['exposed_schemas']) or 'none'}",
          f"- **Looked at:** {res['counts']['relations']} tables and views, {res['counts']['policies']} policies, "
          f"{res['counts']['functions']} functions", "",
          "| Critical | High | Medium | Low | Info |", "|---|---|---|---|---|",
          f"| {s['critical']} | {s['high']} | {s['medium']} | {s['low']} | {s['info']} |", ""]
    if not res["findings"]:
        md.append("No findings. Keep running this after every schema change.")
    else:
        md += ["| Severity | ID | Finding | Object | Evidence | POPIA | Fix |", "|---|---|---|---|---|---|---|"]
        for f in res["findings"]:
            cells = [f["severity"], f["rule_id"], f["title"], f"`{f['object']}`", f["evidence"], f["popia"], f["fix"]]
            md.append("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")
    md += ["", f"> {res['disclaimer']} See DISCLAIMER.md."]
    return "\n".join(md)


def fmt_text(res: Dict[str, Any]) -> str:
    s = res["summary"]
    out = [f"summary: critical={s['critical']}  high={s['high']}  medium={s['medium']}  low={s['low']}  info={s['info']}"]
    for f in res["findings"]:
        out.append(f"[{f['severity'].upper()}] {f['rule_id']} {f['title']} ({f['popia']})\n  {f['object']}: {f['evidence']}\n  fix: {f['fix']}")
    out.append(res["disclaimer"])
    return "\n".join(out)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="popia-kit supabase",
                                 description="Read-only check of a Supabase project's database settings.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sql", help="print the read-only inventory query")
    c = sub.add_parser("check", help="turn the query's result into findings")
    c.add_argument("file", help="result file (JSON or CSV), or - for stdin")
    r = sub.add_parser("run", help="run the query with psql, then check")
    r.add_argument("--env", default="SUPABASE_DB_URL", help="environment variable holding the connection string")
    for p in (c, r):
        p.add_argument("--format", choices=["text", "md", "json"], default="text")
        p.add_argument("--out", help="write the report to a file")
        p.add_argument("--fail-on", choices=SEVERITIES, help="exit 1 if a finding at this severity or worse exists")
    a = ap.parse_args(argv)

    if a.cmd == "sql":
        sys.stdout.write(SQL_PATH.read_text(encoding="utf-8"))
        return 0
    try:
        if a.cmd == "check":
            text = sys.stdin.read() if a.file == "-" else Path(a.file).read_text(encoding="utf-8")
        else:
            text = run_psql(a.env)
        res = analyse(parse_inventory(text))
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as e:
        print(f"popia-kit supabase: {e}", file=sys.stderr)
        return 2
    out = {"text": fmt_text, "md": fmt_md, "json": lambda x: json.dumps(x, indent=2)}[a.format](res)
    if a.out:
        Path(a.out).write_text(out, encoding="utf-8")
        print(f"wrote {a.out}: " + "  ".join(f"{k}={v}" for k, v in res["summary"].items()))
    else:
        print(out)
    if a.fail_on:
        worst = SEVERITIES.index(a.fail_on)
        if any(SEVERITIES.index(f["severity"]) <= worst for f in res["findings"]):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
