// Check logic: parity with tests/scanner/test_site_check.py and tests/security/test_hardening.py,
// plus header, cookie, HTML and URL-sanitising cases.
import {
  BOT_INFO_URL,
  checkCookies,
  checkHeaders,
  checkHtml,
  DISCLAIMER,
  extraPagesSetting,
  isChallenge,
  parseHtml,
  parseRobots,
  parseSetCookie,
  pickLinks,
  runSiteCheck,
  safeUrl,
  UA,
} from "../supabase/functions/site-check/core.ts";
import { assert, assertEquals, fakeDns, html, makeCtx, mockFetch, publicDns } from "./helpers.ts";

const ids = (fs: Array<{ rule_id: string }>) => fs.map((f) => f.rule_id);

// ---------------------------------------------------------------- parity: test_site_check.py

const PAGE = `<!doctype html><html><head>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-TEST"></script>
<script>gtag('config','G-TEST'); fbq('init','1');</script></head>
<body><form><input type="email" name="email"><input type="checkbox" name="marketing_opt_in" checked></form>
<a href="/terms">Terms</a></body></html>`;

function pageHeaders() {
  const h = new Headers({ "content-type": "text/html", "x-powered-by": "Express 4.17.1" });
  h.append("set-cookie", "_ga=GA1.1.1; Path=/");
  h.append("set-cookie", "session_id=abc; Path=/");
  return h;
}

Deno.test("parity test_site_check: findings on an insecure tracker page", async () => {
  const m = mockFetch({ "http://shop.example.co.za/": () => new Response(PAGE, { headers: pageHeaders() }) });
  const res = await runSiteCheck("http://shop.example.co.za/", makeCtx(m.fn, fakeDns(publicDns("shop.example.co.za")).resolve));
  const got = ids(res.findings);
  for (const rid of ["WEB-001", "WEB-004", "WEB-009", "WEB-010", "WEB-011", "WEB-013", "WEB-015", "WEB-016", "WEB-019"]) {
    assert(got.includes(rid), rid);
  }
  assert(res.findings.some((f) => f.title === "Third-party tracker: Meta Pixel"), "Meta Pixel");
  assert(res.findings.some((f) => f.title === "Third-party tracker: Google Tag Manager / gtag"));
  assertEquals(res.disclaimer, DISCLAIMER);
  assert(res.disclaimer.includes("not legal advice"));
  assertEquals(Object.keys(res), [
    "url",
    "final_url",
    "checked_at",
    "summary",
    "findings",
    "cookies",
    "notices",
    "pages_checked",
    "disclaimer",
  ]);
  assertEquals(Object.keys(res.summary), ["critical", "high", "medium", "low", "info"]);
  assertEquals(res.summary.critical, 1);
  assert(/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+00:00$/.test(res.checked_at), res.checked_at);
  // sorted by severity
  const order = ["critical", "high", "medium", "low", "info"];
  const sev = res.findings.map((f) => order.indexOf(f.severity));
  assertEquals(sev, [...sev].sort((a, b) => a - b));
  // titles, severities and POPIA sections as in site_check.py
  const w19 = res.findings.find((f) => f.rule_id === "WEB-019")!;
  assertEquals([w19.title, w19.severity, w19.popia, w19.evidence], [
    "Pre-ticked marketing or consent checkbox",
    "high",
    "s1; s11; s69",
    "input name=marketing_opt_in",
  ]);
  const w10 = res.findings.find((f) => f.rule_id === "WEB-010")!;
  assertEquals([w10.title, w10.severity, w10.popia, w10.evidence], [
    "Tracking cookie set before consent",
    "high",
    "s11; s18; s69 (Reg guidance)",
    "Set-Cookie: _ga",
  ]);
  const w9 = res.findings.find((f) => f.rule_id === "WEB-009")!;
  assertEquals([w9.title, w9.evidence], ["Version disclosed in x-powered-by header", "Express 4.17.1"]);
});

// ---------------------------------------------------------------- parity: test_hardening.py

const SECRET = "SYNTHETICTOKEN" + "q".repeat(30);
const EMAIL_ENC = "person%40example.test";

function hardeningRoutes() {
  const h = new Headers({ "content-type": "text/html" });
  // value and path contain the flag words; the flags themselves are absent
  h.append("set-cookie", "session_id=secure-httponly; Path=/samesite=strict");
  h.append("set-cookie", "auth_token=x; Secure; HttpOnly; SameSite=Lax; Path=/");
  const body = `<html><body><script src="http://cdn.example.co.za/a.js?token=${SECRET}"></script>` +
    `<a href="/p?email=${EMAIL_ENC}&token=${SECRET}">x</a></body></html>`;
  return mockFetch({
    [`http://site.example.co.za/profile?email=${EMAIL_ENC}&token=${SECRET}`]: () => new Response(body, { headers: h }),
  });
}

