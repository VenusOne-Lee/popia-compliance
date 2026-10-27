"""Web and application security patterns that commonly lead to PI exposure. POPIA s19."""
import re

from popia_scan import Rule

CODE = ["*.js", "*.jsx", "*.ts", "*.tsx", "*.mjs", "*.cjs", "*.vue", "*.svelte", "*.astro", "*.py", "*.rb",
        "*.php", "*.go", "*.java", "*.kt", "*.swift", "*.dart", "*.cs"]
CONFIG = ["*.json", "*.yaml", "*.yml", "*.toml", "*.conf", ".htaccess", "*.tf"]
NOT_TESTS = ["*test*", "*spec*", "*fixture*", "*.md"]

# Session or auth cookie names. CSRF cookies are left out: many apps need scripts to read them.
SESSION_NAME = re.compile(r"sess|sid|auth|token|jwt|login|remember", re.I)
# Cookie setters and how many arguments come before the options. Each of these defaults to
# no HttpOnly and no Secure, so a missing flag counts as off.
INSECURE_DEFAULTS = re.compile(r"\b(?:res|response|reply)\.cookie\s*\(|\bcookies\(\)\.set\s*\(|\bsetCookie\s*\(|"
                               r"\.set_cookie\s*\(")
# Setters whose defaults are safe (SvelteKit, Koa, Astro): only an explicit false counts.
SAFE_DEFAULTS = re.compile(r"\bcookies\.set\s*\(")
COOKIE_SETTING = re.compile(r"\b(SESSION_COOKIE_(?:SECURE|HTTPONLY))\b['\"]?\]?\s*=\s*False\b")
SESSION_MW = re.compile(r"\b(?:session|cookieSession)\s*\(")
RAW_HEADER = re.compile(r"Set-Cookie['\"]?\s*[,:]\s*[`'\"]\s*(?:__(?:Host|Secure)-)?(\w+)=([^`'\"]*)", re.I)
STRING = re.compile(r"""(['"`])(?:\\.|(?!\1).)*\1""", re.S)


def _call_args(text, start):
    """Return the text between the parenthesis at start and its match, or None."""
    depth, i, end = 0, start, min(len(text), start + 1500)
    quote = None
    while i < end:
        ch = text[i]
        if quote:
            if ch == "\\":
                i += 1
            elif ch == quote:
                quote = None
        elif ch in "'\"`":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i]
        i += 1
    return None


def _split_args(args):
    out, depth, cur, quote, i = [], 0, "", None, 0
    while i < len(args):
        ch = args[i]
        if quote:
            if ch == "\\" and i + 1 < len(args):
                cur += ch + args[i + 1]
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "'\"`":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
            i += 1
            continue
        cur += ch
        i += 1
    if cur.strip():
        out.append(cur.strip())
    return out


def _flag(opts, key):
    """'off' when set to false, 'on' when set otherwise, None when absent. String contents are ignored."""
    bare = STRING.sub("''", opts)
    m = re.search(r"\b" + key + r"\b\s*(?:[:=]\s*([\w.]+))?", bare, re.I)
    if not m:
        return None
    return "off" if (m.group(1) or "").lower() in ("false", "0", "none") else "on"


def _cookie_name(args):
    for a in args:
        m = re.match(r"""(?:key\s*=\s*)?(['"`])([^'"`]+)\1$""", a)
        if m:
            return m.group(2)
        m = re.search(r"""\bname\s*:\s*(['"`])([^'"`]+)\1""", a)
        if m:
            return m.group(2)
    return ""


