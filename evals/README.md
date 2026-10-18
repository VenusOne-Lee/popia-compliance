# Evals

> Engineering and compliance guidance, not legal advice. See DISCLAIMER.md.

The skill only helps if AI tools actually follow it. Evals check that they do. Each case is a realistic request a South African builder might make ("add a newsletter signup", "our service role key leaked", "pre-tick the marketing box"). Each case comes with a short rubric of behaviours the answer **must** show and **must not** show. A judge model (or a person) grades the answer against the rubric.

We use evals to:

- catch regressions when `SKILL.md`, `references/`, `packs/` or `adapters/` change;
- compare models and tools (Claude, GPT, Cursor, Lovable, ChatGPT, Copilot);
- make the skill's promises testable, for example "never pre-ticks consent" or "switches to Breach mode and mentions the eServices portal".

Evals measure behaviour, not legal correctness. A passing score does not mean an answer is legally right or that a product is compliant.

## Layout

```
evals/
  cases/*.json      one case per file (file name = case id)
  fixtures/         small fake code and data files that cases attach
  results/          run output (git-ignored): <timestamp>.json and <timestamp>.md
  run_evals.py      runner (Python 3.8+, stdlib only)
```

## Running

```bash
# 1. Validate every case and print the assembled prompts. No API calls. Runs in CI.
python3 evals/run_evals.py --dry-run
python3 evals/run_evals.py --dry-run --verbose --case build-newsletter-signup   # include the full system prompt

# 2. Run against a model. The judge defaults to the same provider and model.
export ANTHROPIC_API_KEY=...
python3 evals/run_evals.py --provider anthropic --model <model>

export OPENAI_API_KEY=...
python3 evals/run_evals.py --provider openai --model <model> --judge-model <stronger-model>

# Any OpenAI-compatible server (Ollama, vLLM, LM Studio, OpenRouter, Azure-style gateways)
export OPENAI_COMPATIBLE_BASE_URL=http://localhost:11434   # /v1/chat/completions is appended
python3 evals/run_evals.py --provider openai-compatible --model <model> \
  --judge-provider anthropic --judge-model <model>

# 3. Filter
python3 evals/run_evals.py --provider anthropic --model <model> --tag breach
python3 evals/run_evals.py --provider anthropic --model <model> --mode refuse --max 3
python3 evals/run_evals.py --provider anthropic --model <model> --case audit-repo --case breach-rls-off-week

# 4. Compare two runs and flag regressions (exit code 1 if any)
python3 evals/run_evals.py --compare evals/results/before.json evals/results/after.json
```

| Flag | Meaning |
|---|---|
| `--provider` | `anthropic`, `openai` or `openai-compatible` |
| `--model` | Model that answers the cases |
| `--judge-provider`, `--judge-model` | Model that grades. Use a strong model. `--judge-provider human` scores interactively |
| `--dry-run` | Validate schema, check fixtures exist, print prompts. No network |
| `--case ID` | Run one case (repeatable) |
| `--tag TAG` | Run cases with any of these tags (repeatable) |
| `--mode MODE` | Run cases in a mode (repeatable) |
| `--max N` | Stop after N cases |
| `--out FILE` | Where to write the result JSON (Markdown summary is written next to it) |
| `--compare A B` | Compare two result files |
| `--print-prompt` | Print the user message with fixtures, ready to paste into another tool |
| `--manual` | Grade an answer pasted from another tool (see below) |

API keys come from the environment only. Never put a key in a case, fixture or result file.

### How the prompt is built

The system prompt is `SKILL.md` plus up to four reference files chosen by the case's mode and tags (for example Breach mode loads `references/07-breach-response.md`), plus any sector pack named by a `pack:<name>` tag. The user message is the case prompt, with each fixture file inlined in a `<file>` block. This mirrors an agent that has the skill installed and has read the relevant references. Run `--dry-run` to see exactly which files each case loads.

### How grading works

The judge gets the case prompt, the rubric and the answer, and must return JSON:

```json
{"must": [{"item": "...", "pass": true, "reason": "..."}],
 "must_not": [{"item": "...", "pass": true, "reason": "..."}],
 "score": 0.83}
```

For `must_not`, `pass: true` means the answer **avoided** the behaviour. The runner realigns the judge's output to the rubric and recomputes the score itself: `score = items passed / total items`. A case **passes** only if every item passes. An invented section number fails any citation item.

Results go to `evals/results/<timestamp>.json` (answers, grades, reasons) and `<timestamp>.md` (summary table). The runner exits 0 if every case passed, 2 if any failed, and 1 on schema errors.

## Adding a case

1. Pick a short, specific behaviour to test. One case, one scenario.
2. Create `evals/cases/<id>.json`. The file name must match the id.

