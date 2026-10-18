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

We're looking for an admitted South African attorney (or a firm) with privacy and data protection experience. The role is light: review `legal-review` PRs, flag errors in existing content, and sign off releases that change legal guidance. Reviewers are credited by name on the README and next to the content they reviewed.

**To volunteer:** email **popiakit@venusone.africa**, or, if you're on GitHub, open a [Legal reviewer: volunteer](https://github.com/VenusOne-Lee/popia-compliance/issues/new?template=legal-reviewer.yml) issue (that issue is public).

### Reviewer terms

These terms protect reviewers and users. They are part of this project and apply to every review.

1. **Not legal advice to users.** A review checks the project's content for accuracy. It is not legal advice to anyone who uses POPIA Kit, and users are told so in [DISCLAIMER.md](DISCLAIMER.md).
2. **No client relationship.** Reviewing creates no attorney and client relationship between a reviewer and any user, maintainer, contributor or Venus ARC (Pty) Ltd. Any engagement for advice is separate and must be agreed in writing.
3. **Dated, scoped sign-off.** A sign-off means the reviewer checked the named content against the law as it stood on the review date. It is not a guarantee, and it does not cover later changes or other content.
4. **You choose the scope and the pace.** There are no minimum hours or deadlines. You can decline any request and step away at any time.
5. **Credit, or not.** Reviewers are credited by name (and firm, if they wish) in the README and next to the content they reviewed. You can ask for your name to be removed at any time.
6. **Conflicts and confidentiality.** Don't review content where you have a conflict. Never include client information in a review, an issue or a pull request.
7. **Licence.** Review comments and edits are contributions under [LICENSE-CONTENT](LICENSE-CONTENT) (CC BY 4.0), like all other guidance in this project.

These terms were drafted without a lawyer and are `pending legal review`. The first legal reviewer is welcome to change them.

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
