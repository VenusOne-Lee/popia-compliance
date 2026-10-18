# POPIA Compliance Skill

**Privacy and security guardrails for South African builders, for every AI coding tool.**

An open-source skill that helps you build websites and apps that respect POPIA (the Protection of Personal Information Act) and prove it: a skill your AI tools load, a scanner that finds problems in your code, drop-in components that fix the common ones, and the documents an Information Officer needs.

Maintained by Venus One (Venus ARC (Pty) Ltd) and contributors.

> [!IMPORTANT]
> **Engineering guidance, not legal advice.** This project has **no legal reviewer yet**. Content is researched from the Act, the Regulations and the Information Regulator's publications, but has not been reviewed by an attorney. A clean scan is not a compliance certificate. Read [DISCLAIMER.md](DISCLAIMER.md). Attorneys: [we'd like your help](GOVERNANCE.md#the-legal-reviewer-seat).

Law current to **18 October 2026**. See [regulatory watch](references/10-regulatory-watch.md).

## What's inside

| Part | What it does | Where | Status |
|---|---|---|---|
| **Skill** | Teaches AI tools POPIA in Build, Audit, Breach, Docs and Explain modes | [`SKILL.md`](SKILL.md), [`references/`](references) | Available |
| **Adapters** | Same rules for Cursor, Codex, Copilot, Windsurf, Gemini, Lovable, ChatGPT | [`adapters/`](adapters) | Available |
| **Scanner** | Finds open tables, leaked keys, trackers before consent, pre-ticked boxes, PI in logs and more. Markdown, JSON, SARIF | [`scripts/popia_scan.py`](scripts/popia_scan.py) | Available |
| **Site check** | Passive check of a live site: headers, cookies before consent, trackers, notices | [`scripts/site_check.py`](scripts/site_check.py) | Available |
| **Hosted site check** | The same check as a public endpoint you can host, hardened for untrusted URLs: SSRF guard on every hop, rate limits, optional Turnstile | [`hosted/site-check/`](hosted/site-check) | Available |
| **Components** | Consent banner, Form 4 opt-in, privacy centre, Supabase migrations and edge functions | [`registry/`](registry) | Available |
| **Compliance pack** | Answer questions, get a draft privacy notice, cookie notice, ROPA, PAIA manual and more | [`scripts/popia_pack.py`](scripts/popia_pack.py), [`templates/`](templates) | Available |
| **Sector packs** | Fintech, health, education and children, short-term rentals, e-commerce, HR | [`packs/`](packs) | Available |
| **Translations** | Draft notices in Afrikaans, isiZulu, isiXhosa and Setswana (review wanted) | [`i18n/`](i18n) | Draft, needs native review |
| **MCP server** | Lets any MCP-capable agent run the scanner and look up guidance | [`mcp/`](mcp), [`docs/mcp.md`](docs/mcp.md) | Available |
| **CI** | GitHub Action, pre-commit hook, scan badge | [`action.yml`](action.yml), [`docs/automation.md`](docs/automation.md) | Available |
| **Evals** | Test cases that check AI tools follow the skill | [`evals/`](evals) | Available |

## Start here

New project, existing codebase or Lovable: [docs/quickstart.md](docs/quickstart.md) has a short path for each.

## Install

### Claude (claude.ai, Claude Desktop) and Claude Code
Download the repository as a zip and add it as a skill, or copy the folder into your skills directory (for Claude Code: `.claude/skills/popia-compliance/` in a project, or `~/.claude/skills/popia-compliance/` for all projects). The skill triggers on anything touching personal information of South Africans.

### Cursor, Codex, Copilot, Windsurf, Gemini, Lovable, ChatGPT
Copy the matching file from [`adapters/`](adapters) into your project. Table and paths in [`adapters/README.md`](adapters/README.md).

### Any MCP client
```bash
claude mcp add popia -- uvx popia-kit mcp
# or, from a clone:
claude mcp add popia -- python3 /path/to/popia-compliance/mcp/server.py
```
Config for Claude Desktop, Cursor, VS Code and Windsurf: [`docs/mcp.md`](docs/mcp.md).

## Quick start

Python 3.8 or newer and nothing else. No install needed: run it from [PyPI](https://pypi.org/project/popia-kit/) with whichever tool you already have.

```bash
# uv
uvx popia-kit scan .

# pipx
pipx run popia-kit scan .

# npm (still runs the Python tools, so Python 3.8+ must be installed)
npx -y github:VenusOne-Lee/popia-compliance scan .
```

To keep it installed: `pipx install popia-kit`, then use `popia-kit` anywhere. For the latest code on `main`, use `uvx --from git+https://github.com/VenusOne-Lee/popia-compliance popia-kit scan .`

| Command | What it does |
|---|---|
| `popia-kit scan ./my-app --format md --out popia-scan.md` | Scan a codebase (43 rules). Also `--format json` or `--format sarif` |
| `popia-kit site-check https://example.co.za --out site-check.md` | Passive check of a live site you own |
| `popia-kit pack --interactive --out ./compliance-pack` | Answer questions, get draft notices, PAIA manual, ROPA and more |
| `popia-kit badge popia-scan.json --out popia-badge.svg` | Dated badge from a scan or site check result |
| `popia-kit id validate <id number>` | Check an SA ID number without logging it |
| `popia-kit mcp` | Run the MCP server on stdio |

Prefer a clone? Every command is also a plain script:

```bash
git clone https://github.com/VenusOne-Lee/popia-compliance
cd popia-compliance
python3 scripts/popia_scan.py tests/fixtures/demo-app   # the deliberately broken demo app
```

### In CI

```yaml
# .github/workflows/popia.yml
on: [pull_request]
permissions: { contents: read, security-events: write }
jobs:
  popia:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: VenusOne-Lee/popia-compliance@0192dd213a41c62c2cfeb9e11221bad4af7bc729 # v1.0.0
        with: { fail-on: high }
```

## What the scanner checks

Run `python3 scripts/popia_scan.py --list-rules` for the full list. Highlights:

- **Access control:** Supabase tables without RLS, `using (true)` policies, public buckets, Firebase test-mode rules, identity taken from request bodies.
- **Secrets:** API keys, private keys, Supabase `service_role` keys in client code, secrets behind `VITE_` / `NEXT_PUBLIC_`.
- **Personal information:** valid SA ID numbers and card numbers in code or data files, PI in logs, URLs and browser storage, ID numbers in plain columns.
- **Consent and marketing:** trackers with no consent mechanism, pre-ticked boxes, bundled consent, marketing without unsubscribe.
- **Special PI and children:** race, health, biometrics and other special fields; date of birth and school fields.
- **Operators and AI:** SDKs that make vendors operators and transfers, personal information in LLM prompts, automated decisions.
- **Gaps:** no privacy notice, no PAIA manual, no deletion or export, no retention job, no security.txt, no security CI.

Findings are leads, not verdicts. Every report redacts the secrets and personal information it detects.

## How this maps to POPIA

Every finding and checklist item maps to one of POPIA's eight conditions (accountability, processing limitation, purpose specification, further processing, information quality, openness, security safeguards, data subject participation) or the rules on special personal information, children, direct marketing, automated decisions and cross-border transfers. Start with [`references/01-popia-legal-map.md`](references/01-popia-legal-map.md).

## Contributing

The law changes, enforcement evolves and builders find new ways to leak data. Help keep this current:

- **Report a law change:** open a [law-change issue](.github/ISSUE_TEMPLATE/law-change.yml). A monthly automated watch of the Regulator's site opens these too.
- **Add a scanner rule, component, pack or translation:** see [CONTRIBUTING.md](CONTRIBUTING.md).
- **Attorneys and privacy professionals:** the legal reviewer seat is open. Small, focused reviews, credited by name, and a review is not legal advice to users. Email **popiakit@venusone.africa** or see [GOVERNANCE.md](GOVERNANCE.md#reviewer-terms).

## Licence

Code: [MIT](LICENSE). Guidance, templates and other content: [CC BY 4.0](LICENSE-CONTENT), credit "Venus One (Venus ARC (Pty) Ltd) and contributors". Details in [LICENSING.md](LICENSING.md). Marks: [TRADEMARKS.md](TRADEMARKS.md).
