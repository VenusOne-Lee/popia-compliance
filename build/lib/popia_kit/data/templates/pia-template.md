> Draft template. Engineering and compliance guidance, not legal advice. Have it reviewed by a qualified South African privacy attorney before use. See DISCLAIMER.md.

# Personal information impact assessment: {{processing_activity_name}}

Reg 4 requires the Information Officer to ensure a personal information impact assessment (PIA) is done to ensure adequate measures and standards exist to comply with the conditions for lawful processing. This template is one way to record it.

| Field | Value |
|---|---|
| Responsible party | {{responsible_party_legal_name}} |
| Information Officer | {{io_name}} |
| Assessor | {{assessor_name}} |
| Product / feature / process | {{processing_activity_name}} |
| Version and date | {{pia_version}} ({{pia_date}}) |
| Next review | {{pia_next_review}} |
| Linked ROPA rows | {{ropa_rows}} |

## 1. Description of the processing

- **What is being built or changed:** {{description}}
- **Data subjects:** {{data_subjects}} (natural persons, juristic persons, employees, children?)
- **Estimated volume:** {{volume}}
- **PI fields collected:** {{fields}}
- **Source of the PI (s12):** {{source}} (directly from the data subject, or exception documented)
- **Where stored:** {{data_stores}}
- **Who has access:** {{access_roles}}
- **Operators involved (s20, s21):** {{operators}}
- **Retention and deletion (s14):** {{retention}}

Attach or link a data flow diagram (Mermaid is fine).

## 2. Necessity and proportionality

| Question | Answer |
|---|---|
| What specific, explicitly defined purpose does this serve (s13)? | {{purpose}} |
| Is each field needed for that purpose (s10)? List fields dropped. | {{minimality}} |
| Could the purpose be met with less data, or de-identified data? | {{less_data}} |
| Are optional fields marked optional, with consequences explained (s18(1)(d) and (e))? | {{optional_fields}} |
| Is this further processing of data collected for another purpose? Compatibility assessment (s15). | {{further_processing}} |
| Are SA ID numbers or account numbers collected? Legal requirement or core service need? | {{high_risk_ids}} |

## 3. Lawful basis

| Purpose | s11(1) ground | Evidence or reasoning | Right to object applies (s11(3))? |
|---|---|---|---|
| {{purpose_1}} | {{basis_1}} | {{basis_evidence_1}} | {{objection_1}} |

If s11(1)(f) legitimate interests is used, attach a balancing assessment (PL-07). If s11(1)(a) consent is used, record the wording and how consent and withdrawal are logged (PL-03, PL-04).

Direct marketing by electronic communication: s69 consent (Form 4 or substantially similar) or existing-customer exception. Record which: {{s69_position}}

## 4. Risks

Likelihood: Rare, Unlikely, Possible, Likely, Almost certain. Impact: Minimal, Minor, Moderate, Major, Severe.

| # | Risk to data subjects | Condition / section | Likelihood | Impact | Inherent rating |
|---|---|---|---|---|---|
| R1 | {{risk_1}} | {{risk_1_section}} | {{risk_1_likelihood}} | {{risk_1_impact}} | {{risk_1_rating}} |
| R2 | Unauthorised access to PI through weak access control | s19 | | | |
| R3 | PI kept longer than needed | s14 | | | |
| R4 | Transfer to a country without adequate protection | s72 | | | |
| R5 | Data subjects unaware of processing | s18 | | | |

Consider: identity fraud, financial loss, discrimination, reputational harm, loss of control over PI, unwanted marketing, chilling effects, harm to children.

## 5. Mitigations

| Risk | Control | Control ID | Owner | Due | Status |
|---|---|---|---|---|---|
| R1 | {{mitigation_1}} | {{mitigation_1_control}} | {{mitigation_1_owner}} | {{mitigation_1_due}} | {{mitigation_1_status}} |

Use control IDs from references/09-audit-procedure.md and references/03-security-controls.md.

## 6. Residual risk

| Risk | Residual likelihood | Residual impact | Residual rating | Accepted by |
|---|---|---|---|---|
| R1 | {{residual_1_likelihood}} | {{residual_1_impact}} | {{residual_1_rating}} | {{residual_1_accepted_by}} |

If residual risk is high, do not proceed without Information Officer and attorney sign-off.

## 7. Prior authorisation check (s57)

Tick any that apply. If any is ticked, prior authorisation from the Regulator is needed before processing. The Regulator offers an online application. Failure to notify is an offence (s59).

- [ ] s57(1)(a): processing unique identifiers for a purpose other than the one intended at collection, with the aim of linking with information processed by other responsible parties
- [ ] s57(1)(b): processing information on criminal behaviour or unlawful or objectionable conduct on behalf of third parties
- [ ] s57(1)(c): processing information for credit reporting
- [ ] s57(1)(d): transferring special PI or children's PI to a third party in a foreign country without an adequate level of protection

Outcome: {{s57_outcome}}

## 8. Special personal information and children

**Special PI (s26 to s33).** Fields involved: {{special_pi_fields}}

| Field | Category | s27 ground (or s28 to s33 authorisation) | Separate explicit consent? | Stricter controls (SPI-04) |
|---|---|---|---|---|
| {{spi_field_1}} | {{spi_category_1}} | {{spi_ground_1}} | {{spi_consent_1}} | {{spi_controls_1}} |

Biometrics (face, fingerprint, voice recognition) are special PI. Get attorney review.

**Children (s34, s35).** Does the service collect PI of persons under 18? {{children_yes_no}}

- s35 ground: {{children_ground}}
- Competent person consent flow: {{competent_person_flow}}
- Age gate design: {{age_gate}}
- No behavioural advertising, minimal profile data (CHI-03): {{children_minimisation}}

## 9. Cross-border transfers (s72)

| Recipient | Country | Data | s72 ground | Evidence |
|---|---|---|---|---|
| {{xb_recipient_1}} | {{xb_country_1}} | {{xb_data_1}} | {{xb_ground_1}} | {{xb_evidence_1}} |

The Regulator has not published an adequacy list (as at October 2026). Do not assume any country is adequate without analysis. Disclose transfers in the privacy notice (s18(1)(g)).

## 10. Automated decisions and AI (s71)

- Decisions with legal or substantial effect based solely on automated profiling? {{automated_decisions}}
- s71(2) exception relied on: {{s71_exception}}
- Representations route and explanation of logic (s71(3)): {{s71_measures}}
- AI providers as operators, training disabled, retention recorded: {{ai_providers}}

## 11. Decision and sign-off

Decision: {{decision}} (Proceed / Proceed with conditions / Do not proceed)

Conditions: {{conditions}}

| Role | Name | Signature | Date |
|---|---|---|---|
| Assessor | {{assessor_name}} | | |
| Information Officer | {{io_name}} | | |
| Product owner | {{product_owner}} | | |
| Attorney (if reviewed) | {{attorney_name}} | | |
