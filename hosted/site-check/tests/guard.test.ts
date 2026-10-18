// SSRF guard: IP literals, hostnames, URL validation, DNS checks, redirects, timeouts and body caps.
import {
  assertPublicDns,
  dohResolver,
  guardedFetch,
  isAllowedHostname,
  isPublicIp,
  LIMITS,
  normaliseInputUrl,
  parseIPv4,
  parseIPv6,
  readLimited,
  runSiteCheck,
  validateTargetUrl,
} from "../supabase/functions/site-check/core.ts";
import {
  assert,
  assertEquals,
  assertRejectsType,
  assertThrowsType,
  fakeDns,
  html,
  makeCtx,
  mockFetch,
  publicDns,
  redirect,
} from "./helpers.ts";

const PRIVATE_V4 = [
  "0.0.0.0",
  "0.1.2.3",
  "10.0.0.1",
  "10.255.255.255",
  "100.64.0.1",
  "100.127.255.255",
  "127.0.0.1",
  "127.255.255.254",
  "169.254.0.1",
  "169.254.169.254",
  "172.16.0.1",
  "172.31.255.255",
  "192.0.0.8",
  "192.0.2.1",
  "192.88.99.1",
  "192.168.0.1",
  "192.168.255.255",
  "198.18.0.1",
  "198.19.255.255",
  "198.51.100.7",
  "203.0.113.9",
  "224.0.0.1",
  "239.255.255.250",
  "240.0.0.1",
  "255.255.255.255",
];
const PUBLIC_V4 = [
  "1.1.1.1",
  "8.8.8.8",
  "9.9.9.9",
  "11.0.0.1",
  "100.63.255.255",
  "100.128.0.1",
  "126.255.255.255",
  "128.0.0.1",
  "169.253.255.255",
  "169.255.0.1",
  "172.15.255.255",
  "172.32.0.1",
  "192.0.1.1",
  "192.0.3.1",
  "192.167.255.255",
  "192.169.0.1",
  "198.17.255.255",
  "198.20.0.1",
  "198.51.99.1",
  "203.0.112.1",
  "223.255.255.255",
  "41.0.0.1",
  "196.25.1.1",
];
const PRIVATE_V6 = [
  "::",
  "::1",
  "0:0:0:0:0:0:0:1",
  "::ffff:127.0.0.1",
  "::ffff:7f00:1",
  "::ffff:10.0.0.1",
  "::ffff:169.254.169.254",
  "::ffff:a9fe:a9fe",
  "::ffff:100.64.0.1",
  "::ffff:0.0.0.0",
  "::ffff:224.0.0.1",
  "::127.0.0.1",
  "::ffff:0:7f00:1",
  "64:ff9b::7f00:1",
  "64:ff9b::a00:1",
  "64:ff9b::169.254.169.254",
  "64:ff9b:1::1",
  "100::1",
  "fe80::1",
  "febf:ffff::1",
  "fec0::1",
  "fc00::1",
  "fd00::1",
  "fd12:3456:789a::1",
  "ff02::1",
  "ff05::2",
  "2001::1",
  "2001:0:4136:e378:8000:63bf:3fff:fdd2",
  "2001:2::1",
  "2001:10::1",
  "2001:db8::1",
  "2001:db8:ffff::1",
  "3fff::1",
  "3fff:fff::1",
  "2002:7f00:1::1",
  "2002:a00:1::1",
  "2002:c0a8:101::1",
  "[::1]",
  "[fd00::1]",
  "1::1",
  "4000::1",
  "e000::1",
];
const PUBLIC_V6 = [
  "2606:4700:4700::1111",
  "2001:4860:4860::8888",
  "2c0f:fb50:4002::1",
  "2a00:1450:4001:80b::200e",
  "::ffff:8.8.8.8",
  "::ffff:808:808",
  "64:ff9b::808:808",
  "2002:808:808::1",
  "2001:200::1",
  "3fff:1000::1",
  "[2606:4700:4700::1111]",
];
const UNPARSEABLE = [
  "",
  " ",
  "1.2.3",
  "1.2.3.4.5",
  "01.2.3.4",
  "256.1.1.1",
  "1.2.3.-1",
  "0x7f.0.0.1",
  "fe80::1%eth0",
  "1:2:3:4:5:6:7:8:9",
  "1::2::3",
  ":1:2:3:4:5:6:7",
  "gggg::1",
  "::ffff:1.2.3",
  "12345::1",
  "localhost",
];

