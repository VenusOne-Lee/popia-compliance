> Draft template. Engineering and compliance guidance, not legal advice. Have it reviewed by a qualified South African privacy attorney before use. See DISCLAIMER.md.

# Privacy notice: {{display_name}}

**Effective date:** {{effective_date}}
**Version:** {{notice_version}}

## About this notice

This notice explains how {{company_legal_name}} ("we", "us") processes personal information under the Protection of Personal Information Act 4 of 2013 (POPIA). It applies to {{website}} and to {{products_services}}.

It applies to these groups of people (data subjects):

{{#each data_subject_types}}
- {{this}}
{{else}}
- [[TODO: data_subject_types]]
{{/each}}

{{#if includes_juristic_persons}}
POPIA also protects existing juristic persons, such as companies. This notice applies to information about businesses we deal with and the people who work for them.

{{/if}}
{{#unless children}}
We do not knowingly collect personal information of children under 18. If we learn that we have, we will delete it unless a competent person (a parent or guardian) consents or another s35 ground applies.

{{/unless}}
## Who we are (s18(1)(b))

| | |
|---|---|
| Responsible party | {{company_legal_name}} |
| Registration number | {{company_reg_number}} |
{{#if trading_name}}
| Trading as | {{trading_name}} |
{{/if}}
| Physical address | {{physical_address}} |
{{#if postal_address}}
| Postal address | {{postal_address}} |
{{/if}}
| Website | {{website}} |

**Information Officer:** {{io_name}}, {{io_email}}, {{io_phone}}

{{#if dios}}
**Deputy Information Officer(s):**

{{#each dios}}
- {{this.name}}, {{this.email}}
{{/each}}

{{/if}}
## What information we collect and where we get it (s18(1)(a))

We collect these categories of personal information:

{{#each data_categories}}
- {{this}}
{{else}}
- [[TODO: data_categories]]
{{/each}}

{{#if has_special_pi}}
Some of this is special personal information under s26: {{special_pi_text}}. See "Special personal information" below.

{{/if}}
{{#if children}}
We process personal information of children. See "Children" below.

{{/if}}
Most information comes directly from you. {{#if other_sources}}We also receive information from these sources: {{other_sources}}.{{else}}We do not collect your personal information from other sources.{{/if}}

## Why we collect it and our lawful basis (s18(1)(c))

We only use your information for these purposes. Each purpose has a lawful basis under s11(1).

| Purpose | Information used | Lawful basis |
|---|---|---|
{{#each purposes}}
| {{this.purpose}} | {{this.data}} | {{this.lawful_basis_text}} |
{{else}}
| [[TODO: purposes]] | | |
{{/each}}

If we want to use your information for a new purpose, we will check that it is compatible with the original purpose (s15) or ask for your consent.

## Is providing information voluntary or mandatory (s18(1)(d))

{{collection_mandatory_info}}

Fields that are optional are marked as optional on our forms.

## What happens if you do not provide it (s18(1)(e))

{{consequences_of_not_providing}}

## Laws that authorise or require collection (s18(1)(f))

{{#if laws_requiring_collection}}
{{laws_requiring_collection}}
{{else}}
No specific law requires us to collect your personal information. We collect it for the purposes listed under "Why we collect it".
{{/if}}

## Who we share it with (s18(1)(h))

We do not sell your personal information. We share it with operators that process it on our behalf under written agreements that require them to keep it secure and confidential (s20, s21).

| Operator | Service | Information shared | Country |
|---|---|---|---|
{{#each operators}}
| {{this.name}} | {{this.service}} | {{this.data}} | {{this.country}} |
{{else}}
| [[TODO: operators]] | | | |
{{/each}}

We may also share information where a law requires it, for example with a regulator, SARS or a court.

## Transfers outside South Africa (s18(1)(g))

{{#if has_cross_border}}
Some of our operators store or process your information outside South Africa, in: {{cross_border_countries_text}}.

We only transfer personal information outside South Africa on a ground in s72(1). Our default is a binding agreement that requires the recipient to protect your information in a way substantially similar to POPIA, including rules on onward transfer (s72(1)(a)). The protection in the destination country may differ from South African law.

{{#if has_special_or_children}}
We do not transfer special personal information or children's personal information to a country without an adequate level of protection unless we have prior authorisation from the Information Regulator (s57(1)(d)).

{{/if}}
{{else}}
We do not transfer your personal information outside South Africa. Our systems are hosted in {{hosting_region}}.
{{/if}}

{{#if has_marketing}}
## Direct marketing (s69)

We only send marketing by electronic communication ({{marketing_channels_text}}) if:

- you have opted in to receive it, or
{{#if marketing_existing_customer_exception}}
- you are our customer, we got your contact details when you bought from us, and the marketing is about our own similar products or services. We give you a chance to opt out when we collect your details and in every message.
{{else}}
- another ground in s69 applies. We do not rely on the existing-customer exception.
{{/if}}

Opting out is not treated as consent. Every marketing message identifies us and tells you how to stop further messages (s69(4)). You can also object to direct marketing at any time (s11(3)(b)) by contacting {{dsar_email}}.

{{/if}}
## Cookies and similar technologies

We use cookies and similar technologies on our website and apps. Strictly necessary cookies are always on. We only load analytics or marketing cookies after you choose to allow them. See our Cookie Notice at {{cookie_notice_url}} for the full list and how to change your choices.

{{#if ai_features}}
## AI features

{{ai_description}}

Our AI providers are listed under "Who we share it with". They act as our operators. We send them the minimum information needed. We do not use special personal information in AI features unless a s27 ground applies.

{{/if}}
## Automated decisions (s71)

{{#if automated_decisions}}
{{automated_decisions_description}}

You may make representations about such a decision and ask for a person to review it. We will explain the main factors behind the decision (s71(3)). Contact {{dsar_email}}.
{{else}}
We do not make decisions about you that have legal consequences or affect you to a substantial degree based solely on automated processing.
{{/if}}

## How long we keep it (s14)

We keep personal information only as long as we need it for the purpose, or as long as a law or contract requires.

| Information | Retention period | Starts from |
|---|---|---|
{{#each data_sets}}
| {{this.name}} | {{this.retention}} | {{this.retention_trigger}} |
{{else}}
| [[TODO: data_sets]] | | |
{{/each}}

After that we delete, destroy or de-identify it in a way that prevents reconstruction (s14(4), s14(5)). Backups expire on their normal cycle.

## How we protect it (s19 to s22)

{{security_summary}}

If we have reasonable grounds to believe your personal information was accessed or acquired by an unauthorised person, we will notify the Information Regulator and you as soon as reasonably possible (s22).

{{#if children}}
## Children (s34, s35)

{{children_description}}

We process children's personal information only with the prior consent of a competent person (a parent or guardian) or on another ground in s35(1). How we get that consent: {{children_consent_method}}. We collect the minimum information needed. We do not use children's information for behavioural advertising. A parent or guardian can review the information and refuse further processing by contacting {{dsar_email}}.

{{/if}}
{{#if has_special_pi}}
## Special personal information (s26, s27)

We process these types of special personal information: {{special_pi_text}}.

We use it to {{special_pi_purpose}}. Our ground for processing it is {{special_pi_ground_text}}.

Where consent is the ground, we ask for it separately and you can withdraw it at any time. Access to this information is restricted. We do not use it for marketing or analytics.

{{/if}}
## Your rights (s18(1)(h), s23, s24, s11(3))

You have the right to:

- **Access.** Ask us to confirm, free of charge, whether we hold personal information about you, and ask for a copy or description of it, including the identity of third parties who had access (s23). A fee may apply for a copy, as set out in PAIA. We will tell you before we charge anything.
- **Correction and deletion.** Ask us to correct or delete information that is inaccurate, irrelevant, excessive, out of date, incomplete, misleading or unlawfully obtained, or to destroy a record we may no longer keep (s24). You may use Form 2 from the POPIA Regulations, free of charge.
- **Objection.** Object, on reasonable grounds, to processing based on legitimate interests (s11(1)(d) or (f)), and object at any time to direct marketing (s11(3)). You may use Form 1, free of charge.
- **Withdraw consent.** Where we rely on consent, withdraw it at any time (s11(2)(b)). This does not affect processing before withdrawal.
- **Stop marketing.** Use the unsubscribe link or reply STOP in any marketing message.
{{#if automated_decisions}}
- **Automated decisions.** Make representations about a decision described under "Automated decisions".
{{/if}}
- **Complain.** Lodge a complaint with the Information Regulator (see below).

**How to make a request:** email {{dsar_email}} or write to the Information Officer at the address under "Who we are". We will verify your identity before we act. We will not ask for more information than we already hold. We aim to respond within {{dsar_sla_days}} days.

## Complaints to the Information Regulator (s18(1)(h), s74)

Please contact our Information Officer first so we can try to resolve your concern. You also have the right to lodge a complaint with the Information Regulator, using Form 5 from the POPIA Regulations.

{{regulator_contact}}

Contact details change. Verify the current details on the Regulator's website, https://inforegulator.org.za, before relying on them.

## Changes to this notice

We may update this notice. The effective date at the top shows when it last changed. We will tell you about material changes by {{change_notification_method}}. Earlier versions are available on request.