Deno.test("parity test_hardening: no sensitive URL data in output", async () => {
  const m = hardeningRoutes();
  const url = `http://user:${SECRET}@site.example.co.za/profile?email=${EMAIL_ENC}&token=${SECRET}#frag`;
  const res = await runSiteCheck(url, makeCtx(m.fn, fakeDns(publicDns("site.example.co.za")).resolve));
  const blob = JSON.stringify(res);
  for (const needle of [SECRET, EMAIL_ENC, "person@example.test", "user:", "#frag"]) {
    assert(!blob.includes(needle), needle);
  }
  assert(!m.calls.some((c) => c.url.includes("user:") || c.url.includes("#")), "credentials and fragment never sent");
  assert(ids(res.findings).includes("WEB-012"), "mixed content still reported");
  assert(ids(res.findings).includes("WEB-021"), "PI in URL still reported");
  assertEquals(res.url, "http://site.example.co.za/profile [query removed]");
});

Deno.test("parity test_hardening: cookie flags are not spoofed by values", async () => {
  const m = hardeningRoutes();
  const url = `http://site.example.co.za/profile?email=${EMAIL_ENC}&token=${SECRET}`;
  const res = await runSiteCheck(url, makeCtx(m.fn, fakeDns(publicDns("site.example.co.za")).resolve));
  const c = Object.fromEntries(res.cookies.map((x) => [x.name, x]));
  assertEquals(c["session_id"]!.secure, false);
  assertEquals(c["session_id"]!.httponly, false);
  assertEquals(c["auth_token"]!.secure, true);
  assertEquals(c["auth_token"]!.httponly, true);
  assertEquals(c["auth_token"]!.samesite, "lax");
  const weak = res.findings.filter((f) => f.rule_id === "WEB-011");
  assertEquals(weak.length, 1);
  assert(weak[0]!.evidence.includes("session_id"));
  assertEquals(weak[0]!.evidence, "session_id: secure=False httponly=False");
});

// ---------------------------------------------------------------- cookies

Deno.test("cookies: flags come only from attribute names", () => {
  const cases: Array<[string, boolean, boolean, string | null]> = [
    ["session_id=secure-httponly; Path=/", false, false, null],
    ["session_id=secure-httponly; Path=/samesite=strict", false, false, null],
    ["sid=Secure; Comment=HttpOnly", false, false, null],
    ["sid=x; Path=/Secure/HttpOnly", false, false, null],
    ["sid=x; Domain=secure.example.co.za", false, false, null],
    ["sid=x; Secure; HttpOnly; SameSite=Strict", true, true, "strict"],
    ["sid=x;secure;httponly;samesite=none", true, true, "none"],
    ["sid=x; SECURE; HTTPONLY; SameSite=Lax", true, true, "lax"],
    ["sid=x; Secure=1; HttpOnly=", true, true, null],
    ["token=abc; Expires=Wed, 21 Oct 2026 07:28:00 GMT; Secure", true, false, null],
    ["sid=; Secure", true, false, null],
  ];
  for (const [raw, secure, httponly, samesite] of cases) {
    const c = parseSetCookie(raw)!;
    assertEquals([c.secure, c.httponly, c.samesite], [secure, httponly, samesite], raw);
  }
  assertEquals(parseSetCookie("no-equals-sign; Secure"), null);
  assertEquals(parseSetCookie("=value; Secure"), null);
});
Deno.test("cookies: tracking and session classification", () => {
  const h = new Headers();
  for (
    const c of [
      "_ga=1",
      "_gid=1",
      "_fbp=1",
      "fr=1",
      "_hj_s=1",
      "IDE=1",
      "hubspotutk=1",
      "li_at=1",
      "PHPSESSID=1",
      "csrftoken=1; Secure; HttpOnly",
      "theme=dark",
      "free=1",
      "IDEA=1",
    ]
  ) h.append("set-cookie", c);
  const { cookies, findings } = checkCookies(h);
  const tracking = cookies.filter((c) => c.tracking).map((c) => c.name);
  assertEquals(tracking, ["_ga", "_gid", "_fbp", "fr", "_hj_s", "IDE", "hubspotutk", "li_at"]);
  assertEquals(findings.filter((f) => f.rule_id === "WEB-011").map((f) => f.evidence.split(":")[0]), ["PHPSESSID"]);
});
Deno.test("cookies: the number of cookies is capped", () => {
  const h = new Headers();
  for (let i = 0; i < 200; i++) h.append("set-cookie", `_ga${i}=1`);
  const { cookies } = checkCookies(h);
  assertEquals(cookies.length, 50);
});

