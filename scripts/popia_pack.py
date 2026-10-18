#!/usr/bin/env python3
"""
popia_pack: generate a draft POPIA compliance pack from a questionnaire.

Stdlib only. Python 3.8+.

    python3 popia_pack.py --answers answers.json --out ./compliance-pack
    python3 popia_pack.py --interactive [--out ./compliance-pack] [--save-answers answers.json]
    python3 popia_pack.py --print-questions
    python3 popia_pack.py --example [example-answers.json]

Output is a DRAFT. Engineering and compliance guidance, not legal advice.
Have every document reviewed by a qualified South African privacy attorney
before use. See DISCLAIMER.md.

Programmatic use:
    from popia_pack import generate, load_questions
    files = generate(answers)                  # {filename: content}
    files = generate(answers, "./pack")        # also writes the files

Template syntax (small Handlebars-like subset):
    {{var}}                         value, or [[TODO: var]] when missing
    {{#if var}} ... {{else}} ... {{/if}}
    {{#unless var}} ... {{else}} ... {{/unless}}
    {{#each list}} {{this}} {{this.field}} {{field}} ... {{else}} empty {{/each}}
Blocks nest. A block tag alone on a line removes that whole line.
"""
from __future__ import annotations

import argparse
import copy
import csv
import io
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

__version__ = "1.0.0"

ROOT = Path(__file__).resolve().parent.parent
# Clone layout: <repo>/templates. Installed package: popia_kit/data/templates.
TEMPLATES_DIR = ROOT / "templates"
if not TEMPLATES_DIR.is_dir():
    TEMPLATES_DIR = Path(__file__).resolve().parent / "data" / "templates"
QUESTIONNAIRE = TEMPLATES_DIR / "pack-questionnaire.json"

DISCLAIMER_LINE = (
    "> Draft template. Engineering and compliance guidance, not legal advice. "
    "Have it reviewed by a qualified South African privacy attorney before use. "
    "See DISCLAIMER.md."
)

REGULATOR_PLACEHOLDER = (
    "[[VERIFY: Information Regulator contact details. Copy the current physical "
    "address, postal address, complaints email, general enquiries email and website "
    "from https://inforegulator.org.za. Do not copy details from old documents or "
    "other organisations' notices.]]"
)

REPO_URL = "https://github.com/VenusOne-Lee/popia-compliance"

TODO_RE = re.compile(r"\[\[TODO: ([^\]]+)\]\]")


class TemplateError(ValueError):
    """Raised for malformed templates (unbalanced or unknown tags)."""


# --------------------------------------------------------------------------
# Template engine
# --------------------------------------------------------------------------

_TAG_RE = re.compile(r"\{\{\s*(.*?)\s*\}\}", re.S)
_STANDALONE_RE = re.compile(r"(?m)^[ \t]*(\{\{\s*(?:#|/|else\b)[^}]*\}\})[ \t]*\r?\n")
_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")


def _tokenize(src: str) -> List[Tuple[str, str]]:
    src = _STANDALONE_RE.sub(r"\1", src)
    tokens: List[Tuple[str, str]] = []
    pos = 0
    for m in _TAG_RE.finditer(src):
        if m.start() > pos:
            tokens.append(("text", src[pos:m.start()]))
        tokens.append(("tag", m.group(1)))
        pos = m.end()
    if pos < len(src):
        tokens.append(("text", src[pos:]))
    return tokens


def _parse(tokens: List[Tuple[str, str]]) -> list:
    root: list = []
    # stack entries: (kind, name, node, current_children_list)
    stack: List[list] = []
    current = root
    for kind, val in tokens:
        if kind == "text":
            current.append(("text", val))
            continue
        if val.startswith("#"):
            parts = val[1:].split(None, 1)
            if len(parts) != 2 or parts[0] not in ("if", "unless", "each"):
                raise TemplateError("Unknown block tag: {{%s}}" % val)
            block, name = parts[0], parts[1].strip()
            if not _NAME_RE.match(name):
                raise TemplateError("Bad name in {{%s}}" % val)
            node = {"type": block, "name": name, "body": [], "else": []}
            current.append(node)
            stack.append([block, node, "body"])
            current = node["body"]
        elif val == "else":
            if not stack:
                raise TemplateError("{{else}} outside a block")
            frame = stack[-1]
            if frame[2] == "else":
                raise TemplateError("Duplicate {{else}} in {{#%s}}" % frame[0])
            frame[2] = "else"
            current = frame[1]["else"]
        elif val.startswith("/"):
            block = val[1:].strip()
            if not stack or stack[-1][0] != block:
                raise TemplateError("Unbalanced closing tag {{%s}}" % val)
            stack.pop()
            if stack:
                frame = stack[-1]
                current = frame[1][frame[2]]
            else:
                current = root
        else:
            if not _NAME_RE.match(val):
                raise TemplateError("Unknown tag: {{%s}}" % val)
            current.append(("var", val))
    if stack:
        raise TemplateError("Unclosed block {{#%s %s}}" % (stack[-1][0], stack[-1][1]["name"]))
    return root


_MISSING = object()


def _is_empty(v: Any) -> bool:
    return v is None or v is _MISSING or v == "" or v == [] or v == {}


