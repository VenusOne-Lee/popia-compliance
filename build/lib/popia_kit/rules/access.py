"""Access control: Supabase/Postgres RLS, Firebase rules, storage buckets. POPIA s19."""
import re

from popia_scan import Rule

CREATE_TABLE = re.compile(
    r"create\s+table\s+(?:if\s+not\s+exists\s+)?(?:\"?(\w+)\"?\.)?\"?(\w+)\"?", re.I)
ENABLE_RLS = re.compile(
    r"alter\s+table\s+(?:if\s+exists\s+)?(?:only\s+)?(?:\"?(\w+)\"?\.)?\"?(\w+)\"?\s+enable\s+row\s+level\s+security", re.I)
DISABLE_RLS = re.compile(
    r"alter\s+table\s+(?:if\s+exists\s+)?(?:only\s+)?(?:\"?(\w+)\"?\.)?\"?(\w+)\"?\s+disable\s+row\s+level\s+security", re.I)
SKIP_SCHEMAS = {"auth", "storage", "extensions", "pg_catalog", "information_schema", "graphql", "realtime",
                "supabase_functions", "net", "vault", "cron", "pgsodium"}


def _rls_check(ctx):
    created = {}   # table -> (file, line)
    enabled = set()
    disabled = []
    for rel, text in ctx.files.items():
        if not rel.lower().endswith(".sql"):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            s = line.strip()
            if s.startswith("--"):
                continue
            m = CREATE_TABLE.search(s)
            if m and not re.search(r"\btemp(orary)?\b", s, re.I):
                schema = (m.group(1) or "public").lower()
                if schema not in SKIP_SCHEMAS:
                    created.setdefault(f"{schema}.{m.group(2).lower()}", (rel, i))
            m = ENABLE_RLS.search(s)
            if m:
                enabled.add(f"{(m.group(1) or 'public').lower()}.{m.group(2).lower()}")
            m = DISABLE_RLS.search(s)
            if m:
                disabled.append((f"{(m.group(1) or 'public').lower()}.{m.group(2).lower()}", rel, i))
    hits = []
    for table, (rel, i) in sorted(created.items()):
        if table not in enabled:
            hits.append({"file": rel, "line": i, "snippet": f"create table {table}",
                         "extra": f"No 'enable row level security' found for {table} in any migration."})
    for table, rel, i in disabled:
        hits.append({"file": rel, "line": i, "snippet": f"alter table {table} disable row level security",
                     "extra": "RLS explicitly disabled."})
    return hits


def _firebase_open(rel, text):
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if re.search(r"allow\s+[\w\s,]*(read|write)[\w\s,]*:\s*if\s+true\s*;", line) or \
           re.search(r"request\.time\s*<\s*timestamp\.date\(", line):
            hits.append({"line": i})
        if rel.endswith(".json") and re.search(r"\"\.(read|write)\"\s*:\s*(true|\"true\")", line):
            hits.append({"line": i})
    return hits


def _auth_only(rel, text):
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if re.search(r"allow\s+[\w\s,]*(read|write|get|list)[\w\s,]*:\s*if\s+request\.auth\s*!=\s*null\s*;", line):
            hits.append({"line": i})
    return hits


RULES = [
    Rule(
        id="SEC-004", title="Table created without row-level security", severity="high", popia="s19",
        kind="repo", repo_check=_rls_check,
        message="In Supabase the anon key is public. A table without RLS can be read and changed by anyone "
                "with that key. This is the most common data exposure in Lovable and Supabase apps.",
        fix="ALTER TABLE ... ENABLE ROW LEVEL SECURITY; add owner-scoped policies "
            "(references/04-stack-playbooks.md §1). Then check logs for past anonymous access.",
        confidence="medium", tags=["supabase", "access-control"],
    ),
    Rule(
        id="SEC-005", title="Permissive RLS policy (USING true / anon access)", severity="high", popia="s19",
        pattern=r"create\s+policy[^;]*?(?:using\s*\(\s*true\s*\)|with\s+check\s*\(\s*true\s*\)[^;]*for\s+(?:select|all)|to\s+(?:anon|public)[^;]*for\s+(?:select|all|update|delete))|create\s+policy[^;]*for\s+(?:select|all|update|delete)[^;]*to\s+(?:anon|public)[^;]*using\s*\(\s*true",
        include=["*.sql"],
        message="A policy that evaluates to true (or grants anon read/update/delete) makes RLS decorative. "
                "Insert-only for anon on a lead form can be fine; select/update/delete for anon rarely is.",
        fix="Scope policies to the owner: USING ((select auth.uid()) = user_id). Keep anon to INSERT only "
            "where a public form needs it, with no SELECT policy.",
        confidence="medium", tags=["supabase", "access-control"],
    ),
    Rule(
        id="SEC-006", title="Firebase rules open to everyone or time-boxed test mode", severity="critical",
        popia="s19", kind="file",
        include=["firestore.rules", "storage.rules", "*.rules", "database.rules.json"],
        file_check=_firebase_open,
        message="Test-mode rules let anyone on the internet read or write the database or bucket.",
        fix="Write owner-scoped rules (references/04-stack-playbooks.md §3) and use App Check.",
        confidence="high", tags=["firebase", "access-control"],
    ),
    Rule(
        id="SEC-006b", title="Firebase rules check only that a user is signed in", severity="high",
        popia="s19", kind="file", include=["firestore.rules", "storage.rules", "*.rules"],
        file_check=_auth_only,
        message="'request.auth != null' lets any signed-up user read every other user's documents.",
        fix="Compare request.auth.uid with the document owner.",
        confidence="medium", tags=["firebase", "access-control"],
    ),
    Rule(
        id="SEC-015", title="Public storage bucket", severity="high", popia="s19",
        pattern=r"(insert\s+into\s+storage\.buckets[^;]*\btrue\b)|(createBucket\s*\([^)]*public\s*:\s*true)|(update\s+storage\.buckets\s+set\s+public\s*=\s*true)|(\"?acl\"?\s*[:=]\s*[\"']public-read)",
        include=["*.sql", "*.ts", "*.js", "*.tsx", "*.py", "*.tf", "*.json", "*.yaml", "*.yml"],
        message="Public buckets serve files to anyone with the URL. Uploads (IDs, CVs, proof of address, "
                "medical notes) are personal information.",
        fix="Make the bucket private. Serve files via short-lived signed URLs after an authorisation check.",
        confidence="medium", tags=["storage", "access-control"],
    ),
    Rule(
        id="SEC-016", title="Identity taken from request body in a server function", severity="high",
        popia="s19",
        pattern=r"(?:body|req\.body|await\s+req\.json\(\))\s*[\.\[]?\s*['\"]?(user_?id|userId|uid|owner_?id)\b",
        include=["*supabase/functions/*", "*api/*", "*server/*", "*routes/*", "*actions*"],
        message="Trusting a user id sent by the client lets any user act on anyone else's data (IDOR).",
        fix="Derive the user from the verified session/JWT (supabase.auth.getUser(jwt)) and authorise on that.",
        confidence="low", tags=["access-control"],
    ),
]
