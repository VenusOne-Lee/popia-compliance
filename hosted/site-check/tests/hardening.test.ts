// Security review additions: client IP selection, global cap, regex cost bounds, slow bodies,
// the hard overall budget, more host notations and runtime portability helpers.
import {
  anySignal,
  assertPublicDns,
  checkHeaders,
  checkHtml,
  clientIp,
  createHandler,
  ERROR_MESSAGES,
  GLOBAL_BUCKET,
  guardedFetch,
  hashIp,
  ipBucket,
  isPublicIp,
  LIMITS,
  type RateLimitFn,
  readLimited,
  safeUrl,
  validateTargetUrl,
} from "../supabase/functions/site-check/core.ts";
import {
  assert,
  assertEquals,
  assertRejectsType,
  countConsoleCalls,
  fakeDns,
  html,
  makeCtx,
  mockFetch,
  publicDns,
} from "./helpers.ts";

const ORIGIN = "https://check.venusone.co.za";
const SALT = "test-salt";

function setup(o: { env?: Record<string, string>; rateLimit?: RateLimitFn; fetch?: typeof fetch } = {}) {
  const env: Record<string, string> = { ALLOWED_ORIGINS: ORIGIN, RATE_LIMIT_SALT: SALT, ...o.env };
  const m = mockFetch({
    "https://example.co.za/": html("<p>ok</p>"),
  });
  const hits: Array<{ hash: string; limit: number }> = [];
  const rateLimit: RateLimitFn = o.rateLimit ?? ((hash, limit) => {
    hits.push({ hash, limit });
    return Promise.resolve(true);
  });
  const handler = createHandler({
    fetch: o.fetch ?? m.fn,
    env: (k) => env[k],
    rateLimit,
    resolve: fakeDns(publicDns("example.co.za")).resolve,
  });
  return { handler, calls: m.calls, hits };
}

function post(headers: Record<string, string> = {}, body: BodyInit = JSON.stringify({ url: "https://example.co.za/" })) {
  return new Request("https://proj.supabase.co/functions/v1/site-check", {
    method: "POST",
    headers: { origin: ORIGIN, "content-type": "application/json", ...headers },
    body,
    duplex: "half",
  } as RequestInit);
}

async function errorType(res: Response): Promise<string> {
  const b = await res.json();
  assertEquals(Object.keys(b), ["error", "type"]);
  assertEquals(b.error, ERROR_MESSAGES[b.type]);
  return b.type;
}

const noEnv = () => undefined;
const reqWith = (h: Record<string, string>) => new Request("https://x/f", { headers: h });

// ---------------------------------------------------------------- client IP

