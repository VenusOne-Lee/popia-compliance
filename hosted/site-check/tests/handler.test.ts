// HTTP handler: CORS, method and body rules, Turnstile, rate limiting, error hygiene and no logging.
import {
  createHandler,
  type Deps,
  DISCLAIMER,
  ERROR_MESSAGES,
  hashIp,
  ipBucket,
  type RateLimitFn,
} from "../supabase/functions/site-check/core.ts";
import { supabaseRateLimit } from "../supabase/functions/site-check/index.ts";
import { assert, assertEquals, countConsoleCalls, fakeDns, html, mockFetch, publicDns, type Route } from "./helpers.ts";

const ORIGIN = "https://check.venusone.co.za";
const SECRET = "SYNTHETICTOKEN" + "q".repeat(30);
const SITE: Record<string, Route> = {
  "https://example.co.za/": html(`<a href="/privacy">Privacy</a><a href="/paia">PAIA</a>`, {
    "strict-transport-security": "max-age=63072000",
  }),
  "http://example.co.za/": () => new Response(null, { status: 301, headers: { location: "https://example.co.za/" } }),
  "https://example.co.za/.well-known/security.txt": () =>
    new Response("Contact: mailto:security@example.co.za\n", { headers: { "content-type": "text/plain" } }),
};

interface Setup {
  env?: Record<string, string>;
  routes?: Record<string, Route>;
  rateLimit?: RateLimitFn;
}

function setup(o: Setup = {}) {
  const env: Record<string, string> = {
    ALLOWED_ORIGINS: `${ORIGIN}, https://www.venusone.co.za`,
    RATE_LIMIT_SALT: "test-salt",
    ...o.env,
  };
  const m = mockFetch({ ...SITE, ...o.routes });
  const log: string[] = [];
  const hits: Array<{ hash: string; limit: number }> = [];
  const rateLimit: RateLimitFn = o.rateLimit ?? ((hash, limit) => {
    log.push("ratelimit");
    hits.push({ hash, limit });
    return Promise.resolve(true);
  });
  const fetchFn: Deps["fetch"] = (u, init) => {
    log.push(u.startsWith("https://challenges.cloudflare.com/") ? "turnstile" : "fetch");
    return m.fn(u, init);
  };
  const handler = createHandler({
    fetch: fetchFn,
    env: (k) => env[k],
    rateLimit,
    resolve: fakeDns(publicDns("example.co.za")).resolve,
    now: () => new Date("2026-10-18T09:00:00.123Z"),
  });
  return { handler, calls: m.calls, log, hits };
}

function post(body: unknown, headers: Record<string, string> = {}) {
  return new Request("https://proj.supabase.co/functions/v1/site-check", {
    method: "POST",
    // The client wrote the first x-forwarded-for entry; the proxy appended the real address last.
    headers: { origin: ORIGIN, "content-type": "application/json", "x-forwarded-for": "198.51.100.77, 41.1.2.3", ...headers },
    body: typeof body === "string" ? body : JSON.stringify(body),
  });
}

async function call(s: ReturnType<typeof setup>, req: Request) {
  let res!: Response;
  let body: Record<string, unknown> | null = null;
  const n = await countConsoleCalls(async () => {
    res = await s.handler(req);
    const t = await res.text();
    body = t ? JSON.parse(t) : null;
  });
  assertEquals(n, 0, "no console output");
  return { res, body: body as unknown as Record<string, unknown> };
}

const isError = (b: Record<string, unknown>, type: string) => {
  assertEquals(Object.keys(b), ["error", "type"]);
  assertEquals(b["type"], type);
  assertEquals(b["error"], ERROR_MESSAGES[type]);
};

// ---------------------------------------------------------------- CORS and method

