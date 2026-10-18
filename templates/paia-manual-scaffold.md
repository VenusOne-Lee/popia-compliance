> Draft template. Engineering and compliance guidance, not legal advice. Have it reviewed by a qualified South African privacy attorney before use. See DISCLAIMER.md.

# PAIA manual: {{company_legal_name}}

Prepared under section 51 of the Promotion of Access to Information Act 2 of 2000 (PAIA), for a private body.

**Important:** the Information Regulator publishes a guide and template for PAIA manuals and may update them. Check the current template and guide on https://inforegulator.org.za before publishing, and align this scaffold to it. Requirements for small private bodies may differ. VERIFY whether any exemption applies to you.

**Date of compilation:** {{effective_date}}
**Date of last revision:** {{effective_date}}

## 1. Introduction and purpose

This manual helps people who want to request access to records held by {{company_legal_name}}. It describes the records we hold, how to request them, and how we process personal information under POPIA.

## 2. Contact details (PAIA s51(1)(a))

| | |
|---|---|
| Name of private body | {{company_legal_name}} |
| Registration number | {{company_reg_number}} |
| Head of private body | {{head_of_body}} |
| Information Officer | {{io_name}} |
| Email | {{io_email}} |
| Telephone | {{io_phone}} |
| Physical address | {{physical_address}} |
| Postal address | {{postal_address_display}} |
| Website | {{website}} |

{{#if dios}}
**Deputy Information Officer(s):**

{{#each dios}}
- {{this.name}}, {{this.email}}
{{/each}}

{{/if}}
## 3. Guide on how to use PAIA (PAIA s10)

The Information Regulator has published a guide on how to use PAIA and POPIA. It is available on the Regulator's website and from the Regulator. A copy is available from our Information Officer on request. VERIFY the current guide's title and location.

{{regulator_contact}}

Verify current contact details on https://inforegulator.org.za.

## 4. Records available without a request (PAIA s52)

{{records_automatically_available}}

## 5. Records available under other legislation (PAIA s51(1)(b)(iii))

List legislation under which we hold records, for example (VERIFY which apply to you):

- Basic Conditions of Employment Act 75 of 1997
- Companies Act 71 of 2008
- Employment Equity Act 55 of 1998
- Income Tax Act 58 of 1962
- Labour Relations Act 66 of 1995
- Tax Administration Act 28 of 2011
- Value-Added Tax Act 89 of 1991
{{#if additional_legislation}}
- {{additional_legislation}}
{{/if}}

## 6. Subjects and categories of records held (PAIA s51(1)(b)(iv))

| Subject | Categories of records |
|---|---|
| Company secretarial | Incorporation documents, registers, minutes |
| Finance and tax | Financial statements, tax returns, invoices |
| Human resources | Employment contracts, payroll, leave records |
| Customers | {{data_categories_text}} |
| Suppliers and operators | Contracts, operator agreements, invoices |
| Information technology | Systems documentation, security policies |
| Marketing | Consent records, campaign records |

## 7. How to request access (PAIA s51(1)(b)(ii), s53)

1. Complete the prescribed request form (PAIA Form 2 for private bodies, VERIFY current form number on the Regulator's website).
2. Send it to the Information Officer at the contact details above.
3. Provide proof of identity, and proof of authority if you act for someone else.
4. Say which right you want to exercise or protect, and why the record is needed for it.
5. Pay any request fee and access fee that applies.

We will decide on the request within the period set by PAIA and tell you the outcome. VERIFY the current statutory timelines.

## 8. Fees

PAIA prescribes request and access fees for private bodies. The current fee schedule is published in the PAIA Regulations and on the Regulator's website. VERIFY current amounts before quoting. Requests by a data subject under POPIA s23(1)(a) to confirm whether we hold their PI are free.

## 9. Grounds for refusal (PAIA Part 3, Chapter 4)

We may refuse access on grounds set out in PAIA, for example to protect the privacy of a third party, commercial information, confidential information, safety of individuals and property, records privileged from production in legal proceedings, and research information. VERIFY the full list and section references.

## 10. Remedies

If you are not satisfied with our decision, you may lodge a complaint with the Information Regulator or apply to court, as set out in PAIA. VERIFY current procedure.

## 11. Processing of personal information (POPIA s18, PAIA s51(1)(c))

### Purpose of processing
{{#each purposes}}
- {{this.purpose}}
{{else}}
- [[TODO: purposes]]
{{/each}}

### Categories of data subjects and their personal information
{{#each data_subject_types}}
- {{this}}
{{else}}
- [[TODO: data_subject_types]]
{{/each}}

Categories of information: {{data_categories_text}}

### Recipients or categories of recipients
{{#each operators}}
- {{this.name}} ({{this.service}})
{{else}}
- [[TODO: operators]]
{{/each}}

### Planned transborder flows
{{#if has_cross_border}}
{{cross_border_countries_text}}. Transfers are made under s72(1) of POPIA.
{{else}}
None planned.
{{/if}}

### Security measures
{{security_summary}}

## 12. Availability of this manual

This manual is available on {{website}}, at our physical address, and from the Information Officer on request. VERIFY whether you must also submit it to the Regulator.