Deno.test("client ip: cf-connecting-ip, then x-real-ip, then the LAST x-forwarded-for entry", () => {
  const all = { "cf-connecting-ip": "41.0.0.1", "x-real-ip": "41.0.0.2", "x-forwarded-for": "6.6.6.6, 41.0.0.3" };
  assertEquals(clientIp(reqWith(all), noEnv), "41.0.0.1");
  assertEquals(clientIp(reqWith({ "x-real-ip": "41.0.0.2", "x-forwarded-for": "6.6.6.6, 41.0.0.3" }), noEnv), "41.0.0.2");
  assertEquals(clientIp(reqWith({ "x-forwarded-for": "6.6.6.6, 7.7.7.7, 41.0.0.3" }), noEnv), "41.0.0.3");
  assertEquals(clientIp(reqWith({ "x-forwarded-for": " , 41.0.0.3 , " }), noEnv), "41.0.0.3");
  assertEquals(clientIp(reqWith({ "cf-connecting-ip": "", "x-real-ip": "41.0.0.2" }), noEnv), "41.0.0.2", "empty is absent");
  const h = new Headers();
  h.append("x-forwarded-for", "6.6.6.6");
  h.append("x-forwarded-for", "41.0.0.3");
  assertEquals(clientIp(new Request("https://x/f", { headers: h }), noEnv), "41.0.0.3", "repeated header lines");
  assertEquals(clientIp(reqWith({}), noEnv), null);
});
Deno.test("client ip: ports are stripped", () => {
  assertEquals(clientIp(reqWith({ "x-forwarded-for": "6.6.6.6, 41.0.0.3:51234" }), noEnv), "41.0.0.3");
  assertEquals(clientIp(reqWith({ "cf-connecting-ip": "[2c0f:fb50:4002::1]:443" }), noEnv), "2c0f:fb50:4002::1");
  assertEquals(clientIp(reqWith({ "cf-connecting-ip": "[2c0f:fb50:4002::1]" }), noEnv), "2c0f:fb50:4002::1");
  assertEquals(clientIp(reqWith({ "cf-connecting-ip": "2c0f:fb50:4002::1" }), noEnv), "2c0f:fb50:4002::1");
});
Deno.test("client ip: CLIENT_IP_HEADER replaces the default list", () => {
  const env = (k: string) => (k === "CLIENT_IP_HEADER" ? "Fly-Client-IP" : undefined);
  const h = { "cf-connecting-ip": "6.6.6.6", "fly-client-ip": "41.0.0.9" };
  assertEquals(clientIp(reqWith(h), env), "41.0.0.9");
  assertEquals(clientIp(reqWith({ "cf-connecting-ip": "6.6.6.6" }), env), null, "no fallback to untrusted headers");
  const xff = (k: string) => (k === "CLIENT_IP_HEADER" ? "x-forwarded-for" : undefined);
  assertEquals(clientIp(reqWith({ "cf-connecting-ip": "6.6.6.6", "x-forwarded-for": "6.6.6.7, 41.0.0.3" }), xff), "41.0.0.3");
});
Deno.test("client ip: rotating the first x-forwarded-for entry does not change the bucket", async () => {
  const s = setup();
  for (const spoof of ["1.1.1.1", "8.8.8.8", "9.9.9.9, 4.4.4.4"]) {
    const res = await s.handler(post({ "x-forwarded-for": `${spoof}, 41.1.2.3` }));
    assertEquals(res.status, 200);
  }
  const want = await hashIp("v4:41.1.2.3", SALT);
  const perIp = s.hits.filter((_, i) => i % 2 === 0);
  assertEquals(perIp.map((h) => h.hash), [want, want, want]);
});
Deno.test("client ip: requests without a usable IP share one bucket", async () => {
  const s = setup();
  await s.handler(post());
  await s.handler(post({ "x-forwarded-for": "not-an-ip" }));
  const want = await hashIp("unknown", SALT);
  assertEquals([s.hits[0]!.hash, s.hits[2]!.hash], [want, want]);
});

// ---------------------------------------------------------------- global cap

Deno.test("global cap: checked after the per-IP check with a fixed key, default 300", async () => {
  const s = setup();
  const res = await s.handler(post({ "cf-connecting-ip": "41.1.2.3" }));
  assertEquals(res.status, 200);
  assertEquals(s.hits.length, 2);
  assertEquals(s.hits[0], { hash: await hashIp("v4:41.1.2.3", SALT), limit: 10 });
  assertEquals(s.hits[1], { hash: await hashIp(GLOBAL_BUCKET, SALT), limit: 300 });
  assert(/^[0-9a-f]{64}$/.test(s.hits[1]!.hash), "fits the table's hash check");
  assertEquals(ipBucket(GLOBAL_BUCKET), "unknown", "no IP input can produce the global bucket");
  const other = setup();
  await other.handler(post({ "cf-connecting-ip": "41.9.9.9" }));
  assertEquals(other.hits[1]!.hash, s.hits[1]!.hash, "same global key for every client");
});
Deno.test("global cap: GLOBAL_LIMIT_PER_HOUR, with invalid values falling back to 300", async () => {
  const cases: Array<[string, number]> = [["50", 50], ["abc", 300], ["0", 300], ["-1", 300], ["99999999", 1_000_000]];
  for (const [raw, want] of cases) {
    const s = setup({ env: { GLOBAL_LIMIT_PER_HOUR: raw } });
    await s.handler(post());
    assertEquals(s.hits[1]!.limit, want, raw);
  }
});
Deno.test("global cap: refused, failing or odd global answers fail closed with 429", async () => {
  const second = (g: () => Promise<boolean>): RateLimitFn => {
    let n = 0;
    return () => (n++ === 0 ? Promise.resolve(true) : g());
  };
  const cases: RateLimitFn[] = [
    second(() => Promise.resolve(false)),
    second(() => Promise.reject(new Error("db down"))),
    second(() => Promise.resolve(1 as unknown as boolean)),
  ];
  for (const rl of cases) {
    const m = mockFetch({});
    const s = setup({ rateLimit: rl, fetch: m.fn as typeof fetch });
    const res = await s.handler(post());
    assertEquals(res.status, 429);
    assertEquals(await errorType(res), "rate_limited");
    assertEquals(m.calls.length, 0, "site never fetched");
  }
});
Deno.test("global cap: a request refused per IP does not use global budget", async () => {
  const keys: string[] = [];
  const s = setup({
    rateLimit: (hash) => {
      keys.push(hash);
      return Promise.resolve(false);
    },
  });
  const res = await s.handler(post());
  assertEquals(res.status, 429);
  assertEquals(keys.length, 1);
  assert(keys[0] !== (await hashIp(GLOBAL_BUCKET, SALT)));
});