// ---------------------------------------------------------------- headers

const GOOD = {
  "strict-transport-security": "max-age=63072000; includeSubDomains",
  "content-security-policy": "default-src 'self'; frame-ancestors 'none'",
  "x-content-type-options": "nosniff",
  "referrer-policy": "strict-origin-when-cross-origin",
  "permissions-policy": "camera=()",
  server: "cloudflare",
};
const hdr = (o: Record<string, string>) => new Headers(o);

Deno.test("headers: a well configured HTTPS site has no header findings", () => {
  assertEquals(checkHeaders({ finalUrl: "https://example.co.za/", headers: hdr(GOOD) }), []);
});
Deno.test("headers: missing headers on HTTPS", () => {
  const got = checkHeaders({ finalUrl: "https://example.co.za/", headers: hdr({}) });
  assertEquals(ids(got), ["WEB-003", "WEB-004", "WEB-005", "WEB-006", "WEB-007", "WEB-008"]);
  assertEquals(got.map((f) => f.severity), ["medium", "medium", "low", "low", "low", "info"]);
  assert(got.every((f) => f.popia === "s19"));
});
Deno.test("headers: HTTP final URL gives WEB-001 and skips HSTS", () => {
  const got = checkHeaders({ finalUrl: "http://example.co.za/", headers: hdr(GOOD) });
  assertEquals(ids(got), ["WEB-001"]);
  assertEquals(got[0]!.title, "Site not served over HTTPS");
  assertEquals(got[0]!.evidence, "Final URL http://example.co.za/");
});
Deno.test("headers: short HSTS, weak CSP, framing and versions", () => {
  const short = checkHeaders({
    finalUrl: "https://e.co.za/",
    headers: hdr({ ...GOOD, "strict-transport-security": "max-age=300" }),
  });
  assertEquals(short.map((f) => [f.rule_id, f.title, f.severity]), [["WEB-003", "HSTS max-age is short", "low"]]);
  const upper = checkHeaders({
    finalUrl: "https://e.co.za/",
    headers: hdr({ ...GOOD, "strict-transport-security": "Max-Age=300" }),
  });
  assertEquals(ids(upper), ["WEB-003"]);
  const weak = checkHeaders({
    finalUrl: "https://e.co.za/",
    headers: hdr({ ...GOOD, "content-security-policy": "script-src 'self' 'unsafe-inline'; frame-ancestors 'self'" }),
  });
  assertEquals(weak.map((f) => [f.rule_id, f.title, f.severity]), [["WEB-004", "CSP allows unsafe-inline scripts", "low"]]);
  const nonce = checkHeaders({
    finalUrl: "https://e.co.za/",
    headers: hdr({ ...GOOD, "content-security-policy": "script-src 'nonce-abc' 'unsafe-inline'; frame-ancestors 'self'" }),
  });
  assertEquals(nonce, []);
  const xfo = checkHeaders({
    finalUrl: "https://e.co.za/",
    headers: hdr({ ...GOOD, "content-security-policy": "default-src 'self'", "x-frame-options": "DENY" }),
  });
  assertEquals(xfo, []);
  const ver = checkHeaders({
    finalUrl: "https://e.co.za/",
    headers: hdr({ ...GOOD, server: "nginx/1.25.3", "x-powered-by": "PHP/8.2.1" }),
  });
  assertEquals(ver.map((f) => f.title), ["Version disclosed in server header", "Version disclosed in x-powered-by header"]);
  const nosniff = checkHeaders({ finalUrl: "https://e.co.za/", headers: hdr({ ...GOOD, "x-content-type-options": "NOSNIFF" }) });
  assertEquals(nosniff, []);
});

// ---------------------------------------------------------------- HTML

const BASE = "https://example.co.za/";

