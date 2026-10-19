#!/usr/bin/env python3
"""
popia-kit: one entry point for the POPIA Kit tools.

    popia-kit scan ./my-app                  code scanner (43 rules)
    popia-kit site-check https://example.com passive live site check
    popia-kit supabase sql                   read-only Supabase database check
    popia-kit pack --interactive             draft compliance pack
    popia-kit badge popia-scan.json          dated status badge
    popia-kit id validate <id number>        SA ID number helpers
    popia-kit mcp                            MCP server on stdio
    popia-kit version

Each command takes the same options as the script it wraps. Add --help after a
command for details. Stdlib only. Python 3.8+.

Run it without installing (pick one):

    uvx popia-kit scan .
    pipx run popia-kit scan .
    npx -y github:VenusOne-Lee/popia-compliance scan .

Engineering guidance, not legal advice. See DISCLAIMER.md.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import List, Optional

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

VERSION = "1.1.0"

COMMANDS = {
    "scan": ("popia_scan", "Scan a codebase for POPIA and security risks"),
    "site-check": ("site_check", "Passive check of a live website"),
    "supabase": ("supabase_check", "Read-only check of a Supabase database"),
    "pack": ("popia_pack", "Generate a draft compliance pack"),
    "badge": ("popia_badge", "Build a dated badge from a scan result"),
    "id": ("sa_id", "Validate, parse or mask an SA ID number"),
    "mcp": (None, "Run the MCP server on stdio"),
}


def usage() -> str:
    lines = ["usage: popia-kit <command> [options]", "", "commands:"]
    for name, (_, desc) in COMMANDS.items():
        lines.append(f"  {name:<11} {desc}")
    lines.append(f"  {'version':<11} Print the version")
    lines += ["", "Run 'popia-kit <command> --help' for options.",
              "Engineering guidance, not legal advice."]
    return "\n".join(lines)


def _mcp_main() -> int:
    # Clone layout: <repo>/mcp/server.py. Installed layout: popia_kit/mcp/server.py.
    for base in (HERE.parent / "mcp", HERE / "mcp"):
        if (base / "server.py").is_file():
            if str(base.parent) not in sys.path:
                sys.path.insert(0, str(base.parent))
            break
    try:
        server = importlib.import_module("popia_kit.mcp.server")
    except ImportError:
        server = importlib.import_module("mcp.server")
    server.serve()
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help", "help"):
        print(usage())
        return 0
    cmd, rest = args[0], args[1:]
    if cmd in ("version", "--version", "-V"):
        print("popia-kit " + VERSION)
        return 0
    if cmd not in COMMANDS:
        print(f"popia-kit: unknown command '{cmd}'\n", file=sys.stderr)
        print(usage(), file=sys.stderr)
        return 2
    if cmd == "mcp":
        return _mcp_main()
    module = importlib.import_module(COMMANDS[cmd][0])
    if cmd == "id":
        return int(module._main(["popia-kit id"] + rest) or 0)
    return int(module.main(rest) or 0)


def run_scan() -> int:
    return main(["scan"] + sys.argv[1:])


def run_site_check() -> int:
    return main(["site-check"] + sys.argv[1:])


def run_supabase() -> int:
    return main(["supabase"] + sys.argv[1:])


def run_pack() -> int:
    return main(["pack"] + sys.argv[1:])


def run_badge() -> int:
    return main(["badge"] + sys.argv[1:])


def run_mcp() -> int:
    return main(["mcp"])


if __name__ == "__main__":
    sys.exit(main())
