#!/usr/bin/env python3
"""
popia_scan: static scanner for POPIA and security issues in a codebase.

Stdlib only. Python 3.8+.

    python3 popia_scan.py <path> [--format text|json|md|sarif] [--out FILE]
                                 [--fail-on critical|high|medium|low|info|none]
                                 [--min-severity info] [--rules RULE,RULE] [--list-rules]

Findings are leads, not verdicts. Read the code before reporting them.
This tool is engineering guidance, not legal advice. See DISCLAIMER.md.

Programmatic use:
    from popia_scan import scan
    result = scan("/path/to/repo")          # dict with "findings", "summary", ...
"""
from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

__version__ = "1.0.0"

SEVERITIES = ["critical", "high", "medium", "low", "info"]
SEV_RANK = {s: i for i, s in enumerate(SEVERITIES)}

SCANNED_EXT = {
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte", ".astro",
    ".py", ".rb", ".php", ".go", ".java", ".kt", ".kts", ".swift", ".dart", ".cs",
    ".sql", ".html", ".htm", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".rules", ".tf", ".sh", ".xml", ".plist", ".liquid", ".hbs", ".ejs", ".csv",
}
SCANNED_NAMES = {"Dockerfile", "firestore.rules", "storage.rules", "database.rules.json", ".htaccess"}
SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", ".nuxt", "out", "coverage", "vendor",
    ".venv", "venv", "env", "__pycache__", ".turbo", ".vercel", ".svelte-kit", "target",
    "bin", "obj", "Pods", ".gradle", ".idea", ".vscode", ".cache", ".parcel-cache",
    ".output", "storybook-static", ".expo", "android/app/build", "ios/build",
}
MAX_BYTES = 1_000_000
IGNORE_INLINE = re.compile(r"popia-ignore(?::\s*([^\n]*))?", re.I)
RULE_ID_TOKEN = re.compile(r"\b[A-Z]{2,4}-\d{3}[a-z]?\b")


# --------------------------------------------------------------------------------------
# Rule model
# --------------------------------------------------------------------------------------
@dataclass
class Rule:
    id: str
    title: str
    severity: str
    popia: str                      # e.g. "s19" or "s69; Reg 6"
    message: str                    # why it matters
    fix: str                        # what to do
    kind: str = "line"              # line | file | repo
    pattern: Optional[str] = None   # for line rules
    flags: int = re.I
    include: List[str] = field(default_factory=lambda: ["*"])   # filename globs
    exclude: List[str] = field(default_factory=list)            # path globs
    validator: Optional[Callable[[re.Match, str], bool]] = None  # (match, line) -> keep?
    file_check: Optional[Callable[[str, str], List[dict]]] = None   # (relpath, text) -> [{line, snippet, extra}]
    repo_check: Optional[Callable[["RepoContext"], List[dict]]] = None
    confidence: str = "medium"      # high | medium | low
    tags: List[str] = field(default_factory=list)
    _rx: Optional[re.Pattern] = None

    def compiled(self) -> re.Pattern:
        if self._rx is None and self.pattern:
            self._rx = re.compile(self.pattern, self.flags)
        return self._rx

    def applies_to(self, relpath: str) -> bool:
        name = os.path.basename(relpath)
        if not any(fnmatch.fnmatch(name, g) or fnmatch.fnmatch(relpath, g) for g in self.include):
            return False
        if any(fnmatch.fnmatch(relpath, g) for g in self.exclude):
            return False
        return True


@dataclass
class Finding:
    rule_id: str
    title: str
    severity: str
    popia: str
    file: str
    line: int
    snippet: str
    message: str
    fix: str
    confidence: str
    tags: List[str]
    extra: str = ""


class RepoContext:
    """Whole-repo view for repo-level rules."""

    def __init__(self, root: Path, files: Dict[str, str]):
        self.root = root
        self.files = files  # relpath -> text

    def grep(self, pattern: str, flags: int = re.I, include: Iterable[str] = ("*",)) -> List[tuple]:
        rx = re.compile(pattern, flags)
        hits = []
        for rel, text in self.files.items():
            name = os.path.basename(rel)
            if not any(fnmatch.fnmatch(name, g) or fnmatch.fnmatch(rel, g) for g in include):
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    hits.append((rel, i, line.strip()))
        return hits

    def any(self, pattern: str, flags: int = re.I, include: Iterable[str] = ("*",)) -> bool:
        rx = re.compile(pattern, flags)
        for rel, text in self.files.items():
            name = os.path.basename(rel)
            if any(fnmatch.fnmatch(name, g) or fnmatch.fnmatch(rel, g) for g in include) and rx.search(text):
                return True
        return False

    def paths_matching(self, pattern: str) -> List[str]:
        rx = re.compile(pattern, re.I)
        return [p for p in self.files if rx.search(p)]