Deno.test("html: trackers from script hosts and inline code", () => {
  const r = checkHtml(
    `<script src="https://connect.facebook.net/en_US/fbevents.js"></script>
     <script src="//static.hotjar.com/c/hotjar.js"></script>
     <script>ttq.load('X'); window._linkedin_partner_id = "1"; clarity("set"); var id = "GTM-ABC1234";</script>`,
    BASE,
  );
  assertEquals(r.trackers, [
    "Meta Pixel",
    "Hotjar",
    "TikTok Pixel",
    "LinkedIn Insight",
    "Microsoft Clarity",
    "Google Tag Manager / gtag",
  ]);
  assert(ids(r.findings).includes("WEB-013"));
  assertEquals(r.findings.filter((f) => f.rule_id === "WEB-014").length, 6);
  assert(ids(r.findings).includes("WEB-017"), "trackers with no cookie notice");
});
Deno.test("html: a consent tool or Consent Mode default suppresses WEB-013 only", () => {
  const tool = checkHtml(
    `<script src="https://consent.cookiebot.com/uc.js"></script>
    <script src="https://www.googletagmanager.com/gtag/js?id=G-1"></script><a href="/cookie-policy">Cookies</a>`,
    BASE,
  );
  assertEquals(tool.consentTool, "Cookiebot");
  assert(!ids(tool.findings).includes("WEB-013"));
  assert(ids(tool.findings).includes("WEB-014"));
  assert(!ids(tool.findings).includes("WEB-017"));
  const mode = checkHtml(`<script>gtag('consent', 'default', {ad_storage:'denied'}); gtag('config','G-1');</script>`, BASE);
  assertEquals(mode.consentMode, true);
  assert(!ids(mode.findings).includes("WEB-013"));
});
Deno.test("html: commented-out trackers are ignored", () => {
  const r = checkHtml(`<!-- <script src="https://connect.facebook.net/x.js"></script> fbq('init','1') -->`, BASE);
  assertEquals(r.trackers, []);
});
Deno.test("html: privacy, PAIA, cookie and Information Officer notices", () => {
  const r = checkHtml(
    `<footer><a href="/legal/privacy-notice">Legal</a><a href="/docs/manual.pdf">Access to Information Manual</a>
     <a href="/c">Cookie settings</a><p>Our Information Officer is J. Doe.</p></footer>`,
    BASE,
  );
  assertEquals(r.notices, { privacy: true, paia: true, cookie: true, information_officer: true });
  assert(!ids(r.findings).includes("WEB-015") && !ids(r.findings).includes("WEB-016"));
  const t = checkHtml(`<a href="/p">Privacy Policy</a><a href="/PAIA">x</a>`, BASE);
  assertEquals([t.notices.privacy, t.notices.paia], [true, true]);
  const none = checkHtml(`<a href="/terms">Terms</a><p>privacy matters</p>`, BASE);
  assertEquals([none.notices.privacy, none.notices.paia], [false, false]);
  const w15 = none.findings.find((f) => f.rule_id === "WEB-015")!;
  assertEquals([w15.title, w15.severity, w15.popia], ["No privacy notice link found", "medium", "s18"]);
  const w16 = none.findings.find((f) => f.rule_id === "WEB-016")!;
  assertEquals([w16.title, w16.severity, w16.popia], ["No PAIA manual link found", "medium", "PAIA s51"]);
  assert(w16.fix.includes("not a business may not need one"), w16.fix);
});
Deno.test("html: missing privacy notice is high only when the page collects something", () => {
  const sev = (html: string, cookies = 0) =>
    checkHtml(html, BASE, {}, cookies).findings.find((f) => f.rule_id === "WEB-015")!.severity;
  // Nothing visible collects personal information: medium, never lower.
  const plain = checkHtml(`<a href="/map">Map</a><input type="hidden" name="t"><button>Go</button>`, BASE);
  const w15 = plain.findings.find((f) => f.rule_id === "WEB-015")!;
  assertEquals(w15.severity, "medium");
  assert(w15.evidence.includes("No forms for personal details, cookies or trackers"), w15.evidence);
  assert(w15.fix.includes("IP addresses"), w15.fix);
  assertEquals(sev(`<iframe src="/embed"></iframe>`), "medium"); // same site frame
  // Each of these is a way to collect personal information: high.
  // A search box in a GET form is not collection on its own.
  assertEquals(sev(`<form action="/search" method="get"><input name="q"><select name="from_stop"></select></form>`), "medium");
  assertEquals(sev(`<input name="q">`), "medium");
  // A form that posts, a text area, or a field that asks for personal details is.
  assertEquals(sev(`<form method="POST" action="/s"><button>Go</button></form>`), "high");
  assertEquals(sev(`<form><textarea></textarea></form>`), "high");
  assertEquals(sev(`<form><input name="full_name"></form>`), "high");
  assertEquals(sev(`<input id="x" autocomplete="tel">`), "high");
  assertEquals(sev(`<input type="password" name="p">`), "high");
  assertEquals(sev(`<input type="email" name="e">`), "high");
  assertEquals(sev(`<iframe src="https://video.example.net/embed/1"></iframe>`), "high");
  assertEquals(sev(`<script src="https://www.googletagmanager.com/gtag/js?id=G-TEST"></script>`), "high");
  assertEquals(sev(`<p>hi</p>`, 1), "high");
});
Deno.test("check: cookies set on first load keep a missing privacy notice high", async () => {
  const h = new Headers({ "content-type": "text/html" });
  h.append("set-cookie", "pref=1; Path=/; Secure; HttpOnly");
  const m = mockFetch({ "http://plain.example.co.za/": () => new Response(`<p>hello</p>`, { headers: h }) });
  const res = await runSiteCheck("http://plain.example.co.za/", makeCtx(m.fn, fakeDns(publicDns("plain.example.co.za")).resolve));
  assertEquals(res.findings.find((f) => f.rule_id === "WEB-015")!.severity, "high");
  const m2 = mockFetch({
    "http://plain.example.co.za/": () => new Response(`<p>hello</p>`, { headers: { "content-type": "text/html" } }),
  });
  const res2 = await runSiteCheck(
    "http://plain.example.co.za/",
    makeCtx(m2.fn, fakeDns(publicDns("plain.example.co.za")).resolve),
  );
  assertEquals(res2.findings.find((f) => f.rule_id === "WEB-015")!.severity, "medium");
});
Deno.test("html: probed notice paths count as found", () => {
  const r = checkHtml(`<p>hi</p>`, BASE, { privacy: true, paia: true });
  assertEquals([r.notices.privacy, r.notices.paia, r.notices.cookie], [true, true, false]);
});
Deno.test("html: SPA shells report notices as unknown, not missing", () => {
  const shell = `<!doctype html><html><head><script type="module" src="/assets/index.js"></script></head>
    <body><div id="root"></div></body></html>`;
  const r = checkHtml(shell, BASE);
  assertEquals(r.spa, true);
  assertEquals(r.notices, { privacy: null, paia: null, cookie: null, information_officer: null });
  assertEquals(ids(r.findings).filter((x) => /WEB-01[567]|WEB-022/.test(x)), ["WEB-022"]);
  assertEquals(r.findings.find((f) => f.rule_id === "WEB-022")!.severity, "info");
  const probed = checkHtml(shell, BASE, { privacy: true });
  assertEquals([probed.notices.privacy, probed.notices.paia], [true, null]);
});
Deno.test("challenge: bot check pages and mitigation headers are detected", () => {
  const h = (o: Record<string, string> = {}) => new Headers(o);
  assert(isChallenge(h({ "x-vercel-mitigated": "challenge" }), ""));
  assert(isChallenge(h({ "cf-mitigated": "challenge" }), ""));
  assert(isChallenge(h(), "<html><head><title>Vercel Security Checkpoint</title>"));
  assert(isChallenge(h(), "<html><head><title>Just a moment...</title>"));
  assert(isChallenge(h(), "<title>Attention Required! | Cloudflare</title>"));
  assert(!isChallenge(h(), `<title>Shop</title><script src="/cdn-cgi/challenge-platform/scripts/jsd/main.js"></script>`));
  assert(!isChallenge(h({ server: "Vercel" }), "<title>Privacy matters</title>"));
});
Deno.test("html: pre-ticked checkboxes", () => {
  const cases: Array<[string, boolean]> = [
    [`<input type="checkbox" name="newsletter" checked>`, true],
    [`<input type="checkbox" name="optin" id="marketingOptIn" checked="checked">`, true],
    [`<INPUT TYPE="CHECKBOX" NAME="Partner_Offers" CHECKED />`, true],
    [`<input type=checkbox name=consent checked>`, true],
    [`<input type="checkbox" name="newsletter">`, false],
    [`<input type="checkbox" name="remember_me" checked>`, false],
    [`<input type="radio" name="newsletter" checked>`, false],
    [`<input type="checkbox" name="terms" data-x="checked">`, false],
  ];
  for (const [h, expected] of cases) assertEquals(ids(checkHtml(h, BASE).findings).includes("WEB-019"), expected, h);
});
Deno.test("html: password field on HTTP only", () => {
  const form = `<form><input type="password" name="pw"></form>`;
  assert(ids(checkHtml(form, "http://example.co.za/").findings).includes("WEB-020"));
  assert(!ids(checkHtml(form, BASE).findings).includes("WEB-020"));
});
Deno.test("html: mixed content and PI in URLs", () => {
  const r = checkHtml(
    `<script src="http://cdn.example.co.za/a.js"></script><script src="https://ok.example.co.za/b.js?mobile=0821234567"></script>
    <a href="/x?phone=1">a</a><a href="/y?email=a@b.co">b</a>`,
    BASE,
  );
  assertEquals(r.findings.filter((f) => f.rule_id === "WEB-012").length, 1);
  const pi = r.findings.filter((f) => f.rule_id === "WEB-021");
  assertEquals(pi.length, 1, "reported once");
  assertEquals(pi[0]!.evidence, "/x [query removed]");
});
Deno.test("html: parser handles quotes, entities, odd markup and __proto__", () => {
  const p = parseHtml(`<a data-x="a>b" href='/priv&amp;acy' __proto__="x">Privacy &amp; you</a>
    <a href=/paia>PAIA</a><scr<a href="/z">z</a><script>var s = "</div><a href='/fake'>";</script>
    <style>a{}</style><a href="/c"`);
  // "<scr<a" is one tag name, as in Python's HTMLParser; the script string and the unterminated tag are ignored
  assertEquals(p.links.map((l) => l.href), ["/priv&acy", "/paia"]);
  assertEquals(p.links[0]!.text, "Privacy & you");
  assertEquals(p.inlineJs.length, 1);
  assertEquals(Object.getPrototypeOf({}), Object.prototype, "no global prototype change");
});
Deno.test("html: pathological input stays fast", () => {
  const inputs = [
    "<".repeat(500_000),
    "<a ".repeat(300_000),
    `<a x="`.repeat(200_000),
    "<!--".repeat(300_000),
    "<script>".repeat(200_000),
    "&amp;".repeat(300_000),
    "<a href=x>".repeat(100_000),
  ];
  for (const s of inputs) {
    const t0 = performance.now();
    checkHtml(s, BASE);
    const ms = performance.now() - t0;
    assert(ms < 3_000, `${s.slice(0, 10)} took ${ms} ms`);
  }
});

