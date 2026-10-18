> Draft template. Engineering and compliance guidance, not legal advice. Have it reviewed by a qualified South African privacy attorney before use. See DISCLAIMER.md.

# POPIA and security audit report: {{product_name}}

| Field | Value |
|---|---|
| Responsible party | {{responsible_party_legal_name}} ({{responsible_party_reg_number}}) |
| Operator(s) in scope | {{operators_in_scope}} |
| Commissioned by | {{commissioned_by}} |
| Report recipients | {{report_recipients}} |
| Auditor | {{auditor_name}}, {{auditor_organisation}} |
| Audit period | {{audit_start_date}} to {{audit_end_date}} |
| Report version | {{report_version}} ({{report_date}}) |
| Law current to | {{law_current_to}} (see references/10-regulatory-watch.md) |

## 1. Scope and context

- **Product and URLs:** {{product_urls}}
- **Environments:** {{environments}}
- **Repositories and apps:** {{repositories}}
- **Business model and users:** {{business_model}} (consumers / businesses / employees / children: {{user_types}})
- **Sectors with extra rules:** {{sector_rules}}
- **Data subject volume (order of magnitude):** {{data_subject_volume}}
- **Hosting and key vendors:** {{hosting_and_vendors}}
- **Information Officer:** {{io_name}}. Registration on eServices portal: {{io_registration_status}} (evidence: {{io_registration_evidence}})
- **Deputy Information Officer(s):** {{dio_names}}
- **Access granted:** {{access_granted}}
- **Live testing authorisation:** {{live_testing_authorisation}} (passive checks only unless written scope allows active testing)
- **Out of scope:** {{out_of_scope}}

## 2. Verdict

{{verdict_paragraph}}

Overall rating: **{{overall_rating}}** (worst of Security safeguards, Processing limitation, Openness, Accountability).

## 3. Top 5 fixes

| # | Finding | Severity | Fix | Owner | Due |
|---|---|---|---|---|---|
| 1 | {{top1_id}}: {{top1_title}} | {{top1_severity}} | {{top1_fix}} | {{top1_owner}} | {{top1_due}} |
| 2 | {{top2_id}}: {{top2_title}} | {{top2_severity}} | {{top2_fix}} | {{top2_owner}} | {{top2_due}} |
| 3 | {{top3_id}}: {{top3_title}} | {{top3_severity}} | {{top3_fix}} | {{top3_owner}} | {{top3_due}} |
| 4 | {{top4_id}}: {{top4_title}} | {{top4_severity}} | {{top4_fix}} | {{top4_owner}} | {{top4_due}} |
| 5 | {{top5_id}}: {{top5_title}} | {{top5_severity}} | {{top5_fix}} | {{top5_owner}} | {{top5_due}} |

## 4. Posture by POPIA condition

Rating key: **Strong** (all key controls met, minor gaps only) · **Adequate** (key controls met, some Medium gaps) · **Weak** (any High open, or several key controls partial) · **Critical** (any Critical open).

| Condition | Sections | Rating | Key gaps | Findings |
|---|---|---|---|---|
| Accountability | s8, s55, Reg 4 | {{rating_accountability}} | {{gaps_accountability}} | {{findings_accountability}} |
| Processing limitation | s9 to s12 | {{rating_processing_limitation}} | {{gaps_processing_limitation}} | {{findings_processing_limitation}} |
| Purpose specification and retention | s13, s14 | {{rating_purpose_specification}} | {{gaps_purpose_specification}} | {{findings_purpose_specification}} |
| Further processing limitation | s15 | {{rating_further_processing}} | {{gaps_further_processing}} | {{findings_further_processing}} |
| Information quality | s16 | {{rating_information_quality}} | {{gaps_information_quality}} | {{findings_information_quality}} |
| Openness | s17, s18 | {{rating_openness}} | {{gaps_openness}} | {{findings_openness}} |
| Security safeguards | s19 to s22 | {{rating_security}} | {{gaps_security}} | {{findings_security}} |
| Data subject participation | s23 to s25 | {{rating_participation}} | {{gaps_participation}} | {{findings_participation}} |
| Special personal information | s26 to s33 | {{rating_special_pi}} | {{gaps_special_pi}} | {{findings_special_pi}} |
| Children | s34, s35 | {{rating_children}} | {{gaps_children}} | {{findings_children}} |
| Direct marketing | s69 | {{rating_direct_marketing}} | {{gaps_direct_marketing}} | {{findings_direct_marketing}} |
| Automated decisions and AI | s71 | {{rating_ai}} | {{gaps_ai}} | {{findings_ai}} |
| Operators and cross-border | s20, s21, s72 | {{rating_cross_border}} | {{gaps_cross_border}} | {{findings_cross_border}} |
| Prior authorisation | s57 | {{rating_prior_authorisation}} | {{gaps_prior_authorisation}} | {{findings_prior_authorisation}} |

