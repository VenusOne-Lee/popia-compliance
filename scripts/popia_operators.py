#!/usr/bin/env python3
"""
popia_operators: list every third-party API or SDK a codebase calls, and the
personal information that appears to reach each one.

That list is the start of your operator register (POPIA s20, s21) and of your
list of cross-border transfers (s72). Stdlib only. Python 3.8+.

    python3 popia_operators.py <path> [--format md|json|csv] [--out FILE]
                                      [--ignore-host your-api.co.za]

Sources it reads:
  - dependency manifests: package.json, requirements*.txt, pyproject.toml, Pipfile
  - imports in JavaScript, TypeScript and Python, and the client objects made from them
  - API and script hosts in code (fetch, axios, requests, script tags, form actions)

Fields are matched by name near each call, so "appears to reach" is a lead to
confirm by reading the code. It cannot see data sent from a server you do not
scan, a tag manager, or a no-code tool set up outside the repo.

Engineering guidance, not legal advice. See DISCLAIMER.md.
"""
from __future__ import annotations

import argparse
import csv
import fnmatch
import io
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import popia_scan  # noqa: E402
import popia_vendors as pv  # noqa: E402

__version__ = "1.0.0"

DISCLAIMER = ("Automated findings are leads for review, not legal conclusions. "
              "Engineering guidance only, not legal advice.")

JS_EXT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte", ".astro"}
PY_EXT = {".py"}
CODE_EXT = JS_EXT | PY_EXT | {".html", ".htm", ".php", ".rb", ".go", ".java", ".kt", ".kts", ".swift",
                              ".dart", ".cs", ".liquid", ".hbs", ".ejs", ".sh"}
CONFIG_EXT = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".xml", ".plist"}
TEST_DIRS = {"test", "tests", "__tests__", "__mocks__", "spec", "e2e", "cypress"}
WINDOW = 8           # lines either side of a call that are read for field names, within one function
MAX_LOCATIONS = 8    # evidence lines kept per vendor and per field category

# --------------------------------------------------------------------------------------
# Personal information vocabulary. Terms are token sequences after camelCase is split.
# --------------------------------------------------------------------------------------
PI_CATEGORIES = [
    ("contact", "contact details", [("email",), ("e", "mail"), ("phone",), ("mobile",), ("cellphone",),
                                    ("cell", "number"), ("msisdn",), ("telephone",), ("whatsapp", "number")]),
    ("name", "names", [("first", "name"), ("last", "name"), ("full", "name"), ("surname",), ("firstname",),
                       ("lastname",), ("fullname",), ("given", "name"), ("family", "name"), ("display", "name"),
                       ("customer", "name"), ("user", "name"), ("client", "name"), ("patient", "name"),
                       ("guest", "name"), ("member", "name"), ("employee", "name"), ("contact", "name")]),
    ("id_number", "identity or passport numbers", [("id", "number"), ("idnumber",), ("identity", "number"),
                                                   ("national", "id"), ("sa", "id"), ("rsa", "id"),
                                                   ("passport",)]),
    ("address", "physical addresses", [("address",), ("street",), ("suburb",), ("postal", "code"),
                                       ("postcode",), ("zip", "code"), ("zipcode",)]),
    ("dob", "dates of birth", [("dob",), ("date", "of", "birth"), ("birth", "date"), ("birthdate",),
                               ("birthday",)]),
    ("location", "location", [("latitude",), ("longitude",), ("geolocation",), ("gps",), ("coords",),
                              ("coordinates",)]),
    ("online", "online identifiers", [("ip",), ("ip", "address"), ("user", "agent"), ("device", "id"),
                                      ("username",)]),
    ("financial", "financial information", [("card", "number"), ("cvv",), ("cvc",), ("account", "number"),
                                            ("bank", "account"), ("iban",), ("salary",), ("income",),
                                            ("tax", "number")]),
    ("special", "special personal information (s26)", [("health",), ("medical",), ("diagnosis",),
                                                        ("medication",), ("disability",), ("hiv",),
                                                        ("religion",), ("religious",), ("race",),
                                                        ("ethnicity",), ("ethnic",), ("biometric",),
                                                        ("fingerprint",), ("selfie",), ("face", "match"),
                                                        ("sexual",), ("sex", "life"), ("criminal",),
                                                        ("trade", "union"), ("political",)]),
    ("children", "children's information (s34)", [("child",), ("children",), ("minor",), ("minors",),
                                                   ("learner",), ("pupil",), ("kid",), ("kids",),
                                                   ("guardian",)]),
    ("free_text", "free text about a person", [("notes",), ("transcript",), ("conversation",),
                                               ("free", "text"), ("bio",), ("cv",), ("resume",)]),
    ("identifier", "account identifiers", [("user", "id"), ("customer", "id"), ("member", "id"),
                                           ("patient", "id"), ("account", "id"), ("uid",)]),
]
PI_LABELS = {k: label for k, label, _ in PI_CATEGORIES}
# "address" after these words is not a physical address.
NOT_PHYSICAL_ADDRESS = {"email", "ip", "mac", "wallet", "server", "host", "base", "url", "web", "contract",
                        "memory", "bind", "listen", "remote", "local", "from", "reply", "to"}