Deno.test("cors: missing, unknown and lookalike origins are refused with 403", async () => {
  for (const origin of [null, "https://evil.example", "https://check.venusone.co.za.evil.example", "null", ORIGIN + "/"]) {
    const s = setup();
    const headers: Record<string, string> = { "content-type": "application/json" };
    if (origin) headers["origin"] = origin;
    const { res, body } = await call(s, new Request("https://x.supabase.co/f", { method: "POST", headers, body: "{}" }));
    assertEquals(res.status, 403, String(origin));
    isError(body, "origin_not_allowed");
    assertEquals(res.headers.get("access-control-allow-origin"), null);
    assertEquals(s.calls.length + s.hits.length, 0, "nothing else happened");
  }
});
Deno.test("cors: empty ALLOWED_ORIGINS refuses everything", async () => {
  const s = setup({ env: { ALLOWED_ORIGINS: "" } });
  const { res } = await call(s, post({ url: "https://example.co.za/" }));
  assertEquals(res.status, 403);
});
Deno.test("cors: OPTIONS preflight", async () => {
  const s = setup();
  const ok = await s.handler(
    new Request("https://x/f", { method: "OPTIONS", headers: { origin: "https://www.venusone.co.za" } }),
  );
  assertEquals(ok.status, 204);
  assertEquals(ok.headers.get("access-control-allow-origin"), "https://www.venusone.co.za");
  assertEquals(ok.headers.get("access-control-allow-methods"), "POST, OPTIONS");
  assert(ok.headers.get("access-control-allow-headers")!.includes("content-type"));
  assertEquals(ok.headers.get("vary"), "Origin");
  const bad = await s.handler(new Request("https://x/f", { method: "OPTIONS", headers: { origin: "https://evil.example" } }));
  assertEquals(bad.status, 403);
  assertEquals(bad.headers.get("access-control-allow-origin"), null);
});
Deno.test("method: only POST", async () => {
  for (const method of ["GET", "PUT", "DELETE"]) {
    const s = setup();
    const { res, body } = await call(s, new Request("https://x/f", { method, headers: { origin: ORIGIN } }));
    assertEquals(res.status, 405);
    isError(body, "method_not_allowed");
  }
});
Deno.test("body: JSON only, small, with a url", async () => {
  const s = setup();
  const r1 = await call(s, post({ url: "https://example.co.za/" }, { "content-type": "text/plain" }));
  assertEquals(r1.res.status, 400);
  isError(r1.body, "invalid_request");
  const r2 = await call(s, post("{not json"));
  isError(r2.body, "invalid_request");
  const r3 = await call(s, post({ url: "https://example.co.za/" + "a".repeat(9_000) }));
  isError(r3.body, "invalid_request");
  const r4 = await call(s, post({ url: 42 }));
  isError(r4.body, "invalid_url");
  const r5 = await call(s, post({ url: "https://example.co.za/" + "a".repeat(3_000) }));
  isError(r5.body, "invalid_url");
});

// ---------------------------------------------------------------- Turnstile

function turnstile(success: boolean, seen: string[]): Route {
  return (_u, init) => {
    seen.push(String(init?.body));
    return new Response(JSON.stringify({ success }), { headers: { "content-type": "application/json" } });
  };
}

Deno.test("turnstile: missing token is refused before anything else", async () => {
  const s = setup({ env: { TURNSTILE_SECRET: "ts-secret" } });
  const { res, body } = await call(s, post({ url: "https://example.co.za/" }));
  assertEquals(res.status, 403);
  isError(body, "turnstile_failed");
  assertEquals(s.log, [], "no rate limit hit and no fetch");
});
Deno.test("turnstile: invalid token is refused, valid token proceeds in order", async () => {
  const seen: string[] = [];
  const bad = setup({
    env: { TURNSTILE_SECRET: "ts-secret" },
    routes: { "https://challenges.cloudflare.com/turnstile/v0/siteverify": turnstile(false, seen) },
  });
  const r1 = await call(bad, post({ url: "https://example.co.za/", turnstileToken: "tok" }));
  assertEquals(r1.res.status, 403);
  assertEquals(bad.log, ["turnstile"]);
  const p = new URLSearchParams(seen[0]);
  assertEquals([p.get("secret"), p.get("response")], ["ts-secret", "tok"]);

  const good = setup({
    env: { TURNSTILE_SECRET: "ts-secret" },
    routes: { "https://challenges.cloudflare.com/turnstile/v0/siteverify": turnstile(true, []) },
  });
  const r2 = await call(good, post({ url: "https://example.co.za/", turnstileToken: "tok" }));
  assertEquals(r2.res.status, 200);
  assertEquals(good.log.slice(0, 4), ["turnstile", "ratelimit", "ratelimit", "fetch"], "per-IP then global, then fetch");
});
Deno.test("turnstile: verifier errors fail closed", async () => {
  const s = setup({
    env: { TURNSTILE_SECRET: "ts-secret" },
    routes: { "https://challenges.cloudflare.com/turnstile/v0/siteverify": () => new Response("oops", { status: 500 }) },
  });
  const { res } = await call(s, post({ url: "https://example.co.za/", turnstileToken: "tok" }));
  assertEquals(res.status, 403);
});
Deno.test("turnstile: not required when no secret is set", async () => {
  const s = setup();
  const { res } = await call(s, post({ url: "https://example.co.za/" }));
  assertEquals(res.status, 200);
  assert(!s.log.includes("turnstile"));
});

