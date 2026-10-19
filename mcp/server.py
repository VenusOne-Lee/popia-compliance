#!/usr/bin/env python3
"""
POPIA compliance MCP server (stdio).

Pure Python 3.8+ standard library. Speaks JSON-RPC 2.0 over newline-delimited
messages on stdin/stdout, as the Model Context Protocol stdio transport expects.
Logs go to stderr only. Stdout carries protocol messages and nothing else.

    python3 mcp/server.py

Tool definitions live in mcp/tools.json so the planned hosted server can share
them. This is engineering guidance, not legal advice. See DISCLAIMER.md.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SERVER_NAME = "popia-compliance"
SERVER_VERSION = "1.0.0"
DEFAULT_PROTOCOL = "2025-06-18"
SUPPORTED_PROTOCOLS = ["2025-06-18", "2025-03-26", "2024-11-05"]

HERE = Path(__file__).resolve().parent
if (HERE.parent / "scripts").is_dir():
    # Running from a clone of the repo.
    REPO = HERE.parent
    SCRIPTS = REPO / "scripts"
else:
    # Installed package: popia_kit/mcp/server.py, data under popia_kit/data.
    REPO = HERE.parent / "data"
    SCRIPTS = HERE.parent
TOOLS_FILE = HERE / "tools.json"

DISCLAIMER = ("Engineering guidance only, not legal advice. Automated output is a lead for review. "
              "See DISCLAIMER.md.")
MAX_OUTPUT_CHARS = 120_000
MAX_SNIPPET_CHARS = 500_000
SEVERITIES = ["critical", "high", "medium", "low", "info"]

# JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


def log(*parts: Any) -> None:
    print("[popia-mcp]", *parts, file=sys.stderr, flush=True)


if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


class ToolError(Exception):
    """A failure reported to the client as a tool result with isError true."""


class RpcError(Exception):
    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(message)
        self.code, self.message, self.data = code, message, data


def _import(name: str):
    """Import a scripts/ module lazily, with a clear message if it is not there yet."""
    try:
        return __import__(name)
    except ImportError as e:
        raise ToolError(f"Module scripts/{name}.py could not be imported ({e}). "
                        f"Check that the repository is complete and up to date.")


# --------------------------------------------------------------------------------------
# Tool definitions
# --------------------------------------------------------------------------------------
def load_tool_defs(path: Path = TOOLS_FILE) -> List[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        log(f"cannot load {path}: {e}")
        return []
    out = []
    for t in data.get("tools", []):
        out.append({"name": t["name"], "description": t["description"], "inputSchema": t["inputSchema"]})
    return out


# --------------------------------------------------------------------------------------
# Markdown helpers: sections and checklist tables
# --------------------------------------------------------------------------------------
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


def md_files() -> List[Path]:
    files = sorted((REPO / "references").glob("*.md"))
    files += sorted((REPO / "packs").glob("*.md")) if (REPO / "packs").is_dir() else []
    return files


def split_sections(text: str) -> List[Tuple[str, str]]:
    """Split markdown into (heading, body) at level 1 to 3 headings, ignoring fenced code."""
    sections: List[Tuple[str, str]] = []
    heading, buf, in_code = "(top)", [], False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
        m = HEADING.match(line) if not in_code else None
        if m and len(m.group(1)) <= 3:
            if any(b.strip() for b in buf):
                sections.append((heading, "\n".join(buf).strip()))
            heading, buf = m.group(2).strip(), []
        else:
            buf.append(line)
    if any(b.strip() for b in buf):
        sections.append((heading, "\n".join(buf).strip()))
    return sections


STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are", "what", "how", "do",
        "does", "i", "my", "we", "it", "with", "about", "under", "popia", "be", "can", "should"}


def tokens(s: str) -> List[str]:
    return [w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP and len(w) > 1]


def lookup(query: str, max_results: int = 4, cap: int = 1800) -> List[dict]:
    q = tokens(query)
    if not q:
        return []
    phrase = " ".join(re.findall(r"[a-z0-9]+", query.lower()))
    scored = []
    for f in md_files():
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        for heading, body in split_sections(text):
            h, b = heading.lower(), body.lower()
            score = 0.0
            for t in q:
                score += 4 * h.count(t) + min(b.count(t), 10)
            hits = sum(1 for t in q if t in h or t in b)
            score *= hits / len(q)
            if len(phrase) > 3 and phrase in (h + " " + b):
                score += 15
            if score > 0:
                scored.append((score, f, heading, body))
    scored.sort(key=lambda x: -x[0])
    out = []
    for score, f, heading, body in scored[:max_results]:
        txt = body if len(body) <= cap else body[:cap].rsplit("\n", 1)[0] + "\n[truncated]"
        out.append({"file": str(f.relative_to(REPO)), "heading": heading, "score": round(score, 1), "text": txt})
    return out


def checklist_tables() -> List[dict]:
    """Every markdown table whose first header cell is 'ID', with its file and heading."""
    out = []
    for f in sorted((REPO / "references").glob("*.md")):
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        heading, i = "", 0
        while i < len(lines):
            m = HEADING.match(lines[i])
            if m:
                heading = m.group(2).strip()
            if lines[i].lstrip().startswith("|"):
                block = []
                while i < len(lines) and lines[i].lstrip().startswith("|"):
                    block.append(lines[i].rstrip())
                    i += 1
                first = block[0].strip("| ").split("|")[0].strip()
                if first == "ID" and len(block) > 2:
                    out.append({"file": f.name, "heading": heading, "table": "\n".join(block)})
                continue
            i += 1
    return out


CHECKLIST_AREAS: Dict[str, List[Tuple[str, str]]] = {
    # area -> [(file prefix, heading regex)]
    "accountability": [("09", r"^Accountability")],
    "processing": [("09", r"^Processing limitation"), ("09", r"^Further processing"), ("09", r"^Information quality")],
    "purpose": [("09", r"^Purpose specification")],
    "openness": [("09", r"^Openness")],
    "security": [("09", r"^Security safeguards"), ("03", r".")],
    "participation": [("09", r"^Data subject participation")],
    "special": [("09", r"^Special personal"), ("09", r"^Prior authorisation")],
    "children": [("09", r"^Children")],
    "marketing": [("05", r".")],
    "crossborder": [("06", r".")],
    "breach": [("07", r".")],
    "ai": [("08", r".")],
}


def checklist(area: str) -> str:
    tables = checklist_tables()
    if not tables:
        raise ToolError("No checklist tables found under references/. Check the repository is complete.")
    if area == "all":
        picked = tables
    else:
        specs = CHECKLIST_AREAS.get(area)
        if specs is None:
            raise ToolError(f"Unknown area '{area}'. Use one of: {', '.join(list(CHECKLIST_AREAS) + ['all'])}.")
        picked = [t for t in tables
                  if any(t["file"].startswith(p) and re.search(rx, t["heading"]) for p, rx in specs)]
    if not picked:
        raise ToolError(f"No checklist table found for area '{area}'.")
    md = [f"# POPIA checklist: {area}", "",
          "Mark each control: Met, Partial, Not met, N/A, Unknown. An unknown on a key control is itself a finding.", ""]
    for t in picked:
        md += [f"## {t['heading']}", f"_Source: references/{t['file']}_", "", t["table"], ""]
    return "\n".join(md)


# --------------------------------------------------------------------------------------
# Breach triage (deterministic)
# --------------------------------------------------------------------------------------
CUES = [
    ("credentials", r"password|credential|login|token|api key|secret|\.env|service[_ ]?role|key leak",
     "Force password resets, rotate every exposed key or token, check for reuse, prompt for MFA."),
    ("sa_id_numbers", r"\bid number|identity number|\bsa id|id no\b|passport",
     "Recommend SAFPS protective registration and credit bureau alerts to affected people."),
    ("bank_or_card", r"bank|card|account number|payment|iban|cvv|eft",
     "Notify the bank or payment provider. Check s105 and s106 offence risk. Follow the PCI incident process."),
    ("health_or_special", r"health|medical|patient|diagnos|religio|race|ethnic|biometric|fingerprint|face|union|political|criminal|sex life",
     "Special personal information: plain-language, sensitive notice; consider a support line."),
    ("children", r"child|minor|learner|pupil|school|under 18|student",
     "Children's information: notify competent persons (parents or guardians)."),
    ("large_scale", r"\b\d{4,}\b|thousand|million|all (?:users|customers)|entire|whole database|public(?:ly)?",
     "Large scale or public exposure: prepare a media holding statement; the Regulator may direct publicity."),
]
INCIDENTS = [
    (r"\brls\b|row.level|open api|anon(?:ymous)? (?:key|access)|readable by",
     "RLS off or open API: still a compromise if logs show, or cannot rule out, unauthorised access. Check access logs first; with no logs, assume access."),
    (r"service.?(?:role|key)|key in (?:a )?(?:public )?repo|committed|github",
     "Key in a repository: rotate immediately and review database logs for use of that key."),
    (r"misdirect|wrong recipient|sent to the wrong|wrong email|cc'?d",
     "Misdirected email: request deletion confirmation from the recipient, and still notify."),
    (r"preview|staging|test environment|prod data",
     "Preview deployment with production data: take it down, check access logs, notify if accessed or unknown."),
    (r"\.env|docker image|client bundle|bundle",
     "Leaked .env in an image or bundle: rotate every secret in it."),
    (r"ransom|malware|encrypt(?:ed)? our|locked",
     "Ransomware or malware: isolate hosts, preserve evidence, consider a SAPS case under the Cybercrimes Act."),
    (r"bucket|storage|s3|blob",
     "Public bucket: make it private, keep access logs, list exposed objects before changing anything else."),
    (r"laptop|phone|device|usb|stolen|lost",
     "Lost or stolen device: confirm disk encryption status, revoke sessions and tokens, remote wipe if available."),
    (r"operator|vendor|supplier|third.party|processor",
     "Operator involved: the operator must tell you; you notify. Request their incident report under the contract."),
]
FALLBACK_STEPS = """### Hour 0 to 4: Contain and preserve
1. Assign an incident lead and inform the Information Officer or Deputy IO.
2. Contain: revoke leaked keys, rotate credentials, close exposure. Do not wipe evidence.
3. Preserve: snapshot affected systems, export logs, note timestamps (SAST).
4. Start the incident log.
### Hour 4 to 48: Scope
5. PI categories. 6. Number of data subjects. 7. Accessed or acquired (if unknown, assume yes). 8. Unauthorised parties. 9. Operator involvement. 10. Crime and sector reporting.
### As soon as reasonably possible: Notify
11. Regulator via the eServices portal. 12. Data subjects in writing with s22(5) content. 13. Website notice. 14. Insurers, banks, clients, sector regulators.
### After: Learn
15. Root cause. 16. Update the Regulator notification. 17. Update controls and training. 18. Keep the incident file."""


def playbook_text() -> str:
    f = REPO / "references" / "07-breach-response.md"
    try:
        text = f.read_text(encoding="utf-8")
    except OSError:
        return FALLBACK_STEPS
    m = re.search(r"^## Playbook\s*$(.*?)(?=^## )", text, re.M | re.S)
    return m.group(1).strip() if m else FALLBACK_STEPS


def breach_triage(description: str) -> str:
    d = description.lower()
    cues = [(k, note) for k, rx, note in CUES if re.search(rx, d)]
    incidents = [note for rx, note in INCIDENTS if re.search(rx, d)]
    warn = []
    if re.search(r"\b\d{13}\b", description) or re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", description):
        warn.append("The description appears to contain an ID number or email address. "
                    "Do not share personal information in triage notes. It was not echoed here.")
    yes = lambda k: "[x]" if any(c[0] == k for c in cues) else "[ ]"
    md = ["# s22 security compromise triage", ""]
    if warn:
        md += ["> " + w for w in warn] + [""]
    md += [
        "**Trigger test:** are there reasonable grounds to believe personal information was accessed or "
        "acquired by an unauthorised person? Certainty is not required. There is no risk-of-harm threshold. "
        "If yes, notify the Information Regulator (eServices portal) and affected data subjects as soon as "
        "reasonably possible.", "",
        f"Description received ({len(description)} characters). Matched cues are keyword based. Confirm each one.", "",
        "## Matched severity cues", "",
    ]
    md += [f"- **{k.replace('_', ' ')}**: {note}" for k, note in cues] or ["- None matched. Work through the scope questions below."]
    md += ["", "## Matched incident patterns", ""]
    md += [f"- {n}" for n in incidents] or ["- None matched."]
    md += ["", "## Pre-filled checklist", "",
           "| Item | Status |", "|---|---|",
           "| Incident lead assigned | [ ] |",
           "| Information Officer or Deputy IO informed | [ ] |",
           "| Exposure contained (keys rotated, access closed) | [ ] |",
           "| Evidence preserved (snapshots, logs, timestamps in SAST) | [ ] |",
           "| Incident log started | [ ] |",
           f"| Credentials involved | {yes('credentials')} |",
           f"| SA ID numbers involved | {yes('sa_id_numbers')} |",
           f"| Bank or card data involved | {yes('bank_or_card')} |",
           f"| Special personal information involved | {yes('health_or_special')} |",
           f"| Children's information involved | {yes('children')} |",
           f"| Large scale or public exposure | {yes('large_scale')} |",
           "| Number of data subjects estimated | [ ] |",
           "| Access confirmed, ruled out, or assumed (no logs) | [ ] |",
           f"| Operator involved and incident report requested | {'[x] suspected' if any('Operator' in n for n in incidents) else '[ ]'} |",
           "| SAPS case considered (Cybercrimes Act) | [ ] |",
           "| Regulator notified via eServices portal | [ ] |",
           "| Data subjects notified with s22(5) content | [ ] |",
           "| Website notice published (if used) | [ ] |",
           "| Insurer, bank, clients, sector regulator informed as needed | [ ] |",
           "| Root cause analysis and Regulator update | [ ] |", "",
           "## Playbook (references/07-breach-response.md)", "", playbook_text(), "",
           "Templates: templates/breach-notice-data-subject.md (if present). "
           "Get a POPIA attorney involved for special PI, children's data, or large-scale incidents."]
    return "\n".join(md)


# --------------------------------------------------------------------------------------
# Tools
# --------------------------------------------------------------------------------------
def _str(args: dict, key: str, required: bool = True, default: Optional[str] = None) -> Optional[str]:
    v = args.get(key, default)
    if v is None:
        if required:
            raise RpcError(INVALID_PARAMS, f"Missing required argument '{key}'")
        return None
    if not isinstance(v, str):
        raise RpcError(INVALID_PARAMS, f"Argument '{key}' must be a string")
    return v


def _sev(args: dict) -> str:
    s = _str(args, "min_severity", False, "info").lower()
    if s not in SEVERITIES:
        raise RpcError(INVALID_PARAMS, f"min_severity must be one of {SEVERITIES}")
    return s


def _fmt_scan(ps, res: dict, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(res, indent=2)
    return ps.fmt_md(res)


# Paths an agent may never point the scanner at, even if asked. An agent's instructions can come
# from untrusted content (prompt injection), so the server, not the model, enforces these limits.
_HOME = Path.home().resolve()
SENSITIVE_DIRS = [Path(p).expanduser().resolve() for p in (
    "~/.ssh", "~/.aws", "~/.gnupg", "~/.config", "~/.kube", "~/.docker", "~/.azure", "~/.netrc",
    "~/Library/Keychains", "/etc", "/var", "/usr", "/bin", "/sbin", "/boot", "/proc", "/sys", "/dev",
    "/System", "/Library", "/private")]


def _allowed_roots() -> List[Path]:
    roots = os.environ.get("POPIA_SCAN_ROOTS", "")
    return [Path(r).expanduser().resolve() for r in roots.split(os.pathsep) if r.strip()]


def _safe_scan_path(path: str) -> Path:
    p = Path(os.path.expanduser(path)).resolve()
    if p in (Path(p.anchor), _HOME):
        raise ToolError("Refusing to scan a filesystem root or your whole home folder. Point at a project folder.")
    for d in SENSITIVE_DIRS:
        if p == d or d in p.parents:
            raise ToolError("Refusing to scan a system or credentials folder.")
    roots = _allowed_roots()
    if roots and not any(p == r or r in p.parents for r in roots):
        raise ToolError("Path is outside POPIA_SCAN_ROOTS.")
    return p


def _safe_out_dir(out_dir: str) -> Path:
    """Generated packs go only into a new or empty folder inside the working directory
    (or POPIA_SCAN_ROOTS), so a tool call cannot overwrite existing files."""
    base = Path.cwd().resolve()
    p = (base / os.path.expanduser(out_dir)).resolve()
    roots = _allowed_roots() or [base]
    if not any(p == r or r in p.parents for r in roots) or p in roots:
        raise ToolError("out_dir must be a new sub-folder of the working directory.")
    if p.exists() and (not p.is_dir() or any(p.iterdir())):
        raise ToolError("out_dir already exists and is not empty. Choose a new folder.")
    return p


def tool_popia_scan(args: dict) -> str:
    path = _str(args, "path")
    fmt = _str(args, "format", False, "md")
    if fmt not in ("md", "json"):
        raise RpcError(INVALID_PARAMS, "format must be md or json")
    rules = _str(args, "rules", False)
    p = _safe_scan_path(path)
    if not p.exists():
        raise ToolError("Path not found.")
    ps = _import("popia_scan")
    res = ps.scan(str(p), [r for r in rules.split(",") if r.strip()] if rules else None, _sev(args))
    return _fmt_scan(ps, res, fmt)


SAFE_NAME = re.compile(r"^[A-Za-z0-9._\-/]+$")


def tool_popia_scan_snippet(args: dict) -> str:
    filename = _str(args, "filename").strip().replace("\\", "/")
    content = _str(args, "content")
    fmt = _str(args, "format", False, "md")
    if fmt not in ("md", "json"):
        raise RpcError(INVALID_PARAMS, "format must be md or json")
    parts = [x for x in filename.split("/") if x]
    if (not parts or filename.startswith("/") or any(x in (".", "..") for x in parts)
            or not SAFE_NAME.match(filename) or len(filename) > 200):
        raise RpcError(INVALID_PARAMS, "filename must be a relative path of letters, digits, . _ - / with no '..'")
    if len(content) > MAX_SNIPPET_CHARS:
        raise RpcError(INVALID_PARAMS, f"content exceeds {MAX_SNIPPET_CHARS} characters")
    ps = _import("popia_scan")
    tmp = tempfile.mkdtemp(prefix="popia-snip-")
    try:
        target = Path(tmp, *parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        res = ps.scan(tmp, None, _sev(args))
        res["target"] = f"snippet:{'/'.join(parts)}"
        return _fmt_scan(ps, res, fmt)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def tool_popia_site_check(args: dict) -> str:
    url = _str(args, "url").strip()
    if not re.match(r"^https?://[^\s/]+", url, re.I):
        raise RpcError(INVALID_PARAMS, "url must start with http:// or https://")
    sc = _import("site_check")
    # URLs reach this tool from agents, so never let them reach private or internal services (SSRF).
    allow_private = os.environ.get("POPIA_ALLOW_PRIVATE_URLS") == "1"
    try:
        res = sc.check(url, block_private=not allow_private)
    except getattr(sc, "BlockedTarget", ValueError) as e:
        raise ToolError(f"Refused: {e}.")
    except getattr(sc, "SiteUnreadable", RuntimeError) as e:
        raise ToolError(f"Not checked: {e}.")
    fmt_md = getattr(sc, "fmt_md", None)
    return fmt_md(res) if fmt_md else json.dumps(res, indent=2)


def tool_popia_generate_pack(args: dict) -> str:
    answers = args.get("answers")
    if not isinstance(answers, dict):
        raise RpcError(INVALID_PARAMS, "answers must be an object")
    out_dir = _str(args, "out_dir", False)
    pk = _import("popia_pack")
    target = _safe_out_dir(out_dir) if out_dir else None
    files = pk.generate(answers, str(target) if target else None)
    md = ["# POPIA document pack", "",
          f"{len(files)} files generated." + (f" Written to `{out_dir}`." if out_dir else " Not written to disk."),
          "Drafts need review by the Information Officer and, where flagged, a POPIA attorney.", ""]
    for name, content in files.items():
        md += [f"## {name}", "", "````", str(content), "````", ""]
    return "\n".join(md)


def tool_popia_validate_sa_id(args: dict) -> str:
    raw = _str(args, "id_number")
    sa = _import("sa_id")
    s = raw.strip().replace(" ", "")
    return json.dumps({"valid": bool(sa.is_valid(s)), "masked": sa.mask(s)})


def tool_popia_lookup(args: dict) -> str:
    q = _str(args, "query")
    n = args.get("max_results", 4)
    if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= 10:
        raise RpcError(INVALID_PARAMS, "max_results must be an integer from 1 to 10")
    hits = lookup(q, n)
    if not hits:
        return f"No matching sections for '{q}'. Try different keywords, or read references/01-popia-legal-map.md."
    md = [f"# Lookup: {q}", ""]
    for h in hits:
        md += [f"## {h['heading']}", f"_Source: {h['file']}_", "", h["text"], ""]
    return "\n".join(md)


def tool_popia_checklist(args: dict) -> str:
    return checklist(_str(args, "area").strip().lower())


def tool_popia_breach_triage(args: dict) -> str:
    return breach_triage(_str(args, "description"))


TOOLS = {
    "popia_scan": tool_popia_scan,
    "popia_scan_snippet": tool_popia_scan_snippet,
    "popia_site_check": tool_popia_site_check,
    "popia_generate_pack": tool_popia_generate_pack,
    "popia_validate_sa_id": tool_popia_validate_sa_id,
    "popia_lookup": tool_popia_lookup,
    "popia_checklist": tool_popia_checklist,
    "popia_breach_triage": tool_popia_breach_triage,
}


# --------------------------------------------------------------------------------------
# Resources
# --------------------------------------------------------------------------------------
MIME = {".md": "text/markdown", ".csv": "text/csv", ".json": "application/json", ".txt": "text/plain",
        ".html": "text/html", ".yml": "text/yaml", ".yaml": "text/yaml"}


def resource_index() -> Dict[str, Path]:
    idx: Dict[str, Path] = {}
    for sub, pattern in (("references", "*.md"), ("packs", "*.md"), ("templates", "**/*")):
        d = REPO / sub
        if not d.is_dir():
            continue
        for p in sorted(d.glob(pattern)):
            if p.is_file() and not p.name.startswith("."):
                idx["popia://" + p.relative_to(REPO).as_posix()] = p
    return idx


def _title(p: Path) -> str:
    if p.suffix == ".md":
        try:
            for line in p.read_text(encoding="utf-8").splitlines()[:10]:
                if line.startswith("# "):
                    return line[2:].strip()
        except OSError:
            pass
    return p.name


def resources_list() -> dict:
    return {"resources": [{"uri": uri, "name": p.relative_to(REPO).as_posix(), "title": _title(p),
                           "mimeType": MIME.get(p.suffix.lower(), "text/plain")}
                          for uri, p in resource_index().items()]}


def resources_read(params: dict) -> dict:
    uri = params.get("uri")
    if not isinstance(uri, str):
        raise RpcError(INVALID_PARAMS, "Missing 'uri'")
    p = resource_index().get(uri)
    if p is None:
        raise RpcError(-32002, "Resource not found", {"uri": uri})
    return {"contents": [{"uri": uri, "mimeType": MIME.get(p.suffix.lower(), "text/plain"),
                          "text": p.read_text(encoding="utf-8", errors="replace")}]}


# --------------------------------------------------------------------------------------
# Dispatcher
# --------------------------------------------------------------------------------------
class Server:
    def __init__(self):
        self.tool_defs = load_tool_defs()
        self.initialized = False
        known = {t["name"] for t in self.tool_defs}
        missing = set(TOOLS) - known
        if missing:
            log(f"tools.json has no definition for: {', '.join(sorted(missing))}")

    def initialize(self, params: dict) -> dict:
        asked = params.get("protocolVersion")
        version = asked if asked in SUPPORTED_PROTOCOLS else DEFAULT_PROTOCOL
        client = (params.get("clientInfo") or {}).get("name", "unknown")
        log(f"initialize from {client}, protocol {asked} -> {version}")
        return {
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}, "resources": {"listChanged": False, "subscribe": False}},
            "serverInfo": {"name": SERVER_NAME, "title": "POPIA Compliance", "version": SERVER_VERSION},
            "instructions": ("POPIA (South Africa) privacy-engineering tools. Scanner output is leads, not verdicts. "
                             "Start with popia_lookup or popia_checklist; use popia_breach_triage for any suspected "
                             "security compromise. " + DISCLAIMER),
        }

    def call_tool(self, params: dict) -> dict:
        name = params.get("name")
        args = params.get("arguments") or {}
        if not isinstance(args, dict):
            raise RpcError(INVALID_PARAMS, "arguments must be an object")
        fn = TOOLS.get(name)
        if fn is None or name not in {t["name"] for t in self.tool_defs}:
            raise RpcError(INVALID_PARAMS, f"Unknown tool: {name}")
        try:
            text, is_error = fn(args), False
        except RpcError:
            raise
        except ToolError as e:
            text, is_error = f"Error: {e}", True
        except Exception as e:  # tool bugs become tool errors, not protocol errors
            # Exception messages can hold URLs, tokens, personal information or local paths.
            # Log and return the type only.
            log(f"tool {name} failed: {type(e).__name__}")
            text, is_error = f"Error: the tool failed ({type(e).__name__}). Check the input and try again.", True
        if len(text) > MAX_OUTPUT_CHARS:
            text = text[:MAX_OUTPUT_CHARS] + "\n\n[output truncated]"
        text = text.rstrip() + "\n\n---\n" + DISCLAIMER
        return {"content": [{"type": "text", "text": text}], "isError": is_error}

    def handle(self, msg: Any) -> Optional[dict]:
        if isinstance(msg, dict) and "method" not in msg and ("result" in msg or "error" in msg):
            return None  # a response to a request we never send; ignore
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
            return _err(msg.get("id") if isinstance(msg, dict) else None, INVALID_REQUEST, "Invalid Request")
        method = msg["method"]
        is_notification = "id" not in msg
        mid = msg.get("id")
        params = msg.get("params") or {}
        if not isinstance(params, dict):
            return None if is_notification else _err(mid, INVALID_PARAMS, "params must be an object")
        if is_notification:
            if method == "notifications/initialized":
                self.initialized = True
                log("client initialised")
            elif method == "notifications/cancelled":
                log("cancel requested (requests are synchronous; nothing to cancel)")
            return None
        try:
            if method == "initialize":
                result = self.initialize(params)
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": self.tool_defs}
            elif method == "tools/call":
                result = self.call_tool(params)
            elif method == "resources/list":
                result = resources_list()
            elif method == "resources/read":
                result = resources_read(params)
            elif method == "resources/templates/list":
                result = {"resourceTemplates": []}
            else:
                return _err(mid, METHOD_NOT_FOUND, f"Method not found: {method}")
        except RpcError as e:
            return _err(mid, e.code, e.message, e.data)
        except Exception as e:
            log(f"internal error on {method}: {type(e).__name__}")
            return _err(mid, INTERNAL_ERROR, f"Internal error: {type(e).__name__}")
        return {"jsonrpc": "2.0", "id": mid, "result": result}


def _err(mid: Any, code: int, message: str, data: Any = None) -> dict:
    e: Dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        e["data"] = data
    return {"jsonrpc": "2.0", "id": mid, "error": e}


def _write(obj: Any) -> None:
    sys.stdout.buffer.write((json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))
    sys.stdout.buffer.flush()


def serve(stdin=None) -> None:
    server = Server()
    stream = stdin or sys.stdin.buffer
    log(f"{SERVER_NAME} {SERVER_VERSION} ready on stdio ({len(server.tool_defs)} tools)")
    for raw in stream:
        line = raw.decode("utf-8", errors="replace").strip() if isinstance(raw, bytes) else raw.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            _write(_err(None, PARSE_ERROR, "Parse error"))
            continue
        if isinstance(msg, list):  # JSON-RPC batch (older protocol versions)
            if not msg:
                _write(_err(None, INVALID_REQUEST, "Invalid Request: empty batch"))
                continue
            replies = [r for r in (server.handle(m) for m in msg) if r is not None]
            if replies:
                _write(replies)
            continue
        reply = server.handle(msg)
        if reply is not None:
            _write(reply)
    log("stdin closed, exiting")


if __name__ == "__main__":
    try:
        serve()
    except KeyboardInterrupt:
        pass