CATEGORY_NOTES = {
    "ai": "Check the provider's retention and training settings, and send the minimum fields (references/08).",
    "analytics": "Load only after opt-in consent. Check whether IP addresses and identifiers are sent. "
                 "Ad pixels may also use the data for their own purposes.",
    "errors": "Scrub personal information from events before they are sent.",
    "logs": "Scrub personal information from logs before they are shipped.",
    "replay": "Session replay can record form fields. Mask inputs and load only after consent.",
    "email": "Direct marketing by email needs s69 consent or the customer exception.",
    "messaging": "Direct marketing by SMS or WhatsApp needs s69 consent or the customer exception.",
    "payments": "Card data should go straight to the provider. Record what you store yourself.",
    "backend": "Record the region you chose for the project.",
    "cloud": "Record the region of each bucket, function or service that holds personal information.",
    "automation": "Task history keeps copies of the data. Record its retention.",
    "forms": "Form submissions are stored by the vendor. Record its retention.",
    "unknown": "Find out who runs this service. If it receives personal information, record it as an "
               "operator or a third party you share with. If it is your own API, pass --ignore-host.",
}

# What a service in each category receives by design, whatever the code passes it.
BY_DESIGN = {
    "email": "the email address of each recipient",
    "messaging": "the phone number or account of each recipient",
    "payments": "payment details the customer enters",
    "analytics": "online identifiers: IP address, device and cookie IDs",
    "replay": "online identifiers and what users type and click",
    "errors": "IP address and request details in error events",
    "forms": "whatever the form collects",
    "support": "what customers write to support",
}

# --------------------------------------------------------------------------------------
# Patterns
# --------------------------------------------------------------------------------------
JS_IMPORT = re.compile(
    r"""\bimport\s+(?:type\s+)?(?:([A-Za-z_$][\w$]*)\s*,?\s*)?(?:\{([^}]*)\}|\*\s*as\s+([A-Za-z_$][\w$]*))?"""
    r"""\s*from\s*['"]([^'"]+)['"]""")
JS_SIDE_EFFECT = re.compile(r"""\bimport\s*\(?\s*['"]([^'"]+)['"]""")
JS_REQUIRE = re.compile(
    r"""(?:\b(?:const|let|var)\s+)?(?:([A-Za-z_$][\w$.]*)|\{([^}]*)\})\s*=\s*(?:await\s+)?"""
    r"""(?:require|import)\(\s*['"]([^'"]+)['"]\s*\)""")