# --------------------------------------------------------------------------------------
# Rule loading (plug-in): every rules/*.py module exporting RULES = [Rule, ...]
# --------------------------------------------------------------------------------------
def load_rules(rules_dir: Optional[Path] = None) -> List[Rule]:
    rules_dir = rules_dir or Path(__file__).resolve().parent / "rules"
    sys.modules.setdefault("popia_scan", sys.modules[__name__])
    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:
        sys.path.insert(0, here)
    rules: List[Rule] = []
    seen = set()
    for py in sorted(rules_dir.glob("*.py")):
        if py.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f"popia_rules_{py.stem}", py)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore
        for r in getattr(mod, "RULES", []):
            if r.id in seen:
                raise ValueError(f"Duplicate rule id {r.id} in {py.name}")
            if r.severity not in SEV_RANK:
                raise ValueError(f"Bad severity {r.severity} on {r.id}")
            seen.add(r.id)
            rules.append(r)
    return rules


# --------------------------------------------------------------------------------------
# File walking
# --------------------------------------------------------------------------------------
def load_ignore(root: Path) -> List[str]:
    f = root / ".popiaignore"
    if not f.exists():
        return []
    out = []
    for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line.rstrip("/") + ("/*" if line.endswith("/") else ""))
    return out


def iter_files(root: Path, ignore_globs: List[str]) -> Iterable[Path]:
    if root.is_file():
        yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS and f"{rel_dir}/{d}".lstrip("./") not in SKIP_DIRS
            and not any(fnmatch.fnmatch(f"{rel_dir}/{d}".lstrip("./"), g.rstrip("/*")) for g in ignore_globs)
        ]
        for fn in filenames:
            p = Path(dirpath) / fn
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            if any(fnmatch.fnmatch(rel, g) for g in ignore_globs):
                continue
            ext = p.suffix.lower()
            if ext in SCANNED_EXT or fn in SCANNED_NAMES or fn.startswith(".env"):
                try:
                    if p.stat().st_size <= MAX_BYTES:
                        yield p
                except OSError:
                    continue


def read_text(p: Path) -> Optional[str]:
    try:
        data = p.read_bytes()
    except OSError:
        return None
    if b"\x00" in data[:4096]:
        return None
    return data.decode("utf-8", errors="ignore")


def line_suppressed(line: str, prev: str, rule_id: str) -> bool:
    for txt in (line, prev):
        m = IGNORE_INLINE.search(txt)
        if m:
            ids = RULE_ID_TOKEN.findall(m.group(1) or "")
            if not ids or rule_id in ids:
                return True
    return False


def redact(snippet: str) -> str:
    """Never echo real PI or secrets in reports."""
    s = snippet.strip()
    s = re.sub(r"\b(\d{6})(\d{4})(\d{3})\b", r"\1****\3", s)                     # 13-digit IDs
    s = re.sub(r"\b(\d{4})\d{5,11}(\d{4})\b", r"\1********\2", s)                # long numbers
    s = re.sub(r"([A-Za-z0-9._%+-]{1,2})[A-Za-z0-9._%+-]*@", r"\1***@", s)        # emails
    s = re.sub(r"(sk_live_|sk_test_|AKIA|ghp_|xox[abp]-|sk-ant-|sk-proj-|sk-)([A-Za-z0-9_\-]{4})[A-Za-z0-9_\-]+",
               r"\1\2…REDACTED", s)
    s = re.sub(r"(eyJ[A-Za-z0-9_-]{6})[A-Za-z0-9_\-\.]{20,}", r"\1…REDACTED", s)   # JWTs
    s = re.sub(r"(-----BEGIN [A-Z ]*PRIVATE KEY-----).*", r"\1 …REDACTED", s)
    return s[:220]


