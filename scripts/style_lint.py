#!/usr/bin/env python3
"""
House style lint for prose and UI copy.

Checks:
  - no em dashes (U+2014) or en dashes used as dashes (" – ")
  - no exclamation marks in prose (outside code blocks and inline code) or in quoted UI strings
  - templates and sector packs start with the disclaimer line

    python3 scripts/style_lint.py            # report, exit 1 on problems
    python3 scripts/style_lint.py --fix      # replace em/en dashes with " - " where safe
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROSE_EXT = {".md", ".mdc", ".yml", ".yaml", ".txt"}
CODE_EXT = {".tsx", ".ts", ".jsx", ".js", ".py", ".sql", ".json", ".csv", ".html"}
SKIP_DIRS = {".git", "node_modules", "r", "results", ".typecheck", "__pycache__", "fixtures"}
SKIP_FILES = {"CODE_OF_CONDUCT.md"}
DASH = re.compile(r"—|\s–\s")
EXCL_PROSE = re.compile(r"(?<![!\[<=])[A-Za-z)\"'’]!(?=\s|$|[\"'’)*_])")
UI_STRING_EXCL = re.compile(r"""(["'`])[^"'`\n]{3,}?[A-Za-z]!\1""")
DISCLAIMER_DIRS = {"templates": "> Draft template.", "packs": "> Engineering and compliance guidance"}


def strip_code(text: str) -> str:
    text = re.sub(r"```.*?```", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "``", text)


def lint_file(p: Path, fix: bool):
    problems = []
    rel = p.relative_to(ROOT).as_posix()
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        return problems
    new = text
    if DASH.search(text):
        if fix:
            new = re.sub(r"\s*—\s*", " - ", new)
            new = re.sub(r"\s–\s", " - ", new)
        else:
            for i, line in enumerate(text.splitlines(), 1):
                if DASH.search(line):
                    problems.append(f"{rel}:{i}: dash: {line.strip()[:90]}")
    if p.suffix in PROSE_EXT:
        body = strip_code(new)
        for i, line in enumerate(body.splitlines(), 1):
            if EXCL_PROSE.search(line):
                problems.append(f"{rel}:{i}: exclamation mark in prose: {line.strip()[:90]}")
    elif p.suffix in {".tsx", ".jsx", ".json"} and "i18n" not in rel:
        for i, line in enumerate(new.splitlines(), 1):
            if UI_STRING_EXCL.search(line) and "!=" not in line:
                problems.append(f"{rel}:{i}: exclamation mark in UI string: {line.strip()[:90]}")
    top = rel.split("/", 1)[0]
    if top in DISCLAIMER_DIRS and p.suffix == ".md" and not p.name.startswith(("_", "README")):
        first = next((l for l in new.splitlines() if l.strip()), "")
        if not first.startswith(DISCLAIMER_DIRS[top]):
            problems.append(f"{rel}:1: missing disclaimer line ('{DISCLAIMER_DIRS[top]}...')")
    if fix and new != text:
        p.write_text(new, encoding="utf-8")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("paths", nargs="*")
    a = ap.parse_args(argv)
    targets = [ROOT / x for x in a.paths] if a.paths else [ROOT]
    problems = []
    for t in targets:
        files = [t] if t.is_file() else [
            f for f in t.rglob("*")
            if f.is_file() and not any(part in SKIP_DIRS for part in f.relative_to(ROOT).parts)
        ]
        for f in files:
            if f.name in SKIP_FILES or f.suffix not in PROSE_EXT | CODE_EXT:
                continue
            if f.name == "style_lint.py":
                continue
            problems += lint_file(f, a.fix)
    for pr in problems:
        print(pr)
    print(f"style_lint: {len(problems)} problem(s)", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
