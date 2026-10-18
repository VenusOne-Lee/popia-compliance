> Engineering and compliance guidance, not legal advice. See DISCLAIMER.md.

# Sector packs

A sector pack adds the rules of one industry to the core skill. POPIA applies to every sector, but each sector brings its own laws, regulators, data types and failure patterns. A fintech app has FICA, the National Credit Act and card data. A guesthouse has the Immigration Act guest register. A school app has children's data. The core skill (`SKILL.md` and `references/`) does not repeat these. The packs do.

## Available packs

| Pack | File | Checklist prefix | Load when the product... |
|---|---|---|---|
| Fintech | [`fintech.md`](fintech.md) | `FIN-` | lends, pays, banks, insures, invests, onboards with KYC, stores card or account data |
| Health | [`health.md`](health.md) | `HLT-` | records health, medical, wellness, fitness, wearable or medical aid data; does telehealth or research |
| Education and children | [`education-and-children.md`](education-and-children.md) | `EDU-` | serves schools, learners, parents or anyone under 18 |
| Short-term rentals | [`short-term-rentals.md`](short-term-rentals.md) | `STR-` | runs a guesthouse, Airbnb listing, holiday let or property management business |
| E-commerce | [`ecommerce.md`](ecommerce.md) | `ECM-` | sells goods or services online, runs checkout, carts, reviews or loyalty |
| HR and recruitment | [`hr-and-recruitment.md`](hr-and-recruitment.md) | `HR-` | handles employees, applicants, CVs, payroll, background checks, clocking or monitoring |

A product can match more than one pack. A medical aid app is health and fintech. A school fee platform is education and fintech. Load every pack that matches.

## Structure of a pack

Every pack has the same sections, so agents and people can find things fast:

1. **Who it's for.** The builders and products in scope.
2. **Laws beyond POPIA.** Each law with its status (In force, Draft, Published not in force, Disputed, Unverified) and a primary source.
3. **Data categories and risk.** What the sector collects and how sensitive it is.
4. **Top 10 risky patterns.** What builders actually ship that causes trouble.
5. **Checklist.** Extra controls with IDs (`FIN-01` and so on), the POPIA section each one supports, and the evidence an auditor should ask for.
6. **Build patterns.** Schemas and code that apply the checklist.
7. **Retention.** Sector retention periods. Always marked "verify for your sector".
8. **Scanner rule ideas.** Patterns `scripts/popia_scan.py` could detect. These are proposals, not shipped rules.
9. **Sources.** Primary sources first.

Anything we could not confirm from a primary source is marked **VERIFY**. Treat VERIFY items as open questions for an attorney or the sector regulator, not as facts.

## How SKILL.md and agents use packs

- **Pick packs at the start.** In Build, Audit and Docs mode, read the product description and the data fields. If a pack matches, load it with the relevant core reference files.
- **Build mode.** Apply the pack's build patterns and checklist items on top of the ten Build-mode defaults in `SKILL.md`. Mention briefly which pack rules you applied.
- **Audit mode.** Add the pack's checklist to the master checklist in `references/09-audit-procedure.md`. Report pack findings with their pack IDs (for example `STR-03`) alongside the core IDs. Use the same severity rubric.
- **Docs mode.** Add the sector items to the privacy notice (for example the Immigration Act register for a guesthouse, or the FICA record-keeping duty for a fintech) so the s18 notice names the law that requires collection (s18(1)(f)).
- **Explain mode.** Cite the sector law with its status. Never present a VERIFY item as settled.
- **Non-negotiables still apply.** Packs never relax the core rules. If a pack and a core reference seem to conflict, the stricter rule wins and you flag the conflict.
- **Time-sensitive facts.** Sector law changes. Before relying on a status, check `references/10-regulatory-watch.md` and the pack's "Last reviewed" date.

Tool adapters (Cursor, Lovable, Copilot and others) can include a short pointer such as: "If the product is in fintech, health, education, short-term rentals, e-commerce or HR, load the matching file in `packs/`."

## Contributing a new pack

We welcome packs for other sectors: insurance, telecoms, property and estate agents, legal practices, NPOs and fundraising, security companies, gyms, churches, political parties, municipalities and more.

1. **Open an issue first** at https://github.com/VenusOne-Lee/popia-compliance/issues with the sector, the main laws and who will maintain the pack.
2. **Copy the template:** `cp packs/_template.md packs/<sector>.md`. Keep every section, even if one is short.
3. **Pick a unique checklist prefix** (two to four capital letters) not already in the table above or in `references/09-audit-procedure.md`.
4. **Cite primary sources.** Government Gazette, gov.za, the Information Regulator, the sector regulator, or the Act text. Secondary sources (law firm notes, news) are fine as context but must be labelled as secondary. If you cannot confirm a fact, write **VERIFY**.
5. **Never invent section numbers.** If you are not sure of the section, name the Act and write VERIFY.
6. **Use the house style.** South African English. Short declarative sentences. No em dashes. No exclamation marks. The first line must be the disclaimer line. Run `python3 scripts/style_lint.py packs/`.
7. **Add eval cases.** At least two cases in `evals/cases/` tagged `pack:<sector>`, then run `python3 evals/run_evals.py --dry-run`.
8. **Use fake data only.** Any example ID numbers come from `python3 scripts/sa_id.py fake N`. Never paste real customer, patient, learner or employee data.
9. **Label the PR `legal-review`.** Packs are legal content and follow the law change process in `CONTRIBUTING.md`.

## Maintenance

Each pack has a "Last reviewed" date. Review packs at least every six months, and whenever `references/10-regulatory-watch.md` changes for that sector.
