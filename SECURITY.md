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
- The site check is passive: ordinary page requests only.
- Scan reports redact detected secrets, ID numbers, card numbers and emails.
- The hosted MCP server (when available) must not store submitted code, URLs or results.
