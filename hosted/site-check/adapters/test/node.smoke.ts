// Node 20+ portability: core.ts under Node, the DNS pinned fetch and the Node rate limit adapter.
// Run from adapters/: npm install && npm test  (Node 22.18+ strips the types itself)
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createServer, type IncomingMessage, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { Agent, fetch as undiciFetch } from "undici";
import { createHandler, type DnsResolver, type FetchFn } from "../../supabase/functions/site-check/core.ts";
import { createPinnedFetch, guardedLookup, type LookupFn } from "../node-pinned-fetch.ts";
import { nodeSupabaseRateLimit } from "../node-supabase-rate-limit.ts";

const ORIGIN = "https://check.venusone.co.za";

function listen(handler: (req: IncomingMessage, body: string) => [number, string, Record<string, string>?]) {
  const hits: Array<{ url: string; body: string; headers: IncomingMessage["headers"] }> = [];
  const server: Server = createServer((req, res) => {
    let body = "";
    req.on("data", (c) => (body += c));
    req.on("end", () => {
      hits.push({ url: req.url ?? "", body, headers: req.headers });
      const [status, out, headers] = handler(req, body);
      res.writeHead(status, { "content-type": "application/json", ...headers });
      res.end(out);
    });
  });
  return new Promise<{ port: number; hits: typeof hits; close: () => Promise<void> }>((resolve) => {
    server.listen(0, "127.0.0.1", () => {
      const port = (server.address() as AddressInfo).port;
      resolve({ port, hits, close: () => new Promise((r) => server.close(() => r())) });
    });
  });
}