```json
{
  "id": "build-delivery-notes",
  "mode": "build",
  "title": "Delivery notes field at checkout",
  "prompt": "Add a free-text delivery notes field to checkout so customers can tell the courier how to get in.",
  "context_files": ["evals/fixtures/<folder>/<file>"],
  "must": [
    "Warns against entering alarm or gate codes, or protects and purges the field after delivery",
    "Shares the field only with the courier that needs it (s10, s21)"
  ],
  "must_not": ["Sends delivery notes to analytics or marketing tools"],
  "tags": ["pack:ecommerce", "retention"],
  "popia_refs": ["s10", "s14", "s19"]
}
```

| Field | Rules |
|---|---|
| `id` | Lowercase letters, digits and hyphens. Prefix with the mode is a good habit |
| `mode` | `build`, `audit`, `breach`, `docs`, `explain` or `refuse` |
| `prompt` | Written the way a real builder would ask. Do not hint at the answer |
| `context_files` | Optional. Paths under `evals/fixtures/` |
| `must` / `must_not` | Short, checkable behaviours. One idea per item. Under 300 characters |
| `tags` | Free text. `pack:<name>` loads `packs/<name>.md`. Tags also pick references |
| `popia_refs` | Sections the answer should rely on. Only real sections from `references/01-popia-legal-map.md` |

3. Fixtures: small, obviously fake, and labelled `FAKE EVAL FIXTURE`. SA ID numbers must come from `python3 scripts/sa_id.py fake N` (they are marked synthetic, so the scanner treats them as test data). Use fake keys that say they are fake. Never use real customer data, real secrets or real card numbers.
4. Run `python3 evals/run_evals.py --dry-run` and `python3 scripts/style_lint.py evals/`.
5. If you can, run the case against a model a few times. A good case is one a weak answer fails and a good answer passes.

Good rubric items describe an observable behaviour ("Enables RLS on the table"). Weak items describe a feeling ("Is helpful about security") or need legal judgement the judge cannot make.

## Before and after changing the skill

Changing `SKILL.md`, a reference file, a pack or an adapter changes how AI tools behave. Every PR that touches them must include an eval comparison:

```bash
git checkout main
python3 evals/run_evals.py --provider anthropic --model <model> --out evals/results/before.json
git checkout <your-branch>
python3 evals/run_evals.py --provider anthropic --model <model> --out evals/results/after.json
python3 evals/run_evals.py --compare evals/results/before.json evals/results/after.json
```

Paste the comparison table into the PR description. Explain any regression or say why it is acceptable. Use the same model and judge for both runs. Judges are noisy, so rerun a regressed case before concluding it is real.

No API key? Run `--dry-run`, say so in the PR, and a maintainer will run the full set.

## Evaluating other tools (Cursor, Lovable, ChatGPT, Copilot)

Tools that can't be called through an API can still be scored with the same rubric.

1. Install the adapter for the tool (see `adapters/README.md`): for example `.cursor/rules` for Cursor, project knowledge for Lovable, a custom GPT or project instructions for ChatGPT.
2. Print the case prompt with its fixtures:
   ```bash
   python3 evals/run_evals.py --print-prompt --case build-newsletter-cursor
   ```
   For tools that read files from the workspace, copy the fixture files into the project instead and paste only the prompt.
3. Paste the prompt into the tool in a fresh chat. Copy its full answer (including code) into a file.
4. Grade it:
   ```bash
   # with a judge model
   python3 evals/run_evals.py --manual --case build-newsletter-cursor --tool cursor \
     --answer-file answer.md --judge-provider anthropic --judge-model <model>

   # paste from stdin instead of a file
   pbpaste | python3 evals/run_evals.py --manual --case build-newsletter-cursor --tool cursor \
     --judge-provider anthropic --judge-model <model>

   # no API at all: score it yourself item by item
   python3 evals/run_evals.py --manual --case build-newsletter-cursor --tool lovable \
     --answer-file answer.md --judge-provider human
   ```
5. The result is saved like any other run, with `model` set to the tool name, so `--compare` works across tools.

The three newsletter cases (`build-newsletter-signup`, `build-newsletter-cursor`, `build-newsletter-lovable`) are the same scenario framed for different tools. Run them across tools to compare adapters.

## Current coverage

30 cases: build 14, explain 5, docs 4, breach 3, refuse 3, audit 1. Topics include direct marketing (newsletter, WhatsApp, cold B2B, purchased lists, pre-ticked boxes), Supabase RLS, trackers and cookie banners, SA ID minimisation, AI chatbots and fine-tuning, automated credit decisions, biometrics, children, cross-border hosting, three breach scenarios, data subject rights (access, deletion, objection), privacy notice drafting, a repo audit, fines, uncertainty handling, backdated consent, and sector packs (short-term rentals, fintech, education, HR).

Gaps we would like help with: more audit cases, Firebase and WordPress stacks, health pack cases, multi-turn cases, and isiZulu, isiXhosa, Afrikaans and Setswana prompts.