// ---------------------------------------------------------------- rate limiting

Deno.test("rate limit: refused, backend error and missing salt all give 429", async () => {
  const cases: Setup[] = [
    { rateLimit: () => Promise.resolve(false) },
    { rateLimit: () => Promise.reject(new Error(`db down ${SECRET}`)) },
    { rateLimit: () => Promise.resolve("yes" as unknown as boolean) },
    { env: { RATE_LIMIT_SALT: "" } },
  ];
  for (const c of cases) {
    const s = setup(c);
    const { res, body } = await call(s, post({ url: "https://example.co.za/" }));
    assertEquals(res.status, 429);
    isError(body, "rate_limited");
    assertEquals(s.calls.length, 0, "site never fetched");
  }
});
Deno.test("rate limit: salted hash of the client IP, default and custom limits", async () => {
  const s = setup();
  await call(s, post({ url: "https://example.co.za/" }));
  assertEquals(s.hits[0]!.limit, 10);
  assertEquals(s.hits[0]!.hash, await hashIp("v4:41.1.2.3", "test-salt"));
  assert(/^[0-9a-f]{64}$/.test(s.hits[0]!.hash));
  assert(!s.hits[0]!.hash.includes("41.1.2.3"));
  const s2 = setup({ env: { RATE_LIMIT_PER_HOUR: "3" } });
  await call(s2, post({ url: "https://example.co.za/" }));
  assertEquals(s2.hits[0]!.limit, 3);
  const s3 = setup({ env: { RATE_LIMIT_PER_HOUR: "-5" } });
  await call(s3, post({ url: "https://example.co.za/" }));
  assertEquals(s3.hits[0]!.limit, 10);
  assert((await hashIp("v4:41.1.2.3", "a")) !== (await hashIp("v4:41.1.2.3", "b")), "salt matters");
});
Deno.test("rate limit: rate limiting happens before URL validation", async () => {
  const s = setup();
  await call(s, post({ url: "http://127.0.0.1/" }));
  assertEquals(s.hits.length, 2, "per-IP and global checks both run before URL validation");
});
Deno.test("rate limit: IP buckets", () => {
  assertEquals(ipBucket("41.1.2.3"), "v4:41.1.2.3");
  assertEquals(ipBucket("::ffff:41.1.2.3"), "v4:41.1.2.3");
  assertEquals(ipBucket("2c0f:fb50:4002:12:a::1"), ipBucket("2c0f:fb50:4002:12:ffff::9"));
  assert(ipBucket("2c0f:fb50:4002:12::1") !== ipBucket("2c0f:fb50:4002:13::1"));
  assertEquals(ipBucket(null), "unknown");
  assertEquals(ipBucket("garbage"), "unknown");
});
Deno.test({
  name: "rate limit: supabase rpc wiring",
  sanitizeOps: false,
  sanitizeResources: false,
  fn: async () => {
    const saved = globalThis.fetch;
    const seen: Array<{ url: string; body: string; auth: string | null }> = [];
    let reply: () => Response = () => new Response("true", { headers: { "content-type": "application/json" } });
    globalThis.fetch = (async (input: Request | URL | string, init?: RequestInit) => {
      const req = new Request(input, init);
      seen.push({ url: req.url, body: await req.text(), auth: req.headers.get("authorization") });
      return reply();
    }) as typeof fetch;
    try {
      const env = (k: string) =>
        ({ SUPABASE_URL: "https://proj.supabase.co", SUPABASE_SERVICE_ROLE_KEY: "srk" } as Record<string, string>)[k];
      const sig = new AbortController().signal;
      assertEquals(await supabaseRateLimit("a".repeat(64), 7, sig, env), true);
      assertEquals(seen[0]!.url, "https://proj.supabase.co/rest/v1/rpc/site_check_hit");
      assertEquals(JSON.parse(seen[0]!.body), { p_ip_hash: "a".repeat(64), p_limit: 7 });
      assertEquals(seen[0]!.auth, "Bearer srk");
      reply = () => new Response("false", { headers: { "content-type": "application/json" } });
      assertEquals(await supabaseRateLimit("a".repeat(64), 7, sig, env), false);
      reply = () =>
        new Response(JSON.stringify({ message: "boom" }), { status: 500, headers: { "content-type": "application/json" } });
      let threw = false;
      try {
        await supabaseRateLimit("a".repeat(64), 7, sig, env);
      } catch {
        threw = true;
      }
      assert(threw, "backend error throws so the handler fails closed");
      threw = false;
      try {
        await supabaseRateLimit("a".repeat(64), 7, sig, () => undefined);
      } catch {
        threw = true;
      }
      assert(threw, "missing env throws");
    } finally {
      globalThis.fetch = saved;
    }
  },
});

