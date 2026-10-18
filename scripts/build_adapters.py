#!/usr/bin/env python3
"""
Generate tool-specific adapters from adapters/_core.md so every AI tool gets the same rules.

    python3 scripts/build_adapters.py          # write adapters
    python3 scripts/build_adapters.py --check  # exit 1 if adapters are stale (CI)
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = (ROOT / "adapters" / "_core.md").read_text(encoding="utf-8").strip() + "\n"
BODY = CORE.split("\n", 1)[1].lstrip()  # without the H1
HEADER = "<!-- Generated from adapters/_core.md by scripts/build_adapters.py. Edit the core, not this file. -->\n"

OUTPUTS = {
    # Cursor project rule (.mdc with front matter)
    "adapters/cursor/.cursor/rules/popia.mdc":
        "---\ndescription: POPIA privacy and security guardrails for code that touches personal information of South Africans\n"
        "globs:\nalwaysApply: true\n---\n" + HEADER + CORE,
    # AGENTS.md: OpenAI Codex, Jules, Amp, Aider and other agents that read AGENTS.md
    "adapters/agents/AGENTS.md": HEADER + CORE,
    # GitHub Copilot repository instructions
    "adapters/copilot/.github/copilot-instructions.md": HEADER + CORE,
    # Windsurf (rules folder) and legacy single file
    "adapters/windsurf/.windsurf/rules/popia.md":
        "---\ntrigger: always_on\ndescription: POPIA privacy and security guardrails\n---\n" + HEADER + CORE,
    "adapters/windsurf/.windsurfrules": HEADER + CORE,
    # Gemini CLI / Gemini Code Assist
    "adapters/gemini/GEMINI.md": HEADER + CORE,
    # Claude Code project memory snippet (the full skill is SKILL.md)
    "adapters/claude/CLAUDE.md": HEADER + CORE +
        "\nFor the full skill (audit procedure, references, scanner), install this repository as a skill: see README.\n",
    # Lovable project or workspace knowledge
    "adapters/lovable/knowledge.md": HEADER + CORE +
        "\n## Lovable specifics\n\n- Before publishing, run Lovable's security scan and check every Supabase table has RLS.\n"
        "- Add the consent banner and privacy centre from the components registry instead of hand-rolling them.\n"
        "- Lovable preview links are public. Never connect previews to production data.\n",
    # ChatGPT custom GPT / project instructions (plain text limit friendly)
    "adapters/chatgpt/custom-gpt-instructions.md": HEADER +
        "You are a privacy engineering assistant for South African builders. Apply these rules to every answer about "
        "software that handles personal information.\n\n" + BODY,
}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    stale = []
    for rel, content in OUTPUTS.items():
        p = ROOT / rel
        if a.check:
            if not p.exists() or p.read_text(encoding="utf-8") != content:
                stale.append(rel)
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        print(f"wrote {rel}")
    if a.check and stale:
        print("stale adapters (run scripts/build_adapters.py):\n  " + "\n  ".join(stale), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
