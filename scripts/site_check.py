#!/usr/bin/env python3
"""
site_check: passive POPIA and security check of a live website.

Passive only: ordinary GET requests a browser would make (the page, robots-style well-known
files and a few common notice paths). No probing, fuzzing or authentication attempts.
Only check sites you own or are authorised to assess.

    python3 site_check.py https://example.co.za [--out report.md] [--json report.json] [--timeout 15]

Programmatic:
    from site_check import check, fmt_md
    res = check("https://example.co.za")

Limitations: single-page apps (Lovable, Vite, React) render links and banners in JavaScript.
This tool sees the initial HTML and response headers, not the rendered page. Confirm
banner behaviour in a browser with a clean profile.

Engineering guidance, not legal advice. See DISCLAIMER.md.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import re
import socket
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from http.cookies import SimpleCookie
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

__version__ = "1.0.1"
BOT_INFO_URL = "https://github.com/VenusOne-Lee/popia-compliance/blob/main/docs/site-check-bot.md"
UA = f"popia-site-check/1.0 (+{BOT_INFO_URL}; passive)"
SEV_ORDER = ["critical", "high", "medium", "low", "info"]

TRACKER_DOMAINS = {
    "googletagmanager.com": "Google Tag Manager / gtag", "google-analytics.com": "Google Analytics",
    "connect.facebook.net": "Meta Pixel", "analytics.tiktok.com": "TikTok Pixel",
    "snap.licdn.com": "LinkedIn Insight", "static.hotjar.com": "Hotjar", "clarity.ms": "Microsoft Clarity",
    "static.ads-twitter.com": "X/Twitter Pixel", "sc-static.net": "Snap Pixel", "s.pinimg.com": "Pinterest Tag",
    "googleadservices.com": "Google Ads", "doubleclick.net": "Google Ads (DoubleClick)",
    "cdn.segment.com": "Segment", "cdn.mxpnl.com": "Mixpanel", "cdn.amplitude.com": "Amplitude",
    "posthog.com": "PostHog", "cdn.heapanalytics.com": "Heap", "fullstory.com": "FullStory",
    "cdn.logrocket.io": "LogRocket", "js.hs-scripts.com": "HubSpot", "js.hs-analytics.net": "HubSpot",
    "widget.intercom.io": "Intercom", "plausible.io": "Plausible", "cloudflareinsights.com": "Cloudflare Web Analytics",
}
CONSENT_TOOLS = {
    "cookiebot": "Cookiebot", "onetrust": "OneTrust", "cookieyes": "CookieYes", "klaro": "Klaro",
    "osano": "Osano", "iubenda": "iubenda", "termly": "Termly", "complianz": "Complianz",
    "usercentrics": "Usercentrics", "didomi": "Didomi", "cookie-consent": "generic", "cookieconsent": "generic",
    "consent-banner": "generic", "data-popia-consent": "popia-compliance registry",
}
TRACKING_COOKIES = re.compile(r"^(_ga|_gid|_gat|_gcl_|_fbp|_fbc|fr$|_hj|_clck|_clsk|_ttp|_tt_|li_|lidc|bcookie|"
                              r"ajs_|mp_|amplitude|_uetsid|_uetvid|IDE$|_pin_|_scid|hubspotutk|__hs|intercom-)", re.I)
SESSION_COOKIES = re.compile(r"(sess|sid|auth|token|jwt|csrf|xsrf|login|remember)", re.I)
NOTICE_PATHS = ["/privacy", "/privacy-policy", "/privacy-notice", "/legal/privacy", "/paia", "/paia-manual",
                "/cookies", "/cookie-policy"]


class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.scripts: List[dict] = []
        self.links: List[dict] = []
        self.inputs: List[dict] = []
        self.forms = 0
        self.text: List[str] = []
        self.iframes: List[str] = []
        self._in_a: Optional[dict] = None
        self.inline_js: List[str] = []
        self._in_script = False

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "script":
            self.scripts.append(a)
            self._in_script = not a.get("src")
        elif tag == "a":
            self._in_a = {"href": a.get("href", ""), "text": ""}
        elif tag == "input":
            self.inputs.append(a)
        elif tag == "form":
            self.forms += 1
        elif tag == "iframe":
            self.iframes.append(a.get("src", ""))

    def handle_endtag(self, tag):
        if tag == "a" and self._in_a is not None:
            self.links.append(self._in_a)
            self._in_a = None
        if tag == "script":
            self._in_script = False

    def handle_data(self, data):
        if self._in_script:
            self.inline_js.append(data)
            return
        self.text.append(data)
        if self._in_a is not None:
            self._in_a["text"] += data


class BlockedTarget(ValueError):
    """Raised when a URL or redirect points somewhere site_check must not request."""


class SiteUnreadable(RuntimeError):
    """Raised when the site answers with a bot check or an error page. Grading that page would be wrong."""

    def __init__(self, reason: str, status: int):
        self.reason, self.status = reason, status
        msg = ("the site showed a bot check instead of its page, so nothing was checked. Bot protection such as "
               "Vercel's or Cloudflare's can block automated checks" if reason == "blocked" else
               "the site answered with an error instead of its page, so nothing was checked")
        super().__init__(f"{msg} (HTTP {status})")

    hint = ("Scan your code instead, bot protection does not affect it: popia-kit scan . "
            "Or add the POPIA Kit skill to your AI tool: "
            "https://github.com/VenusOne-Lee/popia-compliance#whats-inside . "
            "If it is your site, you can allow the checker for one check: " + BOT_INFO_URL)


# Only page titles and mitigation headers: challenge scripts also load on normal pages, so they prove nothing.
_CHALLENGE_HEADERS = (("x-vercel-mitigated", re.compile(r"challenge|deny", re.I)),
                      ("cf-mitigated", re.compile(r"challenge", re.I)))
_CHALLENGE_BODY = re.compile(
    r"<title>\s*vercel security checkpoint|<title>\s*just a moment\.\.\.|"
    r"<title>\s*attention required!? \| cloudflare|<title>\s*ddos-guard|incapsula incident id", re.I)


def is_challenge(headers: dict, html: str) -> bool:
    """True when the response is a bot check page rather than the site itself. headers: lower-case keys."""
    if any(rx.search(headers.get(k, "") or "") for k, rx in _CHALLENGE_HEADERS):
        return True
    return bool(_CHALLENGE_BODY.search(html[:65536]))


def _is_public_host(host: str) -> bool:
    """True only if every address the host resolves to is a public unicast address."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%", 1)[0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved
                or ip.is_unspecified or (ip.version == 6 and ip.ipv4_mapped and not ip.ipv4_mapped.is_global)):
            return False
    return True