def _truthy(v: Any) -> bool:
    if _is_empty(v):
        return False
    return bool(v)


def _fmt(v: Any) -> str:
    if isinstance(v, bool):
        return "Yes" if v else "No"
    if isinstance(v, (list, tuple)):
        return ", ".join(_fmt(x) for x in v)
    if isinstance(v, dict):
        return ", ".join("%s: %s" % (k, _fmt(x)) for k, x in v.items())
    return str(v)


class _Renderer:
    def __init__(self) -> None:
        self.missing: List[str] = []

    def _lookup(self, name: str, stack: list) -> Tuple[Any, str]:
        """Return (value, todo_id)."""
        parts = name.split(".")
        if parts[0] == "this":
            for frame in reversed(stack):
                if "__this__" in frame:
                    val = frame["__this__"]
                    todo = frame["__list__"]
                    for p in parts[1:]:
                        todo = "%s.%s" % (todo, p)
                        val = val.get(p, _MISSING) if isinstance(val, dict) else _MISSING
                    return val, todo
            return _MISSING, name
        for frame in reversed(stack):
            scope = frame.get("__this__") if "__this__" in frame else frame
            if isinstance(scope, dict) and parts[0] in scope:
                val = scope[parts[0]]
                for p in parts[1:]:
                    val = val.get(p, _MISSING) if isinstance(val, dict) else _MISSING
                return val, name
        return _MISSING, name

    def render(self, nodes: list, stack: list) -> str:
        out: List[str] = []
        for node in nodes:
            if isinstance(node, tuple):
                if node[0] == "text":
                    out.append(node[1])
                else:
                    val, todo = self._lookup(node[1], stack)
                    if _is_empty(val):
                        self.missing.append(todo)
                        out.append("[[TODO: %s]]" % todo)
                    else:
                        out.append(_fmt(val))
                continue
            val, _ = self._lookup(node["name"], stack)
            if node["type"] == "if":
                out.append(self.render(node["body"] if _truthy(val) else node["else"], stack))
            elif node["type"] == "unless":
                out.append(self.render(node["else"] if _truthy(val) else node["body"], stack))
            else:  # each
                items = val if isinstance(val, (list, tuple)) else []
                if not items:
                    out.append(self.render(node["else"], stack))
                for item in items:
                    frame = {"__this__": item, "__list__": node["name"]}
                    out.append(self.render(node["body"], stack + [frame]))
        return "".join(out)


def render_template(src: str, context: Dict[str, Any]) -> Tuple[str, List[str]]:
    """Render a template string. Returns (text, list of missing variable ids)."""
    r = _Renderer()
    text = r.render(_parse(_tokenize(src)), [context])
    return text, r.missing


# --------------------------------------------------------------------------
# Questions
# --------------------------------------------------------------------------