// ---------------------------------------------------------------- URL sanitising

Deno.test("safeUrl: credentials, query and fragment never appear", () => {
  const cases: Array<[string, string]> = [
    ["https://user:pass@example.co.za/a?b=c#d", "https://example.co.za/a [query removed]"],
    ["https://example.co.za/a#d", "https://example.co.za/a"],
    ["https://example.co.za/a?", "https://example.co.za/a"],
    ["http://example.co.za:8080/x", "http://example.co.za:8080/x"],
    ["/p?email=x", "/p [query removed]"],
    ["//cdn.example.co.za/a.js?t=1", "//cdn.example.co.za/a.js [query removed]"],
    ["//u:p@cdn.example.co.za/a.js", "//cdn.example.co.za/a.js"],
    ["https://e.co.za/u/person@example.test/x", "https://e.co.za/u/pe***@example.test/x"],
    ["https://e.co.za/u/person%40example.test", "https://e.co.za/u/pe***%40example.test"],
    ["https://e.co.za/id/1234567890123", "https://e.co.za/id/*************"],
    ["https://e.co.za/acct/123456789012", "https://e.co.za/acct/*********"],
    ["https://e.co.za/t/eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig", "https://e.co.za/t/eyJhbGc…REDACTED"],
    ["https://e.co.za/k/" + "a".repeat(40), "https://e.co.za/k/…REDACTED"],
  ];
  for (const [inp, out] of cases) assertEquals(safeUrl(inp), out, inp);
  assertEquals(safeUrl("https://e.co.za/a/b", false), "https://e.co.za");
});