def _check_target(url: str, block_private: bool) -> None:
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise BlockedTarget("only http and https URLs are checked")
    if block_private and not _is_public_host(u.hostname):
        raise BlockedTarget("target resolves to a private, loopback or reserved address")


def _fetch(url: str, timeout: float, method: str = "GET", follow: bool = True, block_private: bool = False):
    ctx = ssl.create_default_context()
    _check_target(url, block_private)
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA, "Accept": "text/html,*/*"})

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    class SafeRedirect(urllib.request.HTTPRedirectHandler):
        max_redirections = 5

        def redirect_request(self, req, fp, code, msg, headers, newurl):
            _check_target(newurl, block_private)  # every hop: http(s) only, public if required
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx),
                                         SafeRedirect() if follow else NoRedirect())
    try:
        with opener.open(req, timeout=timeout) as r:
            body = r.read(2_000_000) if method == "GET" else b""
            return r.status, r.geturl(), r.headers, body
    except urllib.error.HTTPError as e:
        return e.code, url, e.headers, b""


def _f(rule_id, title, severity, popia, evidence, fix):
    return {"rule_id": rule_id, "title": title, "severity": severity, "popia": popia,
            "evidence": evidence, "fix": fix}


_REDACT = [
    (re.compile(r"([A-Za-z0-9._%+-]{1,2})[A-Za-z0-9._%+-]*(@|%40)", re.I), r"\1***\2"),
    (re.compile(r"\b\d{6}\d{4}\d{3}\b"), "*************"),
    (re.compile(r"\b\d{9,19}\b"), "*********"),
    (re.compile(r"(eyJ[A-Za-z0-9_-]{4})[A-Za-z0-9_.\-]{12,}"), r"\1…REDACTED"),
    (re.compile(r"[A-Za-z0-9_\-]{32,}"), "…REDACTED"),
]


