"""Consent, trackers, marketing, special personal information and children. POPIA s11, s18, s26, s34, s69."""
import re

from popia_scan import Rule

UI = ["*.js", "*.jsx", "*.ts", "*.tsx", "*.vue", "*.svelte", "*.astro", "*.html", "*.htm", "*.php", "*.liquid",
      "*.hbs", "*.ejs", "*.dart", "*.swift", "*.kt"]
SCHEMA = ["*.sql", "*.prisma", "*.ts", "*.tsx", "*.js", "*.jsx", "*.py", "*.rb", "*.php", "*.json", "*.dart",
          "*.vue", "*.svelte", "*.html"]
NOT_TESTS = ["*test*", "*spec*", "*.md", "*registry/popia/*"]

TRACKERS = {
    "Google Analytics / gtag": r"googletagmanager\.com/gtag/js|gtag\(\s*['\"]config['\"]|google-analytics\.com/analytics\.js|\bga\(\s*['\"]create",
    "Google Tag Manager": r"googletagmanager\.com/gtm\.js|GTM-[A-Z0-9]{5,}",
    "Meta Pixel": r"connect\.facebook\.net/[^'\"]*/fbevents\.js|\bfbq\(\s*['\"]init",
    "TikTok Pixel": r"analytics\.tiktok\.com|\bttq\.load\(",
    "LinkedIn Insight": r"snap\.licdn\.com/li\.lms-analytics|_linkedin_partner_id",
    "Hotjar": r"static\.hotjar\.com|\bhj\(\s*['\"]",
    "Microsoft Clarity": r"clarity\.ms/tag|\bclarity\(\s*['\"]",
    "X/Twitter Pixel": r"static\.ads-twitter\.com|\btwq\(",
    "Snap Pixel": r"sc-static\.net/scevent|\bsnaptr\(",
    "Pinterest Tag": r"s\.pinimg\.com/ct/core\.js|\bpintrk\(",
    "Google Ads": r"googleadservices\.com|AW-\d{6,}",
    "Segment": r"cdn\.segment\.com|analytics\.load\(",
    "Mixpanel": r"cdn\.mxpnl\.com|mixpanel\.init\(",
    "Amplitude": r"cdn\.amplitude\.com|amplitude\.(getInstance|init)\(",
    "PostHog": r"posthog\.init\(|app\.posthog\.com|eu\.posthog\.com",
    "Heap": r"cdn\.heapanalytics\.com|heap\.load\(",
    "FullStory": r"fullstory\.com/s/fs\.js|_fs_org",
    "LogRocket": r"LogRocket\.init\(",
    "Vercel Analytics": r"@vercel/analytics",
    "Plausible": r"plausible\.io/js",
}
TRACKER_RX = re.compile("|".join(f"(?:{p})" for p in TRACKERS.values()), re.I)

CONSENT_SIGNALS = re.compile(
    r"consent|cookiebot|onetrust|cookieyes|klaro|osano|iubenda|termly|complianz|cookie-?banner|"
    r"cookie-?consent|usercentrics|didomi|ConsentGate|useConsent|gtag\(\s*['\"]consent['\"]", re.I)

SPECIAL_FIELDS = re.compile(
    r"""(?:name|id|field|column|key|label)\s*[=:]\s*["'`]?\s*(race|ethnicity|ethnic_?group|population_?group|religion|"""
    r"""religious|faith|church|denomination|health|medical|diagnosis|condition|disability|hiv|allerg\w*|chronic\w*|"""
    r"""medication|pregnan\w*|sexual_?orientation|sexuality|sex_?life|trade_?union|union_?member\w*|political\w*|"""
    r"""party_?affiliation|criminal\w*|conviction\w*|offen[cs]e\w*|biometric\w*|fingerprint\w*|face_?(id|template|embedding)|"""
    r"""retina|iris|voice_?print|selfie)\b""", re.I)
