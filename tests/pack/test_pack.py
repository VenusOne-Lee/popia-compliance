"""Tests for scripts/popia_pack.py. Run from the repo root:

    python3 -m unittest discover -s tests -t .
"""
import copy
import csv
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import popia_pack  # noqa: E402

ANSWERS = Path(__file__).resolve().parent / "kasi-bookings-answers.json"

EXPECTED_FILES = [
    "privacy-notice.md",
    "cookie-notice.md",
    "ropa.csv",
    "consent-wording.md",
    "paia-manual.md",
    "dsar-runbook.md",
    "breach-notice-data-subject.md",
    "operator-register.csv",
    "retention-schedule.csv",
    "README.md",
]

# One heading per s18(1) item, (a) to (h).
S18_HEADINGS = [
    "s18(1)(a)",
    "s18(1)(b)",
    "s18(1)(c)",
    "s18(1)(d)",
    "s18(1)(e)",
    "s18(1)(f)",
    "s18(1)(g)",
    "s18(1)(h)",
]


def load_answers():
    with open(ANSWERS, encoding="utf-8") as fh:
        return json.load(fh)


def headings(md):
    return [line for line in md.splitlines() if line.startswith("#")]


class TemplateEngineTests(unittest.TestCase):
    def render(self, src, ctx):
        return popia_pack.render_template(src, ctx)[0]

    def test_var_and_missing(self):
        self.assertEqual(self.render("Hi {{name}}.", {"name": "Lee"}), "Hi Lee.")
        self.assertEqual(self.render("Hi {{name}}.", {}), "Hi [[TODO: name]].")

    def test_if_else_unless(self):
        src = "{{#if a}}yes{{else}}no{{/if}}|{{#unless a}}u{{/unless}}"
        self.assertEqual(self.render(src, {"a": True}), "yes|")
        self.assertEqual(self.render(src, {"a": []}), "no|u")

    def test_each_nested(self):
        src = "{{#each ops}}[{{this.name}}{{#if this.tags}}:{{#each this.tags}}{{this}}{{/each}}{{/if}}]{{else}}none{{/each}}"
        ctx = {"ops": [{"name": "A", "tags": ["x", "y"]}, {"name": "B"}]}
        self.assertEqual(self.render(src, ctx), "[A:xy][B]")
        self.assertEqual(self.render(src, {"ops": []}), "none")

    def test_each_missing_field_todo(self):
        out = self.render("{{#each ops}}{{this.country}}{{/each}}", {"ops": [{}]})
        self.assertEqual(out, "[[TODO: ops.country]]")

    def test_standalone_block_lines_removed(self):
        src = "a\n{{#if x}}\nb\n{{/if}}\nc\n"
        self.assertEqual(self.render(src, {"x": True}), "a\nb\nc\n")
        self.assertEqual(self.render(src, {"x": False}), "a\nc\n")

    def test_unbalanced_raises(self):
        with self.assertRaises(popia_pack.TemplateError):
            self.render("{{#if a}}x", {})
        with self.assertRaises(popia_pack.TemplateError):
            self.render("{{#if a}}x{{/each}}", {})


class PackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = cls.tmp.name
        cls.files = popia_pack.generate(load_answers(), cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def read(self, name):
        with open(os.path.join(self.out, name), encoding="utf-8") as fh:
            return fh.read()

    def test_all_files_present(self):
        for name in EXPECTED_FILES:
            self.assertTrue(os.path.isfile(os.path.join(self.out, name)), name)
        self.assertEqual(sorted(self.files), sorted(EXPECTED_FILES))

    def test_no_unresolved_tags(self):
        for name in EXPECTED_FILES:
            content = self.read(name)
            self.assertNotIn("{{", content, name)
            self.assertNotIn("}}", content, name)

    def test_markdown_starts_with_disclaimer(self):
        for name in EXPECTED_FILES:
            if name.endswith(".md"):
                self.assertTrue(self.read(name).startswith(popia_pack.DISCLAIMER_LINE), name)

    def test_privacy_notice_has_every_s18_heading(self):
        hs = "\n".join(headings(self.read("privacy-notice.md")))
        for item in S18_HEADINGS:
            self.assertIn(item, hs, "missing heading for %s" % item)
        self.assertIn("Your rights", hs)
        self.assertIn("Complaints to the Information Regulator", hs)

    def test_privacy_notice_content(self):
        pn = self.read("privacy-notice.md")
        self.assertIn("Kasi Bookings (Pty) Ltd", pn)
        self.assertIn("Form 1", pn)
        self.assertIn("Form 2", pn)
        self.assertIn("inforegulator.org.za", pn)
        self.assertIn("United States", pn)
        self.assertIn("## AI features", pn)
        self.assertIn("## Direct marketing (s69)", pn)
        self.assertIn("do not rely on the existing-customer exception", pn)

    def test_regulator_contact_is_placeholder(self):
        for name in ("privacy-notice.md", "dsar-runbook.md", "paia-manual.md", "breach-notice-data-subject.md"):
            self.assertIn("[[VERIFY: Information Regulator contact details", self.read(name), name)

    def test_children_off_means_no_children_section(self):
        pn = self.read("privacy-notice.md")
        self.assertNotIn("## Children", pn)
        self.assertIn("We do not knowingly collect personal information of children", pn)
        self.assertNotIn("## Special personal information", pn)
        self.assertNotIn("Children: competent person consent", self.read("consent-wording.md"))

    def test_children_on_adds_section(self):
        answers = load_answers()
        answers.update({
            "children": True,
            "children_min_age": 13,
            "children_description": "Teenagers can book haircuts with a parent account.",
            "children_purpose": "book appointments",
            "children_consent_method": "A parent account confirms consent before the child books.",
        })
        files = popia_pack.generate(answers)
        self.assertIn("## Children (s34, s35)", files["privacy-notice.md"])
        self.assertNotIn("We do not knowingly collect", files["privacy-notice.md"])
        self.assertIn("Children: competent person consent", files["consent-wording.md"])
        self.assertIn("s57(1)(d)", files["README.md"])

    def test_consent_wording_only_relevant_patterns(self):
        cw = self.read("consent-wording.md")
        self.assertIn("### Email", cw)
        self.assertIn("### WhatsApp", cw)
        self.assertNotIn("### SMS", cw)
        self.assertNotIn("### Phone calls", cw)
        self.assertIn("AI processing notice", cw)
        self.assertNotIn("Call recording notice", cw)
        self.assertNotIn("Existing-customer exception", cw)

    def test_csv_outputs_parse(self):
        ropa = list(csv.DictReader(io.StringIO(self.read("ropa.csv"))))
        self.assertEqual(len(ropa), 3)
        self.assertEqual(ropa[2]["cross_border"], "United States")
        self.assertIn("pending", ropa[1]["operator_agreement"])
        ops = list(csv.DictReader(io.StringIO(self.read("operator-register.csv"))))
        self.assertEqual([o["operator"] for o in ops], ["Supabase", "Paystack", "Clickatell", "OpenAI"])
        self.assertEqual(ops[1]["cross_border"], "no")
        ret = list(csv.DictReader(io.StringIO(self.read("retention-schedule.csv"))))
        self.assertTrue(all(r["status"] == "verify for your sector" for r in ret))

    def test_readme_flags_pending_operator(self):
        self.assertIn("Operator Clickatell", self.read("README.md"))

    def test_no_todos_for_complete_answers(self):
        for name in EXPECTED_FILES:
            self.assertNotIn("[[TODO:", self.read(name), name)

    def test_style_no_em_dash_or_exclamation(self):
        for name in EXPECTED_FILES:
            content = self.read(name)
            self.assertNotIn("\u2014", content, name)
            self.assertNotRegex(content, r"!(?!\[)", name)


class MissingAnswerTests(unittest.TestCase):
    def test_todo_markers_and_readme_listing(self):
        answers = load_answers()
        for key in ("io_name", "operators", "security_summary"):
            answers.pop(key)
        files = popia_pack.generate(answers)
        pn = files["privacy-notice.md"]
        self.assertIn("[[TODO: io_name]]", pn)
        self.assertIn("[[TODO: operators]]", pn)
        self.assertIn("[[TODO: security_summary]]", pn)
        readme = files["README.md"]
        for key in ("io_name", "operators", "security_summary"):
            self.assertIn("| %s |" % key, readme)
        self.assertIn("[[TODO: operators]]", files["operator-register.csv"])

    def test_empty_answers_still_generate(self):
        files = popia_pack.generate({})
        self.assertEqual(sorted(files), sorted(EXPECTED_FILES))
        for content in files.values():
            self.assertNotIn("{{", content)
        self.assertIn("[[TODO: company_legal_name]]", files["privacy-notice.md"])


class TemplateFileTests(unittest.TestCase):
    def test_every_markdown_template_starts_with_disclaimer(self):
        for p in sorted((ROOT / "templates").glob("*.md")):
            with open(p, encoding="utf-8") as fh:
                self.assertEqual(fh.readline().rstrip("\n"), popia_pack.DISCLAIMER_LINE, p.name)

    def test_templates_style(self):
        for p in sorted((ROOT / "templates").iterdir()):
            text = p.read_text(encoding="utf-8")
            self.assertNotIn("\u2014", text, p.name)
            self.assertNotRegex(text, r"!(?!\[)", p.name)

    def test_questionnaire_shape(self):
        qs = popia_pack.load_questions()
        ids = [q["id"] for q in qs]
        self.assertEqual(len(ids), len(set(ids)))
        for q in qs:
            for key in ("id", "prompt", "type", "help"):
                self.assertIn(key, q, q.get("id"))
            if q.get("ask_if"):
                self.assertIn(q["ask_if"], ids, q["id"])


I18N_WARNING = ("> DRAFT translation. Machine-assisted, not yet reviewed by a native speaker or legal reviewer. "
                "Do not use in production until status is 'reviewed' in i18n/README.md.")
I18N_FILES = ["collection-notice.md", "marketing-consent.md", "cookie-banner.json", "breach-notice-short.md"]


class I18nTests(unittest.TestCase):
    def test_files_and_warnings(self):
        en_banner = json.loads((ROOT / "i18n" / "en" / "cookie-banner.json").read_text(encoding="utf-8"))
        en_keys = {k for k in en_banner if not k.startswith("_") and k not in ("lang", "status", "source")}
        for code in ("af", "zu", "xh", "tn"):
            folder = ROOT / "i18n" / code
            for name in I18N_FILES:
                path = folder / name
                self.assertTrue(path.is_file(), str(path))
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("\u2014", text, str(path))
                if name.endswith(".md"):
                    lines = text.splitlines()
                    self.assertEqual(lines[0], I18N_WARNING, str(path))
                    self.assertTrue(lines[2].startswith("> ") and len(lines[2]) > 20, str(path))
                    en = (ROOT / "i18n" / "en" / name).read_text(encoding="utf-8")
                    self.assertEqual(sorted(set(re.findall(r"\{\{\w+\}\}", en))),
                                     sorted(set(re.findall(r"\{\{\w+\}\}", text))), str(path))
                else:
                    data = json.loads(text)
                    self.assertEqual(data["status"], "draft")
                    self.assertEqual(data["_warning"], I18N_WARNING[2:])
                    self.assertTrue(en_keys <= set(data), str(path))
                    self.assertEqual(set(data["descriptions"]), set(en_banner["descriptions"]), str(path))


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "popia_pack.py")] + list(args),
                              capture_output=True, text=True)

    def test_print_questions(self):
        r = self.run_cli("--print-questions")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("company_legal_name", r.stdout)

    def test_example_then_generate(self):
        with tempfile.TemporaryDirectory() as d:
            ex = os.path.join(d, "ex.json")
            r = self.run_cli("--example", ex)
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(ex, encoding="utf-8") as fh:
                self.assertEqual(json.load(fh)["company_legal_name"], "Example Lodge (Pty) Ltd")
            out = os.path.join(d, "pack")
            r = self.run_cli("--answers", ex, "--out", out)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(sorted(os.listdir(out)), sorted(EXPECTED_FILES))