def safe_url(u: str, keep_path: bool = True) -> str:
    """URL for reports: no credentials, query or fragment, and redacted path segments.
    The original URL is still used for the request itself."""
    try:
        p = urlparse(u)
    except ValueError:
        return "[unparseable URL]"
    host = p.hostname or ""
    if p.port:
        host = f"{host}:{p.port}"
    path = p.path if keep_path else ""
    for rx, sub in _REDACT:
        path = rx.sub(sub, path)
    note = " [query removed]" if p.query else ""
    return f"{p.scheme}://{host}{path}{note}" if p.scheme else f"{host}{path}{note}"


def check(url: str, timeout: float = 15, probe_paths: bool = True, block_private: bool = False) -> dict:
    """Passive check. Set block_private=True when the URL comes from someone else (MCP, hosted use):
    it refuses targets and redirects that resolve to private, loopback or reserved addresses."""
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    # Passive checks never authenticate: drop any user:password@ from the URL before requesting.
    _u = urlparse(url)
    if _u.username or _u.password:
        url = _u._replace(netloc=_u.hostname + (f":{_u.port}" if _u.port else "")).geturl()
    findings: List[dict] = []
    status, final_url, headers, body = _fetch(url, timeout, block_private=block_private)
    parsed = urlparse(final_url)
    html = body.decode("utf-8", errors="ignore")
    page = _PageParser()
    try:
        page.feed(html)
    except Exception:
        pass
    h = {k.lower(): v for k, v in headers.items()} if headers else {}
    # Grade only the site itself. A bot check or an error page would produce wrong findings.
    if is_challenge(h, html):
        raise SiteUnreadable("blocked", status)
    if not 200 <= status < 300:
        raise SiteUnreadable("error", status)

    # ---- transport
    if parsed.scheme != "https":
        findings.append(_f("WEB-001", "Site not served over HTTPS", "critical", "s19",
                           f"Final URL {safe_url(final_url)}", "Serve every page over HTTPS and redirect HTTP to HTTPS."))
    else:
        try:
            s2, loc, h2, _ = _fetch("http://" + (parsed.hostname or "") + "/", timeout, follow=False,
                                    block_private=block_private)
            loc = (h2.get("Location") if h2 else "") or ""
            if not (300 <= s2 < 400 and loc.startswith("https://")):
                findings.append(_f("WEB-002", "HTTP does not redirect to HTTPS", "medium", "s19",
                                   f"http:// returned {s2}", "Add a permanent redirect from HTTP to HTTPS."))
        except Exception:
            pass
        hsts = h.get("strict-transport-security", "")
        m = re.search(r"max-age=(\d+)", hsts)
        if not hsts:
            findings.append(_f("WEB-003", "Missing HSTS header", "medium", "s19", "Strict-Transport-Security absent",
                               "Add Strict-Transport-Security: max-age=63072000; includeSubDomains"))
        elif m and int(m.group(1)) < 15552000:
            findings.append(_f("WEB-003", "HSTS max-age is short", "low", "s19", hsts, "Use max-age of at least 6 months."))

    # ---- security headers
    csp = h.get("content-security-policy", "")
    if not csp:
        findings.append(_f("WEB-004", "Missing Content-Security-Policy", "medium", "s19",
                           "No CSP header", "Add a CSP restricting script sources to your domain and approved vendors."))
    elif "unsafe-inline" in csp and "script-src" in csp and "nonce-" not in csp:
        findings.append(_f("WEB-004", "CSP allows unsafe-inline scripts", "low", "s19", csp[:160],
                           "Use nonces or hashes instead of unsafe-inline."))
    if h.get("x-content-type-options", "").lower() != "nosniff":
        findings.append(_f("WEB-005", "Missing X-Content-Type-Options: nosniff", "low", "s19", "", "Add the header."))
    if "frame-ancestors" not in csp and not h.get("x-frame-options"):
        findings.append(_f("WEB-006", "No clickjacking protection", "low", "s19", "No frame-ancestors or X-Frame-Options",
                           "Add CSP frame-ancestors 'none' (or 'self')."))
    if not h.get("referrer-policy"):
        findings.append(_f("WEB-007", "Missing Referrer-Policy", "low", "s19",
                           "Full URLs (with any PI in query strings) can leak to third parties",
                           "Add Referrer-Policy: strict-origin-when-cross-origin"))
    if not h.get("permissions-policy"):
        findings.append(_f("WEB-008", "Missing Permissions-Policy", "info", "s19", "",
                           "Add Permissions-Policy to disable camera, microphone and geolocation unless needed."))
    for hdr in ("server", "x-powered-by"):
        v = h.get(hdr, "")
        if re.search(r"\d+\.\d+", v):
            findings.append(_f("WEB-009", f"Version disclosed in {hdr} header", "low", "s19", v,
                               "Remove version numbers from server headers."))

    # ---- cookies on first load (before any consent)
    cookies = []
    raw_cookies = headers.get_all("Set-Cookie") if headers and hasattr(headers, "get_all") else []
    for raw in raw_cookies or []:
        sc = SimpleCookie()
        try:
            sc.load(raw)
        except Exception:
            continue
        for name, morsel in sc.items():
            # Read parsed attributes, never search the raw header: a value like
            # "session=secure-httponly" must not count as the Secure or HttpOnly flag.
            samesite = morsel.get("samesite") or None
            c = {"name": name, "secure": bool(morsel["secure"]), "httponly": bool(morsel["httponly"]),
                 "samesite": samesite.lower() if isinstance(samesite, str) else None,
                 "tracking": bool(TRACKING_COOKIES.search(name))}
            cookies.append(c)
            if c["tracking"]:
                findings.append(_f("WEB-010", "Tracking cookie set before consent", "high", "s11; s18; s69 (Reg guidance)",
                                   f"Set-Cookie: {name}", "Set analytics and marketing cookies only after opt-in."))
            if SESSION_COOKIES.search(name) and not (c["secure"] and c["httponly"]):
                findings.append(_f("WEB-011", "Session cookie missing Secure or HttpOnly", "medium", "s19",
                                   f"{name}: secure={c['secure']} httponly={c['httponly']}",
                                   "Set Secure, HttpOnly and SameSite on session cookies."))

    # ---- trackers and consent tooling in initial HTML
    trackers = []
    third_party = set()
    for s in page.scripts:
        src = s.get("src", "")
        if src:
            host = (urlparse(urljoin(final_url, src)).hostname or "").lower()
            if host and host != (parsed.hostname or "").lower():
                third_party.add(host)
                if not s.get("integrity") and not any(d in host for d in TRACKER_DOMAINS):
                    pass
            for dom, name in TRACKER_DOMAINS.items():
                if dom in host and name not in trackers:
                    trackers.append(name)
            if src.startswith("http://"):
                findings.append(_f("WEB-012", "Script loaded over HTTP (mixed content)", "high", "s19", safe_url(src),
                                   "Load all scripts over HTTPS."))
    inline = "\n".join(page.inline_js)
    for pat, name in [(r"gtag\(\s*['\"]config", "Google Analytics / gtag"), (r"fbq\(\s*['\"]init", "Meta Pixel"),
                      (r"ttq\.load", "TikTok Pixel"), (r"_linkedin_partner_id", "LinkedIn Insight"),
                      (r"\bhj\(|hotjar", "Hotjar"), (r"clarity\(", "Microsoft Clarity"),
                      (r"GTM-[A-Z0-9]{5,}", "Google Tag Manager / gtag")]:
        if re.search(pat, inline) and name not in trackers:
            trackers.append(name)
    consent_tool = next((n for k, n in CONSENT_TOOLS.items() if k in html.lower()), None)
    consent_mode = bool(re.search(r"gtag\(\s*['\"]consent['\"]\s*,\s*['\"]default['\"]", inline))
    if trackers and not consent_tool and not consent_mode:
        findings.append(_f("WEB-013", "Trackers in page with no consent tool detected", "high",
                           "s11; s18; s69 (Reg guidance); s72",
                           ", ".join(trackers),
                           "Add a consent banner that blocks these tags until opt-in, or set Consent Mode defaults to denied. "
                           "SPAs: confirm in a browser, the banner may render later."))
    for t in trackers:
        findings.append(_f("WEB-014", f"Third-party tracker: {t}", "info", "s20; s21; s72; s18(1)(g)", t,
                           "Record as operator with country and s72 basis. Disclose in the cookie notice."))

    # ---- notices
    text_all = " ".join(page.text).lower()
    hrefs = [(l["href"].lower(), l["text"].strip().lower()) for l in page.links]
    notices = {
        "privacy": any("privacy" in hr or "privacy" in tx for hr, tx in hrefs),
        "paia": any("paia" in hr or "paia" in tx or "access to information" in tx for hr, tx in hrefs),
        "cookie": any("cookie" in hr or "cookie" in tx for hr, tx in hrefs),
        "information_officer": "information officer" in text_all,
    }
    probed = {}
    if probe_paths and parsed.scheme in ("http", "https"):
        base = f"{parsed.scheme}://{parsed.hostname}" + (f":{parsed.port}" if parsed.port else "")
        for path in NOTICE_PATHS:
            try:
                st, fu, _, b = _fetch(base + path, timeout, block_private=block_private)
                # SPAs often return index.html for every path: treat identical body as not found
                probed[path] = st == 200 and b[:2000] != body[:2000]
            except Exception:
                probed[path] = False
        if any(probed.get(p) for p in NOTICE_PATHS[:4]):
            notices["privacy"] = True
        if any(probed.get(p) for p in ("/paia", "/paia-manual")):
            notices["paia"] = True
        if any(probed.get(p) for p in ("/cookies", "/cookie-policy")):
            notices["cookie"] = True
        try:
            st, _, _, b = _fetch(base + "/.well-known/security.txt", timeout, block_private=block_private)
            has_sec_txt = st == 200 and b"contact:" in b.lower()
        except Exception:
            has_sec_txt = False
    else:
        has_sec_txt = False
    # A page that builds its content with JavaScript has no links in its HTML. Absence proves nothing there.
    spa = len(page.text) < 40 and any(s.get("type") == "module" for s in page.scripts)
    if spa:
        notices = {k: (True if v else None) for k, v in notices.items()}
        if notices["privacy"] is None or notices["paia"] is None:
            findings.append(_f("WEB-022", "Page builds its links with JavaScript", "info", "s18",
                               "Notices could not be checked: the first HTML has no links",
                               "Open the site in a browser and confirm the footer links the privacy notice and PAIA "
                               "manual. Server rendering or prerendering makes them visible to search engines and checks."))
    if notices["privacy"] is False:
        findings.append(_f("WEB-015", "No privacy notice link found", "high", "s18", "No link or common path",
                           "Publish a privacy notice and link it in the footer and next to every form."))
    if notices["paia"] is False:
        findings.append(_f("WEB-016", "No PAIA manual link found", "medium", "PAIA s51", "No PAIA link or common path",
                           "Publish the PAIA manual and link it in the footer."))
    if trackers and notices["cookie"] is False:
        findings.append(_f("WEB-017", "Trackers present but no cookie notice link", "medium", "s18",
                           "", "Publish a cookie notice listing each tool, purpose and provider."))
    if not has_sec_txt:
        findings.append(_f("WEB-018", "No /.well-known/security.txt", "low", "s19(2)", "",
                           "Publish security.txt with a security contact."))

    # ---- forms
    for i in page.inputs:
        if i.get("type", "").lower() == "checkbox" and "checked" in i:
            nm = (i.get("name", "") + i.get("id", "")).lower()
            if re.search(r"market|news|promo|consent|subscribe|offer|partner", nm):
                findings.append(_f("WEB-019", "Pre-ticked marketing or consent checkbox", "high", "s1; s11; s69",
                                   f"input name={i.get('name')}", "Default to unchecked."))
        if i.get("type", "").lower() == "password" and parsed.scheme != "https":
            findings.append(_f("WEB-020", "Password field on non-HTTPS page", "critical", "s19", "", "Serve over HTTPS."))
    for a in page.links + [{"href": s.get("src", "")} for s in page.scripts]:
        if re.search(r"[?&](email|phone|id_?number|mobile)=", a.get("href", ""), re.I):
            findings.append(_f("WEB-021", "Personal information in a URL", "medium", "s19", safe_url(a["href"])[:120],
                               "Never put PI in query strings."))
            break

    findings.sort(key=lambda f: SEV_ORDER.index(f["severity"]))
    summary = {s: sum(1 for f in findings if f["severity"] == s) for s in SEV_ORDER}
    return {
        "tool": "site_check", "version": __version__, "url": safe_url(url), "final_url": safe_url(final_url),
        "status": status,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "spa_suspected": spa, "summary": summary, "findings": findings, "cookies": cookies,
        "trackers": trackers, "third_party_script_hosts": sorted(third_party), "consent_tool": consent_tool,
        "consent_mode_default": consent_mode, "notices": notices, "probed_paths": probed,
        "disclaimer": "Passive automated check of initial HTML and headers. Leads for review, not legal "
                      "conclusions. Engineering guidance only, not legal advice.",
    }