// ---------------------------------------------------------------- errors and success

Deno.test("errors: blocked targets give a generic error and never echo the URL", async () => {
  for (
    const url of [
      `http://127.0.0.1/?token=${SECRET}`,
      `http://169.254.169.254/latest/meta-data/?k=${SECRET}`,
      `http://localhost/${SECRET}`,
      `ftp://example.co.za/${SECRET}`,
      `http://example.co.za:8080/${SECRET}`,
    ]
  ) {
    const s = setup();
    const { res, body } = await call(s, post({ url }));
    assertEquals(res.status, 400, url);
    isError(body, "blocked_target");
    assert(!JSON.stringify(body).includes(SECRET));
    assertEquals(s.calls.length, 0);
  }
});
Deno.test("errors: upstream error messages are not echoed", async () => {
  const s = setup({
    routes: {
      [`https://example.co.za/?token=${SECRET}`]: () => {
        throw new TypeError(`error sending request for url (https://example.co.za/?token=${SECRET}): tls handshake`);
      },
    },
  });
  const { res, body } = await call(s, post({ url: `https://example.co.za/?token=${SECRET}` }));
  assertEquals(res.status, 502);
  isError(body, "fetch_failed");
  assert(!JSON.stringify(body).includes(SECRET));
});
Deno.test("errors: DNS failure and redirect loops", async () => {
  const s = setup();
  const r1 = await call(s, post({ url: "https://unknown.example.co.za/" }));
  assertEquals(r1.res.status, 502);
  isError(r1.body, "dns_failed");
  const s2 = setup({
    routes: { "https://example.co.za/": () => new Response(null, { status: 302, headers: { location: "/" } }) },
  });
  const r2 = await call(s2, post({ url: "https://example.co.za/" }));
  isError(r2.body, "too_many_redirects");
});
Deno.test("errors: bot checks and error pages are not graded", async () => {
  const cases: Array<[Route, string]> = [
    [() => new Response("<html></html>", { status: 429, headers: { "x-vercel-mitigated": "challenge" } }), "site_blocked"],
    [() => new Response("", { status: 403, headers: { "cf-mitigated": "challenge" } }), "site_blocked"],
    [html("<html><head><title>Just a moment...</title></head></html>"), "site_blocked"],
    [() => new Response("nope", { status: 500, headers: { "content-type": "text/html" } }), "site_error"],
    [() => new Response("", { status: 401 }), "site_error"],
  ];
  for (const [route, type] of cases) {
    const s = setup({ routes: { "https://example.co.za/": route } });
    const { res, body } = await call(s, post({ url: "https://example.co.za/" }));
    assertEquals(res.status, 422);
    isError(body, type);
  }
});
Deno.test("success: response shape, headers and a clean site", async () => {
  const s = setup();
  const { res, body } = await call(s, post({ url: "https://user:pw@example.co.za/#x" }));
  assertEquals(res.status, 200);
  assertEquals(res.headers.get("access-control-allow-origin"), ORIGIN);
  assertEquals(res.headers.get("cache-control"), "no-store");
  assertEquals(res.headers.get("content-type"), "application/json; charset=utf-8");
  assertEquals(Object.keys(body), ["url", "final_url", "checked_at", "summary", "findings", "cookies", "notices", "disclaimer"]);
  assertEquals(body["url"], "https://example.co.za/");
  assertEquals(body["checked_at"], "2026-10-18T09:00:00+00:00");
  assertEquals(body["disclaimer"], DISCLAIMER);
  const got = (body["findings"] as Array<{ rule_id: string }>).map((f) => f.rule_id);
  assert(
    !got.includes("WEB-002") && !got.includes("WEB-003") && !got.includes("WEB-018") && !got.includes("WEB-015"),
    got.join(),
  );
  assert(!s.calls.some((c) => c.url.includes("pw@")));
});
Deno.test("notice probes: off by default, on with PROBE_NOTICE_PATHS", async () => {
  const shell = `<html><body><div id="root"></div></body></html>`;
  const routes: Record<string, Route> = {
    "https://example.co.za/": html(shell),
    "https://example.co.za/privacy": html(shell), // SPA fallback: same body, not a notice
    "https://example.co.za/privacy-policy": html("<h1>Privacy notice</h1>"),
    "https://example.co.za/paia-manual": () => new Response("%PDF-1.7", { headers: { "content-type": "application/pdf" } }),
  };
  const off = setup({ routes });
  const r1 = await call(off, post({ url: "https://example.co.za/" }));
  assertEquals(r1.body["notices"], { privacy: false, paia: false, cookie: false, information_officer: false });
  assert(!off.calls.some((c) => c.url.endsWith("/privacy")));
  const on = setup({ routes, env: { PROBE_NOTICE_PATHS: "true" } });
  const r2 = await call(on, post({ url: "https://example.co.za/" }));
  assertEquals(r2.body["notices"], { privacy: true, paia: true, cookie: false, information_officer: false });
});

