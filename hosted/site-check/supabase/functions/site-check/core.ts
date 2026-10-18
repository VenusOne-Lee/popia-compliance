// site-check core: passive POPIA and security check of a public website.
//
// Port of popia-compliance/scripts/site_check.py (v1.0.1) for public, untrusted input.
// Passive only: ordinary GET requests. No form submissions, no probing, no authentication.
//
// POST {"url": "...", "turnstileToken": "..."}  ->  {url, final_url, checked_at, summary,
//      findings[], cookies[], notices, disclaimer}
//
// Runtime agnostic. No imports, no Deno or Node globals. Only Web APIs: fetch types,
// Request/Response/Headers, AbortSignal, crypto.subtle, TextEncoder/TextDecoder, ReadableStream.
// Runs on Deno (Supabase Edge Functions, see index.ts) and Node 20+ (see adapters/).
// Only erasable TypeScript syntax is used, so Node's built-in type stripping can load it.
//
// Engineering guidance, not legal advice.

// ---------------------------------------------------------------- constants

export const VERSION = "1.0.1-edge";
const UA = "popia-site-check/1.0 (+https://github.com/VenusOne-Lee/popia-compliance; passive)";
export const SEV_ORDER = ["critical", "high", "medium", "low", "info"] as const;
export type Severity = typeof SEV_ORDER[number];

export const DISCLAIMER = "Passive automated check of initial HTML and headers. Leads for review, not legal conclusions. " +
  "Engineering guidance only, not legal advice.";

export const LIMITS = {
  perRequestMs: 8_000,
  overallMs: 20_000,
  maxBodyBytes: 1_572_864, // 1.5 MB
  maxRedirects: 5,
  maxProbeBytes: 2_000,
  maxSecurityTxtBytes: 32_768,
  maxDohBytes: 65_536,
  maxRequestBodyBytes: 8_192,
  maxUrlLength: 2_048,
  maxTokenLength: 2_048,
  maxCookies: 50,
  maxFindingsPerRule: 20,
  maxEvidence: 300,
  maxCnameDepth: 8,
  requestBodyMs: 5_000, // time allowed to receive the small JSON request body
  maxReportPath: 512, // path characters kept in report URLs; bounds the redaction regexes
  maxHeaderScan: 256, // header characters scanned by WEB-009
};

const DOH_URL = "https://cloudflare-dns.com/dns-query";
const TURNSTILE_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify";
const REDIRECT_STATUSES = new Set([301, 302, 303, 307, 308]);

