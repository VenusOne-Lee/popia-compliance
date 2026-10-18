## What and why

<!-- One or two sentences. Link the issue. -->

## Type
- [ ] Law change (`legal-review`)
- [ ] Other legal content (`legal-review`)
- [ ] Scanner rule
- [ ] Component
- [ ] Translation
- [ ] Sector pack
- [ ] Docs / tooling

## Checklist
- [ ] Legal claims cite sections or primary sources; unsure items marked `VERIFY`
- [ ] Time-sensitive facts are in `references/10-regulatory-watch.md`
- [ ] Tests pass: `python3 -m unittest discover -s tests -t .`
- [ ] Style: `python3 scripts/style_lint.py`
- [ ] Evals: dry-run passes; comparison pasted below if SKILL.md, references or adapters changed
- [ ] Adapters rebuilt if `adapters/_core.md` changed (`python3 scripts/build_adapters.py`)
- [ ] No real personal information, secrets, ID or card numbers anywhere in the PR
- [ ] CHANGELOG updated

## Eval comparison (if applicable)
