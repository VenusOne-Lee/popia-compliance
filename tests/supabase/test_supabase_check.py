"""popia-kit supabase: parsing, rules and exit codes. Optional live run against Postgres."""
import csv
import io
import json
import os
import re
import shutil
import subprocess  # nosec B404: test runs psql against a throwaway database
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import supabase_check as sc  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "supabase"
SEEDED = (FIX / "seeded-risky.json").read_text(encoding="utf-8")
HARDENED = (FIX / "lovable-hardened.json").read_text(encoding="utf-8")


def ids(res):
    return sorted((f["rule_id"], f["object"], f["severity"]) for f in res["findings"])


def run(*args, stdin=None):
    out, err = io.StringIO(), io.StringIO()
    old = sys.stdin
    if stdin is not None:
        sys.stdin = io.StringIO(stdin)
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = sc.main(list(args))
    finally:
        sys.stdin = old
    return code, out.getvalue(), err.getvalue()


class TestParse(unittest.TestCase):
    def test_raw_wrapped_list_and_csv(self):
        inv = sc.parse_inventory(SEEDED)
        raw = json.dumps(inv)
        self.assertEqual(sc.parse_inventory(raw)["relations"], inv["relations"])
        self.assertEqual(sc.parse_inventory(json.dumps([{"popia_kit_inventory": inv}]))["tool"], inv["tool"])
        self.assertEqual(sc.parse_inventory(json.dumps({"popia_kit_inventory": raw}))["tool"], inv["tool"])
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["popia_kit_inventory"])
        w.writerow([raw])
        self.assertEqual(sc.parse_inventory("\ufeff" + buf.getvalue())["relations"], inv["relations"])

    def test_rejects_other_input(self):
        for bad in ("", "hello", "[]", '{"a": 1}', "a,b\n1,2\n"):
            with self.assertRaises(ValueError):
                sc.parse_inventory(bad)


class TestRules(unittest.TestCase):
    def test_seeded_findings(self):
        res = sc.analyse(sc.parse_inventory(SEEDED))
        found = {(r, o) for r, o, _ in ids(res)}
        for want in [("SB-001", "public.profiles"), ("SB-002", "public.staff_only"),
                     ("SB-006", "public.user_emails"), ("SB-007", "public.stats"),
                     ("SB-009", "storage bucket avatars"),
                     ("SB-005", 'public.leads policy "lead_in"')]:
            self.assertIn(want, found)
        self.assertEqual(res["summary"]["critical"], 3)
        self.assertEqual(res["summary"]["high"], 4)

    def test_hardened_app_is_quiet(self):
        res = sc.analyse(sc.parse_inventory(HARDENED))
        self.assertEqual(ids(res), [("SB-005", 'public.newsletter_signups policy "Anyone can sign up"', "low"),
                                    ("SB-011", "schema privacy", "info")])

    def test_platform_schemas_skipped(self):
        inv = sc.parse_inventory(HARDENED)
        res = sc.analyse(inv)
        self.assertFalse([f for f in res["findings"] if f["object"].startswith(("storage.", "graphql_public."))])

    def _one(self, **rel):
        base = {"schema": "public", "name": "t", "kind": "r", "rls": False, "rls_forced": False,
                "security_invoker": False, "anon_select": False, "anon_write": False, "auth_select": False,
                "auth_write": False, "columns": ["id"], "reads_auth_users": False}
        base.update(rel)
        return {"exposed_schemas": ["public"], "relations": [base], "functions": [], "policies": [], "buckets": []}

    def test_rls_off_but_no_grants_is_fine(self):
        self.assertEqual(sc.analyse(self._one())["findings"], [])

    def test_personal_information_raises_severity(self):
        plain = sc.analyse(self._one(auth_select=True))["findings"][0]
        pi = sc.analyse(self._one(auth_select=True, columns=["id", "email"]))["findings"][0]
        self.assertEqual((plain["rule_id"], plain["severity"]), ("SB-002", "high"))
        self.assertEqual((pi["rule_id"], pi["severity"]), ("SB-002", "critical"))

    def test_open_policy_with_personal_information(self):
        inv = self._one(rls=True, anon_select=True, columns=["id", "id_number"])
        inv["policies"] = [{"schema": "public", "table": "t", "name": "open", "permissive": "PERMISSIVE",
                            "roles": ["anon"], "cmd": "SELECT", "using": "true", "with_check": None}]
        f = sc.analyse(inv)["findings"]
        self.assertEqual([(x["rule_id"], x["severity"]) for x in f], [("SB-003", "critical")])

    def test_security_definer_levels(self):
        def sev(**fn):
            base = {"schema": "public", "name": "f", "args": "", "security_definer": True,
                    "fixed_search_path": False, "anon_execute": False, "auth_execute": False}
            base.update(fn)
            inv = {"exposed_schemas": ["public"], "relations": [], "functions": [base], "policies": [], "buckets": []}
            return [x["severity"] for x in sc.analyse(inv)["findings"]]
        self.assertEqual(sev(anon_execute=True), ["high"])
        self.assertEqual(sev(anon_execute=True, fixed_search_path=True), ["medium"])
        self.assertEqual(sev(auth_execute=True), ["medium"])
        self.assertEqual(sev(auth_execute=True, fixed_search_path=True), ["low"])
        self.assertEqual(sev(), [])
        self.assertEqual(sev(anon_execute=True, security_definer=False), [])

    def test_copy_follows_house_rules(self):
        res = sc.analyse(sc.parse_inventory(SEEDED))
        text = sc.fmt_text(res) + sc.fmt_md(res)
        self.assertNotRegex(text, "[\u2013\u2014!]")
        self.assertNotRegex(text.lower(), r"\b(compliant|certified|approved)\b")
        self.assertIn("not legal advice", text)


