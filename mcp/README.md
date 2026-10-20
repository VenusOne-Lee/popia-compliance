# POPIA MCP server

Local Model Context Protocol server for the POPIA compliance skill. Stdio transport, Python 3.8 or later, standard library only.

```bash
python3 mcp/server.py          # run (your MCP client normally starts it)
python3 mcp/smoke_test.py      # check it works
```

Claude Code:

```bash
claude mcp add --transport stdio popia -- python3 /path/to/popia-compliance/mcp/server.py
```

Claude Desktop, Cursor and Windsurf (`mcpServers` block):

```json
{ "mcpServers": { "popia": { "command": "python3", "args": ["/path/to/popia-compliance/mcp/server.py"] } } }
```

Tools: `popia_scan`, `popia_scan_snippet`, `popia_operators`, `popia_site_check`, `popia_generate_pack`, `popia_validate_sa_id`, `popia_lookup`, `popia_checklist`, `popia_breach_triage`. Definitions are in [`tools.json`](tools.json), shared with the planned hosted server.

Full documentation, including VS Code config, resources, protocol notes and the hosted plan: [docs/mcp.md](../docs/mcp.md).

Engineering guidance, not legal advice. See [DISCLAIMER.md](../DISCLAIMER.md).
