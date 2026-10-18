# Regulatory watch

**Last reviewed: 18 October 2026.** This file is the only place time-sensitive facts should live. When the law or the Regulator's practice changes, update this file first (see CONTRIBUTING.md, "Law change process"), then update any reference that depends on it.

Status key: **In force** · **Published, not in force** · **Draft / signalled** · **Disputed / in court** · **Unverified** (needs a primary source)

## Instruments

| Date | Instrument | Status | What it means for builders | Primary source |
|---|---|---|---|---|
| 1 Jul 2021 | POPIA substantive conditions enforceable | In force | Everything in this skill | Act 4 of 2013 |
| 14 Dec 2018 | POPIA Regulations (GNR 1383) | In force, amended 2025 | Forms 1 to 5, IO duties | inforegulator.org.za |
| 4 Dec 2024 | Guidance Note on Direct Marketing | In force (guidance, non-binding) | Form 4 for consent; calls, push, DMs, cookies treated as electronic communication | inforegulator.org.za |
| 1 Apr 2025 | Security compromise reporting via eServices portal | In force (mandatory) | Email/SCN1 not accepted; IO logs on portal | inforegulator.org.za, Fact Sheet 19 Aug 2025 |
| 17 Apr 2025 | Amended POPIA Regulations | In force (immediate) | Free objection/correction, opt-out ≠ consent, complaint process (Form 5), fine instalments | Government Gazette, inforegulator.org.za |
| Mar 2026 | POPIA Regulations on processing health information (s32), GN 7198, GG 54268, reported in force 6 March 2026 | In force (verify final wording) | Extra conditions for employers, insurers, medical schemes and pension funds processing health information. See packs/health.md | Government Gazette; acts.co.za, Fasken, Moonstone summaries |
| 2026 | Draft short-term rentals code (GN 3824 of 2026) | Draft / signalled | Not binding. Watch for STR host obligations. See packs/short-term-rentals.md | Government Gazette (verify) |
| 2026 | CPA Amendment Regulations: pre-emptive block register | In force (check commencement detail) | Scrub against register; doesn't replace POPIA consent | NCC / Government Gazette |
| 2026 | Regulator online prior authorisation + exemption applications, complaints system, iSupport | Live | s57 applications online | inforegulator.org.za |
| - | Guidance Note on transborder flows (s72) | Draft / signalled | No adequacy list yet; use binding agreements | Regulator APP 2025/26 |
| - | Cybercrimes Act s54 reporting (ECSPs, FIs: 72h to SAPS) | Published, not in force (verify) | Monitor if client is a FI or ECSP | Act 19 of 2020 |
| - | PAIA amendments to add enforcement/fines | Draft / signalled (Aug 2026) | PAIA non-compliance may become fineable | Regulator briefing 31 Aug 2026 |
| - | Judicial Matters Amendment Bill: Regulator power to release info after 180 days | In Parliament | PAIA | parliament.gov.za |
| - | AI-specific guidance (automated decisions/profiling) | **Unverified**: secondary sources mention a 2025 guidance note; no primary source located | Don't cite until confirmed | - |

## Enforcement pattern (what the Regulator actually does)

- **Fines so far follow ignored enforcement notices**, not the incident itself. Comply within the notice period and no fine follows under the current framework (Regulator, Aug 2026). The Regulator calls this a weakness and may seek change.
- Known administrative fines (as reported Aug 2026): DOJCD R5m (ransomware; lapsed security licences; disputed), DBE R5m (matric results publication; in court, SCA application), IEC R100k, Lancet Laboratories R100k (unreported compromises), Blouberg Local Municipality R500k reduced by court to R250k, FT Rams Consulting R100k (direct marketing; being processed).
- 2026 enforcement notices: Central Johannesburg TVET College (May 2026: unregistered IO, unlawful disclosure via misdirected email, failure to report compromise), SABS (Aug 2026: post-ransomware assessment found excessive processing, inadequate consent, weak safeguards, unaddressed vulnerabilities, no incident response plan, no collection notice; 90 days to fix).
- Direct marketing: OUTsurance and MTN telephone marketing matters referred to Enforcement Committee (2026).
- 8 000+ security compromise notifications since commencement; 1 220+ between 1 Apr and Aug 2026.
- Assessments without complaints: the Regulator writes to organisations in selected sectors requiring them to demonstrate compliance (2026).
- Live investigations reported (Aug 2026): NCR, Truecaller, Pick n Pay, Gauteng e-Gov, Land Bank, Standard Bank.
- Information Officer registration compliance estimated low; registration is the first thing an assessment checks.

## Court decisions to track

- **Matric results (DBE)**: High Court set aside notices (Dec 2025), leave to appeal refused (Jun 2026); Regulator approached SCA. Key issue: whether exam numbers are PI / pseudonymisation vs anonymisation. Outcome affects how "de-identified" is read.
- **DOJCD fine**: disputed in court.
- **Telephone marketing under s69**: expected litigation.

## Sources used for this review

- Information Regulator: media statements; Fact Sheet on Handling of Security Compromises (19 Aug 2025); enforcement notices page; amended Regulations (17 Apr 2025); Guidance Note on Direct Marketing (Dec 2024).
- Secondary analysis (cross-check against primary before relying): Baker McKenzie (Apr 2025 amendments), Covington Inside Privacy (eServices portal), Michalsons, ITLawCo (Aug 2026 briefing), BusinessTech (Sep 2026 fines), Werksmans (direct marketing guidance).

## Review cadence

- Monthly: Regulator media statements and enforcement notices pages.
- Quarterly: Government Gazette for POPIA/PAIA/CPA/ECTA/Cybercrimes changes.
- On any change: open a `law-change` issue (template in `.github/ISSUE_TEMPLATE/`).