def load_questions(path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load the questionnaire (list of question dicts)."""
    p = Path(path) if path else QUESTIONNAIRE
    with open(p, encoding="utf-8") as fh:
        data = json.load(fh)
    return data["questions"]


def _applicable(q: Dict[str, Any], answers: Dict[str, Any]) -> bool:
    dep = q.get("ask_if")
    return not dep or _truthy(answers.get(dep))


def _prompt(text: str) -> str:
    try:
        return input(text)
    except EOFError:
        return ""


def _ask_one(q: Dict[str, Any]) -> Any:
    qtype = q.get("type", "string")
    default = q.get("default")
    hint = ""
    if q.get("options"):
        hint = " [options: %s]" % ", ".join(q["options"])
    if default not in (None, [], ""):
        hint += " (default: %s)" % _fmt(default)
    print("\n%s%s" % (q["prompt"], hint))
    if q.get("help"):
        print("  " + q["help"])

    if qtype == "boolean":
        raw = _prompt("  y/n: ").strip().lower()
        if not raw:
            return default
        return raw in ("y", "yes", "true", "1", "ja", "ee")
    if qtype in ("multiselect", "list"):
        raw = _prompt("  Separate items with commas: ").strip()
        if not raw:
            return default
        return [x.strip() for x in raw.split(",") if x.strip()]
    if qtype == "number":
        raw = _prompt("  Number: ").strip()
        if not raw:
            return default
        try:
            return int(raw)
        except ValueError:
            print("  Not a number. Left unanswered.")
            return default
    if qtype == "records":
        records = []
        fields = q.get("item_fields", [])
        while True:
            more = _prompt("  Add an entry? y/n: ").strip().lower()
            if more not in ("y", "yes"):
                break
            rec = {}
            for f in fields:
                opts = " [%s]" % ", ".join(f["options"]) if f.get("options") else ""
                val = _prompt("    %s%s: " % (f["prompt"], opts)).strip()
                if val:
                    rec[f["id"]] = val
            records.append(rec)
        return records if records else default
    raw = _prompt("  > ").strip()
    return raw if raw else default


def ask_interactive(questions: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Ask every applicable question on the command line. Returns answers."""
    questions = questions or load_questions()
    print("POPIA compliance pack questionnaire. Press Enter to skip a question.")
    print("Skipped required questions appear as [[TODO: id]] in the pack.")
    answers: Dict[str, Any] = {}
    section = None
    for q in questions:
        if not _applicable(q, answers):
            continue
        if q.get("section") != section:
            section = q.get("section")
            print("\n== %s ==" % section)
        val = _ask_one(q)
        if val is not None:
            answers[q["id"]] = val
    return answers


# --------------------------------------------------------------------------
# Context building
# --------------------------------------------------------------------------

LAWFUL_BASIS_TEXT = {
    "consent": "Consent (s11(1)(a))",
    "contract": "Contract with you (s11(1)(b))",
    "legal_obligation": "Obligation imposed by law (s11(1)(c))",
    "data_subject_interest": "Protects your legitimate interest (s11(1)(d))",
    "public_duty": "Public law duty (s11(1)(e))",
    "legitimate_interest": "Our legitimate interests or those of a third party (s11(1)(f))",
}

S27_GROUND_TEXT = {
    "consent": "your explicit consent (s27(1)(a))",
    "legal_right_or_obligation": "that it is necessary to establish, exercise or defend a right or obligation in law (s27(1)(b))",
    "international_public_law": "that it is necessary to comply with an obligation of international public law (s27(1)(c))",
    "research": "historical, statistical or research purposes with appropriate safeguards (s27(1)(d))",
    "made_public": "that you deliberately made the information public (s27(1)(e))",
    "specific_authorisation": "a specific authorisation in s28 to s33 (s27(1)(f))",
}

SA_NAMES = {"south africa", "za", "rsa", "republic of south africa"}

PACK_FILES = [
    "README.md",
    "privacy-notice.md",
    "cookie-notice.md",
    "consent-wording.md",
    "paia-manual.md",
    "dsar-runbook.md",
    "breach-notice-data-subject.md",
    "ropa.csv",
    "operator-register.csv",
    "retention-schedule.csv",
]

TEMPLATE_MAP = {
    "privacy-notice.md": "privacy-notice.md",
    "cookie-notice.md": "cookie-notice.md",
    "consent-wording.md": "consent-patterns.md",
    "paia-manual.md": "paia-manual-scaffold.md",
    "dsar-runbook.md": "dsar-runbook.md",
    "breach-notice-data-subject.md": "breach-notice-data-subject.md",
}


def _is_sa(country: Any) -> bool:
    return isinstance(country, str) and country.strip().lower() in SA_NAMES


def _as_list(v: Any) -> List[Any]:
    if v is None or v == "":
        return []
    if isinstance(v, (list, tuple)):
        return list(v)
    if isinstance(v, str):
        return [x.strip() for x in re.split(r"[;,]", v) if x.strip()]
    return [v]


def _apply_defaults(answers: Dict[str, Any], questions: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[str]]:
    a = copy.deepcopy(answers)
    defaults_used = []
    for q in questions:
        qid = q["id"]
        if qid not in a and q.get("default") is not None and _applicable(q, a):
            a[qid] = copy.deepcopy(q["default"])
            defaults_used.append(qid)
    return a, defaults_used


def _unanswered(answers: Dict[str, Any], questions: List[Dict[str, Any]]) -> List[str]:
    out = []
    for q in questions:
        if q.get("required") and _applicable(q, answers):
            v = answers.get(q["id"])
            if v is None or v == "":
                out.append(q["id"])
            elif q.get("type") == "records" and v == [] and q.get("default") is None:
                out.append(q["id"])
    return out


def build_context(answers: Dict[str, Any], questions: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Merge answers with defaults and derived values used by templates."""
    questions = questions or load_questions()
    ctx, _ = _apply_defaults(answers, questions)

    legal = ctx.get("company_legal_name")
    ctx["display_name"] = ctx.get("trading_name") or legal
    ctx["company_display"] = ctx["display_name"]

    subjects = [str(s) for s in _as_list(ctx.get("data_subject_types"))]
    ctx["includes_juristic_persons"] = any(
        k in s.lower() for s in subjects for k in ("business", "supplier", "compan", "juristic")
    )
    cats = _as_list(ctx.get("data_categories"))
    ctx["data_categories_text"] = ", ".join(str(c) for c in cats) if cats else None

    # special PI and children
    spi = _as_list(ctx.get("special_pi"))
    ctx["special_pi"] = spi
    ctx["has_special_pi"] = bool(spi)
    ctx["special_pi_text"] = ", ".join(spi) if spi else None
    ground = ctx.get("special_pi_ground")
    ctx["special_pi_ground_text"] = S27_GROUND_TEXT.get(ground, ground) if ground else None
    ctx["children"] = bool(ctx.get("children"))
    ctx["has_special_or_children"] = ctx["has_special_pi"] or ctx["children"]

    # purposes
    purposes = []
    for p in ctx.get("purposes") or []:
        p = dict(p)
        lb = p.get("lawful_basis")
        if lb:
            p["lawful_basis_text"] = LAWFUL_BASIS_TEXT.get(lb, lb)
        purposes.append(p)
    ctx["purposes"] = purposes if ctx.get("purposes") is not None else None

    # operators and cross-border
    ops = ctx.get("operators")
    countries = [c for c in _as_list(ctx.get("cross_border_countries")) if not _is_sa(c)]
    for op in ops or []:
        c = op.get("country")
        if c and not _is_sa(c) and c not in countries:
            countries.append(c)
    ctx["cross_border_countries"] = countries
    ctx["has_cross_border"] = bool(countries)
    ctx["cross_border_countries_text"] = ", ".join(countries) if countries else None
    foreign_ops = [op.get("name") for op in ops or [] if op.get("country") and not _is_sa(op.get("country"))]
    ctx["cross_border_recipient"] = ", ".join(n for n in foreign_ops if n) or None
    ctx["cross_border_data"] = ctx.get("cross_border_data") or "personal information"
    ctx["cross_border_purpose"] = ctx.get("cross_border_consent_purpose")

    # marketing
    channels = [str(c).lower() for c in _as_list(ctx.get("marketing_channels"))]
    ctx["marketing_channels"] = channels
    ctx["has_marketing"] = bool(channels)
    ctx["marketing_any"] = bool(channels)
    for ch in ("email", "sms", "whatsapp", "phone", "push"):
        ctx["marketing_" + ch] = ch in channels
    labels = {"email": "email", "sms": "SMS", "whatsapp": "WhatsApp", "phone": "phone calls", "push": "push notifications"}
    ctx["marketing_channels_text"] = ", ".join(labels.get(c, c) for c in channels) if channels else None
    ctx["marketing_existing_customer_exception"] = bool(ctx.get("marketing_existing_customer_exception"))

    # cookies and tools
    for key in ("analytics_tools", "marketing_tools", "necessary_cookies"):
        ctx[key] = ctx.get(key) or []
    site = (ctx.get("website") or "").rstrip("/")
    if not ctx.get("cookie_notice_url") and site:
        ctx["cookie_notice_url"] = site + "/cookies"
    ctx.setdefault("cookie_review_months", 12)

    # flags
    for key in ("ai_features", "automated_decisions", "call_recording", "cross_border_consent"):
        ctx[key] = bool(ctx.get(key))

    if not ctx.get("postal_address"):
        ctx["postal_address_display"] = ctx.get("physical_address")
    else:
        ctx["postal_address_display"] = ctx.get("postal_address")

    # data subject requests
    if not ctx.get("dsar_email"):
        ctx["dsar_email"] = ctx.get("io_email")

    # Regulator contact: never fabricated
    if not ctx.get("regulator_contact"):
        ctx["regulator_contact"] = REGULATOR_PLACEHOLDER

    ctx["dios"] = ctx.get("dios") or []
    return ctx


# --------------------------------------------------------------------------
# CSV outputs
# --------------------------------------------------------------------------

ROPA_COLUMNS = [
    "data_store", "fields", "data_subjects", "purpose", "lawful_basis", "special_pi", "children",
    "retention", "retention_trigger", "operators", "cross_border", "owner", "reviewed_at",
    "collection_point", "hosting_country", "s72_basis", "operator_agreement", "notes",
]

OPERATOR_COLUMNS = [
    "operator", "service", "personal_information", "processing_country", "cross_border",
    "s72_basis", "operator_agreement", "s21_breach_notice_immediate", "sub_operators_reviewed",
    "return_or_deletion_on_exit", "last_reviewed", "notes",
]


def _csv(rows: List[List[Any]]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    for r in rows:
        w.writerow(["" if v is None else v for v in r])
    return buf.getvalue()


def _todo(qid: str) -> str:
    return "[[TODO: %s]]" % qid


def _cell(rec: Dict[str, Any], key: str, todo_id: str) -> str:
    v = rec.get(key)
    if _is_empty(v):
        return _todo(todo_id)
    if isinstance(v, (list, tuple)):
        return ";".join(str(x) for x in v)
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def _bool_cell(v: Any) -> str:
    if isinstance(v, str):
        return "true" if v.strip().lower() in ("true", "yes", "y", "1") else "false"
    return "true" if v else "false"


def build_ropa(ctx: Dict[str, Any]) -> str:
    rows: List[List[Any]] = [ROPA_COLUMNS]
    ops = {o.get("name"): o for o in ctx.get("operators") or [] if o.get("name")}
    data_sets = ctx.get("data_sets")
    if not data_sets:
        rows.append([_todo("data_sets")] + [""] * (len(ROPA_COLUMNS) - 1))
        return _csv(rows)
    for ds in data_sets:
        op_names = [str(x) for x in _as_list(ds.get("operators"))]
        countries, bases, agreements, notes = [], [], [], []
        for n in op_names:
            op = ops.get(n)
            if not op:
                notes.append("Operator '%s' not in operator list: VERIFY" % n)
                continue
            c = op.get("country") or "VERIFY"
            if c not in countries:
                countries.append(c)
            if not _is_sa(c):
                b = op.get("s72_basis") or "VERIFY"
                if b not in bases:
                    bases.append(b)
            agreements.append("%s: %s" % (n, op.get("agreement") or "unknown"))
        foreign = [c for c in countries if not _is_sa(c)]
        rows.append([
            _cell(ds, "name", "data_sets.name"),
            _cell(ds, "fields", "data_sets.fields"),
            _cell(ds, "data_subjects", "data_sets.data_subjects"),
            _cell(ds, "purpose", "data_sets.purpose"),
            _cell(ds, "lawful_basis", "data_sets.lawful_basis"),
            _bool_cell(ds.get("special_pi")),
            _bool_cell(ds.get("children")),
            _cell(ds, "retention", "data_sets.retention"),
            _cell(ds, "retention_trigger", "data_sets.retention_trigger"),
            ";".join(op_names),
            ";".join(foreign),
            _cell(ds, "owner", "data_sets.owner"),
            ctx.get("effective_date") or _todo("effective_date"),
            _cell(ds, "collection_point", "data_sets.collection_point"),
            ";".join(countries) if countries else (ctx.get("hosting_region") or _todo("hosting_region")),
            ";".join(bases) if foreign else "Not applicable (no transfer)",
            ";".join(agreements),
            "; ".join(notes) or ds.get("notes", ""),
        ])
    return _csv(rows)


def build_operator_register(ctx: Dict[str, Any]) -> str:
    rows: List[List[Any]] = [OPERATOR_COLUMNS]
    ops = ctx.get("operators")
    if not ops:
        rows.append([_todo("operators")] + [""] * (len(OPERATOR_COLUMNS) - 1))
        return _csv(rows)
    for op in ops:
        country = op.get("country")
        foreign = bool(country) and not _is_sa(country)
        rows.append([
            _cell(op, "name", "operators.name"),
            _cell(op, "service", "operators.service"),
            _cell(op, "data", "operators.data"),
            _cell(op, "country", "operators.country"),
            "yes" if foreign else ("no" if country else "VERIFY"),
            (op.get("s72_basis") or "VERIFY") if foreign else "Not applicable",
            op.get("agreement") or "unknown",
            "VERIFY",
            "VERIFY",
            "VERIFY",
            ctx.get("effective_date") or _todo("effective_date"),
            "Check against templates/operator-agreement-checklist.md",
        ])
    return _csv(rows)


def build_retention_schedule(ctx: Dict[str, Any], templates_dir: Path) -> str:
    with open(templates_dir / "retention-schedule.csv", encoding="utf-8", newline="") as fh:
        base = list(csv.reader(fh))
    header, generic = base[0], base[1:]
    rows: List[List[Any]] = [header]
    for ds in ctx.get("data_sets") or []:
        rows.append([
            _cell(ds, "name", "data_sets.name"),
            _cell(ds, "fields", "data_sets.fields"),
            _cell(ds, "retention", "data_sets.retention"),
            _cell(ds, "retention_trigger", "data_sets.retention_trigger"),
            "Business need under s14(1) POPIA, or law named in the ROPA",
            "From your answers. Keep no longer than necessary for the purpose.",
            "Delete or de-identify (s14(4)); prevent reconstruction (s14(5))",
            "verify for your sector",
        ])
    rows.extend(generic)
    return _csv(rows)


# --------------------------------------------------------------------------
# README
# --------------------------------------------------------------------------

REVIEW_NOTES = {
    "privacy-notice.md": "Check every s18(1) item against what the product actually does. Paste the Regulator's current contact details. Publish with a version and effective date. Link from the footer and every form.",
    "cookie-notice.md": "Run scripts/site_check.py and confirm the cookie list matches what the site sets. Confirm nothing non-essential loads before consent.",
    "consent-wording.md": "Confirm each pattern matches the UI exactly. Store the wording version with every consent event.",
    "paia-manual.md": "Align to the Regulator's current PAIA manual template and guide. Resolve every VERIFY item.",
    "dsar-runbook.md": "Name owners, set the log location, test the process end to end. Confirm PAIA fees before quoting.",
    "breach-notice-data-subject.md": "Keep ready. Fill the bracketed items only during an incident. Pair with templates/breach-regulator-checklist.md.",
    "ropa.csv": "Check every data store, field and operator. Resolve VERIFY cells. Keep it next to the schema.",
    "operator-register.csv": "Confirm s21 terms, immediate breach notification, sub-operators and exit terms for each operator.",
    "retention-schedule.csv": "Statutory periods are commonly cited norms. Confirm each one for your sector with your attorney or auditor.",
}


def _verify_items(files: Dict[str, str]) -> Dict[str, List[Tuple[int, str]]]:
    out: Dict[str, List[Tuple[int, str]]] = {}
    for name, content in files.items():
        hits = []
        for i, line in enumerate(content.splitlines(), 1):
            if "VERIFY" in line:
                text = line.strip().lstrip("-|> ").strip()
                if len(text) > 110:
                    text = text[:107] + "..."
                hits.append((i, text))
        if hits:
            out[name] = hits
    return out


def review_flags(ctx: Dict[str, Any]) -> List[str]:
    """Return plain-language flags for processing that needs attorney review."""
    flags = []
    if ctx.get("has_special_pi"):
        flags.append("Special personal information (%s): confirm the s27 ground and the wording of the separate consent." % ctx.get("special_pi_text"))
        if "biometric information" in ctx.get("special_pi", []):
            flags.append("Biometric information: needs a s27 ground and attorney review (AI-12).")
    if ctx.get("children"):
        flags.append("Children's personal information: confirm the s35 ground and the competent person consent flow.")
    if ctx.get("has_special_or_children") and ctx.get("has_cross_border"):
        ops = {o.get("name"): o for o in ctx.get("operators") or []}
        sensitive = [d for d in ctx.get("data_sets") or []
                     if _bool_cell(d.get("special_pi")) == "true" or _bool_cell(d.get("children")) == "true"]
        if sensitive:
            countries = []
            for d in sensitive:
                for n in _as_list(d.get("operators")):
                    c = (ops.get(n) or {}).get("country")
                    if c and not _is_sa(c) and c not in countries:
                        countries.append(c)
        else:
            countries = list(ctx.get("cross_border_countries") or [])
        if countries:
            flags.append("Special or children's personal information goes outside South Africa (%s). Check whether each "
                         "recipient country provides an adequate level of protection. If not, prior authorisation is "
                         "needed (s57(1)(d)). The Regulator has not published an adequacy list." % ", ".join(countries))
    if ctx.get("automated_decisions"):
        flags.append("Automated decisions: confirm the s71(2) exception and the s71(3) measures.")
    if ctx.get("cross_border_consent"):
        flags.append("Consent as the s72 ground: withdrawal breaks the transfer. Consider a binding agreement (s72(1)(a)).")
    if "phone" in ctx.get("marketing_channels", []):
        flags.append("Phone marketing: the Regulator treats calls as s69 electronic communication. The position is disputed (VERIFY).")
    for op in ctx.get("operators") or []:
        if (op.get("agreement") or "unknown") != "signed":
            flags.append("Operator %s: agreement status is '%s'. s21 requires a written contract." % (op.get("name"), op.get("agreement") or "unknown"))
    return flags


def build_readme(ctx: Dict[str, Any], files: Dict[str, str], questions: List[Dict[str, Any]],
                 unanswered: List[str], defaults_used: List[str]) -> str:
    prompts = {q["id"]: q["prompt"] for q in questions}
    todos: List[str] = []
    for content in files.values():
        for m in TODO_RE.finditer(content):
            if m.group(1) not in todos:
                todos.append(m.group(1))
    for qid in unanswered:
        if qid not in todos:
            todos.append(qid)

    lines = [
        DISCLAIMER_LINE,
        "",
        "# POPIA compliance pack: %s" % (ctx.get("display_name") or "[[TODO: company_legal_name]]"),
        "",
        "Generated by `scripts/popia_pack.py` version %s. Effective date in answers: %s."
        % (__version__, ctx.get("effective_date") or "not set"),
        "",
        "Every file here is a **draft**. A person must review it, and a qualified South African "
        "privacy attorney should review it, before it is published or relied on.",
        "",
        "## What was generated",
        "",
        "| File | What it is | Human review needed |",
        "|---|---|---|",
    ]
    desc = {
        "privacy-notice.md": "Privacy notice covering every s18(1) item",
        "cookie-notice.md": "Cookie notice",
        "consent-wording.md": "Consent and notice wording for the features you use",
        "paia-manual.md": "PAIA s51 manual for a private body",
        "dsar-runbook.md": "Data subject request runbook (s23, s24, s11(3))",
        "breach-notice-data-subject.md": "s22 notices to data subjects (email, SMS, website)",
        "ropa.csv": "Record of processing activities (s17)",
        "operator-register.csv": "Operator register (s20, s21, s72)",
        "retention-schedule.csv": "Retention schedule (s14)",
    }
    for name in PACK_FILES[1:]:
        lines.append("| %s | %s | %s |" % (name, desc[name], REVIEW_NOTES[name]))

    lines += ["", "## Unanswered questions (TODO)", ""]
    if todos:
        lines.append("These appear as `[[TODO: id]]` in the files. Answer them and generate the pack again.")
        lines.append("")
        lines.append("| Question id | Question |")
        lines.append("|---|---|")
        for t in todos:
            base = t.split(".")[0]
            lines.append("| %s | %s |" % (t, prompts.get(base, prompts.get(t, "Missing value"))))
    else:
        lines.append("None. Every required question has an answer.")

    lines += ["", "## Items to verify (VERIFY)", ""]
    lines.append("These need a human to confirm a fact against a primary source or your own systems.")
    lines.append("")
    lines.append("- **Information Regulator contact details** are a placeholder in every file that needs them. "
                 "Copy the current details from https://inforegulator.org.za. This tool never supplies them.")
    vitems = _verify_items(files)
    for name in PACK_FILES[1:]:
        hits = vitems.get(name)
        if not hits:
            continue
        lines.append("- **%s**: %d item(s)" % (name, len(hits)))
        for ln, text in hits[:8]:
            lines.append("  - line %d: %s" % (ln, text))
        if len(hits) > 8:
            lines.append("  - and %d more" % (len(hits) - 8))

    lines += ["", "## Flags for attorney review", ""]
    flags = review_flags(ctx)
    if flags:
        lines.append("Your answers include processing that SKILL.md says needs a human decision or a lawyer.")
        lines.append("")
        for f in flags:
            lines.append("- " + f)
    else:
        lines.append("None raised by your answers. Attorney review of the whole pack is still recommended.")

    lines += ["", "## Defaults applied", ""]
    if defaults_used:
        lines.append("You did not answer these, so the questionnaire default was used. Check they are right.")
        lines.append("")
        for d in defaults_used:
            lines.append("- %s: %s" % (d, _fmt(ctx.get(d))))
    else:
        lines.append("None.")

    lines += [
        "",
        "## Before you publish",
        "",
        "- [ ] Every TODO answered and every VERIFY item resolved",
        "- [ ] Information Officer registered on the eServices portal (s55(2))",
        "- [ ] Privacy notice linked in the footer and next to every form that collects personal information",
        "- [ ] Consent wording in the product matches consent-wording.md, and consent events are stored",
        "- [ ] Operator agreements in place for every row in operator-register.csv",
        "- [ ] Retention jobs implement retention-schedule.csv",
        "- [ ] Attorney review completed",
        "",
        "## Disclaimer",
        "",
        "This pack is engineering and compliance guidance, not legal advice. It is generated from your "
        "answers and does not check that they are true. See DISCLAIMER.md in " + REPO_URL + ".",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Generate
# --------------------------------------------------------------------------

def _tidy(text: str) -> str:
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def generate(answers: Dict[str, Any], out_dir: Optional[str] = None,
             templates_dir: Optional[str] = None) -> Dict[str, str]:
    """Generate the pack. Returns {filename: content}; writes files if out_dir is given."""
    tdir = Path(templates_dir) if templates_dir else TEMPLATES_DIR
    questions = load_questions(str(tdir / "pack-questionnaire.json"))
    merged, defaults_used = _apply_defaults(answers, questions)
    unanswered = _unanswered(merged, questions)
    ctx = build_context(answers, questions)

    files: Dict[str, str] = {}
    for out_name, tpl_name in TEMPLATE_MAP.items():
        with open(tdir / tpl_name, encoding="utf-8") as fh:
            src = fh.read()
        text, _missing = render_template(src, ctx)
        files[out_name] = _tidy(text)
    files["ropa.csv"] = build_ropa(ctx)
    files["operator-register.csv"] = build_operator_register(ctx)
    files["retention-schedule.csv"] = build_retention_schedule(ctx, tdir)
    files["README.md"] = build_readme(ctx, files, questions, unanswered, defaults_used)

    ordered = {name: files[name] for name in PACK_FILES}
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        for name, content in ordered.items():
            with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="") as fh:
                fh.write(content)
    return ordered


# --------------------------------------------------------------------------
# Example answers
# --------------------------------------------------------------------------

def example_answers() -> Dict[str, Any]:
    """Answers for a fictional company. All details are made up."""
    return {
        "company_legal_name": "Example Lodge (Pty) Ltd",
        "company_reg_number": "2000/000000/07 (fictional)",
        "trading_name": "Example Lodge",
        "physical_address": "1 Example Road, Example Town, 0000, South Africa (fictional)",
        "website": "https://examplelodge.example",
        "head_of_body": "Thandi Example (Managing Director)",
        "io_name": "Thandi Example",
        "io_email": "privacy@examplelodge.example",
        "io_phone": "+27 00 000 0000 (fictional)",
        "dios": [{"name": "Pieter Voorbeeld", "email": "dio@examplelodge.example"}],
        "products_services": "guest accommodation, online bookings and guided tours",
        "data_subject_types": ["Customers", "Website visitors", "Leads and enquirers", "Suppliers"],
        "data_categories": [
            "Identity details (name, title)",
            "Contact details (email, phone, address)",
            "Payment and transaction records",
            "Device and online identifiers (IP address, cookie IDs)",
            "Communications and support messages",
        ],
        "other_sources": "online travel agents that send us your booking",
        "special_pi": ["health"],
        "special_pi_purpose": "cater for dietary needs and allergies you tell us about",
        "special_pi_ground": "consent",
        "children": False,
        "purposes": [
            {"purpose": "Take and manage bookings", "data": "Name, contact details, stay dates, payment records", "lawful_basis": "contract"},
            {"purpose": "Keep tax and accounting records", "data": "Invoices and payment records", "lawful_basis": "legal_obligation"},
            {"purpose": "Send offers by email", "data": "Name and email", "lawful_basis": "consent"},
            {"purpose": "Keep the website secure", "data": "IP address, device information", "lawful_basis": "legitimate_interest"},
        ],
        "collection_mandatory_info": "Your name, email, phone number and payment details are mandatory to make a booking. Dietary and allergy information is voluntary.",
        "consequences_of_not_providing": "We cannot confirm a booking without the mandatory details. If you do not tell us about allergies, we cannot cater for them.",
        "laws_requiring_collection": "Tax law requires us to keep invoices and payment records.",
        "marketing_channels": ["email"],
        "marketing_products": "accommodation specials and tours",
        "marketing_existing_customer_exception": True,
        "necessary_cookies": [
            {"name": "session_id", "provider": "Example Lodge", "purpose": "Keeps you signed in during a booking", "duration": "Session"},
        ],
        "analytics_tools": [
            {"name": "Plausible Analytics", "country": "European Union", "purpose": "Count visits and popular pages", "duration": "No cookies set"},
        ],
        "marketing_tools": [],
        "operators": [
            {"name": "Supabase", "service": "Database hosting", "data": "Booking and guest records", "country": "Ireland", "agreement": "signed", "s72_basis": "s72(1)(a) binding agreement"},
            {"name": "PayFast", "service": "Card payments", "data": "Name, email, payment details", "country": "South Africa", "agreement": "signed"},
            {"name": "Brevo", "service": "Email delivery and newsletters", "data": "Name and email", "country": "France", "agreement": "signed", "s72_basis": "s72(1)(a) binding agreement"},
        ],
        "hosting_region": "Supabase eu-west-1 (Ireland)",
        "cross_border_countries": ["Ireland", "France"],
        "cross_border_consent": False,
        "ai_features": False,
        "automated_decisions": False,
        "call_recording": False,
        "data_sets": [
            {"name": "bookings", "fields": "name;email;phone;stay_dates;amount", "data_subjects": "Customers", "purpose": "Take and manage bookings", "lawful_basis": "contract", "special_pi": False, "children": False, "retention": "5 years", "retention_trigger": "Date of tax return for the stay (VERIFY)", "operators": "Supabase;PayFast", "collection_point": "Booking form", "owner": "Operations manager"},
            {"name": "guest_dietary_notes", "fields": "allergies;dietary_needs", "data_subjects": "Customers", "purpose": "Cater for dietary needs", "lawful_basis": "consent", "special_pi": True, "children": False, "retention": "30 days", "retention_trigger": "Check-out date", "operators": "Supabase", "collection_point": "Booking form (optional section)", "owner": "Operations manager"},
            {"name": "newsletter_subscribers", "fields": "name;email", "data_subjects": "Customers and leads", "purpose": "Send offers by email", "lawful_basis": "consent", "special_pi": False, "children": False, "retention": "Until consent is withdrawn", "retention_trigger": "Withdrawal of consent", "operators": "Brevo", "collection_point": "Newsletter sign-up", "owner": "Marketing lead"},
        ],
        "security_summary": "We encrypt data in transit and at rest, restrict access to staff who need it, use multi-factor authentication on admin accounts, keep backups, and train staff on privacy.",
        "dsar_email": "privacy@examplelodge.example",
        "dsar_sla_days": 30,
        "dsar_backup_owner": "Pieter Voorbeeld",
        "dsar_log_location": "Privacy requests register (shared drive, restricted)",
        "records_automatically_available": "Our privacy notice, cookie notice and brochures on our website.",
        "effective_date": "2026-11-01",
        "notice_version": "1.0",
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _print_questions(questions: List[Dict[str, Any]]) -> None:
    section = None
    for q in questions:
        if q.get("section") != section:
            section = q.get("section")
            print("\n## %s" % section)
        req = "required" if q.get("required") else "optional"
        cond = " (if %s)" % q["ask_if"] if q.get("ask_if") else ""
        print("- %s [%s, %s%s]: %s" % (q["id"], q.get("type"), req, cond, q["prompt"]))
        if q.get("options"):
            print("    options: %s" % ", ".join(q["options"]))
        if q.get("item_fields"):
            print("    fields: %s" % ", ".join(f["id"] for f in q["item_fields"]))


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Generate a draft POPIA compliance pack. Not legal advice.")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--answers", help="answers JSON file")
    mode.add_argument("--interactive", action="store_true", help="ask questions on the command line")
    mode.add_argument("--print-questions", action="store_true", help="list the questionnaire")
    mode.add_argument("--example", nargs="?", const="example-answers.json", metavar="PATH",
                      help="write example answers for a fictional company (default: example-answers.json)")
    ap.add_argument("--out", default="./compliance-pack", help="output folder (default: ./compliance-pack)")
    ap.add_argument("--save-answers", metavar="PATH", help="with --interactive, save answers to this file")
    ap.add_argument("--templates", help="templates folder (default: repo templates/)")
    ap.add_argument("--version", action="version", version="popia_pack " + __version__)
    args = ap.parse_args(argv)

    qpath = str(Path(args.templates) / "pack-questionnaire.json") if args.templates else None
    questions = load_questions(qpath)

    if args.print_questions:
        _print_questions(questions)
        return 0
    if args.example:
        with open(args.example, "w", encoding="utf-8") as fh:
            json.dump(example_answers(), fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        print("Wrote example answers to %s" % args.example)
        print("Next: run the pack command again with --answers %s --out %s" % (args.example, args.out))
        return 0
    if args.interactive:
        answers = ask_interactive(questions)
        save = args.save_answers or os.path.join(args.out, "answers.json")
        os.makedirs(os.path.dirname(os.path.abspath(save)), exist_ok=True)
        with open(save, "w", encoding="utf-8") as fh:
            json.dump(answers, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        print("\nSaved answers to %s" % save)
    else:
        with open(args.answers, encoding="utf-8") as fh:
            answers = json.load(fh)

    files = generate(answers, args.out, args.templates)
    todos = sorted({m for c in files.values() for m in TODO_RE.findall(c)})
    print("Wrote %d files to %s" % (len(files), args.out))
    if todos:
        print("%d unanswered item(s). See README.md." % len(todos))
    print("Draft only. Not legal advice. Review README.md before use.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
