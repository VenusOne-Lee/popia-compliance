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

sys.path.insert(0, str(ROOT / "scripts"))
import supabase_check  # noqa: E402  (rule titles and fixes for the Lovable skill)

INVENTORY_SQL = "\n".join(
    line for line in (ROOT / "scripts" / "sql" / "supabase_inventory.sql").read_text(encoding="utf-8").splitlines()
    if not line.startswith("--")).strip()

LOVABLE_SPECIFICS = (
    "\n## Lovable specifics\n\n- Before publishing, run Lovable's security scan and check every Supabase table has RLS.\n"
    "- Add the consent banner and privacy centre from the components registry instead of hand-rolling them.\n"
    "- Lovable preview links are public. Never connect previews to production data.\n")


def _lovable_skill() -> str:
    rules = "\n".join(
        f"| {rid} | {r['title']} | {r['popia']} | {r['fix']} |" for rid, r in supabase_check.RULES.items())
    return (
        "---\nname: popia-kit\n"
        "description: POPIA privacy and security guardrails for South African apps, plus a read-only database check. "
        "Use when building or changing anything that handles personal information, before publishing, or when asked "
        "for a POPIA, privacy or security review.\n---\n\n"
        + HEADER + "\n" + CORE + LOVABLE_SPECIFICS +
        "\n## Database check (read-only)\n\n"
        "Run this when asked for a POPIA, privacy or security review, before publishing, and after any migration "
        "that adds a table, view, function, policy or bucket.\n\n"
        "1. Run the query below with your read-only SQL tool. Never run it as a migration. It reads the system "
        "catalogs only: no table data, no personal information, no changes.\n"
        "2. Read the single JSON value it returns and apply the rules below. Skip tables, views, policies and "
        "functions in the platform schemas "
        + ", ".join(f"`{s}`" for s in sorted(supabase_check.PLATFORM_SCHEMAS)) + ", but still check buckets. "
        "Use the severities below. Column names that suggest personal information (email, phone, ID number, "
        "address, date of birth, health, bank details and similar) raise some of them.\n"
        "3. Report a table: severity, rule, object, evidence, POPIA section, fix. Say it is a lead to review, "
        "not a legal conclusion.\n"
        "4. Propose the fixes as one migration and wait for the user to approve it. Never change policies, grants "
        "or buckets without approval. A critical finding may mean personal information was already exposed: tell "
        "the user that s22 may require notifying the Information Regulator and the people affected.\n"
        "5. After the migration, run the query again and confirm the findings are gone.\n\n"
        "Expected and fine: an anon insert policy on a sign-up or contact form table that anon cannot read (SB-005, "
        "low), and an extra exposed schema that only holds protected tables (SB-011, info).\n\n"
        "| Rule | Finding | POPIA | Fix |\n|---|---|---|---|\n" + rules + "\n\n"
        "Severity: SB-001 critical. SB-002 high, critical with personal information. SB-003 high, critical for "
        "select with personal information. SB-004 medium, high with personal information. SB-005 low, high if anon "
        "can also read. SB-006 high, critical if it reads `auth.users` or anon can read personal information. "
        "SB-007 high, critical if anon can read personal information. SB-008 high for anon without a fixed search_path, medium for anon with one or authenticated "
        "without, low for authenticated with one. SB-009 high. SB-010 high. SB-011 info.\n\n"
        "```sql\n" + INVENTORY_SQL + "\n```\n\n"
        "The same query and rules ship as `uvx popia-kit supabase sql` and `uvx popia-kit supabase check result.json`. "
        "For the live site, use the free passive check at https://popiakit.co.za/check.\n")

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
    "adapters/lovable/knowledge.md": HEADER + CORE + LOVABLE_SPECIFICS,
    # Lovable workspace skill: the knowledge plus the read-only database check
    "adapters/lovable/skill/SKILL.md": _lovable_skill(),
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