# --------------------------------------------------------------------------------------
# Scan
# --------------------------------------------------------------------------------------
def scan(path: str, rule_ids: Optional[List[str]] = None, min_severity: str = "info",
         rules: Optional[List[Rule]] = None) -> dict:
    root = Path(path).resolve()
    if not root.exists():
        raise FileNotFoundError(path)
    all_rules = rules or load_rules()
    if rule_ids:
        wanted = {r.strip().upper() for r in rule_ids}
        all_rules = [r for r in all_rules if r.id.upper() in wanted]
    max_rank = SEV_RANK[min_severity]
    all_rules = [r for r in all_rules if SEV_RANK[r.severity] <= max_rank]

    ignore_globs = load_ignore(root if root.is_dir() else root.parent)
    files: Dict[str, str] = {}
    base = root if root.is_dir() else root.parent
    for p in iter_files(root, ignore_globs):
        t = read_text(p)
        if t is not None:
            files[os.path.relpath(p, base).replace(os.sep, "/")] = t

    findings: List[Finding] = []
    line_rules = [r for r in all_rules if r.kind == "line"]
    file_rules = [r for r in all_rules if r.kind == "file"]
    repo_rules = [r for r in all_rules if r.kind == "repo"]

    for rel, text in files.items():
        lines = text.splitlines()
        applicable = [r for r in line_rules if r.applies_to(rel)]
        if applicable:
            for i, line in enumerate(lines, 1):
                if len(line) > 4000:  # minified bundles
                    continue
                prev = lines[i - 2] if i > 1 else ""
                for r in applicable:
                    rx = r.compiled()
                    if not rx:
                        continue
                    for m in rx.finditer(line):
                        if r.validator and not r.validator(m, line):
                            continue
                        if line_suppressed(line, prev, r.id):
                            break
                        findings.append(_mk(r, rel, i, line))
                        break  # one finding per rule per line
        for r in file_rules:
            if r.applies_to(rel) and r.file_check:
                for hit in r.file_check(rel, text) or []:
                    ln = hit.get("line", 1)
                    src = lines[ln - 1] if 0 < ln <= len(lines) else ""
                    prev = lines[ln - 2] if ln > 1 else ""
                    if line_suppressed(src, prev, r.id):
                        continue
                    findings.append(_mk(r, rel, ln, hit.get("snippet", src), hit.get("extra", "")))

    ctx = RepoContext(base, files)
    for r in repo_rules:
        if r.repo_check:
            for hit in r.repo_check(ctx) or []:
                findings.append(_mk(r, hit.get("file", "(repository)"), hit.get("line", 0),
                                    hit.get("snippet", ""), hit.get("extra", "")))

    findings.sort(key=lambda f: (SEV_RANK[f.severity], f.rule_id, f.file, f.line))
    summary = {s: 0 for s in SEVERITIES}
    for f in findings:
        summary[f.severity] += 1
    return {
        "tool": "popia_scan",
        "version": __version__,
        "scanned_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "target": str(root),
        "files_scanned": len(files),
        "rules_run": len(all_rules),
        "summary": summary,
        "findings": [asdict(f) for f in findings],
        "disclaimer": "Automated findings are leads for review, not legal conclusions. "
                      "Engineering guidance only, not legal advice.",
    }


def _mk(r: Rule, rel: str, line: int, snippet: str, extra: str = "") -> Finding:
    return Finding(r.id, r.title, r.severity, r.popia, rel, line, redact(snippet),
                   r.message, r.fix, r.confidence, r.tags, extra)


# --------------------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------------------
def fmt_text(res: dict) -> str:
    out = [f"popia_scan {res['version']}  target={res['target']}  files={res['files_scanned']}  rules={res['rules_run']}"]
    s = res["summary"]
    out.append("summary: " + "  ".join(f"{k}={s[k]}" for k in SEVERITIES))
    for f in res["findings"]:
        loc = f"{f['file']}:{f['line']}" if f["line"] else f["file"]
        out.append(f"\n[{f['severity'].upper()}] {f['rule_id']} {f['title']}  ({f['popia']})\n  {loc}")
        if f["snippet"]:
            out.append(f"  > {f['snippet']}")
        if f["extra"]:
            out.append(f"  note: {f['extra']}")
        out.append(f"  fix: {f['fix']}")
    out.append("\n" + res["disclaimer"])
    return "\n".join(out)


