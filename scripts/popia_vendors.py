"""
Known third-party vendors: package names, import names and API hosts.

Shared by the scanner rule XB-001 (scripts/rules/thirdparty.py) and the operator
inventory (scripts/popia_operators.py). Stdlib only. Python 3.8+.

Each entry maps to (vendor, category). Hosting regions change, so this table
names vendors only. It never claims where a vendor stores data.
"""

# npm and PyPI package names. A key ending in "/" matches every package in that scope.
SDKS = {
    "openai": ("OpenAI", "ai"), "@anthropic-ai/sdk": ("Anthropic", "ai"), "anthropic": ("Anthropic", "ai"),
    "@google/generative-ai": ("Google Gemini", "ai"), "@google/genai": ("Google Gemini", "ai"),
    "google-generativeai": ("Google Gemini", "ai"), "google-genai": ("Google Gemini", "ai"),
    "@mistralai/mistralai": ("Mistral", "ai"), "mistralai": ("Mistral", "ai"),
    "cohere-ai": ("Cohere", "ai"), "cohere": ("Cohere", "ai"), "groq-sdk": ("Groq", "ai"), "groq": ("Groq", "ai"),
    "replicate": ("Replicate", "ai"),
    "elevenlabs": ("ElevenLabs", "ai"), "@elevenlabs/elevenlabs-js": ("ElevenLabs", "ai"),
    "ai": ("Vercel AI SDK (check provider)", "ai"), "langchain": ("LangChain (check provider)", "ai"),
    "@sentry/": ("Sentry", "errors"), "sentry-sdk": ("Sentry", "errors"), "@datadog/": ("Datadog", "logs"),
    "logrocket": ("LogRocket", "replay"), "@intercom/": ("Intercom", "support"),
    "@hubspot/": ("HubSpot", "crm"), "jsforce": ("Salesforce", "crm"), "simple-salesforce": ("Salesforce", "crm"),
    "@sendgrid/mail": ("SendGrid", "email"), "sendgrid": ("SendGrid", "email"), "resend": ("Resend", "email"),
    "postmark": ("Postmark", "email"),
    "@mailchimp/": ("Mailchimp", "email"), "mailchimp-marketing": ("Mailchimp", "email"),
    "mailgun": ("Mailgun", "email"), "nodemailer": ("SMTP provider", "email"),
    "twilio": ("Twilio", "messaging"), "@vonage/": ("Vonage", "messaging"), "clickatell": ("Clickatell", "messaging"),
    "stripe": ("Stripe", "payments"), "@paystack/": ("Paystack", "payments"), "paystack": ("Paystack", "payments"),
    "@supabase/supabase-js": ("Supabase", "backend"), "supabase": ("Supabase", "backend"),
    "firebase": ("Firebase / Google", "backend"),
    "firebase-admin": ("Firebase / Google", "backend"), "@aws-sdk/": ("AWS", "cloud"), "boto3": ("AWS", "cloud"),
    "@azure/": ("Azure", "cloud"), "@google-cloud/": ("Google Cloud", "cloud"), "algoliasearch": ("Algolia", "search"),
    "@pinecone-database/pinecone": ("Pinecone", "ai"), "pinecone": ("Pinecone", "ai"),
    "posthog-js": ("PostHog", "analytics"), "posthog-node": ("PostHog", "analytics"), "posthog": ("PostHog", "analytics"),
    "mixpanel": ("Mixpanel", "analytics"), "mixpanel-browser": ("Mixpanel", "analytics"),
    "@segment/": ("Segment", "analytics"), "@amplitude/": ("Amplitude", "analytics"),
    "zapier": ("Zapier", "automation"), "airtable": ("Airtable", "data"), "pyairtable": ("Airtable", "data"),
    "@notionhq/client": ("Notion", "data"), "notion-client": ("Notion", "data"),
    "googleapis": ("Google APIs", "cloud"), "google-api-python-client": ("Google APIs", "cloud"),
    "@slack/": ("Slack", "messaging"), "slack-sdk": ("Slack", "messaging"), "whatsapp": ("WhatsApp/Meta", "messaging"),
}

