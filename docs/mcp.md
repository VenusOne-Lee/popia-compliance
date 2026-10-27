# MCP server

`mcp/server.py` exposes this skill as a Model Context Protocol server over stdio. Any MCP client can use it: Claude Desktop, Claude Code, Cursor, Windsurf, VS Code and others.

It is pure Python 3.8 or later, standard library only. Two ways to run it:

- **No clone:** `uvx popia-kit mcp` (or `pipx run popia-kit mcp`). Use that as the command in your client config.
- **From a clone:** point your client at `mcp/server.py`. It reads the repository it sits in.

This is engineering guidance, not legal advice. Every tool result ends with that line. See [DISCLAIMER.md](../DISCLAIMER.md).

## Contents

1. Tools
2. Resources
3. Client configuration
4. Testing
5. Protocol notes
6. Hosted MCP (planned)

## 1. Tools

Tool definitions (name, description, input schema) live in [`mcp/tools.json`](../mcp/tools.json). The local server loads them from that file. The planned hosted server must use the same file, so the two stay in sync.

| Tool | Arguments | What it returns |
|---|---|---|
| `popia_scan` | `path`, `min_severity`, `rules`, `format` (`md` or `json`) | Static scan of a local repo, directory or file. Snippets are redacted by the scanner. |
| `popia_scan_snippet` | `filename`, `content`, `min_severity`, `format` | Scan of pasted code. The content is written to a temporary directory under `filename`, scanned, then deleted. The file extension decides which rules apply. Maximum 500 000 characters. |
| `popia_operators` | `path`, `ignore_hosts`, `format` (`md`, `json` or `csv`) | Every third-party API or SDK a local codebase calls, from manifests, imports and API hosts, with the personal information that appears to reach each one. The start of an operator register (s20, s21) and a cross-border list (s72). Same path limits as `popia_scan`. |
| `popia_site_check` | `url` | Passive check of a live site: headers, cookies, trackers, notice links. Ordinary GET requests only. |
| `popia_generate_pack` | `answers`, `from_path` (optional), `out_dir` (optional) | Document pack drafts from questionnaire answers. With `from_path`, answers found in that codebase fill the gaps. Writes to `out_dir` only if given. |
| `popia_validate_sa_id` | `id_number` | `{"valid": true or false, "masked": "**********123"}`. The full number is never echoed. Date of birth, sex and citizenship are not returned. |
| `popia_lookup` | `query`, `max_results` (1 to 10) | Best matching sections from `references/*.md` and `packs/*.md`, each with heading, source file and text (capped). |
| `popia_checklist` | `area` | Checklist tables parsed from the references. Areas: `accountability`, `processing`, `purpose`, `openness`, `security`, `participation`, `special`, `children`, `marketing`, `crossborder`, `breach`, `ai`, `all`. |
| `popia_breach_triage` | `description` | Deterministic s22 triage: severity cues and incident patterns matched by keyword, a pre-filled checklist, and the playbook from `references/07-breach-response.md`. No model call. |

Notes:

- `popia_scan`, `popia_scan_snippet`, `popia_site_check` and `popia_generate_pack` depend on `scripts/popia_scan.py`, `scripts/site_check.py` and `scripts/popia_pack.py`. If a module is missing, the tool returns an error result that names it. The server keeps running.
- `popia_breach_triage` warns if the description looks like it contains an ID number or email address, and does not echo it. Do not paste personal information into triage notes.
- Scanner output is leads, not verdicts. Read the code before reporting a finding.

## 2. Resources

Every file in `references/*.md`, `packs/*.md` and `templates/**` is listed as a resource with a `popia://` URI that mirrors its path:

```
popia://references/07-breach-response.md
popia://templates/ropa.csv
```

`resources/read` only serves URIs from that list. Anything else returns error `-32002`.

## 3. Client configuration

Replace `/path/to/popia-compliance` with the absolute path to your clone. On Windows use `python` and a path like `C:\\Users\\you\\popia-compliance\\mcp\\server.py`.

### Claude Desktop