PY_IMPORT = re.compile(r"^\s*import\s+([\w.]+)(?:\s+as\s+(\w+))?")
PY_FROM = re.compile(r"^\s*from\s+([\w.]+)\s+import\s+\(?([^)#]+)")
URL = re.compile(r"""(?:https?:)?//([A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9-]+)+)""")
HTTP_CALL = re.compile(
    r"""(\bfetch\s*\(|\baxios\b|\.(?:get|post|put|patch|delete|request)\s*\(|\brequests\.|\bhttpx\.|"""
    r"""\burlopen\s*\(|\bhttps?\.request\s*\(|\bgot\s*\(|\bky\s*\(|\bnew\s+URL\s*\(|\bcurl\b|"""
    r"""\bWebSocket\s*\(|\bEventSource\s*\(|\bsendBeacon\s*\(|<script[^>]*\bsrc\s*=|<iframe[^>]*\bsrc\s*=|"""
    r"""<form[^>]*\baction\s*=|<img[^>]*\bsrc\s*=|\bwp_remote_(?:get|post)\b|\bHttpClient\b|\bhttp\.(?:Get|Post)\b)""",
    re.I)
CDN_IMPORT = re.compile(r"^https?://(?:esm\.sh|cdn\.skypack\.dev|esm\.run|cdn\.jsdelivr\.net/npm|unpkg\.com)/(.+)$")


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def _tokens(line: str) -> List[str]:
    split = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", line)
    return re.findall(r"[a-z0-9]+", split.lower())


def pi_in_text(line: str) -> Dict[str, List[str]]:
    """Return {category: [matched terms]} for personal information field names in one line."""
    toks = _tokens(line)
    out: Dict[str, List[str]] = {}
    for key, _, terms in PI_CATEGORIES:
        for term in terms:
            n = len(term)
            for i in range(len(toks) - n + 1):
                if tuple(toks[i:i + n]) != term:
                    continue
                if term == ("address",) and i > 0 and toks[i - 1] in NOT_PHYSICAL_ADDRESS:
                    continue
                found = out.setdefault(key, [])
                if "_".join(term) not in found:
                    found.append("_".join(term))
                break
    return out


def _is_test_path(rel: str) -> bool:
    parts = rel.lower().split("/")
    name = parts[-1]
    return (any(p in TEST_DIRS for p in parts[:-1]) or ".test." in name or ".spec." in name
            or name.startswith("test_") or name.endswith("_test.py"))


def _js_package(spec: str) -> Optional[str]:
    spec = spec.strip()
    m = CDN_IMPORT.match(spec)
    if m:
        spec = m.group(1)
    for prefix in ("npm:", "jsr:"):
        if spec.startswith(prefix):
            spec = spec[len(prefix):]
    if not spec or spec.startswith((".", "/", "node:", "http:", "https:", "~", "#", "$")):
        return None
    parts = spec.split("/")
    name = "/".join(parts[:2]) if spec.startswith("@") else parts[0]
    if name.startswith("@"):
        name = "@" + name[1:].split("@")[0]
    else:
        name = name.split("@")[0]
    return name.lower()


def _py_package(module: str) -> Optional[str]:
    parts = module.split(".")
    for key in (".".join(parts[:2]), parts[0]):
        if key in pv.PY_MODULES:
            return pv.PY_MODULES[key]
    return None


def _names(group: str) -> List[str]:
    """Bound names from 'a, b as c, type d' or '{ a, b as c }'."""
    out = []
    for part in (group or "").split(","):
        part = part.strip().strip("{}() ").replace("type ", "")
        if not part:
            continue
        bits = re.split(r"\s+as\s+|\s*:\s*", part)
        name = bits[-1].strip()
        if re.match(r"^[A-Za-z_$][\w$]*$", name):
            out.append(name)
    return out


