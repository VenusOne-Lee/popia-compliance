"""Scanner rule tests. Secrets, ID numbers and card numbers are generated at runtime, never committed."""
import base64
import json
import os
import random
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import popia_scan  # noqa: E402
from sa_id import luhn_check_digit, is_valid  # noqa: E402

DEMO = ROOT / "tests" / "fixtures" / "demo-app"


def realistic_fake_id(seed=7):
    rng = random.Random(seed)
    while True:
        d = date(1985, 1, 1).toordinal() + rng.randint(0, 3000)
        dob = date.fromordinal(d)
        first12 = f"{dob:%y%m%d}{rng.randint(0, 9999):04d}08"
        cand = first12 + luhn_check_digit(first12)
        if is_valid(cand):
            return cand


def luhn_card(prefix="5", length=16, seed=3):
    rng = random.Random(seed)
    body = prefix + "".join(str(rng.randint(0, 9)) for _ in range(length - len(prefix) - 1))
    return body + luhn_check_digit(body)


def fake_service_jwt():
    enc = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    return f"{enc({'alg': 'HS256', 'typ': 'JWT'})}.{enc({'role': 'service_role', 'iss': 'supabase', 'ref': 'demo'})}.{'x' * 43}"


def ids(res):
    return {f["rule_id"] for f in res["findings"]}


class DemoAppTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = popia_scan.scan(str(DEMO))

    def test_expected_rules_fire(self):
        expected = {"SEC-004", "SEC-005", "SEC-006", "SEC-007", "SEC-009", "SEC-011", "SEC-015", "SEC-016",
                    "CON-001", "CON-002", "CON-003", "SPI-001", "CHI-001", "LOG-001", "PII-004", "PII-005",
                    "STO-001", "DOC-001", "DOC-002", "DSR-001", "RET-001", "DM-001", "AI-001", "XB-001", "XB-002"}
        missing = expected - ids(self.res)
        self.assertFalse(missing, f"rules did not fire: {sorted(missing)}")

    def test_summary_counts_match(self):
        total = sum(self.res["summary"].values())
        self.assertEqual(total, len(self.res["findings"]))

    def test_rls_enabled_table_not_flagged(self):
        flagged = [f for f in self.res["findings"] if f["rule_id"] == "SEC-004"]
        self.assertTrue(any("profiles" in f["snippet"] for f in flagged))
        self.assertFalse(any("leads" in f["snippet"] for f in flagged))


class RuntimeSecretsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def test_secrets_and_pi(self):
        sid = realistic_fake_id()
        card = luhn_card()
        aws = "AKIA" + "Q" * 4 + "7" * 4 + "ZXCVBNMA"
        self.write("src/config.ts", f'export const aws = "{aws}";\nexport const sr = "{fake_service_jwt()}";\n')
        self.write(".env.local", "VITE_SUPABASE_SERVICE_ROLE_KEY=" + "a" * 40 + "\n")
        self.write("data/customers.csv", f"name,id\nTest Person,{sid}\nCard,{card}\n")
        res = popia_scan.scan(str(self.root))
        got = ids(res)
        for rid in ("SEC-001", "SEC-002", "SEC-003", "SEC-014", "PII-001", "PII-003"):
            self.assertIn(rid, got, rid)
        # never echo the full values
        blob = json.dumps(res)
        self.assertNotIn(sid, blob)
        self.assertNotIn(card, blob)
        self.assertNotIn(aws, blob)

    def test_synthetic_ids_ignored(self):
        from sa_id import fake
        self.write("seed.json", json.dumps({"ids": fake(3, seed=1)}))
        self.assertNotIn("PII-001", ids(popia_scan.scan(str(self.root))))

    def test_inline_suppression(self):
        self.write("a.ts", 'el.innerHTML = safeHtml; // popia-ignore: SEC-011 sanitised with DOMPurify\n')
        self.assertNotIn("SEC-011", ids(popia_scan.scan(str(self.root))))

    def test_popiaignore(self):
        self.write("vendor-x/a.ts", "el.innerHTML = x;\n")
        self.write(".popiaignore", "vendor-x/\n")
        self.assertNotIn("SEC-011", ids(popia_scan.scan(str(self.root))))

    def test_clean_app_has_no_high(self):
        self.write("src/App.tsx", 'import { ConsentProvider } from "./consent";\n'
                   '<a href="/privacy">Privacy notice</a> <a href="/paia-manual">PAIA manual</a>\n'
                   '<input type="email" name="email" />\n<input type="checkbox" name="marketing_opt_in" />\n')
        self.write("supabase/migrations/1.sql",
                   "create table public.profiles (id uuid primary key, email text);\n"
                   "alter table public.profiles enable row level security;\n"
                   "create policy own on public.profiles for select to authenticated using ((select auth.uid()) = id);\n"
                   "select cron.schedule('popia-retention','15 2 * * *','select privacy.enforce_retention()');\n")
        self.write("src/account.ts", "export async function deleteMyAccount() {}\n")
        res = popia_scan.scan(str(self.root))
        bad = [f for f in res["findings"] if f["severity"] in ("critical", "high")]
        self.assertEqual(bad, [], bad)


class FormatTest(unittest.TestCase):
    def test_formats(self):
        res = popia_scan.scan(str(DEMO))
        rules = popia_scan.load_rules()
        sarif = json.loads(popia_scan.fmt_sarif(res, rules))
        self.assertEqual(sarif["version"], "2.1.0")
        self.assertTrue(sarif["runs"][0]["results"])
        md = popia_scan.fmt_md(res)
        self.assertIn("# POPIA scan report", md)
        self.assertIn("not legal advice", md)

    def test_rule_ids_unique_and_documented(self):
        rules = popia_scan.load_rules()
        self.assertEqual(len(rules), len({r.id for r in rules}))
        for r in rules:
            self.assertTrue(r.popia and r.message and r.fix, r.id)

    def test_fail_on_exit_code(self):
        self.assertEqual(popia_scan.main([str(DEMO), "--fail-on", "critical", "--format", "json", "--out", os.devnull]), 1)


if __name__ == "__main__":
    unittest.main()
