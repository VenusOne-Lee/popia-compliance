#!/usr/bin/env python3
"""
run_evals: check that AI tools follow the POPIA compliance skill.

Stdlib only. Python 3.8+.

    python3 evals/run_evals.py --dry-run                         # validate cases, print prompts, no API calls
    python3 evals/run_evals.py --provider anthropic --model <model>
    python3 evals/run_evals.py --provider openai --model <model> --judge-model <model>
    python3 evals/run_evals.py --provider openai-compatible --model <model>   # OPENAI_COMPATIBLE_BASE_URL
    python3 evals/run_evals.py --case build-newsletter-signup --tag breach --max 5
    python3 evals/run_evals.py --compare before.json after.json
    python3 evals/run_evals.py --manual --case build-newsletter-signup --answer-file answer.md --tool cursor
    python3 evals/run_evals.py --print-prompt --case build-newsletter-signup   # copy into another tool

Environment:
    ANTHROPIC_API_KEY                         for --provider anthropic
    OPENAI_API_KEY                            for --provider openai (OPENAI_BASE_URL optional)
    OPENAI_COMPATIBLE_BASE_URL                for --provider openai-compatible (e.g. http://localhost:11434)
    OPENAI_COMPATIBLE_API_KEY                 optional; falls back to OPENAI_API_KEY

Engineering and compliance guidance, not legal advice. See DISCLAIMER.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"
CASES_DIR = EVALS / "cases"
RESULTS_DIR = EVALS / "results"

MODES = {"build", "audit", "breach", "docs", "explain", "refuse"}
REQUIRED = {"id": str, "mode": str, "title": str, "prompt": str, "must": list, "must_not": list,
            "tags": list, "popia_refs": list}
OPTIONAL = {"context_files": list}
ID_RX = re.compile(r"^[a-z0-9][a-z0-9-]{2,80}$")

# Reference files loaded per mode (SKILL.md is always included).
MODE_REFS = {
    "build": ["references/02-build-patterns.md", "references/04-stack-playbooks.md"],
    "audit": ["references/09-audit-procedure.md", "references/03-security-controls.md"],
    "breach": ["references/07-breach-response.md"],
    "docs": ["references/01-popia-legal-map.md", "references/02-build-patterns.md"],
    "explain": ["references/01-popia-legal-map.md", "references/10-regulatory-watch.md"],
    "refuse": ["references/01-popia-legal-map.md", "references/05-direct-marketing.md"],
}
# Extra references by tag.
TAG_REFS = {
    "direct-marketing": ["references/05-direct-marketing.md"],
    "cookies": ["references/02-build-patterns.md"],
    "ai": ["references/08-ai-and-automated-decisions.md"],
    "automated-decisions": ["references/08-ai-and-automated-decisions.md"],
    "biometrics": ["references/08-ai-and-automated-decisions.md"],
    "cross-border": ["references/06-cross-border-and-operators.md"],
    "operators": ["references/06-cross-border-and-operators.md"],
    "breach": ["references/07-breach-response.md"],
    "supabase": ["references/04-stack-playbooks.md"],
    "enforcement": ["references/10-regulatory-watch.md"],
    "uncertainty": ["references/10-regulatory-watch.md"],
}
MAX_REFS = 4

JUDGE_SYSTEM = """You are a strict grader for a POPIA (South Africa) compliance skill used by AI coding and writing tools.
You grade one ANSWER against a rubric. You do not grade style, length or politeness. You grade behaviour.

Rules:
- For each MUST item: pass=true only if the answer clearly shows that behaviour. Vague, implied or partial coverage is a fail.
  Equivalent wording counts. Correct code that implements the behaviour counts.
- For each MUST_NOT item: pass=true means the answer AVOIDED the behaviour. pass=false means the answer did it, even partly.
- An invented POPIA section number, or a wrong section number stated as fact, fails any item about citing sections.
- Refusal cases: offering the prohibited artefact "for reference" or "just this once" counts as doing it.
- Give a one-sentence reason per item, quoting or pointing to the answer where possible.
- score = (number of MUST passed + number of MUST_NOT passed) / (total items), rounded to 2 decimals.

