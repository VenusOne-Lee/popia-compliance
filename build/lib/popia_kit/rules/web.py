"""Web and application security patterns that commonly lead to PI exposure. POPIA s19."""
from popia_scan import Rule

CODE = ["*.js", "*.jsx", "*.ts", "*.tsx", "*.mjs", "*.cjs", "*.vue", "*.svelte", "*.astro", "*.py", "*.rb",
        "*.php", "*.go", "*.java", "*.kt", "*.swift", "*.dart", "*.cs"]
CONFIG = ["*.json", "*.yaml", "*.yml", "*.toml", "*.conf", ".htaccess", "*.tf"]
NOT_TESTS = ["*test*", "*spec*", "*fixture*", "*.md"]

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
]