class _Inventory:
    def __init__(self):
        self.vendors: Dict[str, dict] = {}

    def get(self, vendor: str, category: str) -> dict:
        v = self.vendors.get(vendor)
        if v is None:
            v = self.vendors[vendor] = {
                "vendor": vendor, "category": category, "sources": [], "packages": [], "hosts": [],
                "locations": [], "dev_only": True, "_fields": {}, "_windows": [],
            }
        return v

    def add(self, vendor: str, category: str, source: str, rel: str, line: int, snippet: str,
            package: str = "", host: str = "", dev: bool = False) -> dict:
        v = self.get(vendor, category)
        if source not in v["sources"]:
            v["sources"].append(source)
        if package and package not in v["packages"]:
            v["packages"].append(package)
        if host and host not in v["hosts"]:
            v["hosts"].append(host)
        if not dev:
            v["dev_only"] = False
        loc = {"file": rel, "line": line, "source": source, "snippet": popia_scan.redact(snippet)}
        if len(v["locations"]) < MAX_LOCATIONS and loc not in v["locations"]:
            v["locations"].append(loc)
        return v


# --------------------------------------------------------------------------------------
# Readers
# --------------------------------------------------------------------------------------
def _is_extra_manifest(name: str) -> bool:
    return name == "Pipfile" or (name.startswith("requirements") and name.endswith((".txt", ".in")))


def _extra_manifests(root: Path, ignore_globs: List[str]) -> List[Path]:
    """Python manifests the scanner's file walk does not read (requirements*.txt, Pipfile)."""
    if root.is_file():
        return [root] if _is_extra_manifest(root.name) else []
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        dirnames[:] = [d for d in dirnames if d not in popia_scan.SKIP_DIRS
                       and not any(fnmatch.fnmatch(f"{rel_dir}/{d}".lstrip("./"), g.rstrip("/*"))
                                   for g in ignore_globs)]
        for fn in filenames:
            p = Path(dirpath) / fn
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            if (_is_extra_manifest(fn) and not p.is_symlink() and not any(fnmatch.fnmatch(rel, g) for g in ignore_globs)
                    and p.stat().st_size <= popia_scan.MAX_BYTES):
                out.append(p)
    return out


def _find_line(text: str, name: str) -> int:
    for i, ln in enumerate(text.splitlines(), 1):
        if f'"{name}"' in ln or f"'{name}'" in ln or ln.strip().lower().startswith(name.lower()):
            return i
    return 0


def _manifest_names(base: str, text: str) -> List[tuple]:
    """Return [(package, dev)] from one dependency manifest."""
    out: List[tuple] = []
    if base == "package.json":
        try:
            pkg = json.loads(text)
        except ValueError:
            return out
        for key, dev in (("dependencies", False), ("optionalDependencies", False),
                         ("peerDependencies", False), ("devDependencies", True)):
            deps = pkg.get(key) if isinstance(pkg, dict) else None
            if isinstance(deps, dict):
                out += [(n, dev) for n in deps]
    elif base.startswith("requirements") and base.endswith((".txt", ".in")):
        for ln in text.splitlines():
            m = re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9_.\-]*)", ln)
            if m and not ln.strip().startswith(("-", "#")):
                out.append((m.group(1), False))
    elif base == "pyproject.toml":
        section, in_array = "", False
        for ln in text.splitlines():
            st = ln.split("#", 1)[0].strip()
            if st.startswith("[") and not in_array:
                section = st
                continue
            dep_section = "dependencies" in section or "dependency-groups" in section
            opens = (re.match(r"^[\w.\-\"']*dependencies[\"']?\s*=\s*\[", st)
                     or (dep_section and re.match(r"^[\w.\-\"']+\s*=\s*\[", st)))
            if not in_array and opens:
                in_array = True
                st = st.split("[", 1)[1]
            if in_array:
                for m in re.finditer(r"""["']([A-Za-z0-9][A-Za-z0-9_.\-]*)""", st):
                    out.append((m.group(1), "dev" in section))
                if "]" in st:
                    in_array = False
                continue
            m = re.match(r"^([A-Za-z0-9][A-Za-z0-9_.\-]*)\s*=", st)
            if m and dep_section and section.startswith("[tool.poetry"):
                out.append((m.group(1), "dev" in section or "group" in section))
    elif base == "Pipfile":
        section = ""
        for ln in text.splitlines():
            s = ln.strip()
            if s.startswith("["):
                section = s
                continue
            m = re.match(r"^([A-Za-z0-9][A-Za-z0-9_.\-]*)\s*=", s)
            if m and section in ("[packages]", "[dev-packages]"):
                out.append((m.group(1), section == "[dev-packages]"))
    return out