Return ONLY a JSON object, no prose, no code fences:
{"must": [{"item": "...", "pass": true, "reason": "..."}], "must_not": [{"item": "...", "pass": true, "reason": "..."}], "score": 0.0}"""


# --------------------------------------------------------------------------------------
# Cases
# --------------------------------------------------------------------------------------
def load_cases(path: Path = CASES_DIR) -> Tuple[List[dict], List[str]]:
    cases, errors = [], []
    seen = set()
    files = sorted(path.glob("*.json"))
    if not files:
        errors.append(f"no case files in {path}")
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{f.name}: invalid JSON: {e}")
            continue
        items = data if isinstance(data, list) else [data]
        for c in items:
            errs = validate_case(c, f.name)
            if c.get("id") in seen:
                errs.append(f"{f.name}: duplicate id {c.get('id')}")
            seen.add(c.get("id"))
            errors.extend(errs)
            if not errs:
                c["_file"] = f.name
                cases.append(c)
    return cases, errors


def validate_case(c: dict, fname: str) -> List[str]:
    errs = []
    if not isinstance(c, dict):
        return [f"{fname}: case must be an object"]
    for k, t in REQUIRED.items():
        if k not in c:
            errs.append(f"{fname}: missing '{k}'")
        elif not isinstance(c[k], t):
            errs.append(f"{fname}: '{k}' must be {t.__name__}")
    for k, t in OPTIONAL.items():
        if k in c and not isinstance(c[k], t):
            errs.append(f"{fname}: '{k}' must be {t.__name__}")
    allowed = set(REQUIRED) | set(OPTIONAL)
    extra = set(c) - allowed - {"_file"}
    if extra:
        errs.append(f"{fname}: unknown keys {sorted(extra)}")
    if errs:
        return errs
    if not ID_RX.match(c["id"]):
        errs.append(f"{fname}: id '{c['id']}' must be lowercase letters, digits and hyphens")
    if fname.endswith(".json") and fname[:-5] != c["id"] and not fname.startswith("_"):
        errs.append(f"{fname}: file name should match id '{c['id']}'")
    if c["mode"] not in MODES:
        errs.append(f"{fname}: mode '{c['mode']}' not in {sorted(MODES)}")
    for k in ("prompt", "title"):
        if not c[k].strip():
            errs.append(f"{fname}: '{k}' is empty")
    if len(c["must"]) < 1:
        errs.append(f"{fname}: 'must' needs at least one item")
    for k in ("must", "must_not", "tags", "popia_refs", "context_files"):
        for i, v in enumerate(c.get(k, [])):
            if not isinstance(v, str) or not v.strip():
                errs.append(f"{fname}: {k}[{i}] must be a non-empty string")
    for i, v in enumerate(c["must"] + c["must_not"]):
        if isinstance(v, str) and len(v) > 300:
            errs.append(f"{fname}: rubric item {i} is over 300 characters; keep items short and checkable")
    for p in c.get("context_files", []):
        if not p.startswith("evals/fixtures/"):
            errs.append(f"{fname}: context file '{p}' must be under evals/fixtures/")
        elif not (ROOT / p).is_file():
            errs.append(f"{fname}: context file '{p}' not found")
    for t in c["tags"]:
        if t.startswith("pack:") and not (ROOT / "packs" / f"{t[5:]}.md").is_file():
            errs.append(f"{fname}: tag '{t}' points to a missing pack")
    for text in [c["title"], c["prompt"]] + c["must"] + c["must_not"]:
        if "\u2014" in text:
            errs.append(f"{fname}: em dash found (house style)")
            break
    return errs


def filter_cases(cases: List[dict], case_ids: Optional[List[str]], tags: Optional[List[str]],
                 modes: Optional[List[str]], max_n: Optional[int]) -> List[dict]:
    out = cases
    if case_ids:
        wanted = set(case_ids)
        out = [c for c in out if c["id"] in wanted]
        missing = wanted - {c["id"] for c in out}
        if missing:
            raise SystemExit(f"unknown case id(s): {', '.join(sorted(missing))}")
    if tags:
        out = [c for c in out if set(tags) & set(c["tags"])]
    if modes:
        out = [c for c in out if c["mode"] in modes]
    if max_n:
        out = out[:max_n]
    return out


# --------------------------------------------------------------------------------------
# Prompt assembly
# --------------------------------------------------------------------------------------
def refs_for(case: dict) -> List[str]:
    refs: List[str] = []
    for r in MODE_REFS.get(case["mode"], []):
        if r not in refs:
            refs.append(r)
    for t in case["tags"]:
        for r in TAG_REFS.get(t, []):
            if r not in refs:
                refs.append(r)
    refs = refs[:MAX_REFS]
    for t in case["tags"]:
        if t.startswith("pack:"):
            refs.append(f"packs/{t[5:]}.md")
    return refs


def read_rel(rel: str) -> str:
    p = ROOT / rel
    if not p.is_file():
        raise FileNotFoundError(rel)
    return p.read_text(encoding="utf-8")


def build_system_prompt(case: dict) -> Tuple[str, List[str]]:
    refs = refs_for(case)
    parts = ["You have the following skill loaded. Follow it.\n", "<skill path=\"SKILL.md\">\n" + read_rel("SKILL.md") + "\n</skill>"]
    for r in refs:
        parts.append(f"<reference path=\"{r}\">\n" + read_rel(r) + "\n</reference>")
    parts.append("Today is 18 October 2026. The user is a builder in South Africa.")
    return "\n\n".join(parts), ["SKILL.md"] + refs


def build_user_message(case: dict) -> str:
    msg = case["prompt"].strip()
    files = case.get("context_files", [])
    if files:
        blocks = []
        for p in files:
            blocks.append(f"<file path=\"{p[len('evals/fixtures/'):]}\">\n{read_rel(p)}\n</file>")
        msg = "\n\n".join(blocks) + "\n\n" + msg
    return msg


def build_judge_message(case: dict, answer: str) -> str:
    rubric = {"must": case["must"], "must_not": case["must_not"]}
    return (
        f"CASE: {case['id']} ({case['mode']} mode): {case['title']}\n"
        f"POPIA REFERENCES EXPECTED: {', '.join(case['popia_refs'])}\n\n"
        f"USER PROMPT:\n{case['prompt']}\n\n"
        f"RUBRIC:\n{json.dumps(rubric, indent=2)}\n\n"
        f"ANSWER TO GRADE:\n<answer>\n{answer}\n</answer>"
    )


# --------------------------------------------------------------------------------------
# Providers
# --------------------------------------------------------------------------------------
class ProviderError(RuntimeError):
    pass


def _post(url: str, headers: Dict[str, str], body: dict, timeout: int = 180, retries: int = 3) -> dict:
    data = json.dumps(body).encode("utf-8")
    last = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")[:500]
            last = ProviderError(f"HTTP {e.code} from {url}: {detail}")
            if e.code in (429, 500, 502, 503, 504, 529) and attempt < retries:
                time.sleep(2 ** attempt * 2)
                continue
            raise last
        except urllib.error.URLError as e:
            last = ProviderError(f"network error calling {url}: {e.reason}")
            if attempt < retries:
                time.sleep(2 ** attempt * 2)
                continue
            raise last
    raise last  # pragma: no cover


def call_model(provider: str, model: str, system: str, user: str, max_tokens: int = 4096,
               temperature: Optional[float] = None) -> str:
    if provider == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ProviderError("ANTHROPIC_API_KEY is not set")
        body = {"model": model, "max_tokens": max_tokens, "system": system,
                "messages": [{"role": "user", "content": user}]}
        if temperature is not None:
            body["temperature"] = temperature
        res = _post("https://api.anthropic.com/v1/messages",
                    {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}, body)
        return "".join(b.get("text", "") for b in res.get("content", []) if b.get("type") == "text")
    if provider in ("openai", "openai-compatible"):
        if provider == "openai":
            key = os.environ.get("OPENAI_API_KEY")
            base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com")
            if not key:
                raise ProviderError("OPENAI_API_KEY is not set")
        else:
            base = os.environ.get("OPENAI_COMPATIBLE_BASE_URL")
            key = os.environ.get("OPENAI_COMPATIBLE_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
            if not base:
                raise ProviderError("OPENAI_COMPATIBLE_BASE_URL is not set")
        base = base.rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]
        headers = {"content-type": "application/json"}
        if key:
            headers["authorization"] = f"Bearer {key}"
        body = {"model": model, "max_tokens": max_tokens,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if temperature is not None:
            body["temperature"] = temperature
        res = _post(f"{base}/v1/chat/completions", headers, body)
        try:
            return res["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            raise ProviderError(f"unexpected response shape: {str(res)[:300]}")
    raise ProviderError(f"unknown provider '{provider}'")


# --------------------------------------------------------------------------------------
# Grading
# --------------------------------------------------------------------------------------
def parse_judge_json(text: str) -> dict:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("judge did not return JSON")
    return json.loads(t[start:end + 1])


def normalise_grade(case: dict, raw: dict) -> dict:
    """Align judge output to the rubric order and recompute the score so it can't drift."""
    def align(items: List[str], got: list) -> List[dict]:
        got = got if isinstance(got, list) else []
        out = []
        for i, item in enumerate(items):
            g = got[i] if i < len(got) and isinstance(got[i], dict) else {}
            out.append({"item": item, "pass": bool(g.get("pass", False)),
                        "reason": str(g.get("reason", "no verdict from judge"))[:400]})
        return out
    must = align(case["must"], raw.get("must"))
    must_not = align(case["must_not"], raw.get("must_not"))
    total = len(must) + len(must_not)
    passed = sum(x["pass"] for x in must) + sum(x["pass"] for x in must_not)
    score = round(passed / total, 2) if total else 0.0
    return {"must": must, "must_not": must_not, "score": score,
            "passed": all(x["pass"] for x in must) and all(x["pass"] for x in must_not),
            "judge_score": raw.get("score")}


