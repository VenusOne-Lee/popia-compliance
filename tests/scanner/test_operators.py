"""Operator inventory tests. Fixtures are synthetic: no real keys, ID numbers or people."""
import csv
import io
from contextlib import redirect_stderr
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import popia_operators as po  # noqa: E402
from sa_id import fake  # noqa: E402

APP = ROOT / "tests" / "fixtures" / "operators-app"
DEMO = ROOT / "tests" / "fixtures" / "demo-app"


def by_vendor(res):
    return {o["vendor"]: o for o in res["operators"]}


def cats(o):
    return {f["category"] for f in o["personal_information"]}


class TestInventory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = po.inventory(str(APP), ["operators-app.co.za"])
        cls.ops = by_vendor(cls.res)

    def test_finds_every_source(self):
        for vendor in ("Stripe", "Supabase", "Twilio", "Anthropic", "Sentry", "Resend", "Zapier", "Formspree"):
            self.assertIn(vendor, self.ops)
        self.assertIn("manifest", self.ops["Stripe"]["sources"])
        self.assertIn("import", self.ops["Stripe"]["sources"])
        self.assertIn("config", self.ops["Supabase"]["sources"])
        self.assertEqual(self.ops["Zapier"]["sources"], ["api host"])

    def test_python_manifest_and_import(self):
        a = self.ops["Anthropic"]
        self.assertEqual(sorted(a["sources"]), ["import", "manifest"])
        self.assertIn("requirements.txt", {x["file"] for x in a["locations"]})

    def test_fields_traced_through_client_alias(self):
        stripe = self.ops["Stripe"]
        self.assertIn("contact", cats(stripe))
        self.assertTrue(stripe["traced"])
        self.assertIn("email", stripe["personal_information"][0]["fields"])

    def test_special_and_children_flags(self):
        self.assertTrue(self.ops["Anthropic"]["special_pi"])
        self.assertTrue(any("s27" in n for n in self.ops["Anthropic"]["notes"]))
        self.assertTrue(self.ops["Twilio"]["children"])
        self.assertTrue(any("s34" in n for n in self.ops["Twilio"]["notes"]))

    def test_by_design(self):
        self.assertIn("recipient", self.ops["Resend"]["by_design"])
        self.assertIn("form", self.ops["Formspree"]["by_design"])
        self.assertEqual(self.ops["Anthropic"]["by_design"], "")

    def test_cdn_import(self):
        self.assertIn("supabase-edge.ts", {x["file"] for x in self.ops["Resend"]["locations"]})
        self.assertIn("resend", self.ops["Resend"]["packages"])

    def test_unknown_host_and_ignore(self):
        unknown = [v for v in self.ops if v.startswith("Unknown: ")]
        self.assertEqual(unknown, ["Unknown: api.partner-crm.example.co"])
        res = po.inventory(str(APP))
        self.assertIn("Unknown: api.operators-app.co.za", by_vendor(res))

    def test_reference_hosts_and_tests_skipped(self):
        self.assertFalse(any("w3.org" in v for v in self.ops))
        self.assertNotIn("OpenAI", self.ops)  # only imported in tests/

    def test_summary_and_order(self):
        s = self.res["summary"]
        self.assertEqual(s["third_parties"], len(self.res["operators"]))
        self.assertEqual(s["unknown_hosts"], 1)
        self.assertEqual(self.res["operators"][-1]["category"], "unknown")
        self.assertIn("not legal advice", self.res["disclaimer"])

    def test_untraced_manifest_vendor(self):
        res = by_vendor(po.inventory(str(DEMO)))
        self.assertFalse(res["Supabase"]["traced"])
        self.assertTrue(any("No call found" in n for n in res["Supabase"]["notes"]))
        self.assertIn("phone", res["OpenAI"]["personal_information"][0]["fields"])