SPECIAL_COLUMNS = re.compile(
    r"""^\s*["`]?(race|ethnicity|population_group|religion|health_\w+|medical_\w+|diagnosis|disability|hiv_status|"""
    r"""sexual_orientation|trade_union\w*|political_\w+|criminal_\w+|biometric\w*|fingerprint\w*|face_embedding|"""
    r"""face_template|voice_print)["`]?\s+(text|varchar|jsonb?|boolean|bool|int|integer|bytea|vector|enum|character)""",
    re.I)

CHILD_FIELDS = re.compile(
    r"""(?:name|id|field|column|key)\s*[=:]\s*["'`]?\s*(date_?of_?birth|dob|birth_?date|birthday|age|grade|school(_?name)?|"""
    r"""learner\w*|parent_?(name|email|phone)|guardian\w*)\b|^\s*["`]?(date_of_birth|dob|birth_date|grade|school_name|"""
    r"""guardian_\w+|parent_\w+)["`]?\s+(date|text|varchar|int|integer)""", re.I)

PRETICKED = re.compile(
    r"""(defaultChecked(\s*=\s*\{?\s*true\s*\}?)?(?![\w=])|checked(\s*=\s*\{?\s*(true|["']checked["'])\s*\}?)?(?=[\s/>])|"""
    r"""value\s*:\s*true|defaultValue\s*[:=]\s*\{?\s*true|useState\(\s*true\s*\))""")
CONSENT_WORDS = re.compile(r"marketing|newsletter|promot|offers|subscribe|consent|opt.?in|updates|partners|third.?part|agree", re.I)


def _trackers_without_consent(ctx):
    found = []
    for rel, text in ctx.files.items():
        if any(x in rel.lower() for x in ("test", "spec", "fixture", "registry/popia", ".md")):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if len(line) > 4000:
                continue
            m = TRACKER_RX.search(line)
            if m:
                name = next((n for n, p in TRACKERS.items() if re.search(p, line, re.I)), "tracker")
                found.append((rel, i, name, line.strip()))
    if not found:
        return []
    has_consent = any(CONSENT_SIGNALS.search(t) for r, t in ctx.files.items()
                      if not r.endswith(".md") and "registry/popia" not in r)
    if has_consent:
        return []
    out, seen = [], set()
    for rel, i, name, line in found:
        if (rel, name) in seen:
            continue
        seen.add((rel, name))
        out.append({"file": rel, "line": i, "snippet": line, "extra": f"{name} loaded; no consent mechanism found in repo."})
    return out


def _trackers_inventory(ctx):
    out, seen = [], set()
    for rel, text in ctx.files.items():
        if any(x in rel.lower() for x in ("test", "spec", "fixture", "registry/popia", ".md")):
            continue
        for name, pat in TRACKERS.items():
            if name in seen:
                continue
            m = re.search(pat, text, re.I)
            if m:
                seen.add(name)
                line = text[:m.start()].count("\n") + 1
                out.append({"file": rel, "line": line, "snippet": name,
                            "extra": f"{name}: record as operator, check s72 basis, confirm it loads only after consent."})
    return out


def _preticked(rel, text):
    hits = []
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        if not PRETICKED.search(line):
            continue
        if not re.search(r"checkbox|Checkbox|Switch|toggle|type=[\"']checkbox|consent|marketing|optIn|opt_in|subscribe", line):
            # look a little around for a checkbox context
            window = " ".join(lines[max(0, i - 4): i + 3])
            if not re.search(r"checkbox|Checkbox|Switch", window):
                continue
        window = " ".join(lines[max(0, i - 6): i + 6])
        if CONSENT_WORDS.search(window):
            hits.append({"line": i})
    return hits


def _special_fields(rel, text):
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        m = SPECIAL_FIELDS.search(line) or (rel.endswith(".sql") and SPECIAL_COLUMNS.search(line))
        if m:
            hits.append({"line": i, "extra": f"field '{m.group(1)}'"})
    return hits[:20]


