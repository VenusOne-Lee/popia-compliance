"""popia_badge output and wording guard."""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import popia_badge  # noqa: E402

BANNED = re.compile(r"compliant|certified|approved", re.I)


def res(**summary):
    s = {k: 0 for k in popia_badge.SEVERITIES}
    s.update(summary)
    return {"summary": s, "scanned_at": "2026-10-18T09:00:00+00:00"}


class TestBadge(unittest.TestCase):
    def test_message(self):
        self.assertEqual(popia_badge.message(res(high=2)), "0 critical · 2 high · 2026-10-18")

    def test_site_check_date(self):
        site = {"summary": {"medium": 1}, "checked_at": "2026-10-18T09:00:00+00:00"}
        self.assertEqual(popia_badge.message(site), "0 critical · 0 high · 2026-10-18")

    def test_colour_by_worst(self):
        self.assertIn(popia_badge.COLOURS["critical"], popia_badge.render(res(critical=1, low=4)))
        self.assertIn(popia_badge.COLOURS["medium"], popia_badge.render(res(medium=1)))
        self.assertIn(popia_badge.COLOURS["none"], popia_badge.render(res()))
        j = json.loads(popia_badge.render(res(high=1), as_shields=True))
        self.assertEqual(j, {"schemaVersion": 1, "label": "POPIA scan",
                             "message": "0 critical · 1 high · 2026-10-18", "color": "orange"})

    def test_svg_well_formed(self):
        import xml.dom.minidom
        xml.dom.minidom.parseString(popia_badge.render(res(high=3)))

    def test_no_banned_words_in_any_output(self):
        for summary in ({}, {"critical": 1}, {"high": 5}, {"info": 9}):
            for shields in (False, True):
                self.assertIsNone(BANNED.search(popia_badge.render(res(**summary), shields)))

    def test_guard_blocks_banned_label(self):
        for label in ("POPIA compliant", "POPIA Certified", "Approved by scan"):
            with self.assertRaises(popia_badge.BadgeWordingError):
                popia_badge.render(res(), label=label)

    def test_source_strings_free_of_banned_words(self):
        """Only the guard regex and docstring may name the banned words."""
        src = (ROOT / "scripts" / "popia_badge.py").read_text(encoding="utf-8")
        for name in ("LABEL", "SEP"):
            self.assertIsNone(BANNED.search(getattr(popia_badge, name)))
        self.assertIsNone(BANNED.search(json.dumps(popia_badge.COLOURS)))
        self.assertIn("FORBIDDEN", src)

    def test_cli_rejects_banned_label(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"
            p.write_text(json.dumps(res()), encoding="utf-8")
            self.assertEqual(popia_badge.main([str(p), "--label", "compliant", "--out", str(Path(d) / "b.svg")]), 3)
            self.assertEqual(popia_badge.main([str(p), "--out", str(Path(d) / "b.svg")]), 0)
            self.assertIsNone(BANNED.search((Path(d) / "b.svg").read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