// ---------------------------------------------------------------- user agent

// Same string as UA in scripts/site_check.py and docs/site-check-bot.md. Site owners allowlist or block on it.
Deno.test("parity test_site_check: the user agent names the checker and links its page", () => {
  assertEquals(BOT_INFO_URL, "https://github.com/VenusOne-Lee/popia-compliance/blob/main/docs/site-check-bot.md");
  assertEquals(UA, `popia-site-check/1.0 (+${BOT_INFO_URL}; passive)`);
});

// ---------------------------------------------------------------- linked pages and robots.txt

Deno.test("robots: the group for this checker wins, longest rule decides, Allow wins a tie", () => {
  const all = parseRobots("User-agent: *\nDisallow: /private\nAllow: /private/open\nDisallow: /*.php$\n");
  assertEquals([all("/"), all("/private"), all("/private/x"), all("/private/open/1"), all("/a.php"), all("/a.php/b")], [
    true,
    false,
    false,
    true,
    false,
    true,
  ]);
  const mine = parseRobots("User-agent: *\nDisallow: /\n\nUser-agent: popia-site-check\nAllow: /\n");
  assertEquals(mine("/map"), true);
  const blocked = parseRobots("User-agent: popia-site-check\nUser-agent: other\nDisallow: /\n");
  assertEquals(blocked("/map"), false);
  const tie = parseRobots("User-agent: *\nDisallow: /a\nAllow: /a\n");
  assertEquals(tie("/a"), true);
  assertEquals(parseRobots("")("/x"), true);
  assertEquals(parseRobots("User-agent: *\nDisallow:\n")("/x"), true); // empty Disallow allows all
  // Many wildcards on a long path finish quickly: matching is linear, not a backtracking regex.
  const stars = parseRobots("User-agent: *\nDisallow: /" + "*a".repeat(200) + "b\n");
  const t0 = Date.now();
  assertEquals(stars("/" + "a".repeat(5000)), true);
  assert(Date.now() - t0 < 500, "slow robots match");
});