def _line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def _cookie_flags(rel, text):
    hits = []
    for m in COOKIE_SETTING.finditer(text):
        hits.append({"line": _line_of(text, m.start()), "extra": f"{m.group(1)} is False."})
    for rx, insecure in ((INSECURE_DEFAULTS, True), (SAFE_DEFAULTS, False)):
        for m in rx.finditer(text):
            raw = _call_args(text, m.end() - 1)
            if raw is None:
                continue
            args = _split_args(raw)
            name = _cookie_name(args)
            if not name or not SESSION_NAME.search(name):
                continue
            # Hono's setCookie(c, name, value, opts) takes the context first; Fastify's reply.setCookie does not.
            hono = m.group(0).startswith("setCookie") and text[m.start() - 1:m.start()] != "."
            before = 3 if hono else 2
            if len(args) == 1 and args[0].startswith("{"):
                opts, known = args[0], "..." not in args[0]
            elif rel.endswith(".py"):
                opts = ", ".join(args[before:])
                known = "**" not in opts and all("=" in a for a in args[before:])
            else:
                rest = args[before:]
                opts = rest[-1] if rest else ""
                known = not rest or (len(rest) == 1 and opts.startswith("{") and "..." not in opts)
            missing = []
            for key, label in (("http_?only", "HttpOnly"), ("secure", "Secure")):
                state = _flag(opts, key)
                if state == "off" or (state is None and insecure and known):
                    missing.append(label)
            if missing:
                hits.append({"line": _line_of(text, m.start()),
                             "extra": f"Cookie '{name}' is set without {' or '.join(missing)}."})
    for m in SESSION_MW.finditer(text):
        raw = _call_args(text, m.end() - 1)
        if raw and re.search(r"\bcookie\s*:", raw):
            for key, label in (("httpOnly", "HttpOnly"), ("secure", "Secure")):
                if _flag(raw, key) == "off":
                    hits.append({"line": _line_of(text, m.start()),
                                 "extra": f"Session middleware sets {label} to false."})
    for m in RAW_HEADER.finditer(text):
        name, attrs = m.group(1), m.group(2)
        if not SESSION_NAME.search(name):
            continue
        missing = [f for f in ("HttpOnly", "Secure") if not re.search(r";\s*" + f + r"\b", attrs, re.I)]
        if missing:
            hits.append({"line": _line_of(text, m.start()),
                         "extra": f"Set-Cookie header for '{name}' has no {' or '.join(missing)}."})
    return hits