// ---------------------------------------------------------------- regex cost bounds

const fast = (ms: number, budget: number, what: string) => assert(ms < budget, `${what} took ${Math.round(ms)} ms`);

Deno.test("redos: safeUrl bounds long paths and never leaves part of a token at the cut", () => {
  let t = performance.now();
  const out = safeUrl("https://e.co.za/" + "a".repeat(1_000_000));
  fast(performance.now() - t, 200, "1 MB path");
  assertEquals(out, "https://e.co.za/…");
  // A 40 char token that straddles the cut would leave 21 chars, too short for the {32,} pattern.
  const path = "/" + "p/".repeat(245) + "Q".repeat(40) + "/tail";
  t = performance.now();
  const cut = safeUrl("https://e.co.za" + path);
  fast(performance.now() - t, 50, "cut path");
  assert(!cut.includes("QQQQ"), cut.slice(-40));
  assert(cut.endsWith("/…"), cut.slice(-10));
  assert(cut.length <= "https://e.co.za".length + LIMITS.maxReportPath + 1);
  const mail = safeUrl("https://e.co.za/" + "x/".repeat(250) + "person@example.test/" + "y".repeat(600));
  assert(!mail.includes("person"), "email near the cut is still masked");
  assertEquals(safeUrl("https://e.co.za/k/" + "a".repeat(40)), "https://e.co.za/k/…REDACTED", "short paths unchanged");
});
Deno.test("redos: one huge http script src, or thousands of them, stays fast", () => {
  let t = performance.now();
  const one = checkHtml(`<script src="http://cdn.example.co.za/${"a".repeat(1_400_000)}"></script>`, "https://e.co.za/");
  fast(performance.now() - t, 1_000, "1.4 MB src");
  const w12 = one.findings.filter((f) => f.rule_id === "WEB-012");
  assertEquals(w12.length, 1);
  assert(w12[0]!.evidence.length <= LIMITS.maxEvidence);
  const many = `<script src="http://cdn.example.co.za/${"b".repeat(400)}"></script>`.repeat(3_000);
  t = performance.now();
  const r = checkHtml(many, "https://e.co.za/");
  fast(performance.now() - t, 1_500, "3000 http scripts");
  assertEquals(r.findings.filter((f) => f.rule_id === "WEB-012").length, LIMITS.maxFindingsPerRule);
});
Deno.test("redos: huge server and x-powered-by values stay fast and versions are still found", () => {
  const t = performance.now();
  checkHeaders({
    finalUrl: "https://e.co.za/",
    headers: new Headers({ server: "1".repeat(400_000), "x-powered-by": "9".repeat(400_000) }),
  });
  fast(performance.now() - t, 100, "400 KB digit headers");
  const v = checkHeaders({ finalUrl: "https://e.co.za/", headers: new Headers({ server: "nginx/1.25.3" }) });
  assert(v.some((f) => f.rule_id === "WEB-009" && f.evidence === "nginx/1.25.3"));
});
Deno.test("redos: a long redirect Location does not stall the report", async () => {
  const long = "/" + "c".repeat(300_000);
  const m = mockFetch({
    "https://example.co.za/": () => new Response(null, { status: 302, headers: { location: long } }),
    ["https://example.co.za" + long]: html("<p>ok</p>"),
  });
  const s = createHandler({
    fetch: m.fn,
    env: (k) => ({ ALLOWED_ORIGINS: ORIGIN, RATE_LIMIT_SALT: SALT } as Record<string, string>)[k],
    rateLimit: () => Promise.resolve(true),
    resolve: fakeDns(publicDns("example.co.za")).resolve,
  });
  const t = performance.now();
  const res = await s(post());
  fast(performance.now() - t, 1_000, "long final URL");
  const body = await res.json();
  assertEquals(body.final_url, "https://example.co.za/…");
});

