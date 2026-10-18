"""popia_fleet aggregation on two tiny temporary repositories."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import popia_fleet  # noqa: E402

# Built at runtime so no secret-looking literal is committed.
SECRET = "sk_" + "live_" + "Zq7Lp2Xc9Vb4Nm6Kj8Hg3Fd5"


class TestFleet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        leaky = base / "leaky-app" / "src"
        leaky.mkdir(parents=True)
        (leaky / "pay.ts").write_text(f'export const stripeKey = "{SECRET}";\n', encoding="utf-8")
        clean = base / "clean-app" / "src"
        clean.mkdir(parents=True)
        (clean / "hello.ts").write_text("export const greet = (n: string) => `Hello ${n}`;\n", encoding="utf-8")
        cls.base = base
        cls.repos = popia_fleet.scan_targets(popia_fleet.targets_from_dir(str(base)))
        cls.res = popia_fleet.fleet_result(cls.repos, show_names=False)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_structure(self):
        a = self.res["aggregate"]
        for k in ("repos_scanned", "pct_repos_with_critical", "pct_repos_with_critical_or_high",
                  "median_findings_per_repo", "top_rules", "categories", "severity_totals"):
            self.assertIn(k, a)
        self.assertEqual(a["repos_scanned"], 2)
        self.assertEqual({c["category"] for c in a["categories"]} >= {
            "Secrets and credentials", "Access control", "Consent and trackers",
            "Personal information in code and logs", "Cross-border and third parties"}, True)
        for x in a["top_rules"]:
            self.assertGreaterEqual(x["pct_repos"], 0)
            self.assertLessEqual(x["pct_repos"], 100)

    def test_identities_hashed(self):
        ids = [r["id"] for r in self.repos]
        self.assertTrue(all(i.startswith("repo-") and len(i) == 15 for i in ids))
        out = json.dumps(self.res) + popia_fleet.fmt_md(self.res)
        self.assertNotIn("leaky-app", out)
        self.assertNotIn("clean-app", out)
        self.assertNotIn(str(self.base), out)

    def test_no_snippets_or_secrets(self):
        out = json.dumps(self.res) + popia_fleet.fmt_md(self.res)
        self.assertNotIn(SECRET, out)
        self.assertNotIn("Zq7L", out)
        self.assertNotIn('"snippet"', out)
        self.assertNotIn('"file"', out)
        self.assertNotIn("pay.ts", out)

    def test_show_names(self):
        repos = popia_fleet.scan_targets(popia_fleet.targets_from_dir(str(self.base)), show_names=True)
        self.assertEqual(sorted(r["id"] for r in repos), ["clean-app", "leaky-app"])

    def test_markdown_has_method_and_limits(self):
        md = popia_fleet.fmt_md(self.res)
        self.assertIn("## Methodology", md)
        self.assertIn("## Limitations", md)
        self.assertIn("not legal advice", md)

    def test_aggregate_maths(self):
        fake = [
            {"id": "a", "ok": True, "files_scanned": 3, "findings": 2, "summary": {"critical": 1, "high": 1},
             "rules": {"SEC-001": {"title": "t", "severity": "critical", "category": "Secrets and credentials", "count": 1},
                       "SEC-004": {"title": "t", "severity": "high", "category": "Access control", "count": 1}}},
            {"id": "b", "ok": True, "files_scanned": 1, "findings": 0, "summary": {}, "rules": {}},
            {"id": "c", "ok": False, "error": "clone failed"},
        ]
        a = popia_fleet.aggregate(fake)
        self.assertEqual(a["repos_scanned"], 2)
        self.assertEqual(a["repos_failed"], 1)
        self.assertEqual(a["pct_repos_with_critical"], 50.0)
        self.assertEqual(a["median_findings_per_repo"], 1.0)
        self.assertEqual(a["top_rules"][0]["rule_id"], "SEC-001")

    def test_category_mapping(self):
        self.assertEqual(popia_fleet.category("SEC-001", ["secrets"]), "Secrets and credentials")
        self.assertEqual(popia_fleet.category("SEC-004", ["supabase", "access-control"]), "Access control")
        self.assertEqual(popia_fleet.category("LOG-001", ["pii", "logging"]), "Personal information in code and logs")
        self.assertEqual(popia_fleet.category("TRK-001", []), "Consent and trackers")
        self.assertEqual(popia_fleet.category("XB-002", []), "Cross-border and third parties")


if __name__ == "__main__":
    unittest.main()
