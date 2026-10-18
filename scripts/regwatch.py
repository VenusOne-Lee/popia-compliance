#!/usr/bin/env python3
"""
regwatch: monthly check of Information Regulator listing pages for new items.

Fetches each source in regwatch/sources.json, extracts item titles and links,
diffs them against regwatch/state.json and prints new items as Markdown.

    python3 scripts/regwatch.py                      # report new items
    python3 scripts/regwatch.py --update-state       # report, then save them as seen
    python3 scripts/regwatch.py --open-issue         # one law-change issue per run (needs gh)
    python3 scripts/regwatch.py --dry-run            # never write state or open issues
    python3 scripts/regwatch.py --offline-fixture FILE   # parse a saved HTML file instead of fetching

Stdlib only. Python 3.8+. One request per source, polite User-Agent, timeout,
no retries. A new item is a prompt to read the source, not a conclusion that the
law changed. Engineering guidance, not legal advice. See DISCLAIMER.md.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urldefrag

REPO = Path(__file__).resolve().parent.parent
SOURCES = REPO / "regwatch" / "sources.json"
STATE = REPO / "regwatch" / "state.json"
MAX_BYTES = 3_000_000

DEFAULT_CONFIG = {
    "user_agent": "popia-compliance-regwatch/1.0 (+https://github.com/VenusOne-Lee/popia-compliance)",
    "timeout_seconds": 20,
    "delay_between_requests_seconds": 3,
    "sources": [],
    "include_link_patterns": [],
    "exclude_link_patterns": ["#", "^mailto:", "^tel:"],
    "min_title_length": 12,
}

LIKELY_AFFECTED = [
    (r"direct marketing|telemarketing|s69|unsolicited|marketing", ["references/05-direct-marketing.md"]),
    (r"compromise|breach|ransomware|hack|incident|s22", ["references/07-breach-response.md"]),
    (r"cross.border|transborder|s72|transfer", ["references/06-cross-border-and-operators.md"]),
    (r"artificial intelligence|\bai\b|automated|profiling|s71", ["references/08-ai-and-automated-decisions.md"]),
    (r"information officer|registration|s55", ["references/01-popia-legal-map.md", "references/09-audit-procedure.md"]),
    (r"regulation|amend|gazette|form \d", ["references/01-popia-legal-map.md"]),
    (r"enforcement|fine|penalt|infringement", ["references/10-regulatory-watch.md"]),
    (r"children|child|minor|school|learner", ["references/01-popia-legal-map.md", "references/02-build-patterns.md"]),
    (r"paia|access to information", ["references/01-popia-legal-map.md"]),
    (r"security|safeguard|s19", ["references/03-security-controls.md"]),
]


def log(*a) -> None:
    print("[regwatch]", *a, file=sys.stderr)


# --------------------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------------------
class LinkParser(HTMLParser):
    """Collect (href, text) for every <a> element, skipping script/style/nav/header/footer."""

    SKIP = {"script", "style", "noscript", "nav", "header", "footer"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: List[tuple] = []
        self._href: Optional[str] = None
        self._text: List[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag == "a" and not self._skip:
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._text).split())))
            self._href = None

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)


def extract_items(html: str, base_url: str, config: Optional[dict] = None) -> List[dict]:
    """Return de-duplicated [{title, url}] in page order."""
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    inc = [re.compile(p, re.I) for p in cfg.get("include_link_patterns") or []]
    exc = [re.compile(p, re.I) for p in cfg.get("exclude_link_patterns") or []]
    minlen = int(cfg.get("min_title_length", 12))
    p = LinkParser()
    p.feed(html)
    p.close()
    seen, out = set(), []
    for href, text in p.links:
        if not href or not text or len(text) < minlen:
            continue
        raw = href.strip()
        if any(rx.search(raw) for rx in exc):
            continue
        url = urldefrag(urljoin(base_url, raw))[0]
        if inc and not any(rx.search(url) for rx in inc):
            continue
        if any(rx.search(url) for rx in exc if rx.pattern != "#"):
            continue
        if url in seen:
            continue
        seen.add(url)
        out.append({"title": text, "url": url})
    return out


# --------------------------------------------------------------------------------------
# State and diff
# --------------------------------------------------------------------------------------
def load_json(path: Path, default: dict) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return json.loads(json.dumps(default))


def diff(items: List[dict], seen_urls: List[str]) -> List[dict]:
    seen = set(seen_urls)
    return [i for i in items if i["url"] not in seen]


def update_state(state: dict, source_id: str, items: List[dict], now: str) -> dict:
    src = state.setdefault("sources", {}).setdefault(source_id, {"seen": []})
    known = set(src["seen"])
    src["seen"] = src["seen"] + [i["url"] for i in items if i["url"] not in known]
    src["last_checked"] = now
    state["last_checked"] = now
    return state


# --------------------------------------------------------------------------------------
# Fetch
# --------------------------------------------------------------------------------------
def fetch(url: str, ua: str, timeout: float) -> str:
    if not url.startswith("https://"):
        raise ValueError("regwatch sources must be https URLs")
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec: fixed https sources from config
        data = r.read(MAX_BYTES)
        charset = r.headers.get_content_charset() or "utf-8"
    return data.decode(charset, errors="replace")


# --------------------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------------------
def likely_files(title: str) -> List[str]:
    files = ["references/10-regulatory-watch.md"]
    for rx, fs in LIKELY_AFFECTED:
        if re.search(rx, title, re.I):
            files += [f for f in fs if f not in files]
    return files


def report_md(results: List[dict], now: str) -> str:
    total = sum(len(r["new"]) for r in results)
    md = [f"# Regulator watch: {now[:10]}", "",
          f"{total} new item(s) across {len(results)} source(s). A new item is a prompt to read the source, "
          "not a conclusion that the law changed.", ""]
    for r in results:
        md += [f"## {r['name']}", f"Source: {r['url']}", ""]
        if r.get("error"):
            md += [f"Fetch failed: {r['error']}. Check the page by hand.", ""]
            continue
        if not r["new"]:
            md += ["No new items.", ""]
            continue
        md += [f"- [{i['title']}]({i['url']})" for i in r["new"]] + [""]
    md += ["---", "Engineering guidance, not legal advice. See DISCLAIMER.md."]
    return "\n".join(md)


def issue_body(results: List[dict], now: str) -> str:
    """law-change issue body, matching .github/ISSUE_TEMPLATE law-change format."""
    lines = ["## What changed", "",
             "Automated regwatch run found new items on Information Regulator pages. "
             "Read each source and record what changed, if anything.", ""]
    files: List[str] = []
    for r in results:
        for i in r["new"]:
            lines.append(f"- **{r['name']}**: [{i['title']}]({i['url']})")
            files += [f for f in likely_files(i["title"]) if f not in files]
    lines += ["", "## Source link", ""]
    lines += [f"- {r['url']}" for r in results if r["new"]]
    lines += ["", "## Effective date", "", "TBC. Confirm from the primary source (Government Gazette or the Regulator).", "",
              "## Files likely affected", ""]
    lines += [f"- `{f}`" for f in files]
    lines += ["", "## Checklist", "",
              "- [ ] Update `references/10-regulatory-watch.md` (date, instrument, status, primary source)",
              "- [ ] Update affected references",
              "- [ ] Add a CHANGELOG entry",
              "- [ ] Add or update evals that cover the change",
              "- [ ] Re-verify any item marked Unverified", "",
              f"_Opened by scripts/regwatch.py on {now[:10]}. Engineering guidance, not legal advice._"]
    return "\n".join(lines)


def open_issue(title: str, body: str, label: str = "law-change") -> int:
    cmd = ["gh", "issue", "create", "--title", title, "--body", body, "--label", label]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        log(f"gh issue create failed: {e}")
        return 1
    if r.returncode != 0:
        log(f"gh issue create failed: {r.stderr.strip()}")
    else:
        log(f"opened issue {r.stdout.strip()}")
    return r.returncode


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------
def run(config: dict, state: dict, offline_fixture: Optional[str] = None,
        only: Optional[List[str]] = None) -> List[dict]:
    ua = config.get("user_agent", DEFAULT_CONFIG["user_agent"])
    timeout = float(config.get("timeout_seconds", 20))
    delay = float(config.get("delay_between_requests_seconds", 3))
    results = []
    sources = [s for s in config.get("sources", []) if s.get("enabled", True)]
    if only:
        sources = [s for s in sources if s["id"] in only]
    for n, src in enumerate(sources):
        res = {"id": src["id"], "name": src.get("name", src["id"]), "url": src["url"], "items": [], "new": []}
        try:
            if offline_fixture:
                html = Path(offline_fixture).read_text(encoding="utf-8")
            else:
                if n:
                    time.sleep(delay)
                html = fetch(src["url"], ua, timeout)
            res["items"] = extract_items(html, src["url"], config)
            seen = state.get("sources", {}).get(src["id"], {}).get("seen", [])
            res["new"] = diff(res["items"], seen)
        except (urllib.error.URLError, OSError, ValueError) as e:
            res["error"] = f"{type(e).__name__}: {e}"
            log(f"{src['id']}: {res['error']}")
        results.append(res)
    return results


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Watch Information Regulator pages for new items.")
    ap.add_argument("--sources", default=str(SOURCES))
    ap.add_argument("--state", default=str(STATE))
    ap.add_argument("--only", help="comma-separated source ids")
    ap.add_argument("--out", help="write Markdown report to this file")
    ap.add_argument("--json", dest="json_out", help="write JSON results to this file")
    ap.add_argument("--update-state", action="store_true", help="save new items as seen")
    ap.add_argument("--open-issue", action="store_true", help="open one law-change issue with gh")
    ap.add_argument("--dry-run", action="store_true", help="no state writes, no issues")
    ap.add_argument("--offline-fixture", help="parse this HTML file for every source instead of fetching")
    ap.add_argument("--fail-on-error", action="store_true", help="exit 2 if every source failed to fetch")
    a = ap.parse_args(argv)

    config = {**DEFAULT_CONFIG, **load_json(Path(a.sources), DEFAULT_CONFIG)}
    state = load_json(Path(a.state), {"version": 1, "sources": {}})
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    results = run(config, state, a.offline_fixture, a.only.split(",") if a.only else None)

    md = report_md(results, now)
    if a.out:
        Path(a.out).write_text(md, encoding="utf-8")
    else:
        print(md)
    if a.json_out:
        Path(a.json_out).write_text(json.dumps({"checked_at": now, "results": results}, indent=2), encoding="utf-8")

    new_total = sum(len(r["new"]) for r in results)
    errors = [r for r in results if r.get("error")]
    if a.dry_run:
        log(f"dry run: {new_total} new item(s), state and issues untouched")
    else:
        if a.open_issue and new_total:
            rc = open_issue(f"Regulator watch {now[:10]}: {new_total} new item(s) to review", issue_body(results, now))
            if rc != 0:
                return rc
        if a.update_state and not a.offline_fixture:
            for r in results:
                if not r.get("error"):
                    update_state(state, r["id"], r["items"], now)
            Path(a.state).write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
            log(f"state saved to {a.state}")
    if a.fail_on_error and results and len(errors) == len(results):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