OPERATORS_APP = ROOT / "tests" / "fixtures" / "operators-app"


class FromCodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = popia_pack.answers_from_code(str(OPERATORS_APP), ["operators-app.co.za"])

    def test_operators_drafted_without_countries(self):
        ops = {o["name"]: o for o in self.code["operators"]}
        self.assertIn("Stripe", ops)
        self.assertEqual(ops["Stripe"]["service"], "Payments")
        self.assertIn("identity or passport numbers", ops["Stripe"]["data"])
        for o in ops.values():
            self.assertNotIn("country", o)
            self.assertNotIn("s72_basis", o)
            self.assertEqual(o["agreement"], "unknown")
        self.assertFalse(any(n.startswith("Unknown") for n in ops))

    def test_data_categories_are_questionnaire_options(self):
        q = {x["id"]: x for x in popia_pack.load_questions()}
        self.assertTrue(self.code["data_categories"])
        for c in self.code["data_categories"]:
            self.assertIn(c, q["data_categories"]["options"])
        self.assertIn("SA ID or passport number", self.code["data_categories"])

    def test_ai_children_and_special(self):
        self.assertTrue(self.code["ai_features"])
        self.assertIn("Anthropic", self.code["ai_provider"])
        self.assertTrue(self.code["children"])
        self.assertNotIn("special_pi", self.code)
        fc = self.code["_from_code"]
        self.assertIn("Anthropic", fc["special_pi_near"])
        self.assertIn("Twilio", fc["children_near"])
        self.assertEqual(fc["unknown_hosts"], ["api.partner-crm.example.co"])

    def test_own_answers_win(self):
        mine = {"operators": [{"name": "Own Host", "service": "Hosting", "country": "South Africa"}],
                "children": False}
        merged = popia_pack.merge_answers(self.code, mine)
        self.assertEqual(merged["operators"], mine["operators"])
        self.assertFalse(merged["children"])
        self.assertNotIn("operators", merged["_from_code"]["filled"])
        self.assertIn("data_categories", merged["_from_code"]["filled"])

    def test_notice_does_not_claim_no_transfers(self):
        files = popia_pack.generate(self.code)
        notice = files["privacy-notice.md"]
        self.assertNotIn("We do not transfer your personal information outside South Africa", notice)
        self.assertIn("VERIFY: add the processing country for every operator", notice)
        self.assertIn("| Stripe | Payments |", notice)
        self.assertIn("## Found in your code", files["README.md"])
        rows = list(csv.reader(io.StringIO(files["operator-register.csv"])))
        self.assertTrue(all(r[5] == "VERIFY" for r in rows[1:]), rows)

    def test_known_countries_still_say_no_transfer(self):
        answers = json.loads(ANSWERS.read_text(encoding="utf-8"))
        for op in answers.get("operators") or []:
            op["country"] = "South Africa"
        answers["cross_border_countries"] = []
        notice = popia_pack.generate(answers)["privacy-notice.md"]
        self.assertIn("We do not transfer your personal information outside South Africa", notice)

    def test_cli_from_code(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "pack")
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "popia_pack.py"), "--from-code",
                                str(OPERATORS_APP), "--ignore-host", "operators-app.co.za", "--out", out],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Drafted answers from code", r.stdout)
            saved = json.loads(Path(out, "answers.json").read_text(encoding="utf-8"))
            self.assertIn("operators", saved)
            self.assertIn("privacy-notice.md", os.listdir(out))


if __name__ == "__main__":
    unittest.main()