def _read_manifests(inv: _Inventory, files: Dict[str, str]) -> None:
    for rel, text in files.items():
        base = rel.rsplit("/", 1)[-1]
        if base not in ("package.json", "pyproject.toml") and not _is_extra_manifest(base):
            continue
        for name, dev in _manifest_names(base, text):
            norm = name.lower()
            if base != "package.json":
                norm = norm.replace("_", "-")
            hit = pv.sdk_for_package(norm)
            if hit:
                _, vendor, cat = hit
                inv.add(vendor, cat, "manifest", rel, _find_line(text, name), name, package=norm, dev=dev)


def _bindings_js(line: str) -> List[tuple]:
    """[(package, [bound names])] imported on one JS or TS line."""
    out = []
    for m in JS_IMPORT.finditer(line):
        pkg = _js_package(m.group(4))
        if pkg:
            out.append((pkg, [n for n in (m.group(1), m.group(3)) if n] + _names(m.group(2))))
    for m in JS_REQUIRE.finditer(line):
        pkg = _js_package(m.group(3))
        if pkg:
            out.append((pkg, ([m.group(1)] if m.group(1) else []) + _names(m.group(2))))
    if not out:
        for m in JS_SIDE_EFFECT.finditer(line):
            pkg = _js_package(m.group(1))
            if pkg:
                out.append((pkg, []))
    return out


def _bindings_py(line: str) -> List[tuple]:
    m = PY_IMPORT.match(line)
    if m:
        pkg = _py_package(m.group(1))
        return [(pkg, [m.group(2) or m.group(1)])] if pkg else []
    m = PY_FROM.match(line)
    if m:
        out = []
        names = _names(m.group(2))
        pkg = _py_package(m.group(1))
        if pkg:
            out.append((pkg, names))
        else:
            for n in names:
                sub = _py_package(m.group(1) + "." + n)
                if sub:
                    out.append((sub, [n]))
        return out
    return []


def _read_code(inv: _Inventory, files: Dict[str, str], ignore_hosts: List[str]) -> None:
    for rel, text in files.items():
        ext = os.path.splitext(rel)[1].lower()
        base = rel.rsplit("/", 1)[-1]
        is_code = ext in CODE_EXT
        is_config = ext in CONFIG_EXT or base.startswith(".env")
        if not (is_code or is_config) or _is_test_path(rel):
            continue
        if base in ("package.json", "package-lock.json", "pyproject.toml", "Pipfile", "Pipfile.lock"):
            continue
        lines = text.splitlines()
        aliases: Dict[str, set] = {}  # vendor -> names bound to its client
        if ext in JS_EXT or ext in PY_EXT or ext in (".html", ".htm"):
            reader = _bindings_py if ext in PY_EXT else _bindings_js
            for i, line in enumerate(lines, 1):
                if len(line) > 4000:
                    continue
                for pkg, names in reader(line):
                    hit = pv.sdk_for_package(pkg)
                    if not hit:
                        continue
                    _, vendor, cat = hit
                    inv.add(vendor, cat, "import", rel, i, line, package=pkg)
                    aliases.setdefault(vendor, set()).update(n for n in names if len(n) > 1)
            # One hop: const client = new OpenAI(...), client = OpenAI(...), self.client = OpenAI()
            for vendor, names in aliases.items():
                for b in list(names):
                    rx = re.compile(r"([A-Za-z_$][\w$.]*)\s*(?::\s*[\w<>\[\]., ]+)?=\s*(?:new\s+)?(?:await\s+)?"
                                    + re.escape(b) + r"\b")
                    for line in lines:
                        for m in rx.finditer(line):
                            name = m.group(1).split(".")[-1] if m.group(1).startswith("self.") else m.group(1)
                            if name not in ("const", "let", "var") and len(name) > 1:
                                names.add(name)
            for vendor, names in aliases.items():
                if not names:
                    continue
                rx = re.compile(r"(?<![\w$])(?:" + "|".join(re.escape(n) for n in sorted(names)) + r")\b")
                v = inv.vendors[vendor]
                for i, line in enumerate(lines, 1):
                    if rx.search(line) and not (JS_IMPORT.search(line) or PY_IMPORT.match(line)
                                                or PY_FROM.match(line) or JS_REQUIRE.search(line)):
                        v["_windows"].append((rel, i))
        for i, line in enumerate(lines, 1):
            if len(line) > 4000:
                continue
            for m in URL.finditer(line):
                host = m.group(1).lower()
                if pv.is_not_third_party(host) or any(host == h or host.endswith("." + h) for h in ignore_hosts):
                    continue
                hit = pv.sdk_for_host(host)
                snippet = line if is_code else host
                if hit:
                    _, vendor, cat = hit
                    v = inv.add(vendor, cat, "api host" if is_code else "config", rel, i, snippet, host=host)
                    if is_code:
                        v["_windows"].append((rel, i))
                elif is_code and HTTP_CALL.search(line):
                    v = inv.add("Unknown: " + host, "unknown", "api host", rel, i, snippet, host=host)
                    v["_windows"].append((rel, i))