Edit `claude_desktop_config.json` (Settings, Developer, Edit Config). It lives at `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS and `%APPDATA%\Claude\claude_desktop_config.json` on Windows.

```json
{
  "mcpServers": {
    "popia": {
      "command": "python3",
      "args": ["/path/to/popia-compliance/mcp/server.py"]
    }
  }
}
```

Restart Claude Desktop after saving.

### Claude Code

```bash
claude mcp add --transport stdio popia -- python3 /path/to/popia-compliance/mcp/server.py
# share with the team through .mcp.json in the project root
claude mcp add --transport stdio --scope project popia -- python3 /path/to/popia-compliance/mcp/server.py
```

Check with `claude mcp list`, or `/mcp` inside a session.

### Cursor

`.cursor/mcp.json` in the project (or `~/.cursor/mcp.json` for all projects):

```json
{
  "mcpServers": {
    "popia": {
      "command": "python3",
      "args": ["/path/to/popia-compliance/mcp/server.py"]
    }
  }
}
```

### Windsurf

`~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "popia": {
      "command": "python3",
      "args": ["/path/to/popia-compliance/mcp/server.py"]
    }
  }
}
```

### VS Code (GitHub Copilot agent mode)

`.vscode/mcp.json` in the workspace. VS Code uses `servers`, not `mcpServers`:

```json
{
  "servers": {
    "popia": {
      "type": "stdio",
      "command": "python3",
      "args": ["${workspaceFolder}/../popia-compliance/mcp/server.py"]
    }
  }
}
```

### Generic stdio client

Start the process `python3 /path/to/popia-compliance/mcp/server.py`. Send newline-delimited JSON-RPC 2.0 on stdin. Read responses on stdout. Logs go to stderr.

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"cli","version":"0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"popia_checklist","arguments":{"area":"breach"}}}' \
  | python3 mcp/server.py
```

## Safety limits

The server enforces these limits itself, because an agent's instructions can come from untrusted content (prompt injection):

| Tool | Limit | Override |
|---|---|---|
| `popia_scan` | Refuses filesystem roots, the home folder, and system or credential folders (`~/.ssh`, `~/.aws`, `~/.config`, `/etc` and similar). Never follows symlinks. | `POPIA_SCAN_ROOTS` (path list) restricts scanning further to named project folders. |
| `popia_site_check` | Refuses private, loopback, link-local and reserved addresses, on every redirect hop. Never sends credentials embedded in the URL. | `POPIA_ALLOW_PRIVATE_URLS=1` for local development only. |
| `popia_generate_pack` | Writes only to a new or empty sub-folder of the working directory. Never overwrites files. | `POPIA_SCAN_ROOTS` also sets where packs may be written. |
| All tools | Unexpected errors return and log the exception type only, never its message. | None. |

## 4. Testing

```bash
python3 mcp/smoke_test.py                                       # spawns the server, checks every core tool
python -m unittest tests.automation.test_mcp -v                 # in-process tests
```

The smoke test runs in CI on Python 3.8 and 3.12.

## 5. Protocol notes

- Transport: stdio, one JSON message per line, UTF-8.
- `initialize` echoes the client's `protocolVersion` if supported (`2025-06-18`, `2025-03-26`, `2024-11-05`), otherwise answers `2025-06-18`.
- Capabilities: `tools` and `resources` (no subscriptions, no list-changed notifications).
- Methods: `initialize`, `notifications/initialized`, `ping`, `tools/list`, `tools/call`, `resources/list`, `resources/read`, `resources/templates/list` (empty).
- Errors: `-32700` parse error, `-32600` invalid request, `-32601` unknown method, `-32602` invalid params or unknown tool, `-32603` internal error, `-32002` resource not found. A tool that fails returns a normal result with `isError: true`.
- Requests are handled one at a time. Long scans block later requests until they finish.

## 6. Hosted MCP (planned)

A remote (HTTP) MCP server is planned, written in TypeScript and hosted on Lovable. It will load the same `mcp/tools.json` so names, descriptions and schemas match the local server.

| Tool | Hosted | Why |
|---|---|---|
| `popia_lookup` | Yes | Reads bundled references only |
| `popia_checklist` | Yes | Reads bundled references only |
| `popia_breach_triage` | Yes | Deterministic, no state |
| `popia_validate_sa_id` | Yes | Pure function |
| `popia_scan_snippet` | Yes | Works on pasted content, not a local path |
| `popia_site_check` | Yes | Passive GET requests to a public URL |
| `popia_scan` (path) | No, local only | A hosted server cannot see the user's repository |
| `popia_operators` (path) | No, local only | A hosted server cannot see the user's repository |
| `popia_generate_pack` (writes files) | No, local only | Writes to the user's disk. A hosted version may return contents without `out_dir` later |

`tools.json` marks each tool with `local_only`. The hosted server must list only tools where `local_only` is false.

Rules for the hosted version:

- **No storage of submitted code or URLs.** Snippet content, URLs, descriptions and ID numbers are processed in memory and dropped when the response is sent. No database writes, no object storage, no queues.
- **No logging of request bodies.** Log method, tool name, status, duration and a request id only. Error trackers must scrub arguments.
- **No model calls on submitted content.** Tools stay deterministic, as they are locally.
- **Rate limits and size caps** match the local server (500 000 characters for snippets, capped output).
- **Site checks stay passive.** Same request budget and User-Agent as `scripts/site_check.py`. Block private, loopback and link-local addresses to prevent server-side request forgery.
- **Hosting and transfers recorded.** The hosting region and any operator that sees traffic are listed in the privacy notice for the hosted service, with the s72 basis if outside South Africa.
- **Same disclaimer** appended to every tool result.
