# Test fixtures

`demo-app/` is a deliberately non-compliant app used to test the scanner, the MCP server and demos. It contains synthetic data only.

Secrets, SA ID numbers and card numbers used in tests are generated at runtime in `tests/scanner/test_rules.py` so that no secret-looking or ID-looking value is committed. Do not add real or realistic personal information here.