Deno.test("links: same site plain paths only, in page order, no files, actions or notice paths", () => {
  const page = parseHtml(`
    <a href="/map">Map</a><a href="/map#top">Map again</a><a href="https://other.example.net/x">Other</a>
    <a href="/search?q=a">Search</a><a href="/files/a.pdf">PDF</a><a href="/logout">Out</a>
    <a href="/privacy">Privacy</a><a href="/">Home</a><a href="mailto:a@example.test">Mail</a>
    <a href="/stops">Stops</a><a href="/routes/">Routes</a><a href="/about">About</a>`);
  assertEquals(pickLinks(page, BASE, 10), [
    "https://example.co.za/map",
    "https://example.co.za/stops",
    "https://example.co.za/routes/",
    "https://example.co.za/about",
  ]);
  assertEquals(pickLinks(page, BASE, 2), ["https://example.co.za/map", "https://example.co.za/stops"]);
});

Deno.test("html: linked pages add trackers, third-party scripts, mixed content and collection signals", () => {
  const home = `<a href="/map">Map</a><a href="/privacy">Privacy</a><a href="/paia">PAIA</a>`;
  const map = `<script src="https://cdn.example.net/leaflet/1.9.4/leaflet.js"></script>
    <script src="https://static.example.co.za/app.js"></script><script src="http://cdn.example.org/old.js"></script>
    <script src="https://connect.facebook.net/en_US/fbevents.js"></script><form><input name="q"></form>`;
  const one = checkHtml(home, BASE);
  assert(!ids(one.findings).includes("WEB-023"));
  const r = checkHtml(home, BASE, {}, 0, [{ url: "https://example.co.za/map", html: map }]);
  const w23 = r.findings.find((f) => f.rule_id === "WEB-023")!;
  assertEquals([w23.title, w23.severity, w23.popia], ["Scripts loaded from other sites", "info", "s20; s21; s72"]);
  assertEquals(w23.evidence, "cdn.example.net (/map), cdn.example.org (/map)"); // own subdomain and tracker left out
  const w14 = r.findings.find((f) => f.rule_id === "WEB-014")!;
  assertEquals(w14.evidence, "Meta Pixel on /map");
  assert(ids(r.findings).includes("WEB-013"), "tracker on a linked page with no consent tool");
  const w12 = r.findings.find((f) => f.rule_id === "WEB-012")!;
  assertEquals(w12.evidence, "http://cdn.example.org/old.js on /map");
  // Notices still come from the checked page only.
  assertEquals([r.notices.privacy, r.notices.paia], [true, true]);
  // A consent tool on any checked page counts.
  const consent = checkHtml(home, BASE, {}, 0, [{
    url: "https://example.co.za/map",
    html: map + `<div data-popia-consent></div>`,
  }]);
  assert(!ids(consent.findings).includes("WEB-013"));
});

Deno.test("html: a form on a linked page keeps a missing privacy notice high", () => {
  const sev = (extra: string) =>
    checkHtml(`<a href="/map">Map</a>`, BASE, {}, 0, [{ url: "https://example.co.za/map", html: extra }])
      .findings.find((f) => f.rule_id === "WEB-015")!.severity;
  assertEquals(sev(`<p>map</p>`), "medium");
  assertEquals(sev(`<form><input type="email" name="e"></form>`), "high");
});