Deno.test("ip guard: private and reserved IPv4 are refused", () => {
  for (const ip of PRIVATE_V4) assert(!isPublicIp(ip), `should refuse ${ip}`);
});
Deno.test("ip guard: public IPv4 are allowed", () => {
  for (const ip of PUBLIC_V4) assert(isPublicIp(ip), `should allow ${ip}`);
});
Deno.test("ip guard: private, mapped and special IPv6 are refused", () => {
  for (const ip of PRIVATE_V6) assert(!isPublicIp(ip), `should refuse ${ip}`);
});
Deno.test("ip guard: public IPv6 and mapped public IPv4 are allowed", () => {
  for (const ip of PUBLIC_V6) assert(isPublicIp(ip), `should allow ${ip}`);
});
Deno.test("ip guard: unparseable input is never public", () => {
  for (const ip of UNPARSEABLE) assert(!isPublicIp(ip), `should refuse ${JSON.stringify(ip)}`);
});
Deno.test("ip parsing: canonical forms", () => {
  assertEquals(parseIPv4("192.168.1.1"), [192, 168, 1, 1]);
  assertEquals(parseIPv6("::ffff:127.0.0.1"), [0, 0, 0, 0, 0, 0xffff, 0x7f00, 1]);
  assertEquals(parseIPv6("1::"), [1, 0, 0, 0, 0, 0, 0, 0]);
  assertEquals(parseIPv6("::"), [0, 0, 0, 0, 0, 0, 0, 0]);
  assertEquals(parseIPv6("1:2:3:4:5:6:7:8"), [1, 2, 3, 4, 5, 6, 7, 8]);
  assertEquals(parseIPv6("1:2:3:4:5:6:7::"), [1, 2, 3, 4, 5, 6, 7, 0]);
});

Deno.test("hostname guard: internal and special names are refused", () => {
  for (
    const h of [
      "localhost",
      "LOCALHOST",
      "localhost.",
      "app.localhost",
      "printer.local",
      "metadata.google.internal",
      "db.internal",
      "router.lan",
      "nas.home.arpa",
      "1.0.0.127.in-addr.arpa",
      "intranet",
      "kong",
      "supabase_db",
      "host.localdomain",
      "site.test",
      "x.invalid",
      "www.example",
      "abc.onion",
      "",
      "a..b.co.za",
      "-bad.co.za",
      "bad-.co.za",
      "under score.co.za",
      "x.123",
      "a".repeat(64) + ".co.za",
      ("a".repeat(60) + ".").repeat(5) + "za",
    ]
  ) assert(!isAllowedHostname(h), `should refuse ${h}`);
});
Deno.test("hostname guard: ordinary public names are allowed", () => {
  for (
    const h of ["example.co.za", "www.gov.za", "xn--bcher-kva.de", "a.b.c.d.example.com", "my_host.example.com", "example.com."]
  ) {
    assert(isAllowedHostname(h), `should allow ${h}`);
  }
});

