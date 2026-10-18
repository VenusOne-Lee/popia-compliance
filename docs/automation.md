# Automation

How to run the POPIA scanner automatically, keep the law current, scan a portfolio of apps, and show a status badge. Everything here is stdlib Python 3.8 or later.

Scanner output is a set of leads for review, not a legal conclusion. This is engineering guidance, not legal advice. See [DISCLAIMER.md](../DISCLAIMER.md).

## Contents

1. GitHub Action
2. pre-commit hook
3. CI for this repository
4. Regulator watch
5. Fleet scan
6. Badge and wording policy
7. MCP server

## 1. GitHub Action

`action.yml` at the repo root is a composite action called **POPIA Scan**. It sets up Python, runs `scripts/popia_scan.py`, writes Markdown to the job summary, uploads SARIF to GitHub code scanning, and fails the job at the threshold you choose.

Copy [`examples/github-workflow-popia-scan.yml`](../examples/github-workflow-popia-scan.yml) to `.github/workflows/popia-scan.yml`:

```yaml
permissions:
  contents: read
  security-events: write
steps:
  - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4.4.0
  - uses: VenusOne-Lee/popia-compliance@v1.0.0
    with:
      fail-on: high
```

| Input | Default | Meaning |
|---|---|---|
| `path` | `.` | Path to scan |
| `fail-on` | `high` | Fail at this severity or above. `none` never fails |
| `min-severity` | `info` | Lowest severity reported |
| `sarif` | `true` | Write `popia-scan.sarif` |
| `upload-sarif` | `true` | Upload to code scanning (needs `security-events: write`). Runs with `continue-on-error`, so a private repo without code scanning still gets the summary and the threshold check |
| `python-version` | `3.12` | Any version from 3.8 |

| Output | Meaning |
|---|---|
| `critical` | Number of critical findings |
| `high` | Number of high findings |
| `sarif-file` | SARIF path, if written |

Tips:

- Start with `fail-on: critical` on an existing codebase, fix those, then move to `high`.
- Suppress a confirmed false positive inline with `// popia-ignore: RULE-ID` and a reason, or with a `.popiaignore` file. Record why in the PR.
- Findings show in the Security tab under the `popia-scan` category.

## 2. pre-commit hook

`.pre-commit-hooks.yaml` defines the hook `popia-scan`. It scans the whole repository (not only staged files) and blocks the commit on high or critical findings. It needs `python3` on your PATH and installs nothing.

Add to `.pre-commit-config.yaml` in your project:

```yaml
repos:
  - repo: https://github.com/VenusOne-Lee/popia-compliance
    rev: v1.0.0
    hooks:
      - id: popia-scan
```

Then:

```bash
pip install pre-commit
pre-commit install
pre-commit run popia-scan --all-files
```

To change the threshold, override `args` in your config, for example `args: [--fail-on, critical]`. Skip once with `SKIP=popia-scan git commit ...`, and say why in the commit message.

## 3. CI for this repository

`.github/workflows/ci.yml` runs on every push and pull request, on Python 3.8 and 3.12:

```bash
python -m unittest discover -s tests -p "test_*.py" -t .
python3 scripts/popia_scan.py --list-rules
python3 scripts/popia_scan.py tests/fixtures --format json --out scan-fixtures.json   # if fixtures exist
python3 evals/run_evals.py --dry-run                                                 # if present
python3 registry/build.py --check                                                    # if present
python3 mcp/smoke_test.py
python3 scripts/popia_badge.py scan-fixtures.json --out badge.svg
python3 scripts/regwatch.py --dry-run --offline-fixture tests/automation/fixtures/regulator-list.html
python3 scripts/style_lint.py                                                        # if present
```

Optional steps are guarded with `hashFiles(...) != ''`, so CI stays green while parts of the repo are still being written. Every test folder under `tests/` has an `__init__.py` so discovery works from the root.

## 4. Regulator watch

`scripts/regwatch.py` checks Information Regulator listing pages for items it has not seen before. `.github/workflows/regwatch.yml` runs it on the 1st of every month at 06:00 SAST (04:00 UTC), and on demand from the Actions tab.

Sources are configured in [`regwatch/sources.json`](../regwatch/sources.json): media statements, enforcement notices and guidance notes. Add a source by adding an entry with `id`, `name`, `url` and `enabled`. Link filters (`include_link_patterns`, `exclude_link_patterns`, `min_title_length`) are in the same file.

Seen items are stored in [`regwatch/state.json`](../regwatch/state.json). The workflow commits it after each run.

```bash
python3 scripts/regwatch.py --dry-run                     # report only
python3 scripts/regwatch.py --update-state                # report, then mark items as seen
python3 scripts/regwatch.py --open-issue --update-state   # what the monthly workflow runs
python3 scripts/regwatch.py --offline-fixture page.html --dry-run   # test parsing without network
```

