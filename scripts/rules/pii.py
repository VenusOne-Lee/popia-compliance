"""Personal information in code, fixtures, logs, URLs and client storage."""
import re

from popia_scan import Rule
from sa_id import is_valid as sa_id_valid, is_synthetic

DATA = ["*.js", "*.jsx", "*.ts", "*.tsx", "*.mjs", "*.cjs", "*.vue", "*.svelte", "*.py", "*.rb", "*.php", "*.go",
        "*.java", "*.kt", "*.swift", "*.dart", "*.cs", "*.sql", "*.json", "*.yaml", "*.yml", "*.csv", "*.html",
        "*.xml", "*.toml"]
CODE = ["*.js", "*.jsx", "*.ts", "*.tsx", "*.mjs", "*.cjs", "*.vue", "*.svelte", "*.astro", "*.py", "*.rb",
        "*.php", "*.go", "*.java", "*.kt", "*.swift", "*.dart", "*.cs"]
LOCKFILES = ["*package-lock.json", "*yarn.lock", "*pnpm-lock.yaml", "*composer.lock", "*Gemfile.lock",
             "*poetry.lock", "*.min.js", "*.map"]


def _real_sa_id(m, line):
    v = m.group(1)
    # sa_id.fake() marks synthetic IDs with an A digit of 0
    return sa_id_valid(v) and not is_synthetic(v)


def _luhn(num: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(num)):
        n = int(ch)
        if i % 2:
            n = n * 2 - 9 if n > 4 else n * 2
        total += n
    return total % 10 == 0


TEST_CARDS = {"4242424242424242", "4111111111111111", "5555555555554444", "4000056655665556",
              "378282246310005", "6011111111111117", "5105105105105100", "4012888888881881"}


def _card(m, line):
    digits = re.sub(r"[ -]", "", m.group(1))
    if digits in TEST_CARDS or len(set(digits)) < 4:
        return False
    if len(digits) == 13 and sa_id_valid(digits):
        return False  # an SA ID number, handled by PII-001
    if re.search(r"(uuid|guid|hash|sha|id\b|_id|timestamp|epoch|version|sku|order)", line, re.I):
        return False
    return 13 <= len(digits) <= 19 and _luhn(digits)