class TestFormats(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = po.inventory(str(APP), ["operators-app.co.za"])

    def test_markdown(self):
        md = po.fmt_md(self.res)
        self.assertIn("| Stripe | payments |", md)
        self.assertIn("s72", md)
        self.assertIn("What this cannot see", md)
        self.assertNotIn("\u2014", md)
        self.assertNotIn("\u2013", md)

    def test_csv_has_ropa_columns(self):
        rows = list(csv.DictReader(io.StringIO(po.fmt_csv(self.res))))
        self.assertEqual(len(rows), len(self.res["operators"]))
        for col in ("hosting_country", "s72_basis", "operator_agreement"):
            self.assertIn(col, rows[0])
            self.assertEqual(rows[0][col], "")

    def test_json_round_trip(self):
        out = json.loads(json.dumps(self.res))
        self.assertEqual(out["tool"], "popia_operators")
        self.assertFalse(any(k.startswith("_") for o in out["operators"] for k in o))

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "ops.csv"
            with redirect_stderr(io.StringIO()):
                self.assertEqual(po.main([str(APP), "--format", "csv", "--out", str(out)]), 0)
            self.assertTrue(out.read_text(encoding="utf-8").startswith("vendor,category,"))


class TestHelpers(unittest.TestCase):
    def test_pi_terms(self):
        self.assertEqual(po.pi_in_text("const { firstName, idNumber } = body")["name"], ["first_name"])
        self.assertIn("id_number", po.pi_in_text("const { firstName, idNumber } = body")["id_number"])
        self.assertNotIn("address", po.pi_in_text("const emailAddress = x; const ipAddress = y"))
        self.assertIn("online", po.pi_in_text("const ipAddress = y"))
        self.assertIn("address", po.pi_in_text("customer.address"))

    def test_js_package_names(self):
        self.assertEqual(po._js_package("@supabase/supabase-js/dist/x"), "@supabase/supabase-js")
        self.assertEqual(po._js_package("npm:openai@4.2.0"), "openai")
        self.assertEqual(po._js_package("https://esm.sh/@supabase/supabase-js@2"), "@supabase/supabase-js")
        self.assertIsNone(po._js_package("./local"))
        self.assertIsNone(po._js_package("node:fs"))

    def test_python_modules(self):
        self.assertEqual(po._py_package("google.generativeai"), "google-generativeai")
        self.assertEqual(po._bindings_py("from google import genai"), [("google-genai", ["genai"])])
        self.assertEqual(po._bindings_py("import stripe"), [("stripe", ["stripe"])])

    def test_pyproject_reads_dependencies_only(self):
        text = ('[project]\nname = "app"\nkeywords = ["stripe", "openai"]\n'
                'dependencies = [\n  "anthropic>=0.40",\n]\n'
                '[project.optional-dependencies]\ndev = ["sentry-sdk"]\n')
        names = [n for n, _ in po._manifest_names("pyproject.toml", text)]
        self.assertIn("anthropic", names)
        self.assertIn("sentry-sdk", names)
        self.assertNotIn("stripe", names)
        self.assertNotIn("openai", names)

    def test_evidence_is_redacted(self):
        fid = fake(1, seed=11)[0]
        email = "someone" + "@" + "fixture.test"
        with tempfile.TemporaryDirectory() as d:
            Path(d, "a.ts").write_text(
                f'fetch("https://hooks.zapier.com/x?id={fid}&e={email}", {{ method: "POST" }});\n',
                encoding="utf-8")
            res = po.inventory(d)
        text = json.dumps(res)
        self.assertIn("Zapier", text)
        self.assertNotIn(fid, text)
        self.assertNotIn(email, text)

    def test_symlinks_not_followed(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as outside:
            Path(outside, "requirements.txt").write_text("stripe\n", encoding="utf-8")
            try:
                Path(d, "requirements.txt").symlink_to(Path(outside, "requirements.txt"))
            except OSError:
                self.skipTest("symlinks not supported")
            self.assertEqual(po.inventory(d)["operators"], [])


if __name__ == "__main__":
    unittest.main()