With `--open-issue`, one issue per run is created with `gh issue create --label law-change`. The body follows the law-change format:

- What changed (each new item with its link)
- Source link
- Effective date: TBC, confirm from the primary source
- Files likely affected (keyword guess, always includes `references/10-regulatory-watch.md`)
- Checklist: update `references/10-regulatory-watch.md`, update affected references, CHANGELOG, evals

A new item is a prompt to read the source. It is not proof that the law changed. A person must read the item, decide, and follow the law change process in CONTRIBUTING.md.

Politeness: one GET per source, a 3 second gap between sources, a 20 second timeout, no retries, and a User-Agent that names this project. A failed fetch is reported in the output and the workflow fails only if every source fails.

## 5. Fleet scan

`scripts/popia_fleet.py` scans many repositories and produces anonymised aggregate figures, for a report such as "we scanned N apps and X% had a critical finding".

```bash
# a folder whose subfolders are repositories
python3 scripts/popia_fleet.py --dir ~/code/clients --out fleet.md

# a list of local paths or git URLs, one per line (# for comments)
python3 scripts/popia_fleet.py --list repos.txt --out fleet.json

# internal review only: show names instead of hashes
python3 scripts/popia_fleet.py --dir ~/code/clients --show-names --out fleet-internal.md
```

Git URLs are cloned shallow (`--depth 1`) into a temporary directory and deleted after the scan. Private repos need your normal git credentials.

What the report contains:

- Repositories scanned, and how many failed to clone or scan
- Percentage of repositories with at least one critical finding, and with at least one critical or high finding
- Median findings per repository
- Top rules by percentage of repositories affected
- Category breakdown: secrets and credentials, access control, consent and trackers, personal information in code and logs, cross-border and third parties, other
- Per-repository counts by severity, under a hashed id
- Methodology and limitations

What it never contains: code snippets, file paths, secret values, finding messages or, unless `--show-names` is set, repository names or URLs. Identities are the first 10 hex characters of a sha256 of the path or URL.

Before publishing a fleet report:

- Get permission from each client whose code is in the sample, or use only your own projects.
- Keep `--show-names` output internal. Treat it like the code itself.
- Quote the scanner version and rule count from the report header, and the limitations section with it.
- Do not describe the figures as compliance rates. They are scanner hits.

### Using it with Lovable projects

Lovable projects are not cloned from Lovable directly. Sync each project to GitHub first:

1. In each Lovable project, open the GitHub integration and connect the project to a GitHub repository (one repo per project). Lovable keeps the default branch in sync.
2. List the repositories in a file, one per line:
   ```
   https://github.com/your-org/lovable-project-one.git
   https://github.com/your-org/lovable-project-two.git
   ```
   Or clone them all into one folder and use `--dir`.
3. Run `python3 scripts/popia_fleet.py --list lovable-repos.txt --out lovable-fleet.md`.

Lovable apps usually use Supabase. The rules that matter most there are the access control ones (RLS missing or permissive, service role key in client code) and secrets in public env prefixes. The scanner sees migrations and client code in the repo, but not RLS settings changed in the Supabase dashboard. For those, run the read-only SQL in `references/04-stack-playbooks.md` section 1.

## 6. Badge and wording policy

`scripts/popia_badge.py` turns a scan JSON into a two-part badge:

```
POPIA scan | 0 critical · 2 high · 2026-10-18
```

```bash
python3 scripts/popia_scan.py . --format json --out popia-scan.json
python3 scripts/popia_badge.py popia-scan.json --out popia-badge.svg
python3 scripts/popia_badge.py popia-scan.json --shields-json --out popia-badge.json
```

The colour follows the worst severity present: red for critical, orange for high, yellow for medium, yellow-green for low, green for info only, bright green for no findings.

`--shields-json` writes a [shields.io endpoint](https://shields.io/badges/endpoint-badge) file. Commit it (or publish it from CI to a branch or Pages) and use:

```
![POPIA scan](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/OWNER/REPO/BRANCH/popia-badge.json)
```

**Wording policy.** The badge reports what the scanner found on a date. It must never say or imply that a product is compliant, certified, approved or accredited, because:

- POPIA has no certification scheme for apps, and the Information Regulator does not approve products.
- A static scan cannot see consent wording, contracts, Information Officer registration or business process.
- Zero findings means zero scanner hits, not lawful processing.

The badge script enforces this. Any label or message containing "compliant", "compliance", "certif", "approved", "accredited", "passed" or "guarantee" is refused with exit code 3. A unit test (`tests/automation/test_badge.py`) checks every output path. If you build your own badge, follow the same rule, and link it to the scan report rather than to a claim.

## 7. MCP server

The MCP server exposes the scanner, checklists, lookups and breach triage to AI tools. See [docs/mcp.md](mcp.md).