Use ➖ N/A for conditions that do not apply, and say why in "Key gaps".

## 5. Findings

Severity follows the rubric in SKILL.md (Critical, High, Medium, Low, Info). Group duplicates: one root cause across many tables is one finding.

| ID | Control | Section | Severity | Title | Owner | Due | Status |
|---|---|---|---|---|---|---|---|
| F-01 | {{control_id}} | {{section}} | {{severity}} | {{title}} | {{owner}} | {{due}} | Open |
| F-02 | | | | | | | |

### Finding detail format

Repeat this block for every finding. Format matches references/09-audit-procedure.md §6.

```
ID:         F-01
Control:    {{control_id}} ({{section}})
Severity:   {{severity}}
Title:      {{title}}
Evidence:   {{evidence}}   (file:line, URL, command output with timestamp; redact PI)
Risk:       {{risk}}
Fix:        {{fix}}   (concrete diff or snippet where possible)
Owner:      {{owner}}
Due:        {{due}}
Status:     Open
```

Any Critical finding about exposed data also raises the breach question. Record here whether logs show access, and whether references/07-breach-response.md was triggered: {{breach_question_outcome}}

## 6. Data map

Collection points reviewed: {{collection_points}}. Full record of processing activities: attached ROPA ({{ropa_filename}}).

```mermaid
flowchart LR
  Form[{{collection_point_1}}] -->|{{fields_1}}| DB[({{data_store_1}}<br/>region: {{region_1}})]
  DB -->|{{integration_1}}| CRM[{{crm_1}}<br/>region: {{region_2}}]
  Form -->|page events| AN[{{analytics_tool}} - {{analytics_region}}]
  CRM -->|campaigns| EM[{{email_platform}} - {{email_region}}]
```

Unknowns (shown as "region: ?") are findings until resolved.

## 7. Manual control review summary

Mark each control: ✅ Met · ⚠️ Partial · ❌ Not met · ➖ N/A · ❓ Unknown. An unknown on a key control is itself a finding.

| Area | Controls | Met | Partial | Not met | N/A | Unknown |
|---|---|---|---|---|---|---|
| Accountability | ACC-01 to ACC-08 | | | | | |
| Processing limitation | PL-01 to PL-08 | | | | | |
| Purpose and retention | PS-01 to PS-07 | | | | | |
| Further processing | FP-01, FP-02 | | | | | |
| Information quality | IQ-01, IQ-02 | | | | | |
| Openness | OP-01 to OP-07 | | | | | |
| Security | SEC-*, BR-01 to BR-08 | | | | | |
| Participation | DSP-01 to DSP-06 | | | | | |
| Special PI | SPI-01 to SPI-05 | | | | | |
| Children | CHI-01 to CHI-04 | | | | | |
| Direct marketing | DM-01 to DM-12 | | | | | |
| Cross-border and operators | XB-01 to XB-09 | | | | | |
| AI and automated decisions | AI-01 to AI-12 | | | | | |
| Prior authorisation | PA-01, PA-02 | | | | | |

## 8. Remediation and re-test

| Run | Date | Critical | High | Medium | Low | Info |
|---|---|---|---|---|---|---|
| Baseline scan | {{baseline_date}} | | | | | |
| Re-test | {{retest_date}} | | | | | |

Next review scheduled: {{next_review_date}}.

## Appendix A: Scanner evidence

Command and version:

```bash
python3 scripts/popia_scan.py {{repo_path}} --format md --out evidence/popia-scan.md
```

Triage every result as **confirmed**, **false positive** (say why) or **needs info**. Do not paste raw output without triage.

| Scanner rule | File:line | Triage | Linked finding | Note |
|---|---|---|---|---|
| | | | | |

## Appendix B: Site check evidence

```bash
python3 scripts/site_check.py {{site_url}} --out evidence/site-check.md --json evidence/site-check.json
```

| Check | Result | Linked finding | Note |
|---|---|---|---|
| Security headers | | | |
| Cookies set before consent | | | |
| Trackers loaded before consent | | | |
| Privacy notice linked | | | |
| PAIA manual linked | | | |

## Appendix C: Other evidence

List evidence files, where they are stored, and when they will be deleted. Evidence is protected at the same level as the data it describes. Redact PI (emails `l***@domain`, IDs `******123****`).

| File | Description | Location | Delete by |
|---|---|---|---|
| | | | |

## Sign-off

This report is an engineering and compliance review, not a legal opinion.

| Role | Name | Signature | Date |
|---|---|---|---|
| Auditor | {{auditor_name}} | | |
| Information Officer | {{io_name}} | | |
| Reviewing attorney (if any) | {{attorney_name}} | | |
