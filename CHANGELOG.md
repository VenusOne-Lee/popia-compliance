# Changelog

Code follows semantic versioning. Entries that reflect a change in law are headed with the **legal effective date**.

Legal content merged without a legal reviewer is marked `pending legal review` (see GOVERNANCE.md).

## [Unreleased]

## [1.2.0] - 2026-10-19

### Added
- `popia-kit supabase`: a read-only check of a live Supabase database. One catalog query (`popia-kit supabase sql`) that reads settings, never table data, and 11 rules: tables open to the anon key or to every signed-in user, `using (true)` policies, open inserts, views that skip row level security or read `auth.users`, materialized views, callable security definer functions, public buckets, foreign tables and extra exposed schemas. Severity rises when column names suggest personal information. Run the query in the SQL editor and `popia-kit supabase check result.json`, or `popia-kit supabase run` with psql, which uses a read-only session. CI runs it against a throwaway Postgres seeded with known risks.
- `hosted/site-check/report/actions.json`: a proposed action, reason and POPIA Kit pointer for every site check finding, the title of each cited section, and report copy. A test checks it covers every rule.
- Lovable workspace skill in `adapters/lovable/skill/SKILL.md`: the Lovable rules plus the read-only database check, so a Lovable project can run it and propose a migration. Generated from the core, the inventory query and the rule table, and CI checks it is current.

### Fixed
- Site check graded bot check pages. A site behind Vercel or Cloudflare bot protection answered with its challenge page, and the check reported that page's gaps, including a missing privacy link, as the site's. Now a bot check or an error status stops the check with a plain message and nothing is graded. Reported by a user on launch day.
- Site check reported "not found" for notices on pages that build their links with JavaScript. Those notices now show as unknown, with one info finding (WEB-022) that says to confirm in a browser.

### Changed
- popia-kit is on PyPI. Install commands are now `uvx popia-kit scan .`, `pipx run popia-kit scan .` and `pipx install popia-kit`.

## [1.1.0] - 2026-10-18

### Added
- Release workflow: a version tag publishes to PyPI and npm with trusted publishing and npm provenance, then creates a GitHub release. Setup in docs/releasing.md.
- One-line install, no clone needed: `uvx --from git+https://github.com/VenusOne-Lee/popia-compliance popia-kit scan .`, the `pipx run` equivalent, or `npx -y github:VenusOne-Lee/popia-compliance scan .`. One `popia-kit` command with `scan`, `site-check`, `pack`, `badge`, `id` and `mcp`. Packaging files: `pyproject.toml` (package `popia-kit`) and `package.json`. CI installs the package into a clean environment and runs every command.
- Legal reviewer route: reviewer terms in GOVERNANCE.md (`pending legal review`), a "Legal reviewer: volunteer" issue form, and a private contact address, popiakit@venusone.africa.
- First real-model eval run, published in `evals/published/`: Claude Opus 5.5, 26 of 30 cases passed, mean score 0.98. The 4 failures pass after the fixes listed under Changed.
- Hosted site check in `hosted/site-check/`: the passive site check as a Supabase Edge Function, with Node adapters for TanStack Start and similar hosts. Every hop is checked against private, loopback, link-local and metadata addresses. Per-IP and global rate limits, optional Turnstile, no logging, and only a salted IP hash kept for 2 hours. 94 unit tests, 27 SQL tests and 5 Node tests run in CI. Read the residual risks in its README before you host it.
- Security workflow: Bandit, Semgrep, Gitleaks (full history) and CodeQL on every push and pull request, and weekly. Dependabot for GitHub Actions.

### Changed
- `pending legal review`: legal map adds employment screening guidance (consent under s27(1)(a), vendor authorisation under s57(1)(b)) and names the s103(1) and s103(2) offences; SKILL.md and the stack playbook treat hosted automation tools as operators and usually s72 transfers; Explain mode gives the whole list when the Act lists grounds.
- Docs and the example workflow pin this Action to a commit SHA instead of a tag.
- `evals/run_evals.py` refuses provider URLs that are not http or https.

### Fixed
- Hosted site check works on Cloudflare Workers. The DNS over HTTPS and Turnstile calls used `redirect: "error"`, which Workers reject, so every check failed with `fetch_failed`. They now use `redirect: "manual"` and refuse any redirect. A new test fakes the Workers fetch rule.
- Build output (`build/`, `popia_kit.egg-info/`) is no longer tracked in git.
- Hosted site check type checks under strict TypeScript (`noUncheckedIndexedAccess`, `exactOptionalPropertyTypes` and related flags), so strict projects can copy `core.ts` without `@ts-nocheck`. Type-only change, CI now enforces the flags.
- Edge functions: "Delete my account" now checks when the session making the request signed in (its `amr` timestamp), not the account's last sign-in, which any other device could refresh. Client IP for consent evidence prefers `cf-connecting-ip` and `x-real-ip`, then the right-most `X-Forwarded-For` entry, because the left-most one is set by the client. Found in a review of the Lovable port.
- Registry README: the edge functions do need the `privacy` schema exposed in the Data API. Add it to the existing list and apply `0004_function_guards.sql` first.
- Supabase: new migration `0004_function_guards.sql`. `privacy.redact_consent_events` now refuses API callers that are not `service_role`, even if a grant is left open, and `privacy.security_report()` flags security definer functions that `anon` or `authenticated` can execute. Found in an end-to-end test on Lovable Cloud, where the migration tool skipped a revoke and left the function executable by any signed-in user.
- Components compile under strict TypeScript settings (`noPropertyAccessFromIndexSignature`, `exactOptionalPropertyTypes`, `noUncheckedIndexedAccess`), which Lovable's current template turns on.
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