Deno.test("url guard: refuses bad schemes, ports, IP literals and internal names", () => {
  const blockedUrls = [
    "ftp://example.co.za/",
    "file:///etc/passwd",
    "gopher://example.co.za/",
    "data:text/html,hi",
    "javascript:alert(1)",
    "ws://example.co.za/",
    "http://example.co.za:8080/",
    "https://example.co.za:22/",
    "http://example.co.za:0/",
    "https://example.co.za:8443/",
    "http://localhost/",
    "http://LOCALHOST./",
    "http://foo.localhost/",
    "http://printer.local/",
    "http://metadata.google.internal/computeMetadata/v1/",
    "http://router.lan/",
    "http://nas.home.arpa/",
    "http://intranet/",
    "http://127.0.0.1/",
    "http://127.1/",
    "http://2130706433/",
    "http://0x7f.1/",
    "http://0177.0.0.1/",
    "http://0x7f000001/",
    "http://10.0.0.1/",
    "http://192.168.1.1/",
    "http://169.254.169.254/latest/meta-data/",
    "http://[::1]/",
    "http://[::ffff:127.0.0.1]/",
    "http://[::ffff:a9fe:a9fe]/",
    "http://[fd00::1]/",
    "http://[fe80::1]/",
    "http://0.0.0.0/",
    "http://0/",
    "http://100.64.1.1/",
    "http://user:pass@127.0.0.1/",
    "http://example.co.za@127.0.0.1/",
  ];
  for (const u of blockedUrls) {
    try {
      validateTargetUrl(u);
      throw new Error(`should refuse ${u}`);
    } catch (e) {
      const t = (e as { type?: string }).type;
      assert(t === "blocked_target" || t === "invalid_url", `refuse ${u}: got ${String(e)}`);
    }
  }
});
Deno.test("url guard: allows public targets and strips credentials and fragment", () => {
  const ok = [
    ["https://example.co.za/", "https://example.co.za/"],
    ["http://example.co.za:80/", "http://example.co.za/"],
    ["http://example.co.za:443/", "http://example.co.za:443/"],
    ["https://example.co.za:443/a", "https://example.co.za/a"],
    ["https://user:pass@example.co.za/x?q=1#frag", "https://example.co.za/x?q=1"],
    ["https://EXAMPLE.co.za/", "https://example.co.za/"],
    ["https://8.8.8.8/", "https://8.8.8.8/"],
    ["https://[2606:4700:4700::1111]/", "https://[2606:4700:4700::1111]/"],
    ["https://bücher.de/", "https://xn--bcher-kva.de/"],
  ];
  for (const [inp, out] of ok) assertEquals(validateTargetUrl(inp).url.href, out, inp);
});
Deno.test("url guard: zone IDs and garbage are invalid", () => {
  assertThrowsType(() => validateTargetUrl("http://[fe80::1%25eth0]/"), "invalid_url");
  assertThrowsType(() => validateTargetUrl("https://exa mple.co.za/"), "invalid_url");
  assertThrowsType(() => validateTargetUrl("not a url"), "invalid_url");
});
Deno.test("input normalisation: adds https and refuses other schemes", () => {
  assertEquals(normaliseInputUrl("example.co.za"), "https://example.co.za");
  assertEquals(normaliseInputUrl("  HTTP://Example.co.za/x "), "HTTP://Example.co.za/x");
  for (const s of ["ftp://example.co.za", "file:///etc/passwd", "javascript:alert(1)", "data:text/html,x"]) {
    assertThrowsType(() => normaliseInputUrl(s), "blocked_target", s);
  }
});

// ---------------------------------------------------------------- DNS

const sig = () => new AbortController().signal;