def fmt_md(res: dict) -> str:
    s = res["summary"]
    md = [
        "# POPIA scan report", "",
        f"- **Target:** `{res['target']}`",
        f"- **Scanned:** {res['scanned_at']} · {res['files_scanned']} files · {res['rules_run']} rules · popia_scan {res['version']}",
        "",
        "| Critical | High | Medium | Low | Info |", "|---|---|---|---|---|",
        f"| {s['critical']} | {s['high']} | {s['medium']} | {s['low']} | {s['info']} |", "",
    ]
    if not res["findings"]:
        md.append("No findings. That's not proof of compliance: complete the manual checklist in `references/09-audit-procedure.md`.")
    by_rule: Dict[str, List[dict]] = {}
    for f in res["findings"]:
        by_rule.setdefault(f["rule_id"], []).append(f)
    for rid, items in by_rule.items():
        f0 = items[0]
        md += [f"## {f0['severity'].capitalize()} · {rid} · {f0['title']}", "",
               f"**POPIA:** {f0['popia']} · **Confidence:** {f0['confidence']} · **Occurrences:** {len(items)}", "",
               f"**Why it matters:** {f0['message']}", "", f"**Fix:** {f0['fix']}", "",
               "| Location | Evidence (redacted) |", "|---|---|"]
        for f in items[:50]:
            loc = f"`{f['file']}:{f['line']}`" if f["line"] else f"`{f['file']}`"
            ev = (f["snippet"] or f["extra"]).replace("|", "\\|")
            md.append(f"| {loc} | `{ev}` |" if ev else f"| {loc} | |")
        if len(items) > 50:
            md.append(f"| … | {len(items) - 50} more |")
        md.append("")
    md += ["---", "",
           "_Status for each finding: confirmed / false positive / needs info. Triage before sharing._", "",
           f"> {res['disclaimer']} See DISCLAIMER.md."]
    return "\n".join(md)


SARIF_LEVEL = {"critical": "error", "high": "error", "medium": "warning", "low": "note", "info": "note"}


def fmt_sarif(res: dict, rules: List[Rule]) -> str:
    used = {f["rule_id"] for f in res["findings"]}
    rule_meta = [{
        "id": r.id, "name": r.title,
        "shortDescription": {"text": r.title},
        "fullDescription": {"text": r.message},
        "help": {"text": f"{r.fix} (POPIA {r.popia})"},
        "properties": {"severity": r.severity, "popia": r.popia, "tags": r.tags + ["popia"],
                       "security-severity": {"critical": "9.5", "high": "8.0", "medium": "5.5",
                                             "low": "3.0", "info": "1.0"}[r.severity]},
    } for r in rules if r.id in used]
    results = []
    for f in res["findings"]:
        loc = {"physicalLocation": {"artifactLocation": {"uri": f["file"]}}}
        if f["line"]:
            loc["physicalLocation"]["region"] = {"startLine": f["line"]}
        results.append({
            "ruleId": f["rule_id"], "level": SARIF_LEVEL[f["severity"]],
            "message": {"text": f"{f['title']}. {f['message']} Fix: {f['fix']}"},
            "locations": [loc],
        })
    return json.dumps({
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json", "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": "popia_scan", "version": res["version"],
                                      "informationUri": "https://github.com/VenusOne-Lee/popia-compliance",
                                      "rules": rule_meta}},
                  "results": results}],
    }, indent=2)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="POPIA + security static scanner (engineering guidance, not legal advice).")
    ap.add_argument("path", nargs="?", default=".")
    ap.add_argument("--format", choices=["text", "json", "md", "sarif"], default="text")
    ap.add_argument("--out")
    ap.add_argument("--fail-on", default="none", choices=SEVERITIES + ["none"])
    ap.add_argument("--min-severity", default="info", choices=SEVERITIES)
    ap.add_argument("--rules", help="comma-separated rule ids to run")
    ap.add_argument("--list-rules", action="store_true")
    ap.add_argument("--version", action="version", version=__version__)
    a = ap.parse_args(argv)

    rules = load_rules()
    if a.list_rules:
        for r in sorted(rules, key=lambda r: (SEV_RANK[r.severity], r.id)):
            print(f"{r.id:10} {r.severity:8} {r.kind:5} {r.popia:18} {r.title}")
        return 0

    res = scan(a.path, a.rules.split(",") if a.rules else None, a.min_severity, rules)
    out = {"text": fmt_text, "json": lambda r: json.dumps(r, indent=2), "md": fmt_md,
           "sarif": lambda r: fmt_sarif(r, rules)}[a.format](res)
    if a.out:
        Path(a.out).write_text(out, encoding="utf-8")
        s = res["summary"]
        print(f"wrote {a.out}: " + " ".join(f"{k}={s[k]}" for k in SEVERITIES), file=sys.stderr)
    else:
        print(out)

    if a.fail_on != "none":
        threshold = SEV_RANK[a.fail_on]
        if any(SEV_RANK[f["severity"]] <= threshold for f in res["findings"]):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