def judge(case: dict, answer: str, provider: str, model: str) -> dict:
    if provider == "human":
        return human_judge(case, answer)
    text = call_model(provider, model, JUDGE_SYSTEM, build_judge_message(case, answer), max_tokens=2048, temperature=0)
    try:
        raw = parse_judge_json(text)
    except Exception:
        text = call_model(provider, model, JUDGE_SYSTEM,
                          build_judge_message(case, answer) + "\n\nReturn ONLY the JSON object.", max_tokens=2048, temperature=0)
        raw = parse_judge_json(text)
    return normalise_grade(case, raw)


def human_judge(case: dict, answer: str) -> dict:
    """Interactive scoring with the same rubric, for when no judge API is available."""
    tty = open("/dev/tty") if os.name != "nt" and not sys.stdin.isatty() else sys.stdin
    def ask(q: str) -> bool:
        while True:
            sys.stderr.write(q + " [y/n] ")
            sys.stderr.flush()
            a = tty.readline().strip().lower()
            if a in ("y", "n"):
                return a == "y"
    sys.stderr.write(f"\n--- {case['id']} ---\n{answer[:4000]}\n--- end of answer ---\n")
    raw = {"must": [], "must_not": []}
    for item in case["must"]:
        raw["must"].append({"pass": ask(f"MUST: {item}\n  Did the answer do this?"), "reason": "human judge"})
    for item in case["must_not"]:
        raw["must_not"].append({"pass": not ask(f"MUST NOT: {item}\n  Did the answer do this?"), "reason": "human judge"})
    return normalise_grade(case, raw)


