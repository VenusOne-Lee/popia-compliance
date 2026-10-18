#!/usr/bin/env python3
"""
popia_fleet: scan many repositories and report anonymised aggregate statistics.

Use it for a "we scanned N apps" style report. Output never contains code snippets,
file paths or secrets. Repository identities are hashed unless --show-names is set.

    python3 scripts/popia_fleet.py --dir ~/code/clients --out fleet.md
    python3 scripts/popia_fleet.py --list repos.txt --format json --out fleet.json
    python3 scripts/popia_fleet.py --list repos.txt --show-names    # internal use only

--list takes one entry per line: a local path or a git URL (https or ssh). URLs are
cloned shallow into a temporary directory and deleted after the scan. Lines starting
with # are ignored.

Stdlib only. Python 3.8+. Scanner findings are leads, not verdicts. Aggregate figures
describe scanner hits, not compliance. Engineering guidance, not legal advice.
See DISCLAIMER.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

SEVERITIES = ["critical", "high", "medium", "low", "info"]
URL_RX = re.compile(r"^(https?://|git@|ssh://|git://)")

# Category -> predicate on (rule_id, tags). First match wins.
CATEGORIES: List[tuple] = [
    ("Secrets and credentials", lambda rid, tags: "secrets" in tags or rid.startswith("SEC-001") or rid == "SEC-014"),
    ("Access control", lambda rid, tags: bool({"access-control", "auth", "firebase", "supabase"} & set(tags))),
    ("Consent and trackers", lambda rid, tags: bool({"consent", "tracker", "trackers", "cookies", "cookie", "marketing",
                                                     "analytics"} & set(tags)) or rid.startswith(("CON-", "TRK-", "DM-"))),
    ("Cross-border and third parties", lambda rid, tags: bool({"cross-border", "crossborder", "transfer", "ai", "llm",
                                                               "third-party", "vendor"} & set(tags))
     or rid.startswith(("XB-", "AI-"))),
    ("Personal information in code and logs", lambda rid, tags: bool({"pii", "logging", "sa-id", "test-data", "storage"}
                                                                     & set(tags)) or rid.startswith(("PII-", "LOG-", "STO-"))),
]
OTHER = "Other security hygiene"


def category(rule_id: str, tags: List[str]) -> str:
    t = [x.lower() for x in tags or []]
    for name, pred in CATEGORIES:
        if pred(rule_id.upper(), t):
            return name
    return OTHER


def repo_hash(identity: str) -> str:
    return "repo-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:10]


def display_name(identity: str) -> str:
    base = identity.rstrip("/").split("/")[-1]
    return base[:-4] if base.endswith(".git") else base


# --------------------------------------------------------------------------------------
# Targets
# --------------------------------------------------------------------------------------
def targets_from_dir(d: str) -> List[str]:
    root = Path(os.path.expanduser(d)).resolve()
    if not root.is_dir():
        raise SystemExit(f"--dir {d} is not a directory")
    return [str(p) for p in sorted(root.iterdir()) if p.is_dir() and not p.name.startswith(".")]


def targets_from_list(f: str) -> List[str]:
    out = []
    for line in Path(os.path.expanduser(f)).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def clone(url: str, dest: str, timeout: int = 300) -> None:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    subprocess.run(["git", "clone", "--depth", "1", "--quiet", "--no-tags", url, dest],
                   check=True, capture_output=True, timeout=timeout, env=env)


# --------------------------------------------------------------------------------------
# Scan and aggregate
# --------------------------------------------------------------------------------------
def summarise_repo(res: dict) -> dict:
    """Strip a scan result down to counts. No snippets, paths, messages or targets."""
    rules: Dict[str, dict] = {}
    for f in res.get("findings", []):
        r = rules.setdefault(f["rule_id"], {"title": f["title"], "severity": f["severity"],
                                            "category": category(f["rule_id"], f.get("tags", [])), "count": 0})
        r["count"] += 1
    return {"files_scanned": res.get("files_scanned", 0), "summary": dict(res.get("summary", {})),
            "findings": sum(res.get("summary", {}).values()), "rules": rules}


def scan_targets(targets: List[str], scan_fn: Optional[Callable] = None, show_names: bool = False,
                 min_severity: str = "info") -> List[dict]:
    if scan_fn is None:
        try:
            from popia_scan import scan as scan_fn  # type: ignore
        except ImportError as e:
            raise SystemExit(f"Cannot import scripts/popia_scan.py: {e}")
    results = []
    for t in targets:
        identity = t if URL_RX.match(t) else str(Path(os.path.expanduser(t)).resolve())
        rid = display_name(identity) if show_names else repo_hash(identity)
        tmp = None
        try:
            path = identity
            if URL_RX.match(t):
                tmp = tempfile.mkdtemp(prefix="popia-fleet-")
                path = os.path.join(tmp, "repo")
                clone(t, path)
            res = scan_fn(path, None, min_severity)
            entry = {"id": rid, "ok": True, **summarise_repo(res)}
        except subprocess.CalledProcessError as e:
            entry = {"id": rid, "ok": False, "error": "clone failed"}
            print(f"[fleet] {rid}: clone failed ({(e.stderr or b'').decode(errors='replace').strip()[:200]})",
                  file=sys.stderr)
        except Exception as e:  # keep going across the fleet
            entry = {"id": rid, "ok": False, "error": type(e).__name__}
            print(f"[fleet] {rid}: {type(e).__name__}: {e}", file=sys.stderr)
        finally:
            if tmp:
                shutil.rmtree(tmp, ignore_errors=True)
        results.append(entry)
    return results


def pct(n: int, d: int) -> float:
    return round(100.0 * n / d, 1) if d else 0.0


def aggregate(repos: List[dict]) -> dict:
    ok = [r for r in repos if r.get("ok")]
    n = len(ok)
    with_crit = sum(1 for r in ok if r["summary"].get("critical", 0))
    with_high = sum(1 for r in ok if r["summary"].get("critical", 0) or r["summary"].get("high", 0))
    counts = [r["findings"] for r in ok]
    rule_repos: Dict[str, dict] = {}
    cat_repos: Dict[str, set] = {}
    cat_findings: Dict[str, int] = {}
    for r in ok:
        for rid, info in r["rules"].items():
            x = rule_repos.setdefault(rid, {"rule_id": rid, "title": info["title"], "severity": info["severity"],
                                            "category": info["category"], "repos": 0, "findings": 0})
            x["repos"] += 1
            x["findings"] += info["count"]
            cat_repos.setdefault(info["category"], set()).add(r["id"])
            cat_findings[info["category"]] = cat_findings.get(info["category"], 0) + info["count"]
    top = sorted(rule_repos.values(), key=lambda x: (-x["repos"], SEVERITIES.index(x["severity"]), x["rule_id"]))
    for x in top:
        x["pct_repos"] = pct(x["repos"], n)
    cats = []
    for name in [c[0] for c in CATEGORIES] + [OTHER]:
        cats.append({"category": name, "repos": len(cat_repos.get(name, ())),
                     "pct_repos": pct(len(cat_repos.get(name, ())), n), "findings": cat_findings.get(name, 0)})
    sev_tot = {s: sum(r["summary"].get(s, 0) for r in ok) for s in SEVERITIES}
    return {
        "repos_requested": len(repos),
        "repos_scanned": n,
        "repos_failed": len(repos) - n,
        "pct_repos_with_critical": pct(with_crit, n),
        "pct_repos_with_critical_or_high": pct(with_high, n),
        "median_findings_per_repo": statistics.median(counts) if counts else 0,
        "median_files_per_repo": statistics.median([r["files_scanned"] for r in ok]) if ok else 0,
        "severity_totals": sev_tot,
        "top_rules": top[:15],
        "categories": cats,
    }


# --------------------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------------------
def fleet_result(repos: List[dict], show_names: bool) -> dict:
    try:
        import popia_scan  # type: ignore
        version = popia_scan.__version__
        rules_loaded = len(popia_scan.load_rules())
    except Exception:
        version, rules_loaded = "unknown", 0
    return {
        "tool": "popia_fleet",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scanner_version": version,
        "rules_loaded": rules_loaded,
        "identities": "names" if show_names else "sha256-prefix",
        "aggregate": aggregate(repos),
        "repos": repos,
        "disclaimer": "Aggregate scanner hits, not a finding of compliance or non-compliance. "
                      "Engineering guidance only, not legal advice. See DISCLAIMER.md.",
    }


def fmt_md(res: dict) -> str:
    a = res["aggregate"]
    md = ["# POPIA fleet scan", "",
          f"- **Generated:** {res['generated_at']} · popia_scan {res['scanner_version']} · {res['rules_loaded']} rules",
          f"- **Repositories scanned:** {a['repos_scanned']} of {a['repos_requested']}"
          + (f" ({a['repos_failed']} failed to clone or scan)" if a["repos_failed"] else ""),
          f"- **Identities:** {'shown' if res['identities'] == 'names' else 'hashed (sha256 prefix)'}", "",
          "## Headline figures", "",
          "| Measure | Value |", "|---|---|",
          f"| Repos with at least one critical finding | {a['pct_repos_with_critical']}% |",
          f"| Repos with at least one critical or high finding | {a['pct_repos_with_critical_or_high']}% |",
          f"| Median findings per repo | {a['median_findings_per_repo']} |",
          f"| Median files scanned per repo | {a['median_files_per_repo']} |", "",
          "| Critical | High | Medium | Low | Info |", "|---|---|---|---|---|",
          "| " + " | ".join(str(a["severity_totals"][s]) for s in SEVERITIES) + " |", "",
          "## By category", "",
          "| Category | Repos affected | % of repos | Findings |", "|---|---|---|---|"]
    md += [f"| {c['category']} | {c['repos']} | {c['pct_repos']}% | {c['findings']} |" for c in a["categories"]]
    md += ["", "## Top rules by share of repos affected", ""]
    if a["top_rules"]:
        md += ["| Rule | Severity | Title | % of repos | Repos |", "|---|---|---|---|---|"]
        md += [f"| {x['rule_id']} | {x['severity']} | {x['title']} | {x['pct_repos']}% | {x['repos']} |"
               for x in a["top_rules"]]
    else:
        md.append("No rule fired in any repository.")
    md += ["", "## Per repository", "", "| Repo | Files | Critical | High | Medium | Low | Info |",
           "|---|---|---|---|---|---|---|"]
    for r in res["repos"]:
        if r.get("ok"):
            s = r["summary"]
            md.append(f"| {r['id']} | {r['files_scanned']} | " + " | ".join(str(s.get(k, 0)) for k in SEVERITIES) + " |")
        else:
            md.append(f"| {r['id']} | {r.get('error', 'failed')} | | | | | |")
    md += ["", "## Methodology", "",
           "- Each repository was scanned with `scripts/popia_scan.py` at default settings on its current default branch "
           "(shallow clone for URLs). Git history was not scanned.",
           "- A repository counts as affected by a rule if the rule produced at least one finding in it.",
           "- Categories group rules by their tags. A rule belongs to one category.",
           "- No code, snippets, file paths or secret values are kept in this report. Identities are a sha256 prefix "
           "of the path or URL unless names were requested.", "",
           "## Limitations", "",
           "- Static scanning finds leads, not verdicts. Figures include false positives that were not triaged.",
           "- The scanner cannot see business process, contracts, Information Officer registration, consent wording "
           "in the live UI, or backend settings that are not in the repository.",
           "- A clean result is not evidence of compliance. Missing rules, generated code and secrets held outside "
           "the repository are not counted.",
           "- The sample is whatever was supplied. It is not random and does not represent all South African apps.",
           "- Results depend on the rule set version shown above. Compare fleets only on the same version.", "",
           "---", "", f"> {res['disclaimer']}"]
    return "\n".join(md)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Anonymised aggregate POPIA scan across many repositories.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--dir", help="directory whose immediate subdirectories are repositories")
    src.add_argument("--list", help="file with one local path or git URL per line")
    ap.add_argument("--format", choices=["md", "json"], help="output format (default from --out extension, else md)")
    ap.add_argument("--out", help="output file (.md or .json)")
    ap.add_argument("--show-names", action="store_true", help="show repository names instead of hashes")
    ap.add_argument("--min-severity", default="info", choices=SEVERITIES)
    a = ap.parse_args(argv)

    targets = targets_from_dir(a.dir) if a.dir else targets_from_list(a.list)
    if not targets:
        print("No repositories found.", file=sys.stderr)
        return 1
    repos = scan_targets(targets, show_names=a.show_names, min_severity=a.min_severity)
    res = fleet_result(repos, a.show_names)
    fmt = a.format or ("json" if a.out and a.out.endswith(".json") else "md")
    out = json.dumps(res, indent=2) if fmt == "json" else fmt_md(res)
    if a.out:
        Path(a.out).write_text(out, encoding="utf-8")
        print(f"wrote {a.out}: {res['aggregate']['repos_scanned']} repos", file=sys.stderr)
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