# Python import names that differ from the PyPI name. Matched on the first one or two dotted parts.
PY_MODULES = {
    "openai": "openai", "anthropic": "anthropic", "google.generativeai": "google-generativeai",
    "google.genai": "google-genai", "mistralai": "mistralai", "cohere": "cohere", "groq": "groq",
    "replicate": "replicate", "elevenlabs": "elevenlabs", "langchain": "langchain",
    "langchain_openai": "openai", "langchain_anthropic": "anthropic",
    "sentry_sdk": "sentry-sdk", "simple_salesforce": "simple-salesforce", "sendgrid": "sendgrid",
    "mailchimp_marketing": "mailchimp-marketing", "resend": "resend", "postmark": "postmark",
    "twilio": "twilio", "stripe": "stripe", "paystackapi": "paystack", "supabase": "supabase",
    "firebase_admin": "firebase-admin", "boto3": "boto3", "botocore": "boto3", "algoliasearch": "algoliasearch",
    "pinecone": "pinecone", "posthog": "posthog", "mixpanel": "mixpanel", "pyairtable": "pyairtable",
    "notion_client": "notion-client", "googleapiclient": "google-api-python-client", "slack_sdk": "slack-sdk",
    "google.cloud": "@google-cloud/",
}

# API and script hosts. A key matches the host itself or any subdomain of it.
HOSTS = {
    "api.openai.com": ("OpenAI", "ai"), "api.anthropic.com": ("Anthropic", "ai"),
    "generativelanguage.googleapis.com": ("Google Gemini", "ai"), "api.mistral.ai": ("Mistral", "ai"),
    "api.cohere.ai": ("Cohere", "ai"), "api.cohere.com": ("Cohere", "ai"), "api.groq.com": ("Groq", "ai"),
    "api.replicate.com": ("Replicate", "ai"), "api.elevenlabs.io": ("ElevenLabs", "ai"),
    "openrouter.ai": ("OpenRouter", "ai"), "api.together.xyz": ("Together AI", "ai"),
    "sentry.io": ("Sentry", "errors"), "ingest.sentry.io": ("Sentry", "errors"),
    "datadoghq.com": ("Datadog", "logs"), "logrocket.com": ("LogRocket", "replay"),
    "api.intercom.io": ("Intercom", "support"), "widget.intercom.io": ("Intercom", "support"),
    "zendesk.com": ("Zendesk", "support"), "client.crisp.chat": ("Crisp", "support"),
    "api.hubapi.com": ("HubSpot", "crm"), "js.hs-scripts.com": ("HubSpot", "crm"),
    "salesforce.com": ("Salesforce", "crm"), "api.pipedrive.com": ("Pipedrive", "crm"),
    "api.sendgrid.com": ("SendGrid", "email"), "api.resend.com": ("Resend", "email"),
    "api.postmarkapp.com": ("Postmark", "email"), "api.mailchimp.com": ("Mailchimp", "email"),
    "api.mailgun.net": ("Mailgun", "email"), "api.brevo.com": ("Brevo", "email"),
    "api.sendinblue.com": ("Brevo", "email"),
    "api.twilio.com": ("Twilio", "messaging"), "api.nexmo.com": ("Vonage", "messaging"),
    "platform.clickatell.com": ("Clickatell", "messaging"), "api.clickatell.com": ("Clickatell", "messaging"),
    "api.bulksms.com": ("BulkSMS", "messaging"), "graph.facebook.com": ("WhatsApp/Meta", "messaging"),
    "hooks.slack.com": ("Slack", "messaging"), "slack.com": ("Slack", "messaging"),
    "api.telegram.org": ("Telegram", "messaging"), "discord.com": ("Discord", "messaging"),
    "api.stripe.com": ("Stripe", "payments"), "js.stripe.com": ("Stripe", "payments"),
    "api.paystack.co": ("Paystack", "payments"), "js.paystack.co": ("Paystack", "payments"),
    "payfast.co.za": ("PayFast", "payments"), "online.yoco.com": ("Yoco", "payments"),
    "payments.yoco.com": ("Yoco", "payments"), "peachpayments.com": ("Peach Payments", "payments"),
    "oppwa.com": ("Peach Payments", "payments"), "ozow.com": ("Ozow", "payments"),
    "supabase.co": ("Supabase", "backend"), "firebaseio.com": ("Firebase / Google", "backend"),
    "firestore.googleapis.com": ("Firebase / Google", "backend"), "amazonaws.com": ("AWS", "cloud"),
    "blob.core.windows.net": ("Azure", "cloud"), "algolia.net": ("Algolia", "search"),
    "pinecone.io": ("Pinecone", "ai"),
    "google-analytics.com": ("Google Analytics", "analytics"), "googletagmanager.com": ("Google Tag Manager", "analytics"),
    "connect.facebook.net": ("Meta Pixel", "analytics"), "posthog.com": ("PostHog", "analytics"),
    "api.mixpanel.com": ("Mixpanel", "analytics"), "api.segment.io": ("Segment", "analytics"),
    "cdn.segment.com": ("Segment", "analytics"), "api2.amplitude.com": ("Amplitude", "analytics"),
    "static.hotjar.com": ("Hotjar", "analytics"), "clarity.ms": ("Microsoft Clarity", "analytics"),
    "plausible.io": ("Plausible", "analytics"), "snap.licdn.com": ("LinkedIn Insight", "analytics"),
    "analytics.tiktok.com": ("TikTok Pixel", "analytics"),
    "hooks.zapier.com": ("Zapier", "automation"), "hook.eu1.make.com": ("Make", "automation"),
    "hook.us1.make.com": ("Make", "automation"), "app.n8n.cloud": ("n8n Cloud", "automation"),
    "api.airtable.com": ("Airtable", "data"), "api.notion.com": ("Notion", "data"),
    "sheets.googleapis.com": ("Google Sheets", "data"), "maps.googleapis.com": ("Google Maps", "maps"),
    "api.mapbox.com": ("Mapbox", "maps"),
    "formspree.io": ("Formspree", "forms"), "getform.io": ("Getform", "forms"),
    "api.web3forms.com": ("Web3Forms", "forms"), "typeform.com": ("Typeform", "forms"),
    "tally.so": ("Tally", "forms"), "jotform.com": ("Jotform", "forms"),
}