class TestCli(unittest.TestCase):
    def test_sql_is_read_only(self):
        code, out, _ = run("sql")
        self.assertEqual(code, 0)
        body = "\n".join(l for l in out.splitlines() if not l.strip().startswith("--")).lower()
        self.assertIn("popia_kit_inventory", body)
        body = re.sub(r"'[^']*'", "''", body)  # privilege names in quotes are arguments, not statements
        self.assertTrue(body.lstrip().startswith("with "))
        self.assertEqual(body.count(";"), 1)
        self.assertNotRegex(body, r"\b(insert|update|delete|drop|alter|create|grant|revoke|truncate|copy)\b")
        self.assertNotIn("security definer", body)

    def test_check_formats_and_fail_on(self):
        p = str(FIX / "seeded-risky.json")
        code, out, _ = run("check", p, "--format", "json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["summary"]["critical"], 3)
        self.assertEqual(run("check", p, "--fail-on", "high")[0], 1)
        self.assertEqual(run("check", str(FIX / "lovable-hardened.json"), "--fail-on", "medium")[0], 0)
        code, out, _ = run("check", "-", "--format", "md", stdin=SEEDED)
        self.assertEqual(code, 0)
        self.assertIn("| Critical | High |", out)

    def test_bad_input_exits_2(self):
        code, _, err = run("check", "-", stdin="not json")
        self.assertEqual(code, 2)
        self.assertIn("could not find the inventory", err)

    def test_run_needs_url_and_never_echoes_it(self):
        env = dict(os.environ)
        os.environ.pop("SUPABASE_DB_URL", None)
        try:
            code, _, err = run("run")
            self.assertEqual(code, 2)
            self.assertIn("SUPABASE_DB_URL", err)
            marker = "not" + "-a-real-" + "value"
            os.environ["SUPABASE_DB_URL"] = "https://user:" + marker + "@example.com/db"
            code, _, err = run("run")
            self.assertEqual(code, 2)
            self.assertNotIn(marker, err)
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_cli_dispatch(self):
        import cli
        self.assertIn("supabase", cli.COMMANDS)
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(cli.main(["supabase", "check", str(FIX / "lovable-hardened.json")]), 0)
        self.assertIn("SB-005", out.getvalue())


@unittest.skipUnless(os.environ.get("POPIA_TEST_PG_URL") and shutil.which("psql"),
                     "set POPIA_TEST_PG_URL to a throwaway Postgres to run the SQL")
class TestLiveSql(unittest.TestCase):
    """Seeds a throwaway database with Supabase-like roles, then runs the real query through psql."""

    SEED = ROOT / "tests" / "fixtures" / "supabase" / "seed.sql"

    def test_query_runs_read_only_and_finds_seeded_risks(self):
        url = os.environ["POPIA_TEST_PG_URL"]
        subprocess.run(["psql", url, "-X", "-q", "-v", "ON_ERROR_STOP=1", "-f", str(self.SEED)],  # nosec B603 B607
                       check=True, capture_output=True, text=True)
        old = os.environ.get("SUPABASE_DB_URL")
        os.environ["SUPABASE_DB_URL"] = url
        try:
            text = sc.run_psql()
        finally:
            if old is None:
                os.environ.pop("SUPABASE_DB_URL", None)
            else:
                os.environ["SUPABASE_DB_URL"] = old
        res = sc.analyse(sc.parse_inventory(text))
        self.assertEqual(res["postgres"].split(".")[0].isdigit(), True)
        found = {(r, o) for r, o, _ in ids(res)}
        for want in [("SB-001", "public.profiles"), ("SB-006", "public.user_emails"), ("SB-009", "storage bucket avatars"),
                     ("SB-008", "public.wipe(uid uuid)")]:
            self.assertIn(want, found)

    def test_session_refuses_writes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            probe = Path(d) / "probe.sql"
            probe.write_text("create table public.popia_probe (i int);", encoding="utf-8")
            old_path, old_url = sc.SQL_PATH, os.environ.get("SUPABASE_DB_URL")
            sc.SQL_PATH = probe
            os.environ["SUPABASE_DB_URL"] = os.environ["POPIA_TEST_PG_URL"]
            try:
                with self.assertRaisesRegex(RuntimeError, "read-only"):
                    sc.run_psql()
            finally:
                sc.SQL_PATH = old_path
                if old_url is None:
                    os.environ.pop("SUPABASE_DB_URL", None)
                else:
                    os.environ["SUPABASE_DB_URL"] = old_url


if __name__ == "__main__":
    unittest.main()
