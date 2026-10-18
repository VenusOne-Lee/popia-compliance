# Contributing

Thanks for helping South African builders ship products that respect people's personal information. This project only stays useful if it keeps up with the law and with the way people actually build. Both need you.

Please read [DISCLAIMER.md](DISCLAIMER.md) and [GOVERNANCE.md](GOVERNANCE.md) first.

## Ways to help

| You are | Most valuable contribution |
|---|---|
| **Attorney / privacy professional** | Review legal content, correct errors, approve `legal-review` PRs, become the legal reviewer. Email popiakit@venusone.africa or use the "Legal reviewer: volunteer" issue form. [Reviewer terms](GOVERNANCE.md#reviewer-terms) |
| **Developer** | New scanner rules, stack playbooks, components, bug fixes, false-positive reports |
| **Information Officer / compliance** | Checklist gaps, real-world process patterns, template improvements |
| **Translator** | Review a draft translation in `i18n/` (Afrikaans, isiZulu, isiXhosa, Setswana, more welcome) |
| **Sector specialist** | A new sector pack or corrections to an existing one |
| **Anyone** | Report a law change, a broken link, or a confusing explanation |

## Ground rules for content

1. **Every legal claim cites a source.** Section numbers (`s69(2)`), regulation and form numbers, or a link to a primary source (the Act, Government Gazette, inforegulator.org.za). Secondary sources (law firm articles) are fine as context, not as the only source for a rule.
2. **Never invent.** If you're not sure, write `VERIFY` and explain what needs checking. An honest gap beats a confident error.
3. **Time-sensitive facts live in one place.** Dates, statuses, enforcement history and pending changes go in `references/10-regulatory-watch.md`. Other files describe the rule and point there.
4. **Plain language.** Short declarative sentences. South African English. Builder-first: say what to do, then why.
5. **House style.** No em dashes (use commas, colons, full stops or a plain hyphen). No exclamation marks. Run `python3 scripts/style_lint.py`.
6. **Guidance, not advice.** Don't write "this makes you compliant". Write "this addresses s19" or "this supports".

## Law change process

When POPIA, the Regulations, a guidance note, a relevant court judgment or the Regulator's practice changes:

1. **Open a `law-change` issue** using the template. Include: what changed, the primary source link, the date published and the effective date, and which files are likely affected. The automated regulatory watch (`.github/workflows/regwatch.yml`) opens these monthly from the Regulator's site, but anyone can open one.
2. **Update `references/10-regulatory-watch.md` first** in your PR: add or change the row, status and source. Update "Last reviewed".
3. **Update affected references, checklists, templates, packs and scanner rules.** Search the repo for the section number (`grep -rn "s69" references templates packs scripts/rules`).
4. **Add or update eval cases** so the new rule is tested (`evals/cases/`).
5. **Add a CHANGELOG entry** under the legal effective date: `### 2026-04-17: Amended POPIA Regulations`.
6. **Label the PR `legal-review`.** It can't be merged until a legal reviewer approves, or, while the seat is vacant, until two maintainers approve and the change is marked `pending legal review` in the CHANGELOG.

## Adding a scanner rule

Rules are plug-ins. Each file in `scripts/rules/` exports `RULES = [Rule(...)]`.

1. Pick the right module (or add one): `secrets.py`, `pii.py`, `access.py`, `web.py`, `consent.py`, `thirdparty.py`, `repo.py`.
2. Choose an ID prefix: `SEC` security, `PII` personal information, `LOG` logging, `STO` storage, `CON` consent, `SPI` special PI, `CHI` children, `DM` direct marketing, `XB` cross-border/operators, `AI` AI/automated decisions, `DOC` notices, `DSR` rights, `RET` retention. Use the next free number.
3. Fill every field: `title`, `severity` (use the rubric in SKILL.md), `popia` (sections), `message` (why it matters, one or two sentences), `fix` (what to do), `confidence`.
4. Rule kinds: `line` (regex per line, optional `validator`), `file` (`file_check(rel, text)`), `repo` (`repo_check(ctx)` for absence or cross-file checks).
5. **Add a test** in `tests/scanner/test_rules.py`: the bad case must fire, the clean case must not. Never commit real or realistic secrets, ID numbers or card numbers: generate them at runtime like the existing tests do. Use `scripts/sa_id.py fake` for synthetic IDs.
6. Run `python3 -m unittest discover -s tests -t .` and `python3 scripts/popia_scan.py tests/fixtures/demo-app`.
7. Keep false positives low. A noisy rule gets ignored, and then it protects nobody. Prefer `confidence="low"` and `info` severity for heuristics.

## Adding a component

See `registry/README.md`. Components must be accessible, work without browser storage, use plain non-manipulative copy, and cite the section they support in a comment. Rebuild with `python3 registry/build.py` and commit `registry/r/`.

## Translations

See `i18n/README.md`. A translation moves from `draft` to `reviewed` only after a native speaker reviews it, and their name (or handle) is recorded. Keep section references and legal meaning intact. Prefer plain everyday language over literal translation.

## Sector packs

Copy `packs/_template.md`. Packs must list laws beyond POPIA with their status and a primary source, and mark anything unverified.

## Evals

Changing `SKILL.md`, a reference file or an adapter changes how AI tools behave. Before opening the PR:

```bash
python3 evals/run_evals.py --dry-run          # validates cases
python3 evals/run_evals.py --provider anthropic --model <model> --out before.json   # on main
python3 evals/run_evals.py --provider anthropic --model <model> --out after.json    # on your branch
python3 evals/run_evals.py --compare before.json after.json
```

Paste the comparison summary in the PR. No API key? Run `--dry-run` and say so; a maintainer will run the full set.

## Pull requests

- One topic per PR. Small is good.
- Fill in the PR template checklist.
- CI must pass: tests, scanner self-test, eval dry-run, registry build check, style lint.
- Adapters are generated: edit `adapters/_core.md`, then run `python3 scripts/build_adapters.py`.
- By contributing you agree your contribution is licensed under the project's licences (MIT for code, CC BY 4.0 for content). You confirm you have the right to contribute it.

## Reporting a security issue

Don't open a public issue for a vulnerability in this project's code. See [SECURITY.md](SECURITY.md).

## Recognition

Contributors are credited in release notes. Reviewers (legal, translation, sector) are named in `GOVERNANCE.md` and next to the content they reviewed.
