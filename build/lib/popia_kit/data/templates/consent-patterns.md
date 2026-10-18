> Draft template. Engineering and compliance guidance, not legal advice. Have it reviewed by a qualified South African privacy attorney before use. See DISCLAIMER.md.

# Consent and notice wording: {{display_name}}

A wording library for {{company_legal_name}}. Each pattern names the section it serves, gives sample wording, and lists do and don't rules. Store every consent as an event with the exact wording version shown (see `privacy.consent_events` in references/02-build-patterns.md §3).

General rules for every consent:

- Consent must be voluntary, specific and informed (s1). The burden of proof is on the responsible party (s11(2)(a)).
- Unticked by default. One checkbox per purpose. Never bundle with terms and conditions.
- Withdrawal must be as easy as giving consent (s11(2)(b)).
- Opt-out mechanisms are not valid consent (amended Regulations, 2025).

{{#if marketing_any}}
## Direct marketing by electronic communication (s69, Reg 6, Form 4)

Wording must be substantially similar to Form 4. That means it includes: the identity and contact details of the responsible party, the goods or services to be marketed, the channel, a clear choice to consent or not, and a recorded confirmation and date. You may ask a non-customer for consent only once, and not again if they refused (s69(2)).

{{#if marketing_existing_customer_exception}}
**Existing-customer exception (s69(1)(b)).** You may market your own similar products or services to customers whose details you got in the context of a sale, without opt-in, only if you gave them a free, simple chance to opt out at collection and in every message, and they did not opt out. Show this at checkout:

> ☐ Do not send me news and offers about similar {{company_display}} products and services. You can also opt out in any message.

Do: limit to own similar products, and include an opt-out in every message.
Don't: use the exception for non-customers, unrelated products, or partners' products.

{{/if}}
{{#if marketing_email}}
### Email

> ☐ Yes, {{company_legal_name}} may send me marketing about {{marketing_products}} by **email**. I can withdraw at any time using the unsubscribe link or by emailing {{dsar_email}}.

Do: send a confirmation email that records the date, include `List-Unsubscribe` and `List-Unsubscribe-Post` headers, identify the sender in every message (s69(4)).
Don't: pre-tick the box, hide consent in terms, or keep sending after an unsubscribe.

{{/if}}
{{#if marketing_sms}}
### SMS

> ☐ Yes, {{company_legal_name}} may send me marketing about {{marketing_products}} by **SMS**. I can reply STOP at any time or email {{dsar_email}}.

Do: include the sender name and "Reply STOP to opt out" in every SMS.
Don't: rely on a CPA block register check instead of POPIA consent. Do both.

{{/if}}
{{#if marketing_whatsapp}}
### WhatsApp

> ☐ Yes, {{company_legal_name}} may send me marketing about {{marketing_products}} on **WhatsApp** to the number I provided. I can reply STOP at any time or email {{dsar_email}}.

Do: keep WhatsApp consent separate from SMS consent, and honour STOP across all channels.
Don't: treat a customer messaging you on WhatsApp for support as consent to marketing.

{{/if}}
{{#if marketing_phone}}
### Phone calls

> ☐ Yes, {{company_legal_name}} may **phone** me about {{marketing_products}}. I can ask to stop at any time on a call or by emailing {{dsar_email}}.

Do: treat calls (including live and VoIP calls) as s69 electronic communication until a court decides otherwise. Identify the caller and the business at the start of every call.
Don't: cold call from purchased lists.

{{/if}}
{{#if marketing_push}}
### Push notifications and in-app messages

> ☐ Yes, {{company_legal_name}} may send me offers about {{marketing_products}} as **push notifications**. I can turn this off in Settings at any time.

Do: keep marketing pushes behind their own toggle, separate from service notifications.
Don't: use the operating system notification permission as marketing consent.

{{/if}}
Every marketing message must contain the sender's identity and an address or contact details for a stop request (s69(4)).

{{/if}}
{{#if has_special_pi}}
## Special personal information: explicit consent (s26, s27(1)(a))

Use only where consent is the s27 ground. Name the exact category and the exact use.

> ☐ I agree that {{company_legal_name}} may process special personal information about me (**{{special_pi_text}}**) to {{special_pi_purpose}}. I understand this is optional, that it is special personal information, and that I can withdraw consent at any time by emailing {{dsar_email}}.

Do: make it optional unless the ground makes it necessary, store it separately with stricter access, exclude it from analytics, marketing and AI training.
Don't: combine it with any other consent, or use vague wording such as "health and other information".

{{/if}}
{{#if children}}
## Children: competent person consent (s34, s35(1)(a))

Ask the parent or guardian, not the child. Record who gave consent (`competent_person_id`).

> I am the parent or legal guardian of **[child's name]**. I give consent for {{company_legal_name}} to process my child's personal information to {{children_purpose}}. I understand I can review this information and refuse further processing at any time by emailing {{dsar_email}}.
>
> ☐ I confirm I am the parent or legal guardian and I consent.

Do: verify the competent person proportionately, collect the minimum, explain what is collected in plain language.
Don't: let the child tick the box, use children's data for behavioural advertising, or encourage children to share more than needed.

{{/if}}
{{#if cross_border_consent}}
## Cross-border transfer consent (s72(1)(b))

Use only where consent is the s72 ground. A binding agreement under s72(1)(a) is usually better, because withdrawal breaks a consent-based transfer.

> ☐ I agree that {{company_legal_name}} may send my {{cross_border_data}} to {{cross_border_recipient}} in **{{cross_border_countries_text}}** so that {{cross_border_purpose}}. I understand the protection there may differ from South African law.

Do: say where, why and what the risk is.
Don't: rely on consent alone for special PI or children's PI going to a country without adequate protection. That needs prior authorisation (s57(1)(d)).

{{/if}}
{{#if ai_features}}
## AI processing notice (s18, s20, s72)

This is a notice, not a consent, unless consent is your lawful basis. Show it where the user interacts with the AI feature.

> {{company_display}} uses an AI service provided by {{ai_provider}} to {{ai_purpose}}. Your messages are sent to {{ai_provider}} in {{ai_provider_country}} and kept for {{ai_retention}}. They are not used to train AI models. Do not share ID numbers, bank details or health information here. See our Privacy Notice.

Do: tell users when they are interacting with AI, minimise what is sent, disable provider training.
Don't: use customer data to train models without a s15 compatibility assessment or consent.

{{/if}}
{{#if call_recording}}
## Call recording notice (s18)

Play at the start of every recorded call, before any personal information is discussed.

> This call is recorded by {{company_legal_name}} for {{call_recording_purpose}}. Recordings are kept for {{call_recording_retention}}. You can ask for the recording or object by contacting {{dsar_email}}.

Do: give the caller a way to continue without recording where the service allows it.
Don't: create voiceprints or use voice recognition from recordings. That is biometric special PI and needs a s27 ground.

{{/if}}
## Version control

| Pattern | Version | Date approved | Approved by |
|---|---|---|---|
| | | | |
