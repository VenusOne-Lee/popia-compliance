// Test helpers: tiny asserts, a mock fetch and a fake DNS resolver. No network.
import type { Ctx, DnsResolver, FetchFn } from "../supabase/functions/site-check/core.ts";
import { CheckError } from "../supabase/functions/site-check/core.ts";

export function assert(cond: unknown, msg = "assertion failed"): asserts cond {
  if (!cond) throw new Error(msg);
}
export function assertEquals<T>(actual: T, expected: T, msg = "") {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (a !== e) throw new Error(`${msg} expected ${e}, got ${a}`);
}
export async function assertRejectsType(fn: () => Promise<unknown>, type: string, msg = "") {
  try {
    await fn();
  } catch (e) {
    if (e instanceof CheckError && e.type === type) return;
    throw new Error(`${msg} expected CheckError(${type}), got ${e instanceof CheckError ? e.type : String(e)}`);
  }
  throw new Error(`${msg} expected CheckError(${type}), nothing thrown`);
}
export function assertThrowsType(fn: () => unknown, type: string, msg = "") {
  try {
    fn();
  } catch (e) {
    if (e instanceof CheckError && e.type === type) return;
    throw new Error(`${msg} expected CheckError(${type}), got ${e instanceof CheckError ? e.type : String(e)}`);
  }
  throw new Error(`${msg} expected CheckError(${type}), nothing thrown`);
}

export type Route = (url: string, init?: RequestInit) => Response | Promise<Response>;
export interface Call {
  url: string;
  init?: RequestInit;
}

/** Routes keyed by exact URL. Unknown URLs return 404 text/html. Records every call. */
export function mockFetch(routes: Record<string, Route>) {
  const calls: Call[] = [];
  const fn: FetchFn = async (url, init) => {
    calls.push({ url, init });
    if (init?.signal?.aborted) throw init.signal.reason;
    const r = routes[url];
    if (!r) return new Response("<html>not found</html>", { status: 404, headers: { "content-type": "text/html" } });
    return await r(url, init);
  };
  return { fn, calls };
}

export const html = (body: string, headers: Record<string, string> = {}, status = 200) => () =>
  new Response(body, { status, headers: { "content-type": "text/html; charset=utf-8", ...headers } });

export const redirect = (location: string, status = 302) => () => new Response(null, { status, headers: { location } });

export type DnsMap = Record<string, { A?: string[]; AAAA?: string[]; CNAME?: string; status?: number }>;

/** Fake resolver. Unknown names are NXDOMAIN. A CNAME entry is returned without addresses. */
export function fakeDns(map: DnsMap) {
  const queries: string[] = [];
  const resolve: DnsResolver = (name, type) => {
    queries.push(`${name}/${type}`);
    const e = map[name];
    if (!e) return Promise.resolve({ status: 3, answers: [] });
    const answers = [];
    if (e.CNAME) answers.push({ type: 5, data: e.CNAME + "." });
    for (const ip of (type === "A" ? e.A : e.AAAA) ?? []) answers.push({ type: type === "A" ? 1 : 28, data: ip });
    return Promise.resolve({ status: e.status ?? 0, answers });
  };
  return { resolve, queries };
}

export function makeCtx(fetchFn: FetchFn, resolve: DnsResolver, signal = new AbortController().signal): Ctx {
  return { fetch: fetchFn, resolve, signal, dnsCache: new Map() };
}

/** Public DNS for a set of hostnames. */
export function publicDns(...hosts: string[]): DnsMap {
  return Object.fromEntries(hosts.map((h) => [h, { A: ["203.0.114.10"], AAAA: ["2c0f:fb50:4002::10"] }]));
}

/** Stub every console method and return the number of calls made while `fn` runs. */
export async function countConsoleCalls(fn: () => Promise<void>): Promise<number> {
  const methods = ["log", "error", "warn", "info", "debug", "trace", "table", "dir"] as const;
  const saved = methods.map((m) => console[m]);
  let n = 0;
  for (const m of methods) (console as unknown as Record<string, unknown>)[m] = () => n++;
  try {
    await fn();
  } finally {
    methods.forEach((m, i) => ((console as unknown as Record<string, unknown>)[m] = saved[i]));
  }
  return n;
}