DEFINITION = re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\b|def\s|class\s)"
                        r"|^\s*(?:export\s+)?(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?\([^)]*\)\s*=>")


def _window(lines: List[str], ln: int) -> List[int]:
    """Line numbers around a call, stopping at the function that holds it and the next definition."""
    start = ln
    while start > 1 and ln - start < WINDOW and not DEFINITION.search(lines[start - 1]):
        start -= 1
    end = ln
    while end < len(lines) and end - ln < WINDOW and not DEFINITION.search(lines[end]):
        end += 1
    return list(range(start, end + 1))


def _trace_fields(inv: _Inventory, files: Dict[str, str]) -> None:
    for v in inv.vendors.values():
        fields: Dict[str, dict] = {}
        seen = set()
        for rel, ln in v["_windows"]:
            lines = files[rel].splitlines()
            for j in _window(lines, ln):
                if (rel, j) in seen:
                    continue
                seen.add((rel, j))
                for key, terms in pi_in_text(lines[j - 1]).items():
                    f = fields.setdefault(key, {"category": key, "label": PI_LABELS[key], "fields": [],
                                                "locations": []})
                    f["fields"] += [t for t in terms if t not in f["fields"]]
                    if len(f["locations"]) < MAX_LOCATIONS:
                        f["locations"].append(f"{rel}:{j}")
        order = [k for k, _, _ in PI_CATEGORIES]
        v["personal_information"] = [fields[k] for k in order if k in fields]
        v["traced"] = bool(v["_windows"])