Deno.test("dns: all public answers pass", async () => {
  const { resolve } = fakeDns(publicDns("example.co.za"));
  await assertPublicDns("example.co.za", resolve, sig());
});
Deno.test("dns: any private A or AAAA answer is refused", async () => {
  const cases: Array<[string[], string[]]> = [
    [["203.0.114.10", "10.0.0.1"], []],
    [["203.0.114.10"], ["fd00::1"]],
    [["203.0.114.10"], ["::ffff:127.0.0.1"]],
    [["169.254.169.254"], []],
    [[], ["::1"]],
    [["100.64.0.1"], []],
    [["0.0.0.0"], []],
    [["not-an-ip"], []],
  ];
  for (const [A, AAAA] of cases) {
    const { resolve } = fakeDns({ "example.co.za": { A, AAAA } });
    await assertRejectsType(() => assertPublicDns("example.co.za", resolve, sig()), "blocked_target", JSON.stringify([A, AAAA]));
  }
});
Deno.test("dns: CNAME to an internal name is refused", async () => {
  const { resolve } = fakeDns({ "www.example.co.za": { CNAME: "db.corp.internal" } });
  await assertRejectsType(() => assertPublicDns("www.example.co.za", resolve, sig()), "blocked_target");
});
Deno.test("dns: CNAME without addresses is followed and its target checked", async () => {
  const good = fakeDns({ "www.example.co.za": { CNAME: "edge.cdn.example.net" }, ...publicDns("edge.cdn.example.net") });
  await assertPublicDns("www.example.co.za", good.resolve, sig());
  assert(good.queries.includes("edge.cdn.example.net/A"));
  const bad = fakeDns({
    "www.example.co.za": { CNAME: "rebind.example.net" },
    "rebind.example.net": { A: ["127.0.0.1"] },
  });
  await assertRejectsType(() => assertPublicDns("www.example.co.za", bad.resolve, sig()), "blocked_target");
});
Deno.test("dns: CNAME loop, SERVFAIL and NXDOMAIN fail closed", async () => {
  const loop = fakeDns({ "a.example.co.za": { CNAME: "b.example.co.za" }, "b.example.co.za": { CNAME: "a.example.co.za" } });
  await assertRejectsType(() => assertPublicDns("a.example.co.za", loop.resolve, sig()), "dns_failed");
  const servfail = fakeDns({ "example.co.za": { status: 2, A: ["203.0.114.10"] } });
  await assertRejectsType(() => assertPublicDns("example.co.za", servfail.resolve, sig()), "dns_failed");
  await assertRejectsType(() => assertPublicDns("nope.example.co.za", fakeDns({}).resolve, sig()), "dns_failed");
});
Deno.test("dns: DoH resolver sends the right request and parses JSON", async () => {
  const doh = "https://cloudflare-dns.com/dns-query?name=example.co.za&type=A";
  const m = mockFetch({
    [doh]: () =>
      new Response(JSON.stringify({
        Status: 0,
        Answer: [{ name: "example.co.za", type: 5, data: "x.example.net." }, { type: 1, data: "203.0.114.1" }, { junk: 1 }],
      })),
  });
  const r = await dohResolver(m.fn)("example.co.za", "A", sig());
  assertEquals(r, { status: 0, answers: [{ type: 5, data: "x.example.net." }, { type: 1, data: "203.0.114.1" }] });
  assertEquals(new Headers(m.calls[0].init?.headers).get("accept"), "application/dns-json");
  assert(m.calls[0].init?.signal instanceof AbortSignal);
});
Deno.test("dns: DoH errors fail closed", async () => {
  const name = "a&type=TXT&x=.example.co.za";
  const enc = `https://cloudflare-dns.com/dns-query?name=${encodeURIComponent(name)}&type=A`;
  const m1 = mockFetch({ [enc]: () => new Response("x", { status: 500 }) });
  await assertRejectsType(() => dohResolver(m1.fn)(name, "A", sig()), "dns_failed");
  assertEquals(m1.calls[0].url, enc, "name is URL-encoded");
  const m2 = mockFetch({ [enc]: () => new Response("not json") });
  await assertRejectsType(() => dohResolver(m2.fn)(name, "A", sig()), "dns_failed");
});
Deno.test("dns: a full check goes through DoH and refuses a private answer", async () => {
  const doh = (n: string, t: string) => `https://cloudflare-dns.com/dns-query?name=${n}&type=${t}`;
  const m = mockFetch({
    [doh("evil.example.co.za", "A")]: () => new Response(JSON.stringify({ Status: 0, Answer: [{ type: 1, data: "127.0.0.1" }] })),
    [doh("evil.example.co.za", "AAAA")]: () => new Response(JSON.stringify({ Status: 0 })),
  });
  const ctx = makeCtx(m.fn, dohResolver(m.fn));
  await assertRejectsType(() => runSiteCheck("https://evil.example.co.za/", ctx), "blocked_target");
  assert(m.calls.every((c) => c.url.startsWith("https://cloudflare-dns.com/")), "target never fetched");
});

// ---------------------------------------------------------------- redirects

const noBody = { follow: true, bodyLimit: () => 0 };

