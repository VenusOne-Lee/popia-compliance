# Security policy

## Reporting a vulnerability in this project

If you find a vulnerability in this project's code (scanner, MCP server, components, edge functions, GitHub Action), please report it privately using GitHub's "Report a vulnerability" (Security tab), or email the lead maintainer listed in GOVERNANCE.md.

Please include steps to reproduce and the affected version. Don't include real personal information.

We aim to acknowledge reports within 3 working days and to fix critical issues within 14 days.

## Out of scope

- Findings the scanner reports in *your* code. That's the tool working.
- False positives. Open a normal issue with the `false-positive` label.

## Our own practices

- The scanner and site check run locally and send nothing anywhere.
- The site check is passive: ordinary page requests only. It never sends embedded credentials, and with `--block-private` (the default through MCP) it refuses private and internal network targets.
- Scan reports redact detected secrets, ID numbers, card numbers and emails.
- The MCP server returns only exception types on failure, refuses to scan system or credential folders, and never overwrites files when generating packs.
- GitHub Actions used by this project are pinned to full commit SHAs. Pin this Action to a release tag or commit SHA in your own workflows.
- The hosted MCP server (when available) must not store submitted code, URLs or results.

## Adopters: secure defaults to keep

- Edge functions: set `ALLOWED_ORIGINS`, `UNSUBSCRIBE_SECRET` and `CONSENT_IP_SALT` to strong values. Keep `RECENT_AUTH_MINUTES` short. Never move the service role key to the client.
- Migrations: keep row-level security forced on the privacy schema and keep `EXECUTE` on security definer functions restricted to `service_role`.
- Treat scan reports as sensitive. They are redacted, but they show where your weaknesses are.