# --------------------------------------------------------------------------------------
# Inventory
# --------------------------------------------------------------------------------------
def inventory(path: str, ignore_hosts: Optional[List[str]] = None) -> dict:
    root = Path(path).resolve()
    if not root.exists():
        raise FileNotFoundError(path)
    base = root if root.is_dir() else root.parent
    ignore_globs = popia_scan.load_ignore(base)
    files: Dict[str, str] = {}
    for p in list(popia_scan.iter_files(root, ignore_globs)) + _extra_manifests(root, ignore_globs):
        t = popia_scan.read_text(p)
        if t is not None:
            files[os.path.relpath(p, base).replace(os.sep, "/")] = t
    ignore = [h.strip().lower().lstrip(".") for h in (ignore_hosts or []) if h.strip()]

    inv = _Inventory()
    _read_manifests(inv, files)
    _read_code(inv, files, ignore)
    _trace_fields(inv, files)

    operators = []
    for v in inv.vendors.values():
        cats = {f["category"] for f in v["personal_information"]}
        notes = []
        if v["category"] in CATEGORY_NOTES:
            notes.append(CATEGORY_NOTES[v["category"]])
        if "special" in cats:
            notes.append("Special personal information appears near this call. Check a s27 ground. If the "
                         "vendor's country lacks adequate protection, s57(1)(d) prior authorisation may apply.")
        if "children" in cats:
            notes.append("Children's information appears near this call. Check s34 and s35 before sending it.")
        if v["dev_only"]:
            notes.append("Found only as a dev dependency. Check whether it runs in production.")
        if not v["traced"]:
            notes.append("No call found in the scanned code. Check where it is used.")
        by_design = BY_DESIGN.get(v["category"], "") if (v["traced"] or v["sources"] != ["manifest"]) else ""
        operators.append({
            "vendor": v["vendor"], "category": v["category"],
            "role": "find out who runs it" if v["category"] == "unknown" else "likely operator (s20, s21), confirm",
            "sources": v["sources"], "packages": v["packages"], "hosts": v["hosts"],
            "locations": v["locations"], "by_design": by_design,
            "personal_information": v["personal_information"],
            "special_pi": "special" in cats, "children": "children" in cats,
            "dev_only": v["dev_only"], "traced": v["traced"], "notes": notes,
            "to_record": {"hosting_country": "", "s72_basis": "", "operator_agreement": ""},
        })
    operators.sort(key=lambda o: (o["category"] == "unknown", not (o["personal_information"] or o["by_design"]),
                                  o["vendor"].lower()))
    return {
        "tool": "popia_operators",
        "version": __version__,
        "scanned_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "target": str(root),
        "files_scanned": len(files),
        "summary": {
            "third_parties": len(operators),
            "with_personal_information": sum(1 for o in operators if o["personal_information"] or o["by_design"]),
            "special_pi": sum(1 for o in operators if o["special_pi"]),
            "children": sum(1 for o in operators if o["children"]),
            "unknown_hosts": sum(1 for o in operators if o["category"] == "unknown"),
        },
        "operators": operators,
        "disclaimer": DISCLAIMER,
    }


# --------------------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------------------
def _pi_summary(o: dict) -> str:
    parts = [f"by design: {o['by_design']}"] if o["by_design"] else []
    parts += [f"{f['label']} ({', '.join(f['fields'])})" for f in o["personal_information"]]
    if parts:
        return "; ".join(parts)
    return "none seen near calls" if o["traced"] else "not traced: no call found"