def _mark(v) -> str:
    return "✓" if v else ("✗" if v is False else "? (couldn't tell)")


def fmt_md(res: dict) -> str:
    s = res["summary"]
    md = ["# POPIA site check", "",
          f"- **URL:** {res['url']} → {res['final_url']} (HTTP {res['status']})",
          f"- **Checked:** {res['checked_at']} · site_check {res['version']} · passive",
          f"- **Consent tool:** {res['consent_tool'] or 'none detected'} · Consent Mode default: {'yes' if res['consent_mode_default'] else 'no'}",
          f"- **Trackers in initial HTML:** {', '.join(res['trackers']) or 'none detected'}",
          f"- **Notices:** privacy {_mark(res['notices']['privacy'])} · PAIA {_mark(res['notices']['paia'])} · "
          f"cookies {_mark(res['notices']['cookie'])} · Information Officer named {_mark(res['notices']['information_officer'])}",
          ""]
    if res.get("spa_suspected"):
        md += ["> This looks like a single-page app. Links, banners and some trackers render in JavaScript, "
               "so confirm notice and banner findings in a browser with a clean profile.", ""]
    md += ["| Critical | High | Medium | Low | Info |", "|---|---|---|---|---|",
           f"| {s['critical']} | {s['high']} | {s['medium']} | {s['low']} | {s['info']} |", "",
           "| Severity | ID | Finding | POPIA | Evidence | Fix |", "|---|---|---|---|---|---|"]
    for f in res["findings"]:
        ev = (f["evidence"] or "").replace("|", "\\|")[:120]
        md.append(f"| {f['severity']} | {f['rule_id']} | {f['title']} | {f['popia']} | {ev} | {f['fix']} |")
    if res["cookies"]:
        md += ["", "## Cookies set on first load (before any consent)", "", "| Name | Tracking | Secure | HttpOnly | SameSite |",
               "|---|---|---|---|---|"]
        for c in res["cookies"]:
            md.append(f"| {c['name']} | {'yes' if c['tracking'] else 'no'} | {c['secure']} | {c['httponly']} | {c['samesite'] or '-'} |")
    md += ["", f"> {res['disclaimer']} See DISCLAIMER.md."]
    return "\n".join(md)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Passive POPIA + security check of a live site.")
    ap.add_argument("url")
    ap.add_argument("--out", help="write Markdown report")
    ap.add_argument("--json", help="write JSON result")
    ap.add_argument("--timeout", type=float, default=15)
    ap.add_argument("--no-probe", action="store_true", help="don't request common notice paths")
    ap.add_argument("--block-private", action="store_true",
                    help="refuse private, loopback and reserved targets (use for URLs supplied by others)")
    a = ap.parse_args(argv)
    try:
        res = check(a.url, a.timeout, probe_paths=not a.no_probe, block_private=a.block_private)
    except BlockedTarget as e:
        print(f"site_check: refused: {e}", file=sys.stderr)
        return 2
    except SiteUnreadable as e:
        print(f"site_check: {e}\n{e.hint}", file=sys.stderr)
        return 2
    except Exception as e:  # network errors, TLS failures; never echo URL or message (may hold tokens)
        print(f"site_check: could not fetch the site ({type(e).__name__})", file=sys.stderr)
        return 2
    md = fmt_md(res)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(md)
    if a.json:
        open(a.json, "w", encoding="utf-8").write(json.dumps(res, indent=2))
    if not a.out and not a.json:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
