"""Operators, cross-border transfers and AI providers. POPIA s20, s21, s72, s71."""
import json
import re

from popia_scan import Rule

SDKS = {
    # package or import fragment -> (vendor, category)
    "openai": ("OpenAI", "ai"), "@anthropic-ai/sdk": ("Anthropic", "ai"), "anthropic": ("Anthropic", "ai"),
    "@google/generative-ai": ("Google Gemini", "ai"), "@google/genai": ("Google Gemini", "ai"),
    "google-generativeai": ("Google Gemini", "ai"), "@mistralai/mistralai": ("Mistral", "ai"),
    "cohere-ai": ("Cohere", "ai"), "groq-sdk": ("Groq", "ai"), "replicate": ("Replicate", "ai"),
    "elevenlabs": ("ElevenLabs", "ai"), "@elevenlabs/elevenlabs-js": ("ElevenLabs", "ai"),
    "ai": ("Vercel AI SDK (check provider)", "ai"), "langchain": ("LangChain (check provider)", "ai"),
    "@sentry/": ("Sentry", "errors"), "sentry-sdk": ("Sentry", "errors"), "@datadog/": ("Datadog", "logs"),
    "logrocket": ("LogRocket", "replay"), "@intercom/": ("Intercom", "support"),
    "@hubspot/": ("HubSpot", "crm"), "jsforce": ("Salesforce", "crm"), "simple-salesforce": ("Salesforce", "crm"),
    "@sendgrid/mail": ("SendGrid", "email"), "resend": ("Resend", "email"), "postmark": ("Postmark", "email"),
    "@mailchimp/": ("Mailchimp", "email"), "mailgun": ("Mailgun", "email"), "nodemailer": ("SMTP provider", "email"),
    "twilio": ("Twilio", "messaging"), "@vonage/": ("Vonage", "messaging"), "clickatell": ("Clickatell", "messaging"),
    "stripe": ("Stripe", "payments"), "@paystack/": ("Paystack", "payments"), "paystack": ("Paystack", "payments"),
    "@supabase/supabase-js": ("Supabase", "backend"), "firebase": ("Firebase / Google", "backend"),
    "firebase-admin": ("Firebase / Google", "backend"), "@aws-sdk/": ("AWS", "cloud"), "boto3": ("AWS", "cloud"),
    "@azure/": ("Azure", "cloud"), "@google-cloud/": ("Google Cloud", "cloud"), "algoliasearch": ("Algolia", "search"),
    "@pinecone-database/pinecone": ("Pinecone", "ai"), "posthog-js": ("PostHog", "analytics"),
    "mixpanel": ("Mixpanel", "analytics"), "@segment/": ("Segment", "analytics"), "@amplitude/": ("Amplitude", "analytics"),
    "zapier": ("Zapier", "automation"), "airtable": ("Airtable", "data"), "@notionhq/client": ("Notion", "data"),
    "googleapis": ("Google APIs", "cloud"), "@slack/": ("Slack", "messaging"), "whatsapp": ("WhatsApp/Meta", "messaging"),
}


def _manifest_sdks(ctx):
    hits, seen = [], set()
    for rel, text in ctx.files.items():
        base = rel.rsplit("/", 1)[-1]
        names = []
        if base == "package.json":
            try:
                pkg = json.loads(text)
                for k in ("dependencies", "devDependencies", "optionalDependencies"):
                    names += list((pkg.get(k) or {}).keys())
            except Exception:
                continue
        elif base in ("requirements.txt", "pyproject.toml", "Pipfile"):
            names = re.findall(r"^\s*([A-Za-z0-9_.\-]+)", text, re.M)
        else:
            continue
        for n in names:
            for frag, (vendor, cat) in SDKS.items():
                match = n == frag or (frag.endswith("/") and n.startswith(frag)) or (frag == n.lower())
                if match and vendor not in seen:
                    if frag == "ai" and n != "ai":
                        continue
                    seen.add(vendor)
                    line = next((i for i, ln in enumerate(text.splitlines(), 1) if f'"{n}"' in ln or ln.strip().startswith(n)), 0)
                    hits.append({"file": rel, "line": line, "snippet": n,
                                 "extra": f"{vendor} ({cat}): operator under s20/21; record hosting country and s72 basis."})
    return hits


def _llm_with_user_data(ctx):
    rx_call = re.compile(r"(chat\.completions\.create|responses\.create|messages\.create|generateContent|generateText|streamText|ChatOpenAI|ChatAnthropic|invoke\()", re.I)
    rx_pi = re.compile(r"(email|phone|id_?number|idNumber|address|dob|date_?of_?birth|customer|patient|user\.(name|email)|profile|transcript|messages?\b|cv|resume|medical|health)", re.I)
    hits = []
    for rel, text in ctx.files.items():
        if not rel.endswith((".ts", ".tsx", ".js", ".jsx", ".mjs", ".py")) or "test" in rel.lower():
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            if rx_call.search(line):
                window = "\n".join(lines[max(0, i - 15): i + 15])
                if rx_pi.search(window):
                    hits.append({"file": rel, "line": i, "snippet": line.strip(),
                                 "extra": "LLM call near user data."})
                    break
    return hits


def _automated_decision(ctx):
    rx = re.compile(r"\b(approve|reject|decline|deny|eligib\w*|credit_?score|risk_?score|blacklist|blocklist|auto_?ban|shortlist|hire|fraud_?score)\w*\s*[=(:]", re.I)
    rx_ai = re.compile(r"(openai|anthropic|gemini|model\.predict|predict_proba|classifier|llm|score\s*>|threshold)", re.I)
    hits = []
    for rel, text in ctx.files.items():
        if not rel.endswith((".ts", ".tsx", ".js", ".py", ".rb", ".java", ".kt", ".go")) or "test" in rel.lower():
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            if rx.search(line) and rx_ai.search("\n".join(lines[max(0, i - 10): i + 10])):
                hits.append({"file": rel, "line": i, "snippet": line.strip()})
                break
    return hits[:10]


RULES = [
    Rule(
        id="XB-001", title="Third-party SDK that receives data (operator / cross-border)", severity="info",
        popia="s20; s21; s72; s18(1)(g)", kind="repo", repo_check=_manifest_sdks,
        message="Vendors that receive personal information are operators. Most are hosted outside South Africa, "
                "which makes each a transfer under s72.",
        fix="Record each in the ROPA: purpose, fields sent, hosting country, operator agreement, s72 basis. "
            "Disclose in the privacy notice.",
        confidence="high", tags=["cross-border", "operators"],
    ),
    Rule(
        id="AI-001", title="Personal information sent to an AI model", severity="medium",
        popia="s10; s15; s20; s72", kind="repo", repo_check=_llm_with_user_data,
        message="Prompts with user data are processing by an offshore operator. Check minimality, purpose "
                "compatibility, provider retention and training settings.",
        fix="Send the minimum fields, pseudonymise IDs, use zero or limited retention where offered, record "
            "the provider as an operator and a s72 transfer, and tell users (references/08).",
        confidence="low", tags=["ai", "cross-border"],
    ),
    Rule(
        id="AI-002", title="Possible solely automated decision about a person", severity="medium",
        popia="s71", kind="repo", repo_check=_automated_decision,
        message="Decisions with legal or substantial effect based solely on automated profiling are restricted "
                "unless an exception applies and people can make representations and get an explanation.",
        fix="Add meaningful human review for adverse outcomes, store plain-language reasons, and provide a "
            "route to contest (references/08 s71 pattern).",
        confidence="low", tags=["ai", "automated-decisions"],
    ),
]