Deno.test("html: WEB-023 names at most 10 hosts", () => {
  const scripts = Array.from({ length: 12 }, (_, i) => `<script src="https://cdn${i}.example.net/x.js"></script>`).join("");
  const w23 = checkHtml(scripts, BASE).findings.find((f) => f.rule_id === "WEB-023")!;
  assert(w23.evidence.endsWith(", and 2 more"), w23.evidence);
  assert(!w23.evidence.includes("(/"), "hosts on the checked page carry no page label");
});

const HOME = `<a href="/map">Map</a><a href="/stops">Stops</a><a href="/away">Away</a><a href="/slow">Slow</a>`;
const MAP = `<script src="https://cdn.example.net/leaflet.js"></script>`;

function crawlRoutes(robots: () => Response) {
  return {
    "https://example.co.za/": html(HOME),
    "https://example.co.za/robots.txt": robots,
    "https://example.co.za/map": html(MAP),
    "https://example.co.za/stops": html(`<p>stops</p>`),
    "https://example.co.za/away": () => new Response(null, { status: 302, headers: { location: "https://other.example.net/" } }),
    "https://other.example.net/": html(MAP.replace("cdn.example.net", "cdn.other.example.net")),
  };
}
const crawlDns = () => fakeDns(publicDns("example.co.za", "other.example.net")).resolve;

Deno.test("check: linked pages are fetched only where robots.txt allows and only on the same site", async () => {
  const text = (body: string, status = 200) => () => new Response(body, { status, headers: { "content-type": "text/plain" } });
  // No robots.txt: up to 3 linked pages. The off-site redirect is dropped.
  const m = mockFetch(crawlRoutes(text("", 404)));
  const res = await runSiteCheck("https://example.co.za/", makeCtx(m.fn, crawlDns()), { extraPages: 3 });
  assertEquals(res.pages_checked, ["/", "/map", "/stops"]);
  assert(m.calls.some((c) => c.url === "https://example.co.za/away"), "away was tried");
  assert(!m.calls.some((c) => c.url === "https://example.co.za/slow"), "only 3 pages");
  assertEquals(res.findings.find((f) => f.rule_id === "WEB-023")!.evidence, "cdn.example.net (/map)");
  // robots.txt disallows /map for everyone.
  const m2 = mockFetch(crawlRoutes(text("User-agent: *\nDisallow: /map\n")));
  const res2 = await runSiteCheck("https://example.co.za/", makeCtx(m2.fn, crawlDns()), { extraPages: 3 });
  assert(!m2.calls.some((c) => c.url === "https://example.co.za/map"), "disallowed page fetched");
  assert(!ids(res2.findings).includes("WEB-023"));
  assertEquals(res2.pages_checked, ["/", "/stops"]);
  // robots.txt server error: no linked page is fetched.
  const m3 = mockFetch(crawlRoutes(text("", 503)));
  const res3 = await runSiteCheck("https://example.co.za/", makeCtx(m3.fn, crawlDns()), { extraPages: 3 });
  assertEquals(res3.pages_checked, ["/"]);
  assert(!m3.calls.some((c) => c.url === "https://example.co.za/map"));
  // Off by default in the core: not even robots.txt is requested.
  const m4 = mockFetch(crawlRoutes(text("")));
  const res4 = await runSiteCheck("https://example.co.za/", makeCtx(m4.fn, crawlDns()));
  assertEquals(res4.pages_checked, ["/"]);
  assert(!m4.calls.some((c) => c.url.endsWith("/robots.txt")));
});

Deno.test("check: a linked page behind a bot check or with an error is skipped, not graded", async () => {
  const routes = {
    "https://example.co.za/": html(`<a href="/map">Map</a><a href="/stops">Stops</a>`),
    "https://example.co.za/map": html(`<title>Just a moment...</title>` + MAP),
    "https://example.co.za/stops": html(MAP, {}, 500),
  };
  const m = mockFetch(routes);
  const res = await runSiteCheck("https://example.co.za/", makeCtx(m.fn, crawlDns()), { extraPages: 3 });
  assertEquals(res.pages_checked, ["/"]);
  assert(!ids(res.findings).includes("WEB-023"));
});

Deno.test("settings: EXTRA_PAGES defaults to 3, accepts 0 to 3, and fails closed to 0", () => {
  assertEquals(
    [undefined, "", "0", "2", "3", "9", "-1", "two", "1.5"].map((v) => extraPagesSetting(v)),
    [3, 3, 0, 2, 3, 3, 0, 0, 0],
  );
});
