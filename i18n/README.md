# Translations

Short, plain-language versions of the notices people see most: the collection notice, marketing consent, cookie banner and a short breach notice. English sources are in `i18n/en/`.

## Why this exists

s18(1) of POPIA requires a responsible party to take reasonably practicable steps to make the data subject aware of specific information at collection. A notice the person cannot understand does not make them aware. South Africa has 12 official languages. Many users read more easily in a language other than English.

Consent must also be informed (s1). Marketing consent that a person cannot read is weak evidence under s11(2)(a), where the burden of proof sits with the responsible party.

## Status

Do not use a translation in production until its status here is **reviewed**. Every draft file starts with a warning in English and in the target language.

| Language | Code | Files | Status | Reviewer |
|---|---|---|---|---|
| English (source) | en | collection-notice.md, marketing-consent.md, cookie-banner.json, breach-notice-short.md | source | Not applicable |
| Afrikaans | af | collection-notice.md, marketing-consent.md, cookie-banner.json, breach-notice-short.md | draft | Wanted |
| isiZulu | zu | collection-notice.md, marketing-consent.md, cookie-banner.json, breach-notice-short.md | draft | Wanted |
| isiXhosa | xh | collection-notice.md, marketing-consent.md, cookie-banner.json, breach-notice-short.md | draft | Wanted |
| Setswana | tn | collection-notice.md, marketing-consent.md, cookie-banner.json, breach-notice-short.md | draft | Wanted |

Languages we would like next: Sepedi (nso), Sesotho (st), Xitsonga (ts), siSwati (ss), Tshivenda (ve), isiNdebele (nr), South African Sign Language (sasl, as video or glossed text).

## Files

| File | Use | Sections |
|---|---|---|
| collection-notice.md | Short notice next to a form | s18(1), s11(3), s23, s24, s72 |
| marketing-consent.md | Opt-in checkbox wording, one per channel | s69, Reg 6 / Form 4 (substantially similar) |
| cookie-banner.json | UI strings for a cookie banner | s18, s69 guidance |
| breach-notice-short.md | Short s22 notice for SMS, email or web | s22(5) |

`{{placeholders}}` stay in English so code can fill them. The values you put into them must be in the same language as the notice.

## How to review a translation

You do not need to be a lawyer. You do need to be a fluent reader of the language. A legal reviewer is welcome too.

1. Read the English source and the translation side by side.
2. **Plain language.** Use words an ordinary adult reader would use. Prefer short sentences. Avoid formal or archaic terms where a common word exists.
3. **Keep the legal meaning.** Do not soften or strengthen any statement. In particular, keep these meanings exact:
   - "optional" vs "required"
   - "you do not have to tick this box" (consent is voluntary)
   - "you can stop at any time" (withdrawal)
   - "may have accessed" (a compromise is suspected, not proven)
   - "complain to the Information Regulator"
4. **Keep section references** and HTML comments as they are (for example `s18(1)`, `s22(5)`). Keep the English name of a body in brackets after the translated name the first time it appears, for example the Information Regulator and SAFPS.
5. **Keep placeholders** exactly, including the braces.
6. **Keep the cookie-banner.json keys** in English. Translate only the values. Button labels must be short, and "Accept all" and "Reject all" must be equally clear.
7. Do not add an exclamation mark or an em dash. Follow the repository style rules.

## How to contribute

1. Fork https://github.com/VenusOne-Lee/popia-compliance and create a branch, for example `i18n-zu-review`.
2. Edit the files in the language folder.
3. When a file is reviewed, remove both warning lines at the top (and the `_warning` keys in cookie-banner.json), set `"status": "reviewed"` in cookie-banner.json, and update the status table above.
4. Add yourself in the Reviewer column. Use your name, and your organisation if you want. Say whether you reviewed language, legal meaning, or both.
5. Open a pull request. Say which files you reviewed and what you changed.

A new language: copy `i18n/en/` to a new folder named with its ISO 639 code, translate, add the warnings in English and in the new language, and add a row to the table with status **draft**.

## Reviewer credits

| Language | Reviewer | Scope | Date |
|---|---|---|---|
| | | | |

Thank you to everyone who reviews. A notice people can read is a notice that works.

## Disclaimer

Translations are engineering and compliance guidance, not legal advice. Have the final wording reviewed by a qualified South African privacy attorney. See DISCLAIMER.md.