RULES = [
    Rule(
        id="SEC-007", title="CORS allows any origin", severity="medium", popia="s19",
        pattern=r"""(Access-Control-Allow-Origin['"]?\s*[:,=]\s*['"]\*['"])|(origin\s*:\s*['"]\*['"])|(cors\(\s*\)\s*\))|(allow_origins\s*=\s*\[\s*['"]\*['"])|(AllowAnyOrigin\(\))""",
        include=CODE + CONFIG, exclude=NOT_TESTS,
        message="A wildcard origin lets any website call your API from a visitor's browser. Combined with "
                "credentials or permissive auth it exposes user data.",
        fix="Use an explicit allow-list of your own origins. Never combine '*' with credentials.",
        confidence="medium", tags=["web"],
    ),
    Rule(
        id="SEC-008", title="Weak hashing for passwords or tokens", severity="high", popia="s19",
        pattern=r"(md5|sha1)\s*\(|createHash\(\s*['\"](md5|sha1)['\"]|hashlib\.(md5|sha1)\(|MessageDigest\.getInstance\(\s*\"(MD5|SHA-?1)\"|password[^\n]{0,40}(sha256|sha-256)\(",
        include=CODE, exclude=NOT_TESTS,
        message="MD5 and SHA-1 are broken, and fast hashes (even SHA-256) are unsuitable for passwords.",
        fix="Use argon2id, bcrypt (cost 12+) or scrypt for passwords. Use HMAC-SHA256 for tokens.",
        confidence="medium", tags=["crypto"],
    ),
    Rule(
        id="SEC-009", title="Unencrypted http:// endpoint", severity="medium", popia="s19",
        pattern=r"""['"`]http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\]|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|www\.w3\.org|schemas\.|xmlns|example\.(com|org)|purl\.org|ns\.adobe)[^'"`\s]+""",
        include=CODE + ["*.html", "*.env", ".env*"] + CONFIG, exclude=NOT_TESTS,
        message="Plain HTTP exposes data in transit, including form submissions and session tokens.",
        fix="Use HTTPS and enable HSTS.",
        confidence="medium", tags=["transport"],
    ),
    Rule(
        id="SEC-010", title="TLS certificate verification disabled", severity="high", popia="s19",
        pattern=r"verify\s*=\s*False|rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED\s*=?\s*['\"]?0|InsecureSkipVerify\s*:\s*true|CURLOPT_SSL_VERIFYPEER\s*,\s*(0|false)|ServerCertificateValidationCallback\s*=.*true|badCertificateCallback\s*=.*true",
        include=CODE + ["*.env", ".env*", "*.yml", "*.yaml"], exclude=NOT_TESTS,
        message="Disabling certificate checks allows interception of traffic that may carry PI or credentials.",
        fix="Remove the override. Fix the trust store instead (add the CA bundle).",
        confidence="high", tags=["transport"],
    ),
    Rule(
        id="SEC-011", title="Raw HTML injection sink", severity="medium", popia="s19",
        pattern=r"dangerouslySetInnerHTML|v-html=|\.innerHTML\s*=|\{@html\s|bypassSecurityTrust\w+\(|document\.write\(|\|\s*safe\b|mark_safe\(|html_safe",
        include=CODE + ["*.html", "*.vue", "*.svelte", "*.hbs", "*.ejs", "*.liquid"], exclude=NOT_TESTS,
        message="XSS lets an attacker run script in your users' sessions and read whatever PI the page can see.",
        fix="Render text, not HTML. If HTML is required, sanitise with DOMPurify and add a strict CSP.",
        confidence="low", tags=["xss"],
    ),
    Rule(
        id="SEC-012", title="SQL built with string concatenation or interpolation", severity="medium",
        popia="s19",
        pattern=r"""(execute|query|raw|rawQuery|\$queryRawUnsafe|\$executeRawUnsafe|sequelize\.query)\s*\(\s*(f['"]|['"`][^'"`]*['"`]\s*\+|`[^`]*\$\{)|cursor\.execute\(\s*['"][^'"]*%s?['"]\s*%""",
        include=CODE, exclude=NOT_TESTS,
        message="SQL injection is a direct path to bulk extraction of personal information.",
        fix="Use parameterised queries or the ORM's safe query builder.",
        confidence="medium", tags=["injection"],
    ),
    Rule(
        id="SEC-013", title="JWT decoded without verification", severity="high", popia="s19",
        pattern=r"""jwt\.decode\([^)]*(verify\s*=\s*False|options\s*=\s*\{\s*['"]verify_signature['"]\s*:\s*False)|algorithms\s*[:=]\s*\[\s*['"]none['"]|jwtDecode\(|jwt_decode\(""",
        include=CODE, exclude=NOT_TESTS,
        message="Trusting unverified tokens lets anyone forge identity and access other users' data. "
                "(Client-side jwtDecode for display is fine; using it for authorisation is not.)",
        fix="Verify signature, algorithm, expiry and audience on the server before trusting claims.",
        confidence="low", tags=["auth"],
    ),
    Rule(
        id="SEC-017", title="Debug or verbose error output enabled", severity="low", popia="s19",
        pattern=r"DEBUG\s*=\s*True|app\.run\([^)]*debug\s*=\s*True|display_errors\s*=\s*(On|1)|showStackTrace\s*:\s*true",
        include=CODE + CONFIG + ["*.ini", "*.env", ".env*"], exclude=NOT_TESTS,
        message="Debug pages and stack traces can leak configuration, queries and personal data.",
        fix="Disable debug in production; return generic errors and log details server-side without PI.",
        confidence="low", tags=["config"],
    ),
    Rule(
        id="SEC-021", title="Session cookie set without HttpOnly or Secure", severity="medium", popia="s19",
        kind="file", include=CODE, exclude=NOT_TESTS, file_check=_cookie_flags,
        message="Without HttpOnly any script on the page, including injected script, can read the session "
                "cookie. Without Secure the browser sends it over plain HTTP. Either way a session can be "
                "taken over and the account's personal information read.",
        fix="Set httpOnly: true, secure: true and sameSite: 'lax' (or 'strict') on session and auth cookies. "
            "In Django or Flask set SESSION_COOKIE_SECURE = True and SESSION_COOKIE_HTTPONLY = True.",
        confidence="low", tags=["web", "session"],
    ),
]