# Hosts that are never a third party receiving data: local, reserved for examples, or spec URLs.
NOT_THIRD_PARTY = (
    "localhost", "example.com", "example.org", "example.net", "example.co.za",
    "w3.org", "www.w3.org", "json-schema.org", "json.schemastore.org", "schemas.xmlsoap.org",
    "schemas.microsoft.com", "purl.org", "xmlns.com",
)


def sdk_for_package(name: str):
    """Return (key, vendor, category) for a package name, or None."""
    n = name.strip().lower()
    for frag, (vendor, cat) in SDKS.items():
        if frag.endswith("/"):
            if n.startswith(frag):
                return frag, vendor, cat
        elif n == frag:
            return frag, vendor, cat
    return None


def sdk_for_host(host: str):
    """Return (key, vendor, category) for a host name, or None."""
    h = host.strip().lower().rstrip(".")
    for key, (vendor, cat) in HOSTS.items():
        if h == key or h.endswith("." + key):
            return key, vendor, cat
    return None


def is_not_third_party(host: str) -> bool:
    h = host.strip().lower().rstrip(".")
    if h.endswith((".local", ".localhost", ".test", ".internal", ".example", ".invalid")):
        return True
    if h.replace(".", "").isdigit() and h.startswith(("0.", "10.", "127.", "169.254.", "192.168.")):
        return True  # local and private IPv4 literals
    return any(h == x or h.endswith("." + x) for x in NOT_THIRD_PARTY)