def _child_fields(rel, text):
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        m = CHILD_FIELDS.search(line)
        if m:
            hits.append({"line": i})
    return hits[:5]


RULES = [
    Rule(
        id="CON-001", title="Tracking or marketing tags with no consent mechanism", severity="high",
        popia="s11; s18; s69 (Reg guidance)", kind="repo", repo_check=_trackers_without_consent,
        message="Analytics and advertising tags collect online identifiers (personal information) and share "
                "them with offshore operators. Loading them before a choice is made is unlikely to meet POPIA's "
                "consent and notice requirements, and the Regulator's direct marketing guidance treats cookies "
                "used for marketing as in scope.",
        fix="Add a consent banner that blocks tags until opt-in (registry/popia/consent). Set Google Consent "
            "Mode defaults to denied. Disclose tools in the cookie notice.",
        confidence="medium", tags=["consent", "trackers"],
    ),
    Rule(
        id="XB-002", title="Third-party tracker detected (record and gate)", severity="info",
        popia="s18; s20; s21; s72", kind="repo", repo_check=_trackers_inventory,
        message="Each tracker is an operator receiving personal information, usually outside South Africa.",
        fix="Add to the ROPA with purpose, data sent, country, DPA and s72 basis. Confirm it fires only after consent.",
        confidence="high", tags=["trackers", "cross-border"],
    ),
    Rule(
        id="CON-002", title="Pre-ticked consent or marketing checkbox", severity="high", popia="s1 (consent); s11; s69",
        kind="file", include=UI, exclude=NOT_TESTS, file_check=_preticked,
        message="Consent must be a voluntary, specific and informed expression of will. A pre-ticked box is "
                "not that, and opt-out is not valid consent for electronic direct marketing (Regs as amended 2025).",
        fix="Default to unchecked. Separate checkboxes per purpose and channel. Record the consent event.",
        confidence="medium", tags=["consent", "marketing"],
    ),
    Rule(
        id="SPI-001", title="Special personal information field", severity="medium", popia="s26; s27; s57",
        kind="file", include=SCHEMA, exclude=NOT_TESTS + ["*node_modules*"], file_check=_special_fields,
        message="Race, religion, health, disability, sex life, union membership, political views, criminal "
                "behaviour and biometrics are special personal information. Processing is prohibited unless a "
                "s27 ground (often explicit consent) or a specific authorisation (s28 to s33) applies.",
        fix="Confirm the s27 ground or remove the field. Separate explicit consent, stricter access, field "
            "encryption, exclusion from analytics and AI training, and a PIA.",
        confidence="low", tags=["special-pi"],
    ),
    Rule(
        id="CHI-001", title="Date of birth, age or school field: check for children", severity="info",
        popia="s34; s35", kind="file", include=SCHEMA, exclude=NOT_TESTS + ["*node_modules*"],
        file_check=_child_fields,
        message="If anyone under 18 can use the service, processing their information needs a s35 ground, "
                "usually prior consent of a competent person (parent or guardian).",
        fix="Decide whether children are in scope. Add an age gate or a parental consent flow. Minimise data.",
        confidence="low", tags=["children"],
    ),
    Rule(
        id="CON-003", title="Bundled consent wording", severity="medium", popia="s1 (consent); s11; s69",
        pattern=r"by\s+(continuing|signing up|registering|submitting|clicking|using)[^.\n]{0,80}(agree|consent|accept)[^.\n]{0,80}(marketing|newsletter|offers|promotional|third.?part|partners)",
        include=UI, exclude=NOT_TESTS,
        message="Consent bundled into terms or 'by continuing' wording isn't specific or voluntary, and doesn't "
                "meet the s69 opt-in standard for electronic marketing.",
        fix="Separate the marketing consent into its own optional, unticked checkbox.",
        confidence="medium", tags=["consent", "marketing"],
    ),
]