const TRACKER_DOMAINS: Record<string, string> = {
  "googletagmanager.com": "Google Tag Manager / gtag",
  "google-analytics.com": "Google Analytics",
  "connect.facebook.net": "Meta Pixel",
  "analytics.tiktok.com": "TikTok Pixel",
  "snap.licdn.com": "LinkedIn Insight",
  "static.hotjar.com": "Hotjar",
  "clarity.ms": "Microsoft Clarity",
  "static.ads-twitter.com": "X/Twitter Pixel",
  "sc-static.net": "Snap Pixel",
  "s.pinimg.com": "Pinterest Tag",
  "googleadservices.com": "Google Ads",
  "doubleclick.net": "Google Ads (DoubleClick)",
  "cdn.segment.com": "Segment",
  "cdn.mxpnl.com": "Mixpanel",
  "cdn.amplitude.com": "Amplitude",
  "posthog.com": "PostHog",
  "cdn.heapanalytics.com": "Heap",
  "fullstory.com": "FullStory",
  "cdn.logrocket.io": "LogRocket",
  "js.hs-scripts.com": "HubSpot",
  "js.hs-analytics.net": "HubSpot",
  "widget.intercom.io": "Intercom",
  "plausible.io": "Plausible",
  "cloudflareinsights.com": "Cloudflare Web Analytics",
};
const CONSENT_TOOLS: Record<string, string> = {
  "cookiebot": "Cookiebot",
  "onetrust": "OneTrust",
  "cookieyes": "CookieYes",
  "klaro": "Klaro",
  "osano": "Osano",
  "iubenda": "iubenda",
  "termly": "Termly",
  "complianz": "Complianz",
  "usercentrics": "Usercentrics",
  "didomi": "Didomi",
  "cookie-consent": "generic",
  "cookieconsent": "generic",
  "consent-banner": "generic",
  "data-popia-consent": "popia-compliance registry",
};
const INLINE_TRACKERS: Array<[RegExp, string]> = [
  [/gtag\(\s*['"]config/, "Google Analytics / gtag"],
  [/fbq\(\s*['"]init/, "Meta Pixel"],
  [/ttq\.load/, "TikTok Pixel"],
  [/_linkedin_partner_id/, "LinkedIn Insight"],
  [/\bhj\(|hotjar/, "Hotjar"],
  [/clarity\(/, "Microsoft Clarity"],
  [/GTM-[A-Z0-9]{5,}/, "Google Tag Manager / gtag"],
];
const TRACKING_COOKIES = new RegExp(
  "^(_ga|_gid|_gat|_gcl_|_fbp|_fbc|fr$|_hj|_clck|_clsk|_ttp|_tt_|li_|lidc|bcookie|" +
    "ajs_|mp_|amplitude|_uetsid|_uetvid|IDE$|_pin_|_scid|hubspotutk|__hs|intercom-)",
  "i",
);
const SESSION_COOKIES = /(sess|sid|auth|token|jwt|csrf|xsrf|login|remember)/i;
export const NOTICE_PATHS = [
  "/privacy",
  "/privacy-policy",
  "/privacy-notice",
  "/legal/privacy",
  "/paia",
  "/paia-manual",
  "/cookies",
  "/cookie-policy",
];

// Names that never point at a public website. Superset of the required list.
const BLOCKED_SUFFIXES = [
  "localhost",
  "local",
  "internal",
  "lan",
  "home.arpa",
  "arpa",
  "localdomain",
  "test",
  "invalid",
  "example",
  "onion",
];

// ---------------------------------------------------------------- errors

export class CheckError extends Error {
  type: string;
  status: number;
  constructor(type: string, status: number) {
    super(type);
    this.name = "CheckError";
    this.type = type;
    this.status = status;
  }
}

export const ERROR_MESSAGES: Record<string, string> = {
  origin_not_allowed: "Origin not allowed.",
  method_not_allowed: "Use POST.",
  invalid_request: "Send a JSON body with a url field.",
  invalid_url: "Enter a valid http or https address.",
  blocked_target: "This address cannot be checked.",
  turnstile_failed: "Verification failed. Please try again.",
  rate_limited: "Too many checks. Try again later.",
  dns_failed: "The site address could not be resolved.",
  fetch_failed: "The site could not be reached.",
  timeout: "The site took too long to respond.",
  too_many_redirects: "The site redirected too many times.",
  internal_error: "Something went wrong.",
};

const blocked = () => new CheckError("blocked_target", 400);

// ---------------------------------------------------------------- IP guard

/** Strict dotted quad. No leading zeros, no shorthand. */
export function parseIPv4(s: string): number[] | null {
  const m = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/.exec(s);
  if (!m) return null;
  const parts = m.slice(1).map((p) => (p.length > 1 && p.startsWith("0") ? NaN : Number(p)));
  return parts.every((n) => Number.isInteger(n) && n >= 0 && n <= 255) ? parts : null;
}

/** Eight 16-bit groups, or null. Accepts brackets and an embedded IPv4 tail. Rejects zone IDs. */
export function parseIPv6(input: string): number[] | null {
  let s = input.trim();
  if (s.startsWith("[") && s.endsWith("]")) s = s.slice(1, -1);
  if (!s || s.includes("%") || !/^[0-9a-fA-F:.]+$/.test(s) || !s.includes(":")) return null;
  if (s.includes(".")) {
    const i = s.lastIndexOf(":");
    const v4 = parseIPv4(s.slice(i + 1));
    if (!v4) return null;
    s = s.slice(0, i + 1) + ((v4[0]! << 8) | v4[1]!).toString(16) + ":" + ((v4[2]! << 8) | v4[3]!).toString(16);
  }
  const halves = s.split("::");
  if (halves.length > 2) return null;
  const grp = (h: string) => (h === "" ? [] : h.split(":"));
  const head = grp(halves[0]!);
  const tail = halves.length === 2 ? grp(halves[1]!) : [];
  const all = [...head, ...tail];
  if (!all.every((g) => /^[0-9a-fA-F]{1,4}$/.test(g))) return null;
  if (halves.length === 1 && head.length !== 8) return null;
  if (halves.length === 2 && all.length > 7) return null;
  const nums = (a: string[]) => a.map((g) => parseInt(g, 16));
  const fill = new Array(8 - all.length).fill(0);
  return halves.length === 2 ? [...nums(head), ...fill, ...nums(tail)] : nums(head);
}

export function isPublicIPv4(o: number[]): boolean {
  const [a, b, c] = o;
  if (a === 0 || a === 10 || a === 127 || a! >= 224) return false; // this-net, private, loopback, multicast, reserved, broadcast
  if (a === 100 && b! >= 64 && b! <= 127) return false; // CGNAT 100.64/10
  if (a === 169 && b === 254) return false; // link-local incl. 169.254.169.254
  if (a === 172 && b! >= 16 && b! <= 31) return false; // private
  if (a === 192 && b === 168) return false; // private
  if (a === 192 && b === 0 && (c === 0 || c === 2)) return false; // IETF assignments, TEST-NET-1
  if (a === 192 && b === 88 && c === 99) return false; // 6to4 relay anycast
  if (a === 198 && (b === 18 || b === 19)) return false; // benchmarking
  if (a === 198 && b === 51 && c === 100) return false; // TEST-NET-2
  if (a === 203 && b === 0 && c === 113) return false; // TEST-NET-3
  if (a === 168 && b === 63 && c === 129 && o[3] === 16) return false; // Azure WireServer, reachable only from inside Azure
  return true;
}

const v4FromGroups = (hi: number, lo: number) => [hi >> 8, hi & 0xff, lo >> 8, lo & 0xff];

export function isPublicIPv6(g: number[]): boolean {
  const zero = (from: number, to: number) => g.slice(from, to).every((x) => x === 0);
  // IPv4-mapped ::ffff:a.b.c.d: judge the embedded address.
  if (zero(0, 5) && g[5] === 0xffff) return isPublicIPv4(v4FromGroups(g[6]!, g[7]!));
  // NAT64 well-known prefix 64:ff9b::/96: judge the embedded address.
  if (g[0] === 0x64 && g[1] === 0xff9b && zero(2, 6)) return isPublicIPv4(v4FromGroups(g[6]!, g[7]!));
  // Only global unicast 2000::/3. This excludes ::, ::1, ::/8, 64:ff9b:1::/48, 100::/64,
  // fc00::/7, fe80::/10, fec0::/10, ff00::/8 and everything else outside 2000::/3.
  if ((g[0]! & 0xe000) !== 0x2000) return false;
  if (g[0] === 0x2001 && g[1]! < 0x0200) return false; // 2001::/23 IETF assignments incl. Teredo
  if (g[0] === 0x2001 && g[1] === 0x0db8) return false; // documentation
  if (g[0] === 0x3fff && g[1]! < 0x1000) return false; // 3fff::/20 documentation
  if (g[0] === 0x2002) return isPublicIPv4(v4FromGroups(g[1]!, g[2]!)); // 6to4: judge the embedded address
  return true;
}

/** True only for a literal public unicast IPv4 or IPv6 address. Anything unparseable is false. */
export function isPublicIp(s: string): boolean {
  const v4 = parseIPv4(s);
  if (v4) return isPublicIPv4(v4);
  const v6 = parseIPv6(s);
  return v6 ? isPublicIPv6(v6) : false;
}

// ---------------------------------------------------------------- hostname and URL guard

/** Hostname rules for DNS names (not IP literals). Lowercase, no trailing dot expected. */
export function isAllowedHostname(name: string): boolean {
  const host = name.toLowerCase().replace(/\.$/, "");
  if (!host || host.length > 253 || !host.includes(".")) return false; // empty or single label
  const labels = host.split(".");
  if (!labels.every((l) => /^[a-z0-9_](?:[a-z0-9_-]{0,61}[a-z0-9_])?$/.test(l))) return false;
  if (/^\d+$/.test(labels[labels.length - 1]!)) return false; // numeric TLD: an IP in disguise
  return !BLOCKED_SUFFIXES.some((s) => host === s || host.endsWith("." + s));
}

export type HostKind = "ipv4" | "ipv6" | "name";

/**
 * Static URL checks. Returns a new URL with credentials and fragment removed.
 * Throws CheckError("blocked_target") for anything that must not be requested.
 */
export function validateTargetUrl(raw: string): { url: URL; kind: HostKind; host: string } {
  let u: URL;
  try {
    u = new URL(raw);
  } catch {
    throw new CheckError("invalid_url", 400);
  }
  if (u.protocol !== "http:" && u.protocol !== "https:") throw blocked();
  if (u.port !== "" && u.port !== "80" && u.port !== "443") throw blocked();
  u.username = "";
  u.password = "";
  u.hash = "";
  const hostname = u.hostname.toLowerCase();
  if (hostname.startsWith("[")) {
    const v6 = parseIPv6(hostname);
    if (!v6 || !isPublicIPv6(v6)) throw blocked();
    return { url: u, kind: "ipv6", host: hostname };
  }
  if (/^[0-9.]+$/.test(hostname.replace(/\.$/, ""))) {
    const v4 = parseIPv4(hostname.replace(/\.$/, ""));
    if (!v4 || !isPublicIPv4(v4)) throw blocked();
    return { url: u, kind: "ipv4", host: hostname };
  }
  if (!isAllowedHostname(hostname)) throw blocked();
  return { url: u, kind: "name", host: hostname.replace(/\.$/, "") };
}

/** Normalise user input the way site_check.py does: add https:// when no scheme is given. */
export function normaliseInputUrl(input: string): string {
  const s = input.trim();
  if (/^https?:\/\//i.test(s)) return s;
  if (/^[a-z][a-z0-9+.-]*:\/\//i.test(s)) throw blocked(); // ftp://, file://, gopher:// and friends
  if (/^(javascript|data|file|blob|about|mailto|vbscript):/i.test(s)) throw blocked();
  return "https://" + s;
}

// ---------------------------------------------------------------- DNS over HTTPS

export type FetchFn = (input: string, init?: RequestInit) => Promise<Response>;
export interface DnsAnswer {
  type: number;
  data: string;
}
export interface DnsResult {
  status: number;
  answers: DnsAnswer[];
}
export type DnsResolver = (name: string, type: "A" | "AAAA", signal: AbortSignal) => Promise<DnsResult>;

/** AbortSignal.any, with a small fallback for runtimes that lack it (Node before 20.3). */
export function anySignal(signals: AbortSignal[]): AbortSignal {
  const native = (AbortSignal as unknown as { any?: (s: AbortSignal[]) => AbortSignal }).any;
  if (typeof native === "function") return native.call(AbortSignal, signals);
  const ac = new AbortController();
  for (const s of signals) {
    if (s.aborted) {
      ac.abort(s.reason);
      break;
    }
    s.addEventListener("abort", () => ac.abort(s.reason), { once: true });
  }
  return ac.signal;
}

const withTimeout = (signal: AbortSignal, ms = LIMITS.perRequestMs) => anySignal([signal, AbortSignal.timeout(ms)]);

/** Settle with `p`, or reject with the signal's reason as soon as it aborts, whichever comes first. */
function raceSignal<T>(p: Promise<T>, signal: AbortSignal): Promise<T> {
  p.catch(() => {}); // a late rejection after the race is decided must not become unhandled
  if (signal.aborted) return Promise.reject(signal.reason);
  return new Promise<T>((resolve, reject) => {
    const onAbort = () => reject(signal.reason);
    signal.addEventListener("abort", onAbort, { once: true });
    p.then(resolve, reject).finally(() => signal.removeEventListener("abort", onAbort));
  });
}

export function dohResolver(fetchFn: FetchFn): DnsResolver {
  return async (name, type, signal) => {
    const sig = withTimeout(signal);
    const res = await fetchFn(`${DOH_URL}?name=${encodeURIComponent(name)}&type=${type}`, {
      method: "GET",
      headers: { accept: "application/dns-json" },
      redirect: "error",
      signal: sig,
    });
    if (!res.ok) {
      await discard(res);
      throw new CheckError("dns_failed", 502);
    }
    const raw = await readLimited(res.body, LIMITS.maxDohBytes, sig);
    let j: unknown;
    try {
      j = JSON.parse(new TextDecoder().decode(raw));
    } catch {
      throw new CheckError("dns_failed", 502);
    }
    const obj = j as { Status?: unknown; Answer?: unknown };
    if (typeof obj.Status !== "number") throw new CheckError("dns_failed", 502);
    const answers = Array.isArray(obj.Answer)
      ? obj.Answer.filter((a) => a && typeof a.type === "number" && typeof a.data === "string")
        .map((a) => ({ type: a.type as number, data: a.data as string }))
      : [];
    return { status: obj.Status, answers };
  };
}

/**
 * Resolve A and AAAA and refuse if ANY address is not public, or any CNAME target is a
 * blocked name. Follows CNAMEs as returned, and re-queries a CNAME target when the
 * resolver returned the alias without addresses.
 */
export async function assertPublicDns(host: string, resolve: DnsResolver, signal: AbortSignal): Promise<void> {
  let name = host;
  const seen = new Set<string>();
  let addresses = 0;
  for (let depth = 0; depth < LIMITS.maxCnameDepth; depth++) {
    seen.add(name);
    const results = await Promise.all([resolve(name, "A", signal), resolve(name, "AAAA", signal)]);
    let cname: string | null = null;
    for (const r of results) {
      if (r.status !== 0 && r.status !== 3) throw new CheckError("dns_failed", 502); // only NOERROR or NXDOMAIN
      for (const a of r.answers) {
        if (a.type === 1) {
          const v4 = parseIPv4(a.data.trim());
          if (!v4 || !isPublicIPv4(v4)) throw blocked();
          addresses++;
        } else if (a.type === 28) {
          const v6 = parseIPv6(a.data.trim());
          if (!v6 || !isPublicIPv6(v6)) throw blocked();
          addresses++;
        } else if (a.type === 5) {
          const target = a.data.trim().toLowerCase().replace(/\.$/, "");
          if (!isAllowedHostname(target)) throw blocked();
          cname = target;
        }
      }
    }
    if (addresses > 0 || !cname || seen.has(cname)) break;
    name = cname;
  }
  if (addresses === 0) throw new CheckError("dns_failed", 502);
}

// ---------------------------------------------------------------- guarded fetch

export interface Ctx {
  fetch: FetchFn;
  resolve: DnsResolver;
  signal: AbortSignal; // overall budget
  dnsCache: Map<string, Promise<void>>;
}

export async function assertSafeTarget(raw: string, ctx: Ctx): Promise<URL> {
  const t = validateTargetUrl(raw);
  if (t.kind === "name") {
    let p = ctx.dnsCache.get(t.host);
    if (!p) {
      p = assertPublicDns(t.host, ctx.resolve, ctx.signal);
      ctx.dnsCache.set(t.host, p);
    }
    await p;
  }
  return t.url;
}

export interface Fetched {
  status: number;
  url: string;
  headers: Headers;
  contentType: string;
  body: Uint8Array;
}

async function discard(res: Response): Promise<void> {
  try {
    await res.body?.cancel();
  } catch { /* ignore */ }
}

/**
 * Read at most max bytes from a stream, then cancel it. When `signal` aborts, the read stops
 * and the signal's reason is thrown, even if the stream itself never ends or never errors.
 */
export async function readLimited(
  body: ReadableStream<Uint8Array> | null,
  max: number,
  signal?: AbortSignal,
): Promise<Uint8Array> {
  if (!body || max <= 0) {
    try {
      await body?.cancel();
    } catch { /* ignore */ }
    return new Uint8Array(0);
  }
  if (signal?.aborted) {
    body.cancel().catch(() => {});
    throw signal.reason;
  }
  const reader = body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  const onAbort = () => reader.cancel().catch(() => {}); // resolves a pending read with done
  signal?.addEventListener("abort", onAbort, { once: true });
  try {
    while (total < max) {
      const { done, value } = await reader.read();
      if (signal?.aborted) throw signal.reason;
      if (done) break;
      if (!value) continue;
      const take = Math.min(value.byteLength, max - total);
      chunks.push(take < value.byteLength ? value.subarray(0, take) : value);
      total += take;
    }
  } finally {
    signal?.removeEventListener("abort", onAbort);
    reader.cancel().catch(() => {});
  }
  const out = new Uint8Array(total);
  let off = 0;
  for (const c of chunks) {
    out.set(c, off);
    off += c.byteLength;
  }
  return out;
}

/**
 * GET with SSRF guards on every hop. redirect is always manual. `bodyLimit` decides how many
 * bytes to read for a given final response (0 means do not read).
 */
export async function guardedFetch(
  raw: string,
  ctx: Ctx,
  opts: { follow: boolean; bodyLimit: (contentType: string, status: number) => number },
): Promise<Fetched> {
  let current = raw;
  for (let hop = 0;; hop++) {
    const target = await assertSafeTarget(current, ctx);
    const sig = withTimeout(ctx.signal); // one budget per hop, covering headers and body
    const res = await ctx.fetch(target.href, {
      method: "GET",
      redirect: "manual",
      headers: { "user-agent": UA, accept: "text/html,*/*" },
      signal: sig,
    });
    if (opts.follow && REDIRECT_STATUSES.has(res.status)) {
      const loc = res.headers.get("location");
      if (loc) {
        await discard(res);
        if (hop >= LIMITS.maxRedirects) throw new CheckError("too_many_redirects", 502);
        try {
          current = new URL(loc, target).href;
        } catch {
          throw blocked();
        }
        continue;
      }
    }
    const contentType = (res.headers.get("content-type") || "").toLowerCase();
    const body = await readLimited(res.body, opts.bodyLimit(contentType, res.status), sig);
    return { status: res.status, url: target.href, headers: res.headers, contentType, body };
  }
}

const isHtml = (ct: string) => ct.split(";")[0]!.trim() === "text/html";

// ---------------------------------------------------------------- report URL sanitising

const REDACT: Array<[RegExp, string]> = [
  [/([A-Za-z0-9._%+-]{1,2})[A-Za-z0-9._%+-]*(@|%40)/gi, "$1***$2"],
  [/\b\d{6}\d{4}\d{3}\b/g, "*************"],
  [/\b\d{9,19}\b/g, "*********"],
  [/(eyJ[A-Za-z0-9_-]{4})[A-Za-z0-9_.\-]{12,}/g, "$1…REDACTED"],
  [/[A-Za-z0-9_\-]{32,}/g, "…REDACTED"],
];

/** URL for reports: no credentials, query or fragment, and redacted path segments. */
export function safeUrl(u: string, keepPath = true): string {
  let scheme = "";
  let host = "";
  let path = "";
  let hasQuery = false;
  let abs: URL | null = null;
  try {
    abs = new URL(u);
  } catch { /* relative */ }
  if (abs) {
    scheme = abs.protocol.replace(/:$/, "");
    host = abs.hostname + (abs.port ? `:${abs.port}` : "");
    path = abs.pathname;
    hasQuery = abs.search.length > 1;
  } else {
    const noFrag = u.split("#")[0]!;
    const qi = noFrag.indexOf("?");
    hasQuery = qi >= 0 && qi < noFrag.length - 1;
    path = qi >= 0 ? noFrag.slice(0, qi) : noFrag;
    if (path.startsWith("//")) {
      try {
        const p = new URL("https:" + path);
        host = p.hostname + (p.port ? `:${p.port}` : "");
        path = p.pathname;
        return redact(`//${host}`, keepPath ? path : "", hasQuery);
      } catch {
        return "[unparseable URL]";
      }
    }
  }
  return redact(scheme ? `${scheme}://${host}` : host, keepPath ? path : "", hasQuery);
}

// Characters that can be part of something REDACT masks (emails, digit runs, JWTs, long tokens).
const TOKEN_CHAR = /[A-Za-z0-9._%+@-]/;

function redact(prefix: string, path: string, hasQuery: boolean): string {
  let p = path;
  // The first REDACT pattern backtracks quadratically, and paths can come from a 1.5 MB page or a
  // long Location header. Bound the input first. Drop any token cut in half at the boundary, so a
  // partial secret too short to match a pattern can never slip through.
  if (p.length > LIMITS.maxReportPath) {
    let end = LIMITS.maxReportPath;
    while (end > 0 && TOKEN_CHAR.test(p[end - 1]!)) end--;
    p = p.slice(0, end) + "…";
  }
  for (const [rx, sub] of REDACT) p = p.replace(rx, sub);
  return `${prefix}${p}${hasQuery ? " [query removed]" : ""}`;
}

// ---------------------------------------------------------------- HTML parsing (no dependencies)

export interface Page {
  scripts: Array<Record<string, string>>;
  links: Array<{ href: string; text: string }>;
  inputs: Array<Record<string, string>>;
  forms: number;
  text: string[];
  iframes: string[];
  inlineJs: string[];
}

const ENTITIES: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };

export function decodeEntities(s: string): string {
  if (!s.includes("&")) return s;
  return s.replace(/&(#[xX][0-9a-fA-F]{1,6}|#\d{1,7}|[a-zA-Z]{2,8});?/g, (m, e: string) => {
    if (e[0] === "#") {
      const n = e[1] === "x" || e[1] === "X" ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10);
      return n > 0 && n <= 0x10ffff ? String.fromCodePoint(n) : m;
    }
    return ENTITIES[e.toLowerCase()] ?? m;
  });
}

function parseAttrs(src: string): Record<string, string> {
  const out: Record<string, string> = Object.create(null); // no prototype: "__proto__" is just a name
  let i = 0;
  const n = src.length;
  while (i < n) {
    while (i < n && /[\s\/]/.test(src[i]!)) i++;
    if (i >= n) break;
    const start = i;
    while (i < n && !/[\s\/=>]/.test(src[i]!)) i++;
    const name = src.slice(start, i).toLowerCase();
    if (!name) {
      i++;
      continue;
    }
    while (i < n && /\s/.test(src[i]!)) i++;
    let value = "";
    if (src[i] === "=") {
      i++;
      while (i < n && /\s/.test(src[i]!)) i++;
      const q = src[i];
      if (q === '"' || q === "'") {
        const end = src.indexOf(q, i + 1);
        value = src.slice(i + 1, end < 0 ? n : end);
        i = end < 0 ? n : end + 1;
      } else {
        const vs = i;
        while (i < n && !/[\s>]/.test(src[i]!)) i++;
        value = src.slice(vs, i);
      }
    }
    out[name] = decodeEntities(value);
  }
  return out;
}

/** Find the end of a start tag, respecting quoted attribute values. Returns index of '>' or -1. */
function tagEnd(html: string, from: number): number {
  let q: string | null = null;
  for (let i = from; i < html.length; i++) {
    const c = html[i];
    if (q) {
      if (c === q) q = null;
    } else if (c === '"' || c === "'") {
      // quotes only open after '=' (attribute value); a stray quote elsewhere is literal
      let j = i - 1;
      while (j >= from && /\s/.test(html[j]!)) j--;
      if (html[j] === "=") q = c;
    } else if (c === ">") return i;
  }
  return -1;
}

/** Linear-time tolerant tokenizer that mirrors the parts of Python's HTMLParser the checks use. */
export function parseHtml(html: string): Page {
  const page: Page = { scripts: [], links: [], inputs: [], forms: 0, text: [], iframes: [], inlineJs: [] };
  let inA: { href: string; text: string } | null = null;
  const data = (s: string) => {
    if (!s) return;
    const d = decodeEntities(s);
    page.text.push(d);
    if (inA) inA.text += d;
  };
  const lower = html.toLowerCase();
  let i = 0;
  const n = html.length;
  while (i < n) {
    const lt = html.indexOf("<", i);
    if (lt < 0) {
      data(html.slice(i));
      break;
    }
    if (lt > i) data(html.slice(i, lt));
    if (html.startsWith("<!--", lt)) {
      const e = html.indexOf("-->", lt + 4);
      i = e < 0 ? n : e + 3;
      continue;
    }
    const next = html[lt + 1] ?? "";
    if (next === "!" || next === "?") {
      const e = html.indexOf(">", lt);
      i = e < 0 ? n : e + 1;
      continue;
    }
    if (next === "/") {
      const m = /^<\/([a-zA-Z][a-zA-Z0-9:-]*)[^>]*>/.exec(html.slice(lt, lt + 256));
      if (!m) {
        data("<");
        i = lt + 1;
        continue;
      }
      if (m[1]!.toLowerCase() === "a" && inA) {
        page.links.push(inA);
        inA = null;
      }
      i = lt + m[0].length;
      continue;
    }
    if (!/[a-zA-Z]/.test(next)) {
      data("<");
      i = lt + 1;
      continue;
    }
    let j = lt + 1;
    while (j < n && !/[\s\/>]/.test(html[j]!)) j++;
    const tag = html.slice(lt + 1, j).toLowerCase();
    const end = tagEnd(html, j);
    if (end < 0) break; // incomplete tag at EOF: stop, like HTMLParser
    const attrs = parseAttrs(html.slice(j, end));
    i = end + 1;
    if (tag === "script" || tag === "style") {
      const close = lower.indexOf("</" + tag, i);
      const content = html.slice(i, close < 0 ? n : close);
      if (tag === "script") {
        page.scripts.push(attrs);
        if (!attrs["src"]) {
          if (content) page.inlineJs.push(content);
        } else if (content) page.text.push(content);
      } else if (content) page.text.push(content);
      if (close < 0) break;
      const ce = html.indexOf(">", close);
      i = ce < 0 ? n : ce + 1;
      continue;
    }
    if (tag === "a") inA = { href: attrs["href"] ?? "", text: "" };
    else if (tag === "input") page.inputs.push(attrs);
    else if (tag === "form") page.forms++;
    else if (tag === "iframe") page.iframes.push(attrs["src"] ?? "");
  }
  return page;
}

// ---------------------------------------------------------------- cookies

export interface CookieInfo {
  name: string;
  secure: boolean;
  httponly: boolean;
  samesite: string | null;
  tracking: boolean;
}

/**
 * Parse one Set-Cookie header the way a browser does (RFC 6265 section 5.2). Flags come from
 * attribute names only, never from the value or other attribute values, so
 * "session_id=secure-httponly; Path=/" is neither Secure nor HttpOnly.
 */
export function parseSetCookie(raw: string): CookieInfo | null {
  const parts = raw.split(";");
  const nv = parts.shift() ?? "";
  const eq = nv.indexOf("=");
  if (eq < 0) return null;
  const name = nv.slice(0, eq).trim();
  // deno-lint-ignore no-control-regex -- control characters in a cookie name are deliberately rejected
  if (!name || name.length > 256 || /[\s\x00-\x1f\x7f]/.test(name)) return null;
  let secure = false;
  let httponly = false;
  let samesite: string | null = null;
  for (const p of parts) {
    const e = p.indexOf("=");
    const an = (e < 0 ? p : p.slice(0, e)).trim().toLowerCase();
    const av = e < 0 ? "" : p.slice(e + 1).trim();
    if (an === "secure") secure = true;
    else if (an === "httponly") httponly = true;
    else if (an === "samesite") samesite = av ? av.toLowerCase() : null;
  }
  return { name, secure, httponly, samesite, tracking: TRACKING_COOKIES.test(name) };
}

export function getSetCookies(h: Headers): string[] {
  const anyH = h as Headers & { getSetCookie?: () => string[] };
  if (typeof anyH.getSetCookie === "function") return anyH.getSetCookie();
  const v = h.get("set-cookie");
  return v ? [v] : [];
}

// ---------------------------------------------------------------- findings

export interface Finding {
  rule_id: string;
  title: string;
  severity: Severity;
  popia: string;
  evidence: string;
  fix: string;
}

const cap = (s: string, n = LIMITS.maxEvidence) => (s.length > n ? s.slice(0, n) : s);

function f(rule_id: string, title: string, severity: Severity, popia: string, evidence: string, fix: string): Finding {
  return { rule_id, title: cap(title, 200), severity, popia, evidence: cap(evidence), fix };
}

export interface HeaderInput {
  finalUrl: string;
  headers: Headers;
}

/** Transport (except the HTTP probe) and security header checks: WEB-001, WEB-003 to WEB-009. */
export function checkHeaders({ finalUrl, headers: h }: HeaderInput): Finding[] {
  const out: Finding[] = [];
  const https = new URL(finalUrl).protocol === "https:";
  const get = (k: string) => h.get(k) ?? "";
  if (!https) {
    out.push(
      f(
        "WEB-001",
        "Site not served over HTTPS",
        "critical",
        "s19",
        `Final URL ${safeUrl(finalUrl)}`,
        "Serve every page over HTTPS and redirect HTTP to HTTPS.",
      ),
    );
  } else {
    const hsts = get("strict-transport-security");
    const m = /max-age=(\d+)/i.exec(hsts);
    if (!hsts) {
      out.push(
        f(
          "WEB-003",
          "Missing HSTS header",
          "medium",
          "s19",
          "Strict-Transport-Security absent",
          "Add Strict-Transport-Security: max-age=63072000; includeSubDomains",
        ),
      );
    } else if (m && Number(m[1]) < 15552000) {
      out.push(f("WEB-003", "HSTS max-age is short", "low", "s19", hsts, "Use max-age of at least 6 months."));
    }
  }
  const csp = get("content-security-policy");
  if (!csp) {
    out.push(
      f(
        "WEB-004",
        "Missing Content-Security-Policy",
        "medium",
        "s19",
        "No CSP header",
        "Add a CSP restricting script sources to your domain and approved vendors.",
      ),
    );
  } else if (csp.includes("unsafe-inline") && csp.includes("script-src") && !csp.includes("nonce-")) {
    out.push(
      f(
        "WEB-004",
        "CSP allows unsafe-inline scripts",
        "low",
        "s19",
        csp.slice(0, 160),
        "Use nonces or hashes instead of unsafe-inline.",
      ),
    );
  }
  if (get("x-content-type-options").toLowerCase() !== "nosniff") {
    out.push(f("WEB-005", "Missing X-Content-Type-Options: nosniff", "low", "s19", "", "Add the header."));
  }
  if (!csp.includes("frame-ancestors") && !get("x-frame-options")) {
    out.push(
      f(
        "WEB-006",
        "No clickjacking protection",
        "low",
        "s19",
        "No frame-ancestors or X-Frame-Options",
        "Add CSP frame-ancestors 'none' (or 'self').",
      ),
    );
  }
  if (!get("referrer-policy")) {
    out.push(
      f(
        "WEB-007",
        "Missing Referrer-Policy",
        "low",
        "s19",
        "Full URLs (with any PI in query strings) can leak to third parties",
        "Add Referrer-Policy: strict-origin-when-cross-origin",
      ),
    );
  }
  if (!get("permissions-policy")) {
    out.push(
      f(
        "WEB-008",
        "Missing Permissions-Policy",
        "info",
        "s19",
        "",
        "Add Permissions-Policy to disable camera, microphone and geolocation unless needed.",
      ),
    );
  }
  for (const hdr of ["server", "x-powered-by"]) {
    const v = get(hdr).slice(0, LIMITS.maxHeaderScan); // /\d+\.\d+/ is quadratic on a long run of digits
    if (/\d+\.\d+/.test(v)) {
      out.push(
        f("WEB-009", `Version disclosed in ${hdr} header`, "low", "s19", v, "Remove version numbers from server headers."),
      );
    }
  }
  return out;
}

/** Cookies set on first load: WEB-010, WEB-011. */
export function checkCookies(h: Headers): { cookies: CookieInfo[]; findings: Finding[] } {
  const cookies: CookieInfo[] = [];
  const findings: Finding[] = [];
  for (const raw of getSetCookies(h).slice(0, LIMITS.maxCookies)) {
    const c = parseSetCookie(raw);
    if (!c) continue;
    cookies.push(c);
    if (c.tracking) {
      findings.push(
        f(
          "WEB-010",
          "Tracking cookie set before consent",
          "high",
          "s11; s18; s69 (Reg guidance)",
          `Set-Cookie: ${c.name}`,
          "Set analytics and marketing cookies only after opt-in.",
        ),
      );
    }
    if (SESSION_COOKIES.test(c.name) && !(c.secure && c.httponly)) {
      findings.push(
        f(
          "WEB-011",
          "Session cookie missing Secure or HttpOnly",
          "medium",
          "s19",
          `${c.name}: secure=${c.secure ? "True" : "False"} httponly=${c.httponly ? "True" : "False"}`,
          "Set Secure, HttpOnly and SameSite on session cookies.",
        ),
      );
    }
  }
  return { cookies, findings };
}

export interface Notices {
  privacy: boolean;
  paia: boolean;
  cookie: boolean;
  information_officer: boolean;
}

export interface HtmlResult {
  findings: Finding[];
  trackers: string[];
  notices: Notices;
  spa: boolean;
  consentTool: string | null;
  consentMode: boolean;
}

/**
 * HTML checks on the initial document: WEB-012 to WEB-017, WEB-019 to WEB-021.
 * `probed` lets the caller mark notices found via common paths. WEB-018 is added by the caller.
 */
export function checkHtml(html: string, finalUrl: string, probed: Partial<Notices> = {}): HtmlResult {
  const findings: Finding[] = [];
  const page = parseHtml(html);
  const base = new URL(finalUrl);
  const trackers: string[] = [];
  let mixed = 0;
  for (const s of page.scripts) {
    const src = s["src"] ?? "";
    if (!src) continue;
    let host = "";
    try {
      host = new URL(src, base).hostname.toLowerCase();
    } catch { /* ignore */ }
    // As in site_check.py, match tracker domains on every script host (a substring match).
    for (const [dom, name] of Object.entries(TRACKER_DOMAINS)) {
      if (host && host.includes(dom) && !trackers.includes(name)) trackers.push(name);
    }
    // Stop building WEB-012 evidence once the per-rule cap is reached: a page can hold tens of
    // thousands of script tags, and each one costs a safeUrl call.
    if (/^http:\/\//i.test(src) && mixed++ < LIMITS.maxFindingsPerRule) {
      findings.push(
        f("WEB-012", "Script loaded over HTTP (mixed content)", "high", "s19", safeUrl(src), "Load all scripts over HTTPS."),
      );
    }
  }
  const inline = page.inlineJs.join("\n");
  for (const [rx, name] of INLINE_TRACKERS) {
    if (rx.test(inline) && !trackers.includes(name)) trackers.push(name);
  }
  const lowerHtml = html.toLowerCase();
  const consentTool = Object.entries(CONSENT_TOOLS).find(([k]) => lowerHtml.includes(k))?.[1] ?? null;
  const consentMode = /gtag\(\s*['"]consent['"]\s*,\s*['"]default['"]/.test(inline);
  if (trackers.length && !consentTool && !consentMode) {
    findings.push(
      f(
        "WEB-013",
        "Trackers in page with no consent tool detected",
        "high",
        "s11; s18; s69 (Reg guidance); s72",
        trackers.join(", "),
        "Add a consent banner that blocks these tags until opt-in, or set Consent Mode defaults to denied. " +
          "SPAs: confirm in a browser, the banner may render later.",
      ),
    );
  }
  for (const t of trackers) {
    findings.push(
      f(
        "WEB-014",
        `Third-party tracker: ${t}`,
        "info",
        "s20; s21; s72; s18(1)(g)",
        t,
        "Record as operator with country and s72 basis. Disclose in the cookie notice.",
      ),
    );
  }

  const textAll = page.text.join(" ").toLowerCase();
  const hrefs = page.links.map((l) => [l.href.toLowerCase(), l.text.trim().toLowerCase()] as const);
  const notices: Notices = {
    privacy: hrefs.some(([hr, tx]) => hr.includes("privacy") || tx.includes("privacy")) || !!probed.privacy,
    paia: hrefs.some(([hr, tx]) => hr.includes("paia") || tx.includes("paia") || tx.includes("access to information")) ||
      !!probed.paia,
    cookie: hrefs.some(([hr, tx]) => hr.includes("cookie") || tx.includes("cookie")) || !!probed.cookie,
    information_officer: textAll.includes("information officer"),
  };
  const spa = page.text.length < 40 && page.scripts.some((s) => s["type"] === "module");
  if (!notices.privacy) {
    findings.push(
      f(
        "WEB-015",
        "No privacy notice link found",
        "high",
        "s18",
        "No link or common path" + (spa ? " (SPA: links may render client-side)" : ""),
        "Publish a privacy notice and link it in the footer and next to every form.",
      ),
    );
  }
  if (!notices.paia) {
    findings.push(
      f(
        "WEB-016",
        "No PAIA manual link found",
        "medium",
        "PAIA s51",
        "No PAIA link or common path" + (spa ? " (SPA: may render client-side)" : ""),
        "Publish the PAIA manual and link it in the footer.",
      ),
    );
  }
  if (trackers.length && !notices.cookie) {
    findings.push(
      f(
        "WEB-017",
        "Trackers present but no cookie notice link",
        "medium",
        "s18",
        "",
        "Publish a cookie notice listing each tool, purpose and provider.",
      ),
    );
  }

  const https = base.protocol === "https:";
  for (const inp of page.inputs) {
    const type = (inp["type"] ?? "").toLowerCase();
    if (type === "checkbox" && Object.hasOwn(inp, "checked")) {
      const nm = ((inp["name"] ?? "") + (inp["id"] ?? "")).toLowerCase();
      if (/market|news|promo|consent|subscribe|offer|partner/.test(nm)) {
        findings.push(
          f(
            "WEB-019",
            "Pre-ticked marketing or consent checkbox",
            "high",
            "s1; s11; s69",
            `input name=${inp["name"] ?? "None"}`,
            "Default to unchecked.",
          ),
        );
      }
    }
    if (type === "password" && !https) {
      findings.push(f("WEB-020", "Password field on non-HTTPS page", "critical", "s19", "", "Serve over HTTPS."));
    }
  }
  for (const href of [...page.links.map((l) => l.href), ...page.scripts.map((s) => s["src"] ?? "")]) {
    if (/[?&](email|phone|id_?number|mobile)=/i.test(href)) {
      findings.push(
        f(
          "WEB-021",
          "Personal information in a URL",
          "medium",
          "s19",
          safeUrl(href).slice(0, 120),
          "Never put PI in query strings.",
        ),
      );
      break;
    }
  }
  return { findings, trackers, notices, spa, consentTool, consentMode };
}

function capPerRule(findings: Finding[]): Finding[] {
  const counts = new Map<string, number>();
  return findings.filter((x) => {
    const c = (counts.get(x.rule_id) ?? 0) + 1;
    counts.set(x.rule_id, c);
    return c <= LIMITS.maxFindingsPerRule;
  });
}

// ---------------------------------------------------------------- full check

export interface CheckResult {
  url: string;
  final_url: string;
  checked_at: string;
  summary: Record<Severity, number>;
  findings: Finding[];
  cookies: CookieInfo[];
  notices: Notices;
  disclaimer: string;
}

export interface CheckOptions {
  probeNoticePaths?: boolean;
  now?: (() => Date) | undefined;
}

export async function runSiteCheck(input: string, ctx: Ctx, opts: CheckOptions = {}): Promise<CheckResult> {
  if (input.length > LIMITS.maxUrlLength) throw new CheckError("invalid_url", 400);
  const requested = validateTargetUrl(normaliseInputUrl(input)).url.href; // strips credentials and fragment
  const main = await guardedFetch(requested, ctx, {
    follow: true,
    bodyLimit: (ct, st) => (st >= 200 && st < 300 && isHtml(ct) ? LIMITS.maxBodyBytes : 0),
  });
  const finalUrl = main.url;
  const final = new URL(finalUrl);
  const html = new TextDecoder("utf-8", { fatal: false }).decode(main.body);
  const base = `${final.protocol}//${final.host}`;

  // Extra probes, all through the guarded fetch, run in parallel. A failed probe never fails the check.
  const httpProbe = final.protocol === "https:"
    // Deliberate: checks that plain HTTP redirects to HTTPS.
    ? guardedFetch(`http://${final.hostname}/`, ctx, { follow: false, bodyLimit: () => 0 }) // popia-ignore: SEC-009
    : null;
  const secTxt = guardedFetch(`${base}/.well-known/security.txt`, ctx, {
    follow: true,
    bodyLimit: (ct, st) => (st === 200 && ct.split(";")[0]!.trim() === "text/plain" ? LIMITS.maxSecurityTxtBytes : 0),
  });
  const mainPrefix = main.body.subarray(0, LIMITS.maxProbeBytes);
  const noticeProbes = opts.probeNoticePaths
    ? NOTICE_PATHS.map((p) =>
      guardedFetch(base + p, ctx, {
        follow: true,
        bodyLimit: (ct, st) => (st === 200 && isHtml(ct) ? LIMITS.maxProbeBytes : 0),
      })
    )
    : [];
  const [httpR, secR, ...noticeR] = await Promise.allSettled([httpProbe ?? Promise.resolve(null), secTxt, ...noticeProbes]);

  const findings: Finding[] = [];
  if (httpR.status === "fulfilled" && httpR.value) {
    const s2 = httpR.value.status;
    const loc = httpR.value.headers.get("location") ?? "";
    if (!(s2 >= 300 && s2 < 400 && loc.startsWith("https://"))) {
      findings.push(
        f(
          "WEB-002",
          "HTTP does not redirect to HTTPS",
          "medium",
          "s19",
          `http:// returned ${s2}`,
          "Add a permanent redirect from HTTP to HTTPS.",
        ),
      );
    }
  }
  findings.push(...checkHeaders({ finalUrl, headers: main.headers })); // same order as site_check.py
  const ck = checkCookies(main.headers);
  findings.push(...ck.findings);

  const probed: Partial<Notices> = {};
  if (noticeR.length) {
    const found = (i: number) => {
      const r = noticeR[i]!;
      if (r.status !== "fulfilled" || !r.value || r.value.status !== 200) return false;
      if (!isHtml(r.value.contentType)) return true; // e.g. a PDF PAIA manual
      const b = r.value.body;
      return b.length !== mainPrefix.length || b.some((x, k) => x !== mainPrefix[k]); // SPA fallback returns the same page
    };
    probed.privacy = [0, 1, 2, 3].some(found);
    probed.paia = [4, 5].some(found);
    probed.cookie = [6, 7].some(found);
  }
  const hr = checkHtml(html, finalUrl, probed);
  findings.push(...hr.findings);

  const hasSecTxt = secR.status === "fulfilled" && secR.value.status === 200 &&
    /contact:/i.test(new TextDecoder().decode(secR.value.body));
  if (!hasSecTxt) {
    findings.push(
      f("WEB-018", "No /.well-known/security.txt", "low", "s19(2)", "", "Publish security.txt with a security contact."),
    );
  }

  const sorted = capPerRule(findings).sort((a, b) => SEV_ORDER.indexOf(a.severity) - SEV_ORDER.indexOf(b.severity));
  const summary = Object.fromEntries(SEV_ORDER.map((s) => [s, sorted.filter((x) => x.severity === s).length])) as Record<
    Severity,
    number
  >;
  const now = (opts.now ?? (() => new Date()))();
  return {
    url: safeUrl(requested),
    final_url: safeUrl(finalUrl),
    checked_at: now.toISOString().replace(/\.\d{3}Z$/, "+00:00"),
    summary,
    findings: sorted,
    cookies: ck.cookies,
    notices: hr.notices,
    disclaimer: DISCLAIMER,
  };
}

// ---------------------------------------------------------------- rate limiting

export type EnvFn = (key: string) => string | undefined;
/** Count one hit against `key` (a 64 char hex hash) and return true while within `limit` per hour. */
export type RateLimitFn = (ipHash: string, limit: number, signal: AbortSignal, env: EnvFn) => Promise<boolean>;

/** Bucket key for an IP. IPv6 is bucketed per /64 because a single client usually controls a whole /64. */
export function ipBucket(ip: string | null): string {
  const s = (ip ?? "").trim();
  const v4 = parseIPv4(s);
  if (v4) return "v4:" + v4.join(".");
  const v6 = parseIPv6(s);
  if (v6) {
    if (v6.slice(0, 5).every((x) => x === 0) && v6[5] === 0xffff) return "v4:" + v4FromGroups(v6[6]!, v6[7]!).join(".");
    return "v6:" + v6.slice(0, 4).map((x) => x.toString(16)).join(":") + "::/64";
  }
  return "unknown";
}

/** Bucket for the global cap. Cannot collide with an IP bucket, which always starts with v4:, v6: or unknown. */
export const GLOBAL_BUCKET = "global";

/**
 * Default client IP headers, in order. The first one present wins.
 * cf-connecting-ip and x-real-ip are single values set by the edge in front of the function.
 * x-forwarded-for is a list the client can start, so only its LAST entry (added by the nearest
 * proxy) is used, never the first.
 */
export const CLIENT_IP_HEADERS = ["cf-connecting-ip", "x-real-ip", "x-forwarded-for"] as const;

/** "1.2.3.4:5678" and "[2001:db8::1]:443" to the bare address. Anything else is returned unchanged. */
function stripPort(s: string): string {
  const b = /^\[([0-9A-Fa-f:.]+)\](?::\d{1,5})?$/.exec(s);
  if (b) return b[1]!;
  const p = /^(\d{1,3}(?:\.\d{1,3}){3}):\d{1,5}$/.exec(s);
  return p ? p[1]! : s;
}

/**
 * Client IP for rate limiting. CLIENT_IP_HEADER, when set, replaces the default list with that
 * one header. For any comma separated value the last entry is used.
 */
export function clientIp(req: Request, env: EnvFn): string | null {
  const override = (env("CLIENT_IP_HEADER") ?? "").trim().toLowerCase();
  const names: readonly string[] = override ? [override] : CLIENT_IP_HEADERS;
  for (const name of names) {
    const v = req.headers.get(name);
    if (!v) continue;
    const parts = v.split(",").map((s) => s.trim()).filter(Boolean);
    if (parts.length) return stripPort(parts[parts.length - 1]!);
  }
  return null;
}

export async function hashIp(bucket: string, salt: string): Promise<string> {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(`${salt}:${bucket}`));
  return Array.from(new Uint8Array(d), (b) => b.toString(16).padStart(2, "0")).join("");
}

/** Positive integer from env, clamped to max, or the default. */
function intEnv(raw: string | undefined, def: number, max: number): number {
  const n = parseInt(raw ?? "", 10);
  return Number.isFinite(n) && n > 0 ? Math.min(n, max) : def;
}

/** Minimal shape of supabase-js used here, so core needs no import. */
interface RpcClient {
  rpc(
    fn: string,
    args: Record<string, unknown>,
  ): { abortSignal(s: AbortSignal): PromiseLike<{ data: unknown; error: unknown }> };
}
type CreateClientFn = (url: string, key: string, options: Record<string, unknown>) => unknown;

/**
 * Rate limit backed by the site_check_hit SQL function. Pass supabase-js's createClient; the
 * runtime entry decides how it is imported (an npm specifier on Deno, a bare import on Node).
 * Every failure throws, and the handler turns any throw into a 429.
 */
export function supabaseRpcRateLimit(createClient: CreateClientFn): RateLimitFn {
  let client: RpcClient | null = null;
  let clientKey = "";
  return async (ipHash, limit, signal, env) => {
    const url = env("SUPABASE_URL");
    const key = env("SUPABASE_SERVICE_ROLE_KEY");
    if (!url || !key) throw new Error("rate limit backend not configured");
    if (!client || clientKey !== url + "\n" + key) {
      client = createClient(url, key, {
        auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
      }) as RpcClient;
      clientKey = url + "\n" + key;
    }
    const { data, error } = await client.rpc("site_check_hit", { p_ip_hash: ipHash, p_limit: limit }).abortSignal(signal);
    if (error || typeof data !== "boolean") throw new Error("rate limit backend error");
    return data;
  };
}

// ---------------------------------------------------------------- HTTP handler

export interface Deps {
  fetch: FetchFn;
  env: EnvFn;
  rateLimit: RateLimitFn;
  resolve?: DnsResolver;
  now?: () => Date;
}

function allowedOrigins(env: EnvFn): string[] {
  return (env("ALLOWED_ORIGINS") ?? "").split(",").map((s) => s.trim().replace(/\/$/, "")).filter(Boolean);
}

function baseHeaders(origin: string | null): Headers {
  const h = new Headers({
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    vary: "Origin",
  });
  if (origin) h.set("access-control-allow-origin", origin);
  return h;
}

function json(body: unknown, status: number, origin: string | null): Response {
  return new Response(JSON.stringify(body), { status, headers: baseHeaders(origin) });
}

/** Generic error body: a fixed message and a type. Never echoes input or upstream messages. */
export function errorResponse(type: string, status: number, origin: string | null): Response {
  return json({ error: ERROR_MESSAGES[type] ?? ERROR_MESSAGES["internal_error"], type }, status, origin);
}

async function verifyTurnstile(token: string, secret: string, fetchFn: FetchFn, signal: AbortSignal): Promise<boolean> {
  try {
    const body = new URLSearchParams({ secret, response: token });
    const sig = withTimeout(signal);
    const res = await fetchFn(TURNSTILE_URL, {
      method: "POST",
      body,
      headers: { "content-type": "application/x-www-form-urlencoded" },
      redirect: "error",
      signal: sig,
    });
    if (!res.ok) {
      await discard(res);
      return false;
    }
    const j = JSON.parse(new TextDecoder().decode(await readLimited(res.body, 16_384, sig)));
    return j?.success === true;
  } catch {
    return false;
  }
}

function classify(e: unknown): CheckError {
  if (e instanceof CheckError) return e;
  const name = (e as { name?: string })?.name;
  if (name === "TimeoutError" || name === "AbortError") return new CheckError("timeout", 504);
  if (e instanceof TypeError) return new CheckError("fetch_failed", 502); // network, TLS, DNS at fetch time
  return new CheckError("internal_error", 500);
}

/** Read the small JSON request body with a size cap and a time limit (a slow upload cannot hold the handler). */
async function readJsonBody(req: Request, overall: AbortSignal): Promise<{ url?: unknown; turnstileToken?: unknown }> {
  if (!(req.headers.get("content-type") ?? "").toLowerCase().startsWith("application/json")) {
    throw new CheckError("invalid_request", 400);
  }
  const declared = Number(req.headers.get("content-length") ?? "");
  if (Number.isFinite(declared) && declared > LIMITS.maxRequestBodyBytes) throw new CheckError("invalid_request", 400);
  const raw = await readLimited(req.body, LIMITS.maxRequestBodyBytes + 1, withTimeout(overall, LIMITS.requestBodyMs));
  if (raw.length > LIMITS.maxRequestBodyBytes) throw new CheckError("invalid_request", 400);
  let body: unknown;
  try {
    body = JSON.parse(new TextDecoder().decode(raw));
  } catch {
    throw new CheckError("invalid_request", 400);
  }
  if (!body || typeof body !== "object") throw new CheckError("invalid_request", 400);
  return body as { url?: unknown; turnstileToken?: unknown };
}

/** Per-IP limit first, then the global cap. Any backend problem, or a missing salt, fails closed. */
async function rateLimitAllows(req: Request, deps: Deps, overall: AbortSignal): Promise<boolean> {
  const env = deps.env;
  try {
    const salt = env("RATE_LIMIT_SALT");
    if (!salt) return false;
    const perIp = intEnv(env("RATE_LIMIT_PER_HOUR"), 10, 10_000);
    const ipHash = await hashIp(ipBucket(clientIp(req, env)), salt);
    if ((await deps.rateLimit(ipHash, perIp, withTimeout(overall, 5_000), env)) !== true) return false;
    const global = intEnv(env("GLOBAL_LIMIT_PER_HOUR"), 300, 1_000_000);
    const globalHash = await hashIp(GLOBAL_BUCKET, salt);
    return (await deps.rateLimit(globalHash, global, withTimeout(overall, 5_000), env)) === true;
  } catch {
    return false;
  }
}

/**
 * The HTTP handler: a plain (Request) => Promise<Response>, usable from Deno serve, a Node 20+
 * server route (TanStack Start, Hono, Next.js route handlers) or any Fetch API host.
 */
export function createHandler(deps: Deps): (req: Request) => Promise<Response> {
  return async (req: Request): Promise<Response> => {
    const env = deps.env;
    const origin = req.headers.get("origin");
    const okOrigin = origin && allowedOrigins(env).includes(origin) ? origin : null;
    if (!okOrigin) return errorResponse("origin_not_allowed", 403, null);

    if (req.method === "OPTIONS") {
      const h = baseHeaders(okOrigin);
      h.delete("content-type");
      h.set("access-control-allow-methods", "POST, OPTIONS");
      h.set("access-control-allow-headers", "authorization, apikey, content-type, x-client-info");
      h.set("access-control-max-age", "600");
      return new Response(null, { status: 204, headers: h });
    }
    if (req.method !== "POST") return errorResponse("method_not_allowed", 405, okOrigin);

    const overall = AbortSignal.timeout(LIMITS.overallMs);
    const work = async (): Promise<Response> => {
      const body = await readJsonBody(req, overall);

      // Turnstile first, before rate limiting or touching the URL.
      const secret = env("TURNSTILE_SECRET");
      if (secret) {
        const token = body.turnstileToken;
        if (typeof token !== "string" || !token || token.length > LIMITS.maxTokenLength) {
          throw new CheckError("turnstile_failed", 403);
        }
        if (!(await verifyTurnstile(token, secret, deps.fetch, overall))) throw new CheckError("turnstile_failed", 403);
      }

      if (!(await rateLimitAllows(req, deps, overall))) throw new CheckError("rate_limited", 429);

      if (typeof body.url !== "string" || !body.url.trim()) throw new CheckError("invalid_url", 400);
      const ctx: Ctx = {
        fetch: deps.fetch,
        resolve: deps.resolve ?? dohResolver(deps.fetch),
        signal: overall,
        dnsCache: new Map(),
      };
      const result = await runSiteCheck(body.url, ctx, {
        probeNoticePaths: (env("PROBE_NOTICE_PATHS") ?? "").toLowerCase() === "true",
        now: deps.now,
      });
      return json(result, 200, okOrigin);
    };
    try {
      // The race makes the overall budget hard, even if an injected dependency ignores its signal.
      return await raceSignal(work(), overall);
    } catch (e) {
      const ce = overall.aborted && !(e instanceof CheckError) ? new CheckError("timeout", 504) : classify(e);
      return errorResponse(ce.type, ce.status, okOrigin); // never log; never echo input or upstream messages
    }
  };
}