def _cell(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def fmt_md(res: dict) -> str:
    s = res["summary"]
    md = [
        "# Third parties and operators", "",
        "Every third-party API or SDK found in the code and dependency manifests, and the personal information "
        "that appears to reach each one. Use it to start your operator register (s20, s21) and your list of "
        "cross-border transfers (s72). Record each one in the ROPA (`templates/ropa.csv`) and disclose it in "
        "the privacy notice (s18(1)(g)).", "",
        f"- **Target:** `{res['target']}`",
        f"- **Scanned:** {res['scanned_at']} · {res['files_scanned']} files · popia_operators {res['version']}",
        f"- **Third parties:** {s['third_parties']} · with personal information: {s['with_personal_information']}"
        f" · special personal information: {s['special_pi']} · children: {s['children']}"
        f" · unknown hosts: {s['unknown_hosts']}", "",
    ]
    ops = res["operators"]
    if not ops:
        md += ["No third-party APIs or SDKs found. That does not mean there are none: check server code you "
               "did not scan, tag managers and no-code tools.", ""]
    else:
        md += ["| Third party | Category | Found in | Personal information that appears to reach it |",
               "|---|---|---|---|"]
        for o in ops:
            md.append(f"| {_cell(o['vendor'])} | {o['category']} | {', '.join(o['sources'])} | "
                      f"{_cell(_pi_summary(o))} |")
        md.append("")
    for o in ops:
        md += [f"## {o['vendor']}", "", f"**Category:** {o['category']} · **Role:** {o['role']}", ""]
        if o["packages"]:
            md.append("**Packages:** " + ", ".join(f"`{p}`" for p in o["packages"]))
        if o["hosts"]:
            md.append("**Hosts:** " + ", ".join(f"`{h}`" for h in o["hosts"]))
        md += ["", "| Location | Source | Evidence (redacted) |", "|---|---|---|"]
        for loc in o["locations"]:
            where = f"`{loc['file']}:{loc['line']}`" if loc["line"] else f"`{loc['file']}`"
            md.append(f"| {where} | {loc['source']} | `{_cell(loc['snippet'])}` |")
        md.append("")
        if o["by_design"]:
            md += [f"**Receives by design:** {o['by_design']}.", ""]
        if o["personal_information"]:
            md += ["**Personal information near calls:**", ""]
            for f in o["personal_information"]:
                md.append(f"- {f['label']}: {', '.join(f'`{x}`' for x in f['fields'])} at "
                          + ", ".join(f"`{x}`" for x in f["locations"][:4]))
            md.append("")
        for n in o["notes"]:
            md.append(f"> {n}")
        md += ["", "**To record:** hosting country, s72 basis, operator agreement with s21 terms.", ""]
    md += [
        "## What this cannot see", "",
        "- Data your server forwards from code that was not scanned, or from environment-configured URLs.",
        "- Tags loaded through a tag manager, and no-code tools (Zapier, Make, n8n) set up outside the repo.",
        "- Where each vendor stores data. Confirm the hosting country and region with each vendor.",
        "- Whether a field really reaches the vendor. Field names are matched near each call. Read the code.", "",
        "---", "",
        "_Status for each row: confirmed / not personal information / needs info. Triage before sharing._", "",
        f"> {res['disclaimer']} See DISCLAIMER.md.",
    ]
    return "\n".join(md)


CSV_COLUMNS = ["vendor", "category", "role", "found_in", "packages", "hosts", "by_design", "personal_information",
               "special_pi", "children", "locations", "hosting_country", "s72_basis", "operator_agreement",
               "notes"]


def fmt_csv(res: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(CSV_COLUMNS)
    for o in res["operators"]:
        w.writerow([
            o["vendor"], o["category"], o["role"], ";".join(o["sources"]), ";".join(o["packages"]),
            ";".join(o["hosts"]), o["by_design"],
            ";".join(f"{f['category']}:{'/'.join(f['fields'])}" for f in o["personal_information"]),
            str(o["special_pi"]).lower(), str(o["children"]).lower(),
            ";".join(f"{x['file']}:{x['line']}" for x in o["locations"]),
            "", "", "", " ".join(o["notes"]),
        ])
    return buf.getvalue()


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="List third-party APIs and SDKs in a codebase and the personal information that appears "
                    "to reach each (operators s20, s21; cross-border s72). Engineering guidance, not legal advice.")
    ap.add_argument("path", nargs="?", default=".")
    ap.add_argument("--format", choices=["md", "json", "csv"], default="md")
    ap.add_argument("--out")
    ap.add_argument("--ignore-host", action="append", default=[],
                    help="a host you run yourself, for example api.my-app.co.za. Matches subdomains. Repeatable.")
    ap.add_argument("--version", action="version", version=__version__)
    a = ap.parse_args(argv)
    res = inventory(a.path, a.ignore_host)
    out = {"md": fmt_md, "json": lambda r: json.dumps(r, indent=2), "csv": fmt_csv}[a.format](res)
    if a.out:
        Path(a.out).write_text(out, encoding="utf-8")
        s = res["summary"]
        print(f"wrote {a.out}: third_parties={s['third_parties']} "
              f"with_personal_information={s['with_personal_information']}", file=sys.stderr)
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