test("core.ts has no imports and no runtime specific globals", () => {
  const src = readFileSync(new URL("../../supabase/functions/site-check/core.ts", import.meta.url), "utf8");
  assert.doesNotMatch(src, /^\s*import\s/m, "no import statements");
  assert.doesNotMatch(src, /\bimport\s*\(/, "no dynamic import");
  for (const bad of ["npm:", "jsr:", "Deno.", "process.", "require(", "Buffer", "node:"]) {
    assert.ok(!src.includes(bad), `core.ts mentions ${bad}`);
  }
});

test("createHandler runs under Node with Node's Request, Response and Headers", async () => {
  const page = new Headers({ "content-type": "text/html" });
  page.append("set-cookie", "_ga=1");
  const routes: Record<string, () => Response> = {
    "https://example.co.za/": () => new Response(`<a href="/privacy">Privacy</a>`, { headers: page }),
  };
  const fetchFn: FetchFn = (url) => Promise.resolve(routes[url]?.() ?? new Response("x", { status: 404 }));
  const resolve: DnsResolver = (_n, type) =>
    Promise.resolve({ status: 0, answers: [{ type: type === "A" ? 1 : 28, data: type === "A" ? "41.0.0.1" : "2c0f:fb50::1" }] });
  const env: Record<string, string> = { ALLOWED_ORIGINS: ORIGIN, RATE_LIMIT_SALT: "s" };
  const keys: string[] = [];
  const handler = createHandler({
    fetch: fetchFn,
    env: (k) => env[k],
    rateLimit: (k) => (keys.push(k), Promise.resolve(true)),
    resolve,
  });
  const post = (url: string) =>
    new Request("https://h/f", {
      method: "POST",
      headers: { origin: ORIGIN, "content-type": "application/json", "x-forwarded-for": "6.6.6.6, 41.1.2.3" },
      body: JSON.stringify({ url }),
    });
  const res = await handler(post("example.co.za"));
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.deepEqual(Object.keys(body), [
    "url",
    "final_url",
    "checked_at",
    "summary",
    "findings",
    "cookies",
    "notices",
    "disclaimer",
  ]);
  assert.equal(body.notices.privacy, true);
  assert.deepEqual(body.cookies.map((c: { name: string }) => c.name), ["_ga"]);
  assert.equal(keys.length, 2, "per-IP and global");
  const blocked = await handler(post("http://169.254.169.254/latest/meta-data/"));
  assert.equal(blocked.status, 400);
  assert.deepEqual(await blocked.json(), { error: "This address cannot be checked.", type: "blocked_target" });
});

test("guardedLookup: refuses when any address is not public, passes public answers through", async () => {
  const fake = (addrs: Array<[string, number]>): LookupFn => (_h, _o, cb) =>
    cb(null, addrs.map(([address, family]) => ({ address, family })));
  const run = (base: LookupFn, options: unknown) =>
    new Promise<{ err: (Error & { code?: string }) | null; a: unknown; f?: number }>((r) =>
      guardedLookup(base)("x.example.co.za", options as never, (err, a, f) => r({ err: err as never, a, f }))
    );
  const ok = await run(fake([["41.0.0.1", 4], ["2c0f:fb50::1", 6]]), { all: true });
  assert.equal(ok.err, null);
  assert.deepEqual(ok.a, [{ address: "41.0.0.1", family: 4 }, { address: "2c0f:fb50::1", family: 6 }]);
  const single = await run(fake([["41.0.0.1", 4]]), {});
  assert.deepEqual([single.err, single.a, single.f], [null, "41.0.0.1", 4]);
  const legacy = await run(fake([["41.0.0.1", 4]]), 4);
  assert.deepEqual([legacy.err, legacy.a], [null, "41.0.0.1"]);
  for (
    const bad of [
      [["41.0.0.1", 4], ["10.0.0.1", 4]],
      [["127.0.0.1", 4]],
      [["::ffff:169.254.169.254", 6]],
      [["fd00:ec2::254", 6]],
      [],
    ] as Array<Array<[string, number]>>
  ) {
    const r = await run(fake(bad), { all: true });
    assert.equal(r.err?.code, "EADDRNOTALLOWED", JSON.stringify(bad));
  }
});

test("pinned fetch: a name that rebinds to loopback never reaches the socket", async () => {
  const srv = await listen(() => [200, "{}"]);
  try {
    // Simulates the rebinding answer: the DoH check saw a public address, the socket lookup sees loopback.
    const rebind: LookupFn = (_h, _o, cb) => cb(null, [{ address: "127.0.0.1", family: 4 }]);
    const url = `http://rebind.example.co.za:${srv.port}/`;

    // Control: an unguarded agent with the same lookup does connect.
    const open = new Agent({
      connect: {
        lookup: ((_h: string, o: { all?: boolean }, cb: (...a: unknown[]) => void) =>
          o?.all ? cb(null, [{ address: "127.0.0.1", family: 4 }]) : cb(null, "127.0.0.1", 4)) as never,
      },
    });
    const control = await undiciFetch(url, { dispatcher: open });
    assert.equal(control.status, 200);
    await control.text();
    assert.equal(srv.hits.length, 1);

    const pinned = createPinnedFetch(rebind);
    await assert.rejects(pinned(url, { redirect: "manual" }), (e: Error & { cause?: { code?: string } }) => {
      assert.equal(e.name, "TypeError");
      assert.equal(e.cause?.code, "EADDRNOTALLOWED");
      return true;
    });
    await assert.rejects(createPinnedFetch()(`http://localhost:${srv.port}/`), TypeError, "system resolver answer refused");
    await assert.rejects(createPinnedFetch()(`http://127.0.0.1:${srv.port}/`), TypeError, "IP literal refused");
    await assert.rejects(createPinnedFetch()(`http://[::1]:${srv.port}/`), TypeError, "IPv6 literal refused");
    assert.equal(srv.hits.length, 1, "guarded requests never arrived");
    await open.close();
  } finally {
    await srv.close();
  }
});

test("node rate limit adapter: supabase-js RPC wiring, false, errors and missing env", async () => {
  let reply: [number, string] = [200, "true"];
  const srv = await listen(() => reply);
  try {
    const env = (k: string) =>
      ({ SUPABASE_URL: `http://127.0.0.1:${srv.port}`, SUPABASE_SERVICE_ROLE_KEY: "srk" } as Record<string, string>)[k];
    const sig = new AbortController().signal;
    assert.equal(await nodeSupabaseRateLimit("a".repeat(64), 7, sig, env), true);
    assert.equal(srv.hits[0].url, "/rest/v1/rpc/site_check_hit");
    assert.deepEqual(JSON.parse(srv.hits[0].body), { p_ip_hash: "a".repeat(64), p_limit: 7 });
    assert.equal(srv.hits[0].headers.authorization, "Bearer srk");
    reply = [200, "false"];
    assert.equal(await nodeSupabaseRateLimit("a".repeat(64), 7, sig, env), false);
    reply = [500, JSON.stringify({ message: "boom" })];
    await assert.rejects(nodeSupabaseRateLimit("a".repeat(64), 7, sig, env));
    reply = [200, JSON.stringify("yes")];
    await assert.rejects(nodeSupabaseRateLimit("a".repeat(64), 7, sig, env), "non boolean answer throws");
    await assert.rejects(nodeSupabaseRateLimit("a".repeat(64), 7, sig, () => undefined), "missing env throws");
  } finally {
    await srv.close();
  }
});