RULES = [
    Rule(
        id="PII-001", title="Valid SA ID number in code or data files", severity="high", popia="s19; s10; s57",
        pattern=r"(?<![\d.])(\d{13})(?![\d.])", flags=0, include=DATA, exclude=LOCKFILES,
        validator=_real_sa_id,
        message="A 13-digit value passes SA ID validation (date + Luhn). Real ID numbers in repos, seeds, "
                "fixtures or exports are personal information outside your access controls and reveal date "
                "of birth, sex and citizenship.",
        fix="Remove it and purge from history. Use synthetic IDs for tests (scripts/sa_id.py fake). "
            "If this is production data, treat as a possible security compromise (references/07).",
        confidence="medium", tags=["pii", "sa-id"],
    ),
    Rule(
        id="PII-003", title="Possible payment card number", severity="critical", popia="s19; s105",
        pattern=r"(?<![\d])((?:\d[ -]?){12,18}\d)(?![\d])", flags=0, include=DATA, exclude=LOCKFILES,
        validator=_card,
        message="A Luhn-valid 13 to 19 digit number that isn't a known test card. Card numbers must never "
                "be stored outside a PCI DSS environment. Account number misuse is a POPIA offence (s105, s106).",
        fix="Remove and purge. Use payment provider tokens. If real, start breach triage.",
        confidence="low", tags=["pii", "financial"],
    ),
    Rule(
        id="PII-002", title="SA mobile number or personal email in seed or fixture data", severity="low",
        popia="s19; s15",
        pattern=r"((?:\+27|\b0)[6-8]\d[ -]?\d{3}[ -]?\d{4}\b)|([A-Za-z0-9._%+-]+@(?:gmail|yahoo|outlook|hotmail|icloud|webmail|mweb|telkomsa|vodamail)\.(?:com|co\.za|net))",
        include=["*seed*", "*fixture*", "*mock*", "*.csv", "*sample*", "*data*.json"],
        exclude=LOCKFILES,
        message="Seed and fixture files often get copied from production. Real contact details here are "
                "personal information used for a purpose they weren't collected for.",
        fix="Replace with synthetic data (example.com addresses, +27 10 000 0000 style numbers).",
        confidence="low", tags=["pii", "test-data"],
    ),
    Rule(
        id="LOG-001", title="Personal information or secrets written to logs", severity="medium",
        popia="s19; s14",
        pattern=r"(?:console\.(?:log|info|warn|error|debug)|logger\.\w+|log\.\w+|print|logging\.\w+|Log\.\w|println|fmt\.Print\w*|error_log)\s*\(.*\b(email|e_mail|phone|mobile|cell|msisdn|id_?number|idNumber|identity_?number|sa_?id|passport|password|passwd|token|secret|authorization|dob|date_?of_?birth|account_?number|card_?number|address|req\.body|request\.body|body\b|user\b|customer\b|patient)",
        include=CODE, exclude=["*test*", "*spec*"],
        message="Logs end up in offshore log tools, with wide access and long retention. PI in logs escapes "
                "your access controls and deletion processes.",
        fix="Log identifiers and events, not values. Add a redaction layer to the logger "
            "(registry/popia/lib/redact.ts). Scrub error trackers with beforeSend.",
        confidence="medium", tags=["pii", "logging"],
    ),
    Rule(
        id="PII-004", title="Personal information in URL or query string", severity="medium", popia="s19",
        pattern=r"""[?&](email|e-mail|phone|mobile|id_?number|idnumber|sa_?id|passport|dob|full_?name|first_?name|surname|token)=""",
        include=CODE + ["*.html"], exclude=["*test*", "*spec*"],
        message="Query strings are stored in server logs, browser history, analytics tools and Referer headers. "
                "PI there leaks to every tool on the page.",
        fix="Send PI in POST bodies or keep it server-side; pass an opaque ID instead.",
        confidence="medium", tags=["pii", "web"],
    ),
    Rule(
        id="STO-001", title="Personal information or tokens in browser storage", severity="medium", popia="s19",
        pattern=r"(?:localStorage|sessionStorage|AsyncStorage|SharedPreferences)\s*\.?\s*(?:setItem|set|putString)\s*\(\s*['\"`][^'\"`]*(email|phone|id_?number|idnumber|sa_?id|dob|address|passport|token|jwt|password|user|profile)",
        include=CODE,
        message="Browser and plain device storage is readable by any script on the page (XSS, third-party "
                "tags) and survives logout.",
        fix="Keep PI server-side. Store auth in HttpOnly cookies or platform secure storage (Keychain/Keystore).",
        confidence="medium", tags=["pii", "storage"],
    ),
]

RULES.append(Rule(
    id="PII-005", title="High-risk identifier stored in a plain column", severity="medium", popia="s19; s105",
    pattern=r"""^\s*["`]?(id_?number|sa_?id(_number)?|identity_?number|national_?id|passport(_?number)?|tax_?number|account_?number|bank_?account(_number)?|card_?number|medical_?aid_?number)["`]?\s+(text|varchar|character varying|char|bigint|numeric|int8)""",
    include=["*.sql", "*.prisma"],
    message="ID, passport, tax, bank and medical aid numbers enable identity fraud. Account number misuse is "
            "a POPIA offence (s105, s106). Plain columns are exposed by any access-control slip.",
    fix="Question whether you need it (s10). If you do: field-level encryption or tokenisation, a blind "
        "index for lookups, masked display, restricted role access, and access logging.",
    confidence="medium", tags=["pii", "sa-id", "encryption"],
))
