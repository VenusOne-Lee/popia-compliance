# Adapters

The same POPIA guardrails, packaged for each AI coding tool. All files are generated from [`_core.md`](_core.md) by `scripts/build_adapters.py`. Edit the core, then rebuild.

| Tool | File in this folder | Copy to your project |
|---|---|---|
| Claude, Claude Code | use the full skill (`SKILL.md` + folders); `claude/CLAUDE.md` is a lightweight alternative | see README "Install" |
| Cursor | `cursor/.cursor/rules/popia.mdc` | `.cursor/rules/popia.mdc` |
| OpenAI Codex, Jules, Amp, Aider and other AGENTS.md readers | `agents/AGENTS.md` | `AGENTS.md` (append if you have one) |
| GitHub Copilot | `copilot/.github/copilot-instructions.md` | `.github/copilot-instructions.md` |
| Windsurf | `windsurf/.windsurf/rules/popia.md` (or legacy `windsurf/.windsurfrules`) | same path |
| Gemini CLI / Code Assist | `gemini/GEMINI.md` | `GEMINI.md` |
| Lovable | `lovable/knowledge.md` | Project settings, Knowledge (or workspace knowledge) |
| ChatGPT | `chatgpt/custom-gpt-instructions.md` | Custom GPT or Project instructions |

Tool file locations change. If a path no longer works, check the tool's current docs and open an issue.

For deeper checks than rules files allow, connect the MCP server (`docs/mcp.md`) so the tool can run the scanner and look up references.
