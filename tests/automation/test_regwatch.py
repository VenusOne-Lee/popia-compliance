"""regwatch parsing and diff tests, offline against a synthetic HTML fixture."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import regwatch  # noqa: E402

FIXTURE = ROOT / "tests" / "automation" / "fixtures" / "regulator-list.html"
BASE = "https://inforegulator.org.za/media-statements/"


def config():
    return json.loads((ROOT / "regwatch" / "sources.json").read_text(encoding="utf-8"))


class TestParse(unittest.TestCase):
    def setUp(self):
        self.items = regwatch.extract_items(FIXTURE.read_text(encoding="utf-8"), BASE, config())

    def test_extracts_list_items_only(self):
        titles = [i["title"] for i in self.items]
        self.assertEqual(titles, [
            "Fixture statement alpha on test topic one",
            "Fixture enforcement notice beta issued to test entity",
            "Fixture guidance gamma about sample rules",
        ])

    def test_resolves_relative_links(self):
        self.assertEqual(self.items[0]["url"],
                         "https://inforegulator.org.za/wp-content/uploads/2026/09/Fixture-Statement-Alpha.pdf")
        self.assertTrue(self.items[1]["url"].startswith("https://example.test/"))

    def test_skips_nav_footer_pagination_short_and_duplicates(self):
        urls = [i["url"] for i in self.items]
        self.assertEqual(len(urls), len(set(urls)))
        joined = " ".join(urls)
        for bad in ("facebook", "mailto:", "/page/2/", "/category/", "/short/", "/about/"):
            self.assertNotIn(bad, joined)


class TestDiffAndState(unittest.TestCase):
    def test_diff_and_update(self):
        items = regwatch.extract_items(FIXTURE.read_text(encoding="utf-8"), BASE, config())
        state = {"version": 1, "sources": {}}
        self.assertEqual(len(regwatch.diff(items, [])), 3)
        regwatch.update_state(state, "media-statements", items[:2], "2026-10-18T04:00:00+00:00")
        new = regwatch.diff(items, state["sources"]["media-statements"]["seen"])
        self.assertEqual([i["title"] for i in new], ["Fixture guidance gamma about sample rules"])
        regwatch.update_state(state, "media-statements", items, "2026-10-18T04:00:00+00:00")
        self.assertEqual(len(state["sources"]["media-statements"]["seen"]), 3)
        self.assertEqual(regwatch.diff(items, state["sources"]["media-statements"]["seen"]), [])

    def test_issue_body_has_law_change_sections(self):
        results = [{"name": "Test source", "url": BASE,
                    "new": [{"title": "Guidance note on direct marketing update", "url": BASE + "x.pdf"}]}]
        body = regwatch.issue_body(results, "2026-10-18T04:00:00+00:00")
        for part in ("## What changed", "## Source link", "## Effective date", "TBC", "## Files likely affected",
                     "references/10-regulatory-watch.md", "references/05-direct-marketing.md",
                     "Update affected references", "CHANGELOG", "evals"):
            self.assertIn(part, body)

    def test_cli_offline_dry_run_does_not_write_state(self):
        with tempfile.TemporaryDirectory() as d:
            st = Path(d) / "state.json"
            st.write_text('{"version": 1, "sources": {}}', encoding="utf-8")
            out = Path(d) / "r.md"
            rc = regwatch.main(["--dry-run", "--offline-fixture", str(FIXTURE), "--state", str(st),
                                "--only", "media-statements", "--out", str(out)])
            self.assertEqual(rc, 0)
            self.assertIn("3 new item(s)", out.read_text(encoding="utf-8"))
            self.assertEqual(json.loads(st.read_text(encoding="utf-8"))["sources"], {})

    def test_sources_config_has_required_pages(self):
        urls = {s["url"] for s in config()["sources"]}
        self.assertIn("https://inforegulator.org.za/media-statements/", urls)
        self.assertIn("https://inforegulator.org.za/enforcement-notices/", urls)


if __name__ == "__main__":
    unittest.main()