// ---------------------------------------------------------------- slow and oversized bodies

function silentStream(counter = { pulled: 0 }) {
  return new ReadableStream<Uint8Array>({
    pull() {
      counter.pulled++;
      return new Promise(() => {}); // never delivers, never closes
    },
  }, { highWaterMark: 0 });
}

Deno.test({
  name: "request body: a slow upload times out instead of holding the handler",
  sanitizeOps: false,
  sanitizeResources: false,
  fn: async () => {
    const saved = LIMITS.requestBodyMs;
    LIMITS.requestBodyMs = 50;
    try {
      const s = setup();
      const t0 = Date.now();
      const res = await s.handler(post({}, silentStream()));
      assertEquals(res.status, 504);
      assertEquals(await errorType(res), "timeout");
      assert(Date.now() - t0 < 2_000);
      assertEquals(s.hits.length + s.calls.length, 0, "nothing else happened");
    } finally {
      LIMITS.requestBodyMs = saved;
    }
  },
});
Deno.test("request body: a declared length over the cap is refused without reading", async () => {
  const counter = { pulled: 0 };
  const s = setup();
  const res = await s.handler(post({ "content-length": "100000" }, silentStream(counter)));
  assertEquals(res.status, 400);
  assertEquals(await errorType(res), "invalid_request");
  assertEquals(counter.pulled, 0);
});
Deno.test({
  name: "slowloris: a body that trickles forever is cut off by the per-request timeout",
  sanitizeOps: false,
  sanitizeResources: false,
  fn: async () => {
    const saved = LIMITS.perRequestMs;
    LIMITS.perRequestMs = 100;
    try {
      let timer: ReturnType<typeof setInterval> | undefined;
      const trickle = new ReadableStream<Uint8Array>({
        start(c) {
          timer = setInterval(() => c.enqueue(new Uint8Array([32])), 5);
        },
        cancel() {
          clearInterval(timer);
        },
      });
      // This fetch ignores its signal entirely, so only readLimited can stop the read.
      const fetchFn = () => Promise.resolve(new Response(trickle, { headers: { "content-type": "text/html" } }));
      const ctx = makeCtx(fetchFn, fakeDns(publicDns("example.co.za")).resolve);
      const t0 = Date.now();
      let name = "";
      try {
        await guardedFetch("https://example.co.za/", ctx, { follow: true, bodyLimit: () => LIMITS.maxBodyBytes });
      } catch (e) {
        name = (e as Error).name;
      }
      clearInterval(timer);
      assertEquals(name, "TimeoutError");
      assert(Date.now() - t0 < 2_000);
    } finally {
      LIMITS.perRequestMs = saved;
    }
  },
});
Deno.test("readLimited: an aborted signal throws its reason, before or during the read", async () => {
  const ac = new AbortController();
  ac.abort(new DOMException("stop", "TimeoutError"));
  let name = "";
  try {
    await readLimited(silentStream(), 10, ac.signal);
  } catch (e) {
    name = (e as Error).name;
  }
  assertEquals(name, "TimeoutError");
  const ac2 = new AbortController();
  setTimeout(() => ac2.abort(new DOMException("stop", "TimeoutError")), 10);
  name = "";
  try {
    await readLimited(silentStream(), 10, ac2.signal);
  } catch (e) {
    name = (e as Error).name;
  }
  assertEquals(name, "TimeoutError");
});
Deno.test({
  name: "overall budget: holds even when an injected fetch ignores its signal",
  sanitizeOps: false,
  sanitizeResources: false,
  fn: async () => {
    const saved = LIMITS.overallMs;
    LIMITS.overallMs = 100;
    try {
      const never = () => new Promise<Response>(() => {});
      const s = setup({ fetch: never as typeof fetch });
      const t0 = Date.now();
      let res!: Response;
      // AbortSignal.timeout timers do not hold the event loop open; a server would. Hold it here.
      const keepAlive = setTimeout(() => {}, 5_000);
      const n = await countConsoleCalls(async () => {
        res = await s.handler(post());
      });
      clearTimeout(keepAlive);
      assertEquals(res.status, 504);
      assertEquals(await errorType(res), "timeout");
      assert(Date.now() - t0 < 2_000);
      assertEquals(n, 0, "no console output");
    } finally {
      LIMITS.overallMs = saved;
    }
  },
});

