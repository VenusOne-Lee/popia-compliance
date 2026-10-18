# Changelog

Code follows semantic versioning. Entries that reflect a change in law are headed with the **legal effective date**.

Legal content merged without a legal reviewer is marked `pending legal review` (see GOVERNANCE.md).

## [Unreleased]

### Added
- Security workflow: Bandit, Semgrep, Gitleaks (full history) and CodeQL on every push and pull request, and weekly. Dependabot for GitHub Actions.

### Changed
- Docs and the example workflow pin this Action to a commit SHA instead of a tag.
- `evals/run_evals.py` refuses provider URLs that are not http or https.

### Fixed
- `popia_badge`: badges built from a `site_check` JSON result now show the check date (`checked_at`), not just scanner results (`scanned_at`).

## [1.0.1] - 2026-10-18

Security hardening release. No change to legal content.

### Security
- `site_check`: reports and errors no longer include credentials, query strings or fragments from URLs; embedded credentials are never sent; cookie `Secure`, `HttpOnly` and `SameSite` flags are read from parsed attributes, so cookie values cannot fake them; new `--block-private` mode (on by default through MCP) refuses private, loopback, link-local and reserved targets on every redirect hop; redirects are limited to http and https.
- MCP server: unexpected errors return and log the exception type only; `popia_scan` refuses filesystem roots, the home folder and credential or system folders (optionally limited further with `POPIA_SCAN_ROOTS`); `popia_generate_pack` writes only to a new, empty sub-folder of the working directory; `popia_site_check` blocks private network targets unless `POPIA_ALLOW_PRIVATE_URLS=1`.
- Scanner: no longer follows symlinks out of the scanned tree.
- Fleet scan: clones only `https://` or `git@host:` URLs, separates the URL with `--`, disables hooks, submodules, LFS smudge and the file and ext transports, and redacts tokens from clone errors.
- Supabase functions: account deletion requires a recent sign-in (`RECENT_AUTH_MINUTES`, default 15); deletion and export list every page and sub-folder of storage and treat listing errors as failures, never as empty; exports are rate limited (`EXPORTS_PER_HOUR`, default 3); `competent_person_id` must be a UUID.
- GitHub Actions in the composite action, workflows and examples are pinned to full commit SHAs.
- `regwatch` fetches https sources only.
- Reference snippets: the retention function now pins `search_path` and restricts `EXECUTE`; the SA ID masking example is corrected; the public lead insert policy carries an abuse warning and a length constraint.
- Replaced a real-format sample ID number in `sa_id.py` documentation with a synthetic one. Added `.popiaignore` so a self-scan of this repo skips deliberate test fixtures.

### Credit
Findings 1 to 4 (URL leakage, cookie flag spoofing, MCP error leakage, incomplete storage deletion and export) came from an external review shared by the maintainer. The remaining items came from this review.

## [1.0.0] - 2026-10-18

First public release. All legal content: `pending legal review`.

### Law reflected (current to 18 October 2026)
- POPIA Act 4 of 2013 and Regulations as amended **17 April 2025** (free objections and corrections, opt-out is not consent, complaint process, fine instalments).
- Mandatory security compromise reporting via the Regulator's **eServices portal** from **1 April 2025**.
- Guidance Note on Direct Marketing (**4 December 2024**).
- Enforcement practice to the Regulator's **31 August 2026** briefing.

### Added
- `SKILL.md` with Build, Audit, Breach, Docs and Explain modes.
- References 01 to 10: legal map, build patterns, security control catalogue, stack playbooks, direct marketing, cross-border and operators, breach response, AI and automated decisions, audit procedure, regulatory watch.
- `popia_scan` static scanner with plug-in rules, Markdown, JSON and SARIF output.
- `site_check` passive live-site check.
- `sa_id` validation, masking and synthetic ID helpers.
- Compliance pack generator, templates and draft translations (af, zu, xh, tn).
- Drop-in components registry (consent banner, opt-in, privacy centre, Supabase migrations and edge functions).
- Sector packs, eval suite, MCP server, GitHub Action, pre-commit hook, regulatory watch, fleet scan and scan badge.
- Adapters for Claude, Cursor, Codex and other AGENTS.md tools, GitHub Copilot, Windsurf, Gemini, Lovable and ChatGPT.
- Open-source governance: dual licence, contributing guide, law change process, disclaimer.
