"""Secrets and credentials. POPIA s19: a leaked key is usually a route to personal information."""
import math
import re

from popia_scan import Rule

CODE = ["*.js", "*.jsx", "*.ts", "*.tsx", "*.mjs", "*.cjs", "*.vue", "*.svelte", "*.astro", "*.py", "*.rb",
        "*.php", "*.go", "*.java", "*.kt", "*.swift", "*.dart", "*.cs", "*.json", "*.yaml", "*.yml", "*.toml",
        "*.env", ".env*", "*.ini", "*.cfg", "*.tf", "*.sh", "*.xml", "*.plist", "*.html", "Dockerfile"]
TEST_PATHS = ["*test*", "*spec*", "*fixture*", "*mock*", "*example*", "*sample*", "*.md"]


def _entropy(s: str) -> float:
    if not s:
        return 0.0
    freq = {c: s.count(c) for c in set(s)}
    return -sum(n / len(s) * math.log2(n / len(s)) for n in freq.values())


def _not_placeholder(m, line):
    val = m.group(m.lastindex or 0)
    low = val.lower()
    if any(x in low for x in ("xxxx", "your_", "your-", "<", "changeme", "example", "placeholder", "dummy",
                               "process.env", "import.meta.env", "os.environ", "getenv", "${", "{{")):
        return False
    return _entropy(val) > 3.0


def _jwt_service_role(m, line):
    import base64
    import json
    token = m.group(0)
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload.encode()).decode("utf-8", "ignore"))
        return data.get("role") == "service_role"
    except Exception:
        return False


RULES = [
    Rule(
        id="SEC-001", title="Hard-coded secret or API key", severity="critical", popia="s19",
        pattern=(r"(AKIA[0-9A-Z]{16})|(sk_live_[0-9a-zA-Z]{20,})|(rk_live_[0-9a-zA-Z]{20,})"
                 r"|(ghp_[0-9A-Za-z]{36})|(github_pat_[0-9A-Za-z_]{40,})|(xox[abpr]-[0-9A-Za-z-]{10,})"
                 r"|(sk-ant-[A-Za-z0-9_\-]{20,})|(sk-proj-[A-Za-z0-9_\-]{20,})|(sk-[A-Za-z0-9]{40,})"
                 r"|(AIza[0-9A-Za-z_\-]{35})|(SG\.[A-Za-z0-9_\-]{16,}\.[A-Za-z0-9_\-]{16,})"
                 r"|(-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----)"
                 r"|(re_[A-Za-z0-9]{8,}_[A-Za-z0-9]{16,})"),
        flags=0, include=CODE, exclude=TEST_PATHS,
        message="A live credential in source code gives anyone with repo or bundle access a path to "
                "systems holding personal information. Git history keeps it even after deletion.",
        fix="Rotate the key now. Move it to a secret manager or server-only env var. Purge from history "
            "(git filter-repo) and add secret scanning (gitleaks or GitHub push protection).",
        confidence="high", tags=["secrets"],
    ),
    Rule(
        id="SEC-001b", title="Possible hard-coded password or token", severity="high", popia="s19",
        pattern=r"""(?:password|passwd|pwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret)\s*[:=]\s*["']([^"'\s]{12,})["']""",
        include=CODE, exclude=TEST_PATHS, validator=_not_placeholder,
        message="Looks like a credential assigned in code. Credentials in code leak through repos, bundles and logs.",
        fix="Load from environment or a secret manager at runtime. Rotate if this value was ever real.",
        confidence="medium", tags=["secrets"],
    ),
    Rule(
        id="SEC-002", title="Supabase service_role key outside server code", severity="critical", popia="s19",
        pattern=r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}",
        flags=0, include=CODE, exclude=["*supabase/functions/*", "*server/*", "*api/*"] + TEST_PATHS,
        validator=_jwt_service_role,
        message="The service_role key bypasses row-level security. If it reaches a browser, app bundle or "
                "public repo, every table is readable and writable by anyone.",
        fix="Rotate the JWT secret / service key in Supabase. Use the anon key in clients and keep "
            "service_role only in edge function or server secrets.",
        confidence="high", tags=["secrets", "supabase", "access-control"],
    ),
    Rule(
        id="SEC-003", title="Secret exposed through a public env prefix", severity="critical", popia="s19",
        pattern=r"\b(?:NEXT_PUBLIC|VITE|EXPO_PUBLIC|REACT_APP|PUBLIC|NUXT_PUBLIC|GATSBY)_[A-Z0-9_]*(?:SERVICE_ROLE|SECRET|PRIVATE|ADMIN|SERVICE_KEY|PASSWORD|STRIPE_SK|SK_LIVE)[A-Z0-9_]*",
        flags=0, include=CODE + ["*.md"],
        message="Variables with these prefixes are bundled into client code by the framework. A secret here "
                "ships to every visitor.",
        fix="Rename without the public prefix, read it only in server code, and rotate the value.",
        confidence="high", tags=["secrets", "frontend"],
    ),
    Rule(
        id="SEC-014", title="Environment file with values committed", severity="high", popia="s19",
        kind="file", include=[".env", ".env.local", ".env.production", ".env.prod", ".env.development", ".env.staging"],
        file_check=lambda rel, text: [
            {"line": i, "snippet": ln.split("=", 1)[0] + "=…"}
            for i, ln in enumerate(text.splitlines(), 1)
            if re.match(r"^[A-Z0-9_]*(KEY|SECRET|TOKEN|PASSWORD|PASS|DSN|URL)[A-Z0-9_]*\s*=\s*\S{8,}", ln)
            and "example" not in rel.lower()
        ][:5],
        message="Env files with real values belong in a secret manager or local only. Committed env files are "
                "a common source of leaked database URLs and keys.",
        fix="Remove from the repo, add to .gitignore, rotate the values, commit a .env.example with placeholders.",
        confidence="medium", tags=["secrets"],
    ),
]