Deno.test("redirects: a hop to a private IP literal is refused before it is fetched", async () => {
  const m = mockFetch({ "https://example.co.za/": redirect("http://127.0.0.1:80/admin") });
  const ctx = makeCtx(m.fn, fakeDns(publicDns("example.co.za")).resolve);
  await assertRejectsType(() => guardedFetch("https://example.co.za/", ctx, noBody), "blocked_target");
  assertEquals(m.calls.map((c) => c.url), ["https://example.co.za/"]);
});
Deno.test("redirects: a hop to a name that resolves privately is refused before it is fetched", async () => {
  const m = mockFetch({ "https://example.co.za/": redirect("https://internal.example.co.za/") });
  const dns = fakeDns({ ...publicDns("example.co.za"), "internal.example.co.za": { A: ["10.1.2.3"] } });
  await assertRejectsType(() => guardedFetch("https://example.co.za/", makeCtx(m.fn, dns.resolve), noBody), "blocked_target");
  assertEquals(m.calls.length, 1);
});
Deno.test("redirects: other schemes, ports and metadata hosts are refused", async () => {
  for (
    const loc of [
      "ftp://example.co.za/",
      "file:///etc/passwd",
      "https://example.co.za:8443/",
      "http://169.254.169.254/",
      "http://[::ffff:169.254.169.254]/",
      "http://metadata.google.internal/",
      "http://localhost/",
    ]
  ) {
    const m = mockFetch({ "https://example.co.za/": redirect(loc) });
    const ctx = makeCtx(m.fn, fakeDns(publicDns("example.co.za")).resolve);
    await assertRejectsType(() => guardedFetch("https://example.co.za/", ctx, noBody), "blocked_target", loc);
    assertEquals(m.calls.length, 1, loc);
  }
});
Deno.test("redirects: five hops are followed, the sixth is refused", async () => {
  const routes: Record<string, () => Response> = {};
  for (let i = 0; i < 5; i++) routes[`https://example.co.za/${i}`] = redirect(`/${i + 1}`);
  routes["https://example.co.za/5"] = html("<p>done</p>");
  const m = mockFetch(routes);
  const r = await guardedFetch("https://example.co.za/0", makeCtx(m.fn, fakeDns(publicDns("example.co.za")).resolve), noBody);
  assertEquals(r.url, "https://example.co.za/5");
  assertEquals(m.calls.length, 6);

  routes["https://example.co.za/5"] = redirect("/6");
  routes["https://example.co.za/6"] = html("<p>too far</p>");
  const m2 = mockFetch(routes);
  await assertRejectsType(
    () => guardedFetch("https://example.co.za/0", makeCtx(m2.fn, fakeDns(publicDns("example.co.za")).resolve), noBody),
    "too_many_redirects",
  );
  assertEquals(m2.calls.length, 6);
});
Deno.test("redirects: every request is GET with manual redirects, a signal and no credentials", async () => {
  const m = mockFetch({
    "https://example.co.za/": redirect("https://admin:hunter2@www.example.co.za/next#x", 301),
    "https://www.example.co.za/next": html("<p>ok</p>"),
  });
  const ctx = makeCtx(m.fn, fakeDns(publicDns("example.co.za", "www.example.co.za")).resolve);
  const r = await guardedFetch("https://u:p@example.co.za/", ctx, noBody);
  assertEquals(r.url, "https://www.example.co.za/next");
  for (const c of m.calls) {
    assertEquals(c.init?.method, "GET");
    assertEquals(c.init?.redirect, "manual");
    assert(c.init?.signal instanceof AbortSignal);
    assert(!c.url.includes("@") && !c.url.includes("hunter2") && !c.url.includes("#"), c.url);
    assertEquals(c.init?.body, undefined);
  }
});
Deno.test("probes: http and security.txt probes go through the same guard", async () => {
  const m = mockFetch({
    "https://example.co.za/": html("<a href='/privacy'>Privacy</a><a href='/paia'>PAIA</a>"),
    "http://example.co.za/": redirect("http://10.0.0.1/"),
    "https://example.co.za/.well-known/security.txt": redirect("http://169.254.169.254/latest/meta-data/"),
  });
  const res = await runSiteCheck("https://example.co.za/", makeCtx(m.fn, fakeDns(publicDns("example.co.za")).resolve));
  assert(!m.calls.some((c) => c.url.includes("10.0.0.1") || c.url.includes("169.254")), "private hops never fetched");
  const ids = res.findings.map((f) => f.rule_id);
  assert(ids.includes("WEB-002"), "http probe that does not redirect to https is flagged");
  assert(ids.includes("WEB-018"), "security.txt probe failure reads as missing");
  assertEquals(m.calls.find((c) => c.url === "http://example.co.za/") !== undefined, true);
});

