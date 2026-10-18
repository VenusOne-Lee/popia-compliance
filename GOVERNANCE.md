# Governance

## Stewardship

The project is maintained by **Venus ARC (Pty) Ltd, trading as Venus One** (Centurion, South Africa) as an open-source public good for South African builders. Venus One sets direction and holds final decision rights while the contributor community grows. We aim to add maintainers from outside Venus One as people make sustained contributions.

## Roles

| Role | Who | Responsibilities |
|---|---|---|
| **Lead maintainer** | Lethabo (Lee) Ntshudisane, Venus One | Direction, releases, final decisions, community |
| **Maintainers** | Open (apply via an issue) | Review and merge PRs, triage issues, run evals |
| **Legal reviewer** | **Vacant** | Approve `legal-review` PRs, flag errors, sign off releases that change legal content |
| **Translation reviewers** | Vacant per language | Review and approve translations in `i18n/` |
| **Sector reviewers** | Vacant per pack | Review sector packs (fintech, health, education, short-term rentals, e-commerce, HR) |

### The legal reviewer seat

We don't have a legal reviewer yet, and we say so plainly in [DISCLAIMER.md](DISCLAIMER.md) and the README.

We're looking for an admitted South African attorney (or a firm) with privacy and data protection experience. The role is light: review `legal-review` PRs, flag errors in existing content, and sign off releases that change legal guidance. Reviewers are credited by name on the README and next to the content they reviewed. If that's you, open an issue titled "Legal reviewer" or contact the lead maintainer.

**While the seat is vacant:** PRs that change legal content need approval from two maintainers, must cite primary sources, and are recorded in the CHANGELOG as `pending legal review`. When a legal reviewer joins, their first task is a review of all `pending legal review` items.

## Decisions

- **Day to day:** maintainers decide by approving PRs. Disagreements are discussed in the PR.
- **Legal content:** the legal reviewer's view prevails on interpretation. Where the law is unclear, we document both readings and recommend the more protective one for builders.
- **Direction and scope:** lead maintainer, after discussion in an issue labelled `rfc`.

## Labels

| Label | Meaning |
|---|---|
| `law-change` | A change in law or regulator practice needs to be reflected |
| `legal-review` | Changes legal content; needs legal reviewer (or two maintainers while vacant) |
| `pending-legal-review` | Merged under the vacancy rule; needs review when a legal reviewer joins |
| `rule` | Scanner rule work |
| `false-positive` | Scanner flagged something incorrectly |
| `component` | Drop-in component work |
| `translation` | i18n work |
| `pack` | Sector pack work |
| `evals` | Eval suite |
| `good first issue` | Small, well-scoped |
| `rfc` | Proposal for discussion |

## Releases

Semantic versioning for code (`v1.2.0`). Content changes are also tagged and listed in CHANGELOG.md with the legal effective date of any law change they reflect. The GitHub Action is referenced by release tag (for example `VenusOne-Lee/popia-compliance@v1.0.0`). A floating `v1` tag will follow.

## Neutrality

The project names vendors only where it helps builders (e.g. hosting regions, SDK detection). It doesn't endorse vendors, and inclusion isn't a recommendation. Venus One may offer paid services related to POPIA. Those services are separate from this project, and the project won't be shaped to require them.
