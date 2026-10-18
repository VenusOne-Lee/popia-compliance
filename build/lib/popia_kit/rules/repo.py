"""Repository-level gaps: notices, rights, retention, security hygiene. Absence checks are heuristics."""
import re

from popia_scan import Rule

APP_HINT = re.compile(r"\.(tsx|jsx|vue|svelte|astro|html|php|dart|swift|kt)$", re.I)
COLLECTS_PI = re.compile(r"type=[\"']email|name=[\"']email|<input[^>]*(phone|tel)|signUp|signup|auth\.signUp|createUser|register|contact.?form|insert\(.*(email|phone)", re.I)


def _is_app(ctx):
    return any(APP_HINT.search(p) for p in ctx.files)


def _collects(ctx):
    return any(COLLECTS_PI.search(t) for p, t in ctx.files.items() if not p.endswith(".md"))


def _no_privacy_notice(ctx):
    if not _is_app(ctx) or not _collects(ctx):
        return []
    if ctx.paths_matching(r"privacy") or ctx.any(r"href=[\"'{]?[^\"'>]*privacy|/privacy|privacy[- ]?(policy|notice)"):
        return []
    return [{"extra": "App collects personal information but no privacy notice route, file or link was found."}]


def _no_paia(ctx):
    if not _is_app(ctx) or not _collects(ctx):
        return []
    if ctx.any(r"paia|access[- ]to[- ]information|section\s*51\s*manual"):
        return []
    return [{"extra": "No PAIA manual link or page found. Private bodies must make a PAIA manual available."}]


def _no_deletion(ctx):
    if not _collects(ctx):
        return []
    if ctx.any(r"delete[_ ]?(my[_ ]?)?account|deleteUser|delete_user|auth\.admin\.deleteUser|account[_-]?deletion|dsar|data[_ ]?subject|erase|right[_ ]?to[_ ]?(be[_ ]?forgotten|delete)|export[_ ]?(my[_ ]?)?data|download[_ ]?(my[_ ]?)?data"):
        return []
    return [{"extra": "No account deletion, data export or data subject request handling found."}]


def _no_retention(ctx):
    if not _collects(ctx):
        return []
    if ctx.any(r"retention|purge|cron\.schedule|pg_cron|expire_?after|ttl\b|deleteMany\(\s*\{[^}]*(createdAt|created_at|lt)|interval\s+'\d+\s+(day|month|year)|older_?than", re.I):
        return []
    return [{"extra": "No retention, purge or scheduled deletion logic found."}]


def _no_unsubscribe(ctx):
    if not ctx.any(r"campaign|broadcast|sendBulk|bulk_?send|newsletter\w*\.send|sendNewsletter|mailchimp|brevo|sendgrid|klaviyo|resend\.(emails|batch)\.send|messages\.create\(.*whatsapp", include=("*.ts", "*.tsx", "*.js", "*.jsx", "*.mjs", "*.py", "*.rb", "*.php", "*.go")):
        return []
    if ctx.any(r"unsubscribe|opt[-_ ]?out|List-Unsubscribe|STOP\b"):
        return []
    return [{"extra": "Marketing sending found but no unsubscribe or opt-out handling."}]


def _no_security_txt(ctx):
    if not _is_app(ctx):
        return []
    if ctx.paths_matching(r"security\.txt$"):
        return []
    return [{"extra": "No /.well-known/security.txt. A disclosure route helps you hear about exposures first."}]


def _no_lockfile_audit(ctx):
    has_pkg = bool(ctx.paths_matching(r"(^|/)package\.json$"))
    if not has_pkg:
        return []
    if ctx.paths_matching(r"(dependabot\.ya?ml|renovate\.json|\.github/workflows/.*\.ya?ml)$") and \
       ctx.any(r"npm audit|dependabot|renovate|snyk|osv-scanner|codeql|semgrep|popia", include=("*.yml", "*.yaml", "*.json")):
        return []
    return [{"extra": "No dependency scanning or security CI found."}]


def _no_ci_popia(ctx):
    if ctx.any(r"popia_scan|popia-compliance", include=("*.yml", "*.yaml", ".pre-commit-config.yaml")):
        return []
    if not _is_app(ctx):
        return []
    return [{"extra": "Add the POPIA scan to CI so regressions are blocked (examples/github-workflow-popia-scan.yml)."}]


RULES = [
    Rule(id="DOC-001", title="No privacy notice found", severity="high", popia="s18; s17", kind="repo",
         repo_check=_no_privacy_notice,
         message="Data subjects must be told, at collection, who you are, why you collect, their rights and "
                 "how to complain to the Information Regulator.",
         fix="Publish a privacy notice (templates/privacy-notice.md or scripts/popia_pack.py), link it in the "
             "footer and next to every form.",
         confidence="medium", tags=["openness"]),
    Rule(id="DOC-002", title="No PAIA manual link found", severity="medium", popia="PAIA s51; Reg 4",
         kind="repo", repo_check=_no_paia,
         message="Private bodies must have a PAIA manual available. The Information Officer must ensure it exists.",
         fix="Publish the PAIA manual (templates/paia-manual-scaffold.md) and link it in the footer.",
         confidence="low", tags=["openness"]),
    Rule(id="DSR-001", title="No data subject rights handling found", severity="medium", popia="s23; s24; s11(3)",
         kind="repo", repo_check=_no_deletion,
         message="People can ask for access, correction and deletion, and can object. Without a built or "
                 "documented process, requests get lost.",
         fix="Add export, delete-account and preference controls (registry/popia/account/privacy-centre.tsx) "
             "or document a manual process with an SLA (templates/dsar-runbook.md).",
         confidence="low", tags=["participation"]),
    Rule(id="RET-001", title="No retention or deletion job found", severity="medium", popia="s14", kind="repo",
         repo_check=_no_retention,
         message="Personal information must be deleted or de-identified once it's no longer needed.",
         fix="Define retention per data set and schedule a job to enforce it "
             "(registry/popia/supabase/migrations/0002_retention.sql).",
         confidence="low", tags=["retention"]),
    Rule(id="DM-001", title="Marketing sends without unsubscribe handling", severity="high", popia="s69(4); s11(3)(b)",
         kind="repo", repo_check=_no_unsubscribe,
         message="Every direct marketing message must identify the sender and offer a way to stop.",
         fix="Add one-click unsubscribe (List-Unsubscribe + List-Unsubscribe-Post), STOP handling for SMS and "
             "WhatsApp, and a global suppression list.",
         confidence="low", tags=["marketing"]),
    Rule(id="SEC-018", title="No security.txt disclosure route", severity="low", popia="s19(2)", kind="repo",
         repo_check=_no_security_txt,
         message="A disclosure route helps researchers report exposures to you before they become incidents.",
         fix="Add public/.well-known/security.txt with a contact and policy.",
         confidence="medium", tags=["hygiene"]),
    Rule(id="SEC-019", title="No dependency or security scanning in CI", severity="low", popia="s19(2)(c)",
         kind="repo", repo_check=_no_lockfile_audit,
         message="s19 requires you to regularly verify safeguards. Automated scanning is the cheapest evidence.",
         fix="Enable Dependabot or Renovate and add npm audit / CodeQL / Semgrep to CI.",
         confidence="medium", tags=["hygiene"]),
    Rule(id="SEC-020", title="POPIA scan not in CI", severity="info", popia="s19(2)(c)", kind="repo",
         repo_check=_no_ci_popia,
         message="Running this scanner on every pull request blocks regressions.",
         fix="Add the GitHub Action (examples/github-workflow-popia-scan.yml) or the pre-commit hook.",
         confidence="high", tags=["hygiene"]),
]