// ---------------------------------------------------------------- body limits and timeouts

function endless(chunk: number, counter: { pulled: number; cancelled: boolean }, prefix = "") {
  const enc = new TextEncoder();
  let first = true;
  return new ReadableStream<Uint8Array>({
    pull(c) {
      const s = first ? prefix + " ".repeat(Math.max(0, chunk - prefix.length)) : "<p>x</p>".repeat(chunk / 8);
      first = false;
      counter.pulled += chunk;
      c.enqueue(enc.encode(s));
    },
    cancel() {
      counter.cancelled = true;
    },
  }, { highWaterMark: 0 });
}

Deno.test("body: reads at most 1.5 MB of HTML, then cancels the stream", async () => {
  const counter = { pulled: 0, cancelled: false };
  const m = mockFetch({
    "https://example.co.za/": () =>
      new Response(endless(65_536, counter, "<a href='/privacy'>Privacy</a>"), { headers: { "content-type": "text/html" } }),
  });
  const res = await runSiteCheck("https://example.co.za/", makeCtx(m.fn, fakeDns(publicDns("example.co.za")).resolve));
  assert(counter.pulled <= LIMITS.maxBodyBytes + 65_536, `pulled ${counter.pulled}`);
  assert(counter.pulled >= LIMITS.maxBodyBytes, "read up to the cap");
  assert(counter.cancelled, "stream cancelled");
  assertEquals(res.notices.privacy, true);
});
Deno.test("body: non-HTML bodies are not read or parsed", async () => {
  const counter = { pulled: 0, cancelled: false };
  const m = mockFetch({
    "https://example.co.za/": () =>
      new Response(endless(65_536, counter, "<a href='/privacy'>Privacy</a>"), {
        headers: { "content-type": "application/json" },
      }),
  });
  const res = await runSiteCheck("https://example.co.za/", makeCtx(m.fn, fakeDns(publicDns("example.co.za")).resolve));
  assert(counter.pulled <= 65_536, `pulled ${counter.pulled}`);
  assert(counter.cancelled, "stream cancelled");
  assertEquals(res.notices.privacy, false);
});
Deno.test("body: readLimited trims the last chunk exactly", async () => {
  const s = new ReadableStream<Uint8Array>({
    start(c) {
      c.enqueue(new Uint8Array(10));
      c.enqueue(new Uint8Array(10));
      c.close();
    },
  });
  assertEquals((await readLimited(s, 15)).length, 15);
  assertEquals((await readLimited(null, 15)).length, 0);
});
Deno.test({
  name: "timeouts: a hanging site aborts on the per-request timeout",
  sanitizeOps: false,
  sanitizeResources: false,
  fn: async () => {
    const saved = LIMITS.perRequestMs;
    LIMITS.perRequestMs = 50;
    try {
      const hang = (_u: string, init?: RequestInit) =>
        new Promise<Response>((_, rej) => init?.signal?.addEventListener("abort", () => rej(init.signal!.reason)));
      const ctx = makeCtx(hang, fakeDns(publicDns("example.co.za")).resolve);
      const t0 = Date.now();
      let name = "";
      try {
        await guardedFetch("https://example.co.za/", ctx, noBody);
      } catch (e) {
        name = (e as Error).name;
      }
      assertEquals(name, "TimeoutError");
      assert(Date.now() - t0 < 2_000);
    } finally {
      LIMITS.perRequestMs = saved;
    }
  },
});
Deno.test({
  name: "timeouts: the overall budget signal aborts requests",
  sanitizeOps: false,
  sanitizeResources: false,
  fn: async () => {
    const ac = new AbortController();
    const hang = (_u: string, init?: RequestInit) =>
      new Promise<Response>((_, rej) => init?.signal?.addEventListener("abort", () => rej(init.signal!.reason)));
    const ctx = makeCtx(hang, fakeDns(publicDns("example.co.za")).resolve, ac.signal);
    setTimeout(() => ac.abort(new DOMException("budget", "TimeoutError")), 20);
    let name = "";
    try {
      await guardedFetch("https://example.co.za/", ctx, noBody);
    } catch (e) {
      name = (e as Error).name;
    }
    assertEquals(name, "TimeoutError");
  },
});
