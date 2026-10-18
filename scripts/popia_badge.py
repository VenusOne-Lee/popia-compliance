#!/usr/bin/env python3
"""
popia_badge: turn a popia_scan JSON result into a status badge.

    python3 scripts/popia_scan.py . --format json --out popia-scan.json
    python3 scripts/popia_badge.py popia-scan.json --out popia-badge.svg
    python3 scripts/popia_badge.py popia-scan.json --shields-json --out popia-badge.json

The badge reports scanner counts and the scan date, for example
"POPIA scan | 0 critical · 2 high · 2026-10-18". It never states or implies that a
product is compliant, certified or approved: a scan result is a lead for review.
See docs/automation.md for the wording policy. Stdlib only. Python 3.8+.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional
from xml.sax.saxutils import escape

LABEL = "POPIA scan"
SEP = " · "  # middle dot
# Colours by worst severity present (shields.io palette).
COLOURS = {"critical": "#e05d44", "high": "#fe7d37", "medium": "#dfb317", "low": "#a4a61d",
           "info": "#97ca00", "none": "#4c1"}
SHIELDS_COLOURS = {"critical": "red", "high": "orange", "medium": "yellow", "low": "yellowgreen",
                   "info": "green", "none": "brightgreen"}
SEVERITIES = ["critical", "high", "medium", "low", "info"]

# Wording policy. These words must never appear in badge output.
FORBIDDEN = re.compile(r"compliant|compliance|certif|approved|accredited|passed|guarantee", re.I)


class BadgeWordingError(ValueError):
    pass


def worst(summary: dict) -> str:
    for s in SEVERITIES:
        if summary.get(s, 0):
            return s
    return "none"


def message(res: dict) -> str:
    s = res.get("summary", {})
    date = str(res.get("scanned_at", ""))[:10]
    parts = [f"{s.get('critical', 0)} critical", f"{s.get('high', 0)} high"]
    if date:
        parts.append(date)
    return SEP.join(parts)


def guard(*texts: str) -> None:
    for t in texts:
        if FORBIDDEN.search(t):
            raise BadgeWordingError(f"Badge text breaks the wording policy: {t!r}")


def _text_width(s: str) -> int:
    """Approximate Verdana 11px width, close enough to lay out a shields-style badge."""
    narrow, wide = set("ijl.,:;|!' ·()-1"), set("mwMW@%")
    w = 0.0
    for ch in s:
        w += 3.6 if ch in narrow else 9.5 if ch in wide else 7.2 if ch.isupper() else 6.6
    return int(w + 0.5)


def svg(label: str, msg: str, colour: str) -> str:
    guard(label, msg)
    lw, mw = _text_width(label) + 12, _text_width(msg) + 12
    total = lw + mw
    l, m = escape(label), escape(msg)
    title = escape(f"{label}: {msg}")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="20" role="img" aria-label="{title}">
<title>{title}</title>
<linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>
<clipPath id="r"><rect width="{total}" height="20" rx="3" fill="#fff"/></clipPath>
<g clip-path="url(#r)">
<rect width="{lw}" height="20" fill="#555"/>
<rect x="{lw}" width="{mw}" height="20" fill="{colour}"/>
<rect width="{total}" height="20" fill="url(#s)"/>
</g>
<g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
<text x="{lw / 2:.1f}" y="15" fill="#010101" fill-opacity=".3">{l}</text>
<text x="{lw / 2:.1f}" y="14">{l}</text>
<text x="{lw + mw / 2:.1f}" y="15" fill="#010101" fill-opacity=".3">{m}</text>
<text x="{lw + mw / 2:.1f}" y="14">{m}</text>
</g>
</svg>
"""


def shields_json(label: str, msg: str, sev: str) -> str:
    guard(label, msg)
    return json.dumps({"schemaVersion": 1, "label": label, "message": msg, "color": SHIELDS_COLOURS[sev]}, indent=2)


def render(res: dict, as_shields: bool = False, label: str = LABEL) -> str:
    sev = worst(res.get("summary", {}))
    msg = message(res)
    return shields_json(label, msg, sev) if as_shields else svg(label, msg, COLOURS[sev])


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="SVG or shields.io endpoint badge from a popia_scan JSON result.")
    ap.add_argument("scan_json", help="output of popia_scan.py --format json")
    ap.add_argument("--out", help="write here instead of stdout")
    ap.add_argument("--shields-json", action="store_true", help="emit a shields.io endpoint JSON instead of SVG")
    ap.add_argument("--label", default=LABEL)
    a = ap.parse_args(argv)
    try:
        res = json.loads(Path(a.scan_json).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"Cannot read scan JSON: {e}", file=sys.stderr)
        return 2
    try:
        out = render(res, a.shields_json, a.label)
    except BadgeWordingError as e:
        print(str(e), file=sys.stderr)
        return 3
    if a.out:
        Path(a.out).write_text(out, encoding="utf-8")
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
