#!/usr/bin/env python3
"""
popia_init: set up POPIA Kit in a project with one command.

    popia-kit init [path] [--tools auto|claude,cursor,...] [--no-workflow] [--no-ignore]
                          [--force] [--dry-run]

Adds the POPIA rules file for each AI coding tool the project uses, a GitHub workflow
that runs the scanner, and a starter .popiaignore. Never overwrites your own content:
shared files such as CLAUDE.md and AGENTS.md get a marked block that later runs update,
and files that already exist are left alone unless you pass --force.

Stdlib only. Python 3.8+. Engineering guidance, not legal advice. See DISCLAIMER.md.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
# Clone layout: <repo>/adapters and <repo>/examples. Installed: popia_kit/data/...
ADAPTERS_DIR = HERE.parent / "adapters"
EXAMPLES_DIR = HERE.parent / "examples"
if not ADAPTERS_DIR.is_dir():
    ADAPTERS_DIR = HERE / "data" / "adapters"
    EXAMPLES_DIR = HERE / "data" / "examples"

START = "<!-- popia-kit:start -->"
END = "<!-- popia-kit:end -->"

# tool: (adapter source, destination in the project, shared file?)
TOOLS: Dict[str, Tuple[str, str, bool]] = {
    "claude": ("claude/CLAUDE.md", "CLAUDE.md", True),
    "agents": ("agents/AGENTS.md", "AGENTS.md", True),
    "cursor": ("cursor/.cursor/rules/popia.mdc", ".cursor/rules/popia.mdc", False),
    "copilot": ("copilot/.github/copilot-instructions.md", ".github/copilot-instructions.md", True),
    "windsurf": ("windsurf/.windsurf/rules/popia.md", ".windsurf/rules/popia.md", False),
    "gemini": ("gemini/GEMINI.md", "GEMINI.md", True),
}

# A tool counts as in use when any of these exist in the project.
SIGNS: Dict[str, List[str]] = {
    "claude": ["CLAUDE.md", ".claude"],
    "agents": ["AGENTS.md"],
    "cursor": [".cursor", ".cursorrules"],
    "copilot": [".github/copilot-instructions.md", ".github/instructions"],
    "windsurf": [".windsurf", ".windsurfrules"],
    "gemini": ["GEMINI.md", ".gemini"],
}

WORKFLOW_DEST = ".github/workflows/popia-scan.yml"

POPIAIGNORE = """\
# Paths the POPIA scanner skips, one glob per line. Record why for each entry.
# Prefer an inline "popia-ignore: RULE-ID reason" comment for a single false positive.
# Synthetic test data, never real personal information:
# tests/fixtures/
"""


def detect(root: Path) -> List[str]:
    found = [t for t, signs in SIGNS.items() if any((root / s).exists() for s in signs)]
    return found or ["agents"]  # AGENTS.md is read by Codex, Jules, Amp, Aider and others


def _inside(root: Path, dest: Path) -> bool:
    try:
        dest.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _through_symlink(root: Path, rel: str) -> bool:
    """True if any part of rel below root is a symlink."""
    p = root
    for part in Path(rel).parts:
        p = p / part
        if p.is_symlink():
            return True
    return False


def merge_block(existing: str, body: str) -> str:
    """Add or replace the marked POPIA Kit block in a shared file, keeping the rest."""
    block = f"{START}\n{body.strip()}\n{END}\n"
    if START in existing and END in existing and existing.index(START) < existing.index(END):
        before = existing[:existing.index(START)]
        after = existing[existing.index(END) + len(END):].lstrip("\n")
        return before + block + (("\n" + after) if after else "")
    if not existing:
        return block
    return existing.rstrip("\n") + "\n\n" + block


def plan(root: Path, tools: List[str], workflow: bool, ignore: bool,
         force: bool) -> List[Tuple[str, str, str, str]]:
    """Return (action, relative path, new content, note) for each file. action is create,
    update, skip or refuse."""
    out: List[Tuple[str, str, str, str]] = []

    def add(rel: str, content: str, shared: bool) -> None:
        dest = root / rel
        # Never follow a symlink or write outside the project, at any level of the path.
        if _through_symlink(root, rel) or not _inside(root, dest):
            out.append(("refuse", rel, "", "symlink or outside the project, not touched"))
        elif not dest.exists():
            out.append(("create", rel, merge_block("", content) if shared else content, ""))
        elif shared:
            old = dest.read_text(encoding="utf-8", errors="replace")
            new = merge_block(old, content)
            out.append(("skip", rel, "", "already up to date") if new == old else
                       ("update", rel, new, "POPIA Kit block added or refreshed, the rest kept"))
        elif force:
            out.append(("update", rel, content, "replaced (--force)"))
        else:
            out.append(("skip", rel, "", "already there, left alone. Use --force to replace"))

    for t in tools:
        src, rel, shared = TOOLS[t]
        add(rel, (ADAPTERS_DIR / src).read_text(encoding="utf-8"), shared)
    if workflow:
        add(WORKFLOW_DEST, (EXAMPLES_DIR / "github-workflow-popia-scan.yml").read_text(encoding="utf-8"), False)
    if ignore:
        add(".popiaignore", POPIAIGNORE, False)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="popia-kit init",
        description="Set up POPIA Kit in a project: AI rules files, a scan workflow and .popiaignore.")
    ap.add_argument("path", nargs="?", default=".")
    ap.add_argument("--tools", default="auto",
                    help="auto, or a comma-separated list of: " + ", ".join(TOOLS))
    ap.add_argument("--no-workflow", action="store_true", help="don't add .github/workflows/popia-scan.yml")
    ap.add_argument("--no-ignore", action="store_true", help="don't add .popiaignore")
    ap.add_argument("--force", action="store_true", help="replace POPIA Kit files that already exist")
    ap.add_argument("--dry-run", action="store_true", help="show what would change, write nothing")
    a = ap.parse_args(argv)

    root = Path(a.path)
    if not root.is_dir():
        print(f"popia-kit init: not a folder: {a.path}", file=sys.stderr)
        return 2
    if a.tools == "auto":
        tools = detect(root)
    else:
        tools = [t.strip().lower() for t in a.tools.split(",") if t.strip()]
        unknown = [t for t in tools if t not in TOOLS]
        if unknown or not tools:
            print(f"popia-kit init: unknown tool {', '.join(unknown) or '(none)'}. "
                  f"Choose from: {', '.join(TOOLS)}", file=sys.stderr)
            return 2

    steps = plan(root, tools, not a.no_workflow, not a.no_ignore, a.force)
    for action, rel, content, note in steps:
        if action in ("create", "update") and not a.dry_run:
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
        print(f"  {action:<7} {rel}" + (f"  ({note})" if note else ""))

    print(f"\nTools: {', '.join(tools)}" + ("  (dry run, nothing written)" if a.dry_run else ""))
    print("Next: run 'popia-kit scan .' and triage each finding. "
          "On an existing codebase, start with 'popia-kit scan . --write-baseline popia-baseline.json'.")
    print("Engineering guidance, not legal advice.")
    return 1 if any(s[0] == "refuse" for s in steps) else 0


if __name__ == "__main__":
    sys.exit(main())
