> Draft template. Engineering and compliance guidance, not legal advice. Have it reviewed by a qualified South African privacy attorney before use. See DISCLAIMER.md.

# Cookie notice: {{display_name}}

**Effective date:** {{effective_date}}

This notice explains the cookies and similar technologies (pixels, local storage, SDKs) used on {{website}} by {{company_legal_name}}. Read it with our Privacy Notice.

## What cookies are

Cookies are small files stored on your device. Similar technologies, such as pixels and local storage, work in the same way. Some are set by us. Others are set by third parties we use. Information collected through them can be personal information.

## Your choices

- **Strictly necessary** cookies are always on. The site cannot work without them.
- **Analytics** and **marketing** cookies only load after you choose to allow them.
- "Accept all" and "Reject all" are equally easy to use.
- You can change your choice at any time using the "Cookie settings" link in the footer. Withdrawing consent is as easy as giving it.

## Cookies we use

### Strictly necessary

These keep the site secure and working, for example session, security (CSRF) and load-balancing cookies. They do not need consent but we disclose them here.

| Name | Provider | Purpose | Duration |
|---|---|---|---|
{{#each necessary_cookies}}
| {{this.name}} | {{this.provider}} | {{this.purpose}} | {{this.duration}} |
{{/each}}
| cookie_consent | {{company_legal_name}} | Remembers your cookie choices | 12 months |

{{#if analytics_tools}}
### Analytics (only with your consent)

These help us understand how the site is used so we can improve it.

| Tool | Provider country | Purpose | Duration |
|---|---|---|---|
{{#each analytics_tools}}
| {{this.name}} | {{this.country}} | {{this.purpose}} | {{this.duration}} |
{{/each}}

{{/if}}
{{#if marketing_tools}}
### Marketing (only with your consent)

These measure advertising and may be used to show you ads on other sites.

| Tool | Provider country | Purpose | Duration |
|---|---|---|---|
{{#each marketing_tools}}
| {{this.name}} | {{this.country}} | {{this.purpose}} | {{this.duration}} |
{{/each}}

{{/if}}
{{#unless analytics_tools}}
{{#unless marketing_tools}}
We do not use analytics or marketing cookies.

{{/unless}}
{{/unless}}
## Transfers outside South Africa

Some cookie providers process information outside South Africa. See "Transfers outside South Africa" in our Privacy Notice (s18(1)(g), s72).

## Keeping this notice accurate

We review this list when we add or remove a tool, and at least every {{cookie_review_months}} months. Run `scripts/site_check.py` to confirm the site sets only the cookies listed here.

## Contact

Questions about cookies: {{dsar_email}}. Information Officer: {{io_name}}, {{io_email}}.
