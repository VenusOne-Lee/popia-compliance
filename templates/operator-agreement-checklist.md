> Draft template. Engineering and compliance guidance, not legal advice. Have it reviewed by a qualified South African privacy attorney before use. See DISCLAIMER.md.

# Operator agreement checklist (s20, s21, s72)

Use this for every operator: any person or vendor that processes personal information on behalf of {{company_legal_name}} under a contract, without coming under its direct authority. Examples: hosting, database, email, CRM, analytics, payments, support desk, AI APIs, agencies and freelancers.

The responsible party stays accountable. An operator's breach is the responsible party's s22 notification.

| Field | Value |
|---|---|
| Operator | {{operator_name}} |
| Service | {{operator_service}} |
| Personal information processed | {{operator_data}} |
| Processing location(s) | {{operator_country}} |
| Agreement reference | {{operator_agreement_ref}} |
| Reviewed by / date | {{reviewer}} / {{review_date}} |

## s20: Processing on authority and confidentiality

- [ ] Operator processes PI only with the knowledge or authorisation of the responsible party
- [ ] Operator processes only on documented instructions, for the agreed purposes
- [ ] Operator treats PI as confidential and does not disclose it unless required by law or in the course of its proper duties
- [ ] Operator staff with access are bound by confidentiality

## s21: Security measures and breach notification

- [ ] Written contract in place (s21(1))
- [ ] Operator must establish and maintain the s19 security measures (technical and organisational)
- [ ] Security measures are described or referenced (for example: encryption, access control, MFA, logging, backups, vulnerability management)
- [ ] Operator must notify the responsible party **immediately** where there are reasonable grounds to believe PI has been accessed or acquired by an unauthorised person (s21(2)). Avoid long windows. If a period is defined, it should be short. (XB-03)
- [ ] Notice content defined: what happened, PI involved, data subjects affected, measures taken, contact person
- [ ] Operator must cooperate with the responsible party's s22 notifications and Regulator enquiries

## Sub-operators and onward transfer

- [ ] Operator may use sub-operators only with prior written authorisation (specific or general with notice and a right to object)
- [ ] Current sub-operator list obtained, with countries
- [ ] Same s20 and s21 obligations pushed down to sub-operators in writing
- [ ] Operator remains liable for sub-operators
- [ ] Onward transfers outside South Africa meet s72 (XB-08)

## Cross-border (s72)

- [ ] Processing countries recorded (XB-04)
- [ ] s72(1) ground documented (XB-05). Default: binding agreement providing an adequate level of protection, with principles substantially similar to POPIA's conditions, including onward transfer rules (s72(1)(a))
- [ ] No special PI or children's PI to a country without adequate protection unless prior authorisation obtained (s57(1)(d)) (XB-06)
- [ ] Transfers disclosed in the privacy notice (s18(1)(g)) (XB-07)

### POPIA addendum to GDPR SCCs or a vendor DPA

Many vendors offer an EU GDPR data processing agreement with Standard Contractual Clauses. It helps but does not map one to one to POPIA. Add a POPIA addendum that:

- [ ] Applies the agreement to personal information of **juristic persons** (existing companies and other legal entities), which GDPR does not cover
- [ ] Uses POPIA terms: responsible party, operator, data subject, personal information, special personal information
- [ ] Covers POPIA special PI categories (s26), including criminal behaviour and biometrics
- [ ] Covers children's PI (under 18, s34)
- [ ] Requires immediate notification under s21(2)
- [ ] Names the Information Regulator as a competent authority for cooperation and enquiries
- [ ] States that South African law applies to the POPIA obligations (VERIFY wording with your attorney)

## Audit and assurance

- [ ] Responsible party may audit, or receive independent reports (for example ISO 27001 certificate or SOC 2 report), on reasonable notice
- [ ] Operator answers security questionnaires and provides evidence on request
- [ ] Operator notifies material changes to security measures or locations

## Data subject rights and assistance

- [ ] Operator assists with access, correction, deletion and objection requests (s23, s24, s11(3)) within a defined time
- [ ] Operator forwards requests it receives directly, without responding itself unless instructed

## Return and deletion

- [ ] At the end of the service, operator returns or deletes all PI at the responsible party's choice (XB-09)
- [ ] Deletion prevents reconstruction in an intelligible form (s14(5))
- [ ] Deletion covers backups on their natural expiry, with the window stated
- [ ] Operator confirms deletion in writing

## AI providers (extra)

- [ ] Provider does not use PI to train models (or training disabled and evidenced) (AI-02)
- [ ] Retention of prompts and outputs recorded; zero or limited retention used where available (AI-03)
- [ ] Region recorded

## If you are the operator

If {{company_legal_name}} builds or runs systems for a client, it is often the operator, and the client is the responsible party. Put that in the client contract, and push the same terms down to your own sub-operators.