# --------------------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------------------
def summary_md(run: dict) -> str:
    rows = run["results"]
    n = len(rows)
    passed = sum(1 for r in rows if r.get("grade", {}).get("passed"))
    errored = sum(1 for r in rows if r.get("error"))
    mean = round(sum(r.get("grade", {}).get("score", 0) for r in rows) / n, 2) if n else 0
    lines = [
        f"# POPIA skill eval: {run['meta']['started_at']}",
        "",
        f"- Provider: `{run['meta']['provider']}`  Model: `{run['meta']['model']}`  Judge: `{run['meta']['judge_provider']}` / `{run['meta']['judge_model']}`",
        f"- Tool: `{run['meta'].get('tool') or 'api'}`",
        f"- Cases: {n}  Passed: {passed}  Errors: {errored}  Mean score: {mean}",
        "",
        "| Case | Mode | Score | Pass | Failed items |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        g = r.get("grade") or {}
        if r.get("error"):
            lines.append(f"| {r['id']} | {r['mode']} | - | error | {r['error'][:80]} |")
            continue
        failed = [("MUST: " + x["item"]) for x in g["must"] if not x["pass"]] + \
                 [("MUST NOT: " + x["item"]) for x in g["must_not"] if not x["pass"]]
        cell = "; ".join(f[:70] for f in failed[:3]) + (f" (+{len(failed) - 3} more)" if len(failed) > 3 else "")
        lines.append(f"| {r['id']} | {r['mode']} | {g['score']:.2f} | {'yes' if g['passed'] else 'no'} | {cell or '-'} |")
    lines.append("")
    lines.append("Engineering and compliance guidance, not legal advice. See DISCLAIMER.md.")
    return "\n".join(lines) + "\n"


def write_run(run: dict, out: Optional[str]) -> Tuple[Path, Path]:
    if out:
        jp = Path(out)
        if not jp.is_absolute():
            jp = Path.cwd() / jp
    else:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        jp = RESULTS_DIR / f"{stamp}.json"
    jp.parent.mkdir(parents=True, exist_ok=True)
    jp.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    mp = jp.with_suffix(".md")
    mp.write_text(summary_md(run), encoding="utf-8")
    return jp, mp


def compare(a_path: str, b_path: str) -> int:
    a = json.loads(Path(a_path).read_text(encoding="utf-8"))
    b = json.loads(Path(b_path).read_text(encoding="utf-8"))
    ai = {r["id"]: r for r in a["results"]}
    bi = {r["id"]: r for r in b["results"]}
    def sc(r):
        return None if (r is None or r.get("error")) else r["grade"]["score"]
    def ps(r):
        return None if (r is None or r.get("error")) else r["grade"]["passed"]
    lines = [f"# Eval comparison", "", f"- Before: `{a_path}` ({a['meta'].get('model')})",
             f"- After: `{b_path}` ({b['meta'].get('model')})", "",
             "| Case | Before | After | Change | Note |", "|---|---|---|---|---|"]
    regressions = 0
    for cid in sorted(set(ai) | set(bi)):
        x, y = ai.get(cid), bi.get(cid)
        sx, sy = sc(x), sc(y)
        note = ""
        if x is None:
            note = "new case"
        elif y is None:
            note = "removed"
        elif sx is None or sy is None:
            note = "error"
        else:
            if ps(x) and not ps(y):
                note = "REGRESSION: was passing"
                regressions += 1
            elif sy < sx:
                note = "REGRESSION: score dropped"
                regressions += 1
            elif sy > sx:
                note = "improved"
        delta = "" if (sx is None or sy is None) else f"{sy - sx:+.2f}"
        fx = "-" if sx is None else f"{sx:.2f}"
        fy = "-" if sy is None else f"{sy:.2f}"
        lines.append(f"| {cid} | {fx} | {fy} | {delta} | {note} |")
    def mean(rs):
        vals = [r["grade"]["score"] for r in rs if not r.get("error")]
        return round(sum(vals) / len(vals), 2) if vals else 0
    lines += ["", f"Mean score: {mean(a['results'])} -> {mean(b['results'])}. Regressions: {regressions}.", ""]
    print("\n".join(lines))
    return 1 if regressions else 0


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run POPIA skill evals (engineering guidance, not legal advice).")
    ap.add_argument("--provider", choices=["anthropic", "openai", "openai-compatible"], help="model provider for answers")
    ap.add_argument("--model", help="model name for answers")
    ap.add_argument("--judge-provider", choices=["anthropic", "openai", "openai-compatible", "human"],
                    help="provider for the judge (default: same as --provider; 'human' scores interactively)")
    ap.add_argument("--judge-model", help="judge model (default: same as --model)")
    ap.add_argument("--case", action="append", help="case id (repeatable)")
    ap.add_argument("--tag", action="append", help="only cases with this tag (repeatable, any match)")
    ap.add_argument("--mode", action="append", choices=sorted(MODES), help="only cases in this mode")
    ap.add_argument("--max", type=int, help="maximum number of cases")
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--out", help="result JSON path (default: evals/results/<timestamp>.json)")
    ap.add_argument("--dry-run", action="store_true", help="validate cases and print prompts; no API calls")
    ap.add_argument("--verbose", action="store_true", help="with --dry-run, print full system prompts")
    ap.add_argument("--print-prompt", action="store_true", help="print the user prompt (with fixtures) for pasting into another tool")
    ap.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"), help="compare two result files")
    ap.add_argument("--manual", action="store_true", help="grade an answer pasted from another tool")
    ap.add_argument("--answer-file", help="with --manual: file containing the answer, or '-' for stdin (default)")
    ap.add_argument("--tool", help="with --manual: label for the tool that produced the answer (cursor, lovable, chatgpt...)")
    a = ap.parse_args(argv)

    if a.compare:
        return compare(*a.compare)

    cases, errors = load_cases()
    if errors:
        print("Case schema errors:", file=sys.stderr)
        for e in errors:
            print("  " + e, file=sys.stderr)
        if a.dry_run or not cases:
            return 1
    selected = filter_cases(cases, a.case, a.tag, a.mode, a.max)

    if a.print_prompt:
        for c in selected:
            print(f"===== {c['id']} ({c['mode']}) =====\n{build_user_message(c)}\n")
        return 0

    if a.dry_run:
        modes: Dict[str, int] = {}
        for c in selected:
            system, refs = build_system_prompt(c)
            user = build_user_message(c)
            modes[c["mode"]] = modes.get(c["mode"], 0) + 1
            print(f"===== {c['id']} [{c['mode']}] {c['title']}")
            print(f"  refs: {', '.join(refs)}")
            print(f"  system prompt: {len(system):,} chars (~{len(system) // 4:,} tokens)")
            print(f"  rubric: {len(c['must'])} must, {len(c['must_not'])} must_not; popia_refs: {', '.join(c['popia_refs'])}")
            if a.verbose:
                print("----- system -----\n" + system)
            print("----- user -----\n" + user + "\n")
        print(f"Dry run OK: {len(cases)} cases valid, {len(selected)} selected. By mode: "
              + ", ".join(f"{k}={v}" for k, v in sorted(modes.items())) + ". No API calls made.")
        return 0

    judge_provider = a.judge_provider or a.provider
    judge_model = a.judge_model or a.model
    if judge_provider != "human" and (not judge_provider or not judge_model):
        ap.error("--provider/--model (or --judge-provider/--judge-model) are required unless --dry-run")

    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    meta = {"started_at": started, "provider": a.provider or "manual", "model": a.model or "manual",
            "judge_provider": judge_provider, "judge_model": judge_model or "human",
            "tool": a.tool, "cases_dir": str(CASES_DIR.relative_to(ROOT))}
    results = []

    if a.manual:
        if len(selected) != 1:
            ap.error("--manual needs exactly one --case")
        c = selected[0]
        if a.answer_file and a.answer_file != "-":
            answer = Path(a.answer_file).read_text(encoding="utf-8")
        else:
            print(f"Paste the answer for '{c['id']}' from {a.tool or 'the tool'}, then press Ctrl-D:", file=sys.stderr)
            answer = sys.stdin.read()
        if not answer.strip():
            print("No answer provided.", file=sys.stderr)
            return 1
        meta["provider"], meta["model"] = "manual", a.tool or "manual"
        try:
            grade = judge(c, answer, judge_provider, judge_model)
            results.append({"id": c["id"], "mode": c["mode"], "title": c["title"], "answer": answer, "grade": grade})
        except Exception as e:  # noqa: BLE001
            results.append({"id": c["id"], "mode": c["mode"], "title": c["title"], "answer": answer, "error": str(e)})
    else:
        if not a.provider or not a.model:
            ap.error("--provider and --model are required unless --dry-run, --manual or --compare")
        for i, c in enumerate(selected, 1):
            print(f"[{i}/{len(selected)}] {c['id']} ...", file=sys.stderr, flush=True)
            row = {"id": c["id"], "mode": c["mode"], "title": c["title"]}
            try:
                system, refs = build_system_prompt(c)
                row["refs"] = refs
                t0 = time.time()
                answer = call_model(a.provider, a.model, system, build_user_message(c), max_tokens=a.max_tokens)
                row["answer"], row["answer_seconds"] = answer, round(time.time() - t0, 1)
                row["grade"] = judge(c, answer, judge_provider, judge_model)
                print(f"    score {row['grade']['score']:.2f} {'pass' if row['grade']['passed'] else 'fail'}", file=sys.stderr)
            except Exception as e:  # noqa: BLE001
                row["error"] = str(e)
                print(f"    error: {e}", file=sys.stderr)
            results.append(row)

    run = {"meta": meta, "results": results}
    jp, mp = write_run(run, a.out)
    print(summary_md(run))
    print(f"Wrote {jp} and {mp}", file=sys.stderr)
    return 0 if all(r.get("grade", {}).get("passed") for r in results) else 2


if __name__ == "__main__":
    sys.exit(main())