// ---------------------------------------------------------------- more host notations

Deno.test("url guard: alternate notations, IDNA tricks and trailing dots are refused", () => {
  for (
    const u of [
      "http://127%2e0%2e0%2e1/",
      "http://127.0.0.1./",
      "http://017700000001/",
      "http://0x7f.0x0.0x0.0x1/",
      "http://0.0.0.0./",
      "http://[::]/",
      "http://[::127.0.0.1]/",
      "http://[0:0:0:0:0:ffff:127.0.0.1]/",
      "http://[64:ff9b::169.254.169.254]/",
      "http://[64:ff9b::a00:1]/",
      "http://[2002:a9fe:a9fe::1]/",
      "http://[2002:7f00:1::]/",
      "http://[2001:0:4136:e378:8000:63bf:3fff:fdd2]/",
      "http://[fec0::1]/",
      "http://[fd00:ec2::254]/",
      "http://１２７.０.０.１/",
      "http://127。0。0。1/",
      "http://ⓛⓞⓒⓐⓛⓗⓞⓢⓣ/",
      "http://localhost%2e/",
      "http://example.co.za\n@127.0.0.1/",
      "https:////127.0.0.1/",
      "http://168.63.129.16/",
      "http://100.100.100.200/",
      "http://metadata.google.internal./",
    ]
  ) {
    try {
      validateTargetUrl(u);
      throw new Error(`should refuse ${JSON.stringify(u)}`);
    } catch (e) {
      const t = (e as { type?: string }).type;
      assert(t === "blocked_target" || t === "invalid_url", `refuse ${JSON.stringify(u)}: got ${String(e)}`);
    }
  }
  assert(!isPublicIp("168.63.129.16"));
  assert(isPublicIp("168.63.129.17"));
});
Deno.test("dns: the Azure WireServer address is refused in answers too", async () => {
  const { resolve } = fakeDns({ "example.co.za": { A: ["168.63.129.16"] } });
  await assertRejectsType(() => assertPublicDns("example.co.za", resolve, new AbortController().signal), "blocked_target");
});

// ---------------------------------------------------------------- portability

Deno.test("anySignal: the fallback used when AbortSignal.any is missing works", () => {
  const a = AbortSignal as unknown as { any?: unknown };
  const saved = a.any;
  try {
    a.any = undefined;
    const c1 = new AbortController();
    const c2 = new AbortController();
    const s = anySignal([c1.signal, c2.signal]);
    assert(!s.aborted);
    c2.abort("why");
    assert(s.aborted);
    assertEquals(s.reason, "why");
    const pre = new AbortController();
    pre.abort("early");
    assertEquals(anySignal([pre.signal]).reason, "early");
  } finally {
    a.any = saved;
  }
});