// ---------------------------------------------------------------- user-facing copy

Deno.test("copy: no dashes, exclamation marks or compliance claims in user-facing strings", async () => {
  const strings: string[] = [...Object.values(ERROR_MESSAGES), DISCLAIMER];
  const bad = `<script src="http://www.googletagmanager.com/gtag/js"></script><script>fbq('init','1')</script>
    <form><input type="password"><input type="checkbox" name="newsletter" checked></form><a href="/x?email=a">x</a>`;
  const h = new Headers({
    "content-type": "text/html",
    server: "Apache/2.4.1",
    "content-security-policy": "script-src 'unsafe-inline'",
  });
  h.append("set-cookie", "_ga=1");
  h.append("set-cookie", "sessionid=1");
  const s = setup({ routes: { "http://example.co.za/": () => new Response(bad, { headers: h }) } });
  const { body } = await call(s, post({ url: "http://example.co.za/" }));
  for (const f of body["findings"] as Array<{ title: string; fix: string }>) strings.push(f.title, f.fix);
  assert((body["findings"] as unknown[]).length >= 12);
  for (const str of strings) {
    assert(!/[\u2013\u2014!]/.test(str), `dash or exclamation in: ${str}`);
    assert(!/compliant/i.test(str), `compliance claim in: ${str}`);
  }
});
