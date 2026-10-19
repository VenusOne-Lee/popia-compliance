"""Scanner baseline, changed-files mode and extra reports."""
import io
import json
import shutil
import subprocess  # nosec B404: drives git in a throwaway repo
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import popia_scan  # noqa: E402

CORS_ANY = 'app.use(cors({ origin: "*" }));\n'
CORS_HEADER = 'res.setHeader("Access-Control-Allow-Origin", "*");\n'


def run(*args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = popia_scan.main(list(args))
    return code, out.getvalue(), err.getvalue()


class TestBaseline(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="popia-baseline-"))
        (self.dir / "a.js").write_text(CORS_ANY, encoding="utf-8")
        self.baseline = self.dir / "popia-baseline.json"

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def scan_json(self, *extra):
        code, out, _ = run(str(self.dir), "--rules", "SEC-007", "--format", "json", *extra)
        return code, json.loads(out)

    def test_known_findings_are_hidden_and_new_ones_fail(self):
        code, _, _ = run(str(self.dir), "--rules", "SEC-007", "--write-baseline", str(self.baseline))
        self.assertEqual(code, 0)
        code, res = self.scan_json("--baseline", str(self.baseline), "--fail-on", "medium")
        self.assertEqual((code, res["findings"]), (0, []))
        self.assertEqual(res["baseline"], {"known": 1, "fixed": 0})

        (self.dir / "b.js").write_text(CORS_HEADER, encoding="utf-8")
        code, res = self.scan_json("--baseline", str(self.baseline), "--fail-on", "medium")
        self.assertEqual(code, 1)
        self.assertEqual([f["file"] for f in res["findings"]], ["b.js"])

    def test_line_moves_keep_the_match(self):
        run(str(self.dir), "--rules", "SEC-007", "--write-baseline", str(self.baseline))
        (self.dir / "a.js").write_text("// moved down\n\n" + CORS_ANY, encoding="utf-8")
        _, res = self.scan_json("--baseline", str(self.baseline))
        self.assertEqual(res["findings"], [])

    def test_a_second_copy_still_shows(self):
        run(str(self.dir), "--rules", "SEC-007", "--write-baseline", str(self.baseline))
        (self.dir / "a.js").write_text(CORS_ANY + CORS_ANY, encoding="utf-8")
        _, res = self.scan_json("--baseline", str(self.baseline))
        self.assertEqual(len(res["findings"]), 1)

    def test_fixed_findings_are_counted(self):
        run(str(self.dir), "--rules", "SEC-007", "--write-baseline", str(self.baseline))
        (self.dir / "a.js").write_text("// fixed\n", encoding="utf-8")
        _, res = self.scan_json("--baseline", str(self.baseline))
        self.assertEqual(res["baseline"], {"known": 0, "fixed": 1})

    def test_baseline_holds_no_evidence(self):
        run(str(self.dir), "--rules", "SEC-007", "--write-baseline", str(self.baseline))
        text = self.baseline.read_text(encoding="utf-8")
        self.assertNotIn("cors", text)
        entry = json.loads(text)["findings"][0]
        self.assertEqual(set(entry), {"fingerprint", "rule_id", "file"})

    def test_bad_baseline_file(self):
        self.baseline.write_text('{"nope": 1}', encoding="utf-8")
        code, _, err = run(str(self.dir), "--baseline", str(self.baseline))
        self.assertEqual(code, 2)
        self.assertIn("cannot read baseline", err)

    def test_extra_reports_from_one_scan(self):
        md, sarif = self.dir / "r.md", self.dir / "r.sarif"
        code, out, _ = run(str(self.dir), "--rules", "SEC-007", "--format", "json",
                           "--report", f"md={md}", "--report", f"sarif={sarif}")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["summary"]["medium"], 1)
        self.assertIn("SEC-007", md.read_text(encoding="utf-8"))
        self.assertEqual(json.loads(sarif.read_text(encoding="utf-8"))["version"], "2.1.0")

    def test_bad_report_spec(self):
        with self.assertRaises(SystemExit):
            run(str(self.dir), "--report", "pdf=x.pdf")


@unittest.skipUnless(shutil.which("git"), "git not installed")
class TestChangedSince(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="popia-changed-"))
        self.git("init", "-q", "-b", "main")
        (self.dir / "old.js").write_text(CORS_ANY, encoding="utf-8")
        self.git("add", ".")
        self.git("-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "base")
        self.git("checkout", "-q", "-b", "feature")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.dir), *args], check=True, capture_output=True)  # nosec B603 B607

    def test_only_changed_files_are_reported(self):
        (self.dir / "new.js").write_text(CORS_HEADER, encoding="utf-8")
        code, out, _ = run(str(self.dir), "--rules", "SEC-007", "--format", "json", "--changed-since", "main")
        res = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual([f["file"] for f in res["findings"]], ["new.js"])
        self.assertEqual(res["changed_since"], {"ref": "main", "files": 1})

    def test_unsafe_ref_is_refused(self):
        code, _, err = run(str(self.dir), "--changed-since=--output=x")
        self.assertEqual(code, 2)
        self.assertIn("ref must be", err)

    def test_missing_ref(self):
        code, _, err = run(str(self.dir), "--changed-since", "no-such-branch")
        self.assertEqual(code, 2)
        self.assertIn("needs git", err)


if __name__ == "__main__":
    unittest.main()
