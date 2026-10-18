// DNS pinned fetch for Node 20+ hosts. Closes the DNS rebinding window that remains on Deno.
//
// core.ts checks every hostname with DNS over HTTPS before each request, but the runtime's fetch
// then resolves the name again on its own. A hostile name can answer the first lookup with a
// public address and the second with a private one. Here the connection itself is guarded: every
// address the system resolver returns for the socket is checked with isPublicIp, and the socket
// connects only to those checked addresses. TLS still verifies the certificate for the hostname.
//
// Use it as the `fetch` passed to createHandler. It is also used for the DoH and Turnstile calls,
// which are public hosts and pass the same check.
//
// Server only. Needs the `undici` package (Node's built-in fetch does not accept a custom lookup).

import { lookup as dnsLookup, type LookupAddress } from "node:dns";
import { Agent, fetch as undiciFetch } from "undici";
import { type FetchFn, isPublicIp } from "../supabase/functions/site-check/core.ts";

type LookupCallback = (err: Error | null, address: string | LookupAddress[], family?: number) => void;
type LookupOptions = { family?: number | string; all?: boolean; hints?: number; verbatim?: boolean };
export type LookupFn = (
  hostname: string,
  options: LookupOptions,
  callback: (err: Error | null, addresses: LookupAddress[]) => void,
) => void;

const systemLookup: LookupFn = (hostname, options, callback) =>
  dnsLookup(hostname, { ...options, all: true } as never, callback as never);

/** A net.connect lookup that refuses the connection if ANY resolved address is not public unicast. */
export function guardedLookup(base: LookupFn = systemLookup) {
  return (hostname: string, options: LookupOptions | number | LookupCallback, callback?: LookupCallback): void => {
    let opts: LookupOptions = {};
    let cb = callback as LookupCallback;
    if (typeof options === "function") cb = options;
    else if (typeof options === "number") opts = { family: options };
    else if (options) opts = options;
    base(hostname, { ...opts, all: true }, (err, addresses) => {
      if (err) return cb(err, []);
      const list = Array.isArray(addresses) ? addresses : [];
      if (!list.length || list.some((a) => !isPublicIp(a.address))) {
        return cb(Object.assign(new Error("address not allowed"), { code: "EADDRNOTALLOWED" }), []);
      }
      if (opts.all) return cb(null, list);
      cb(null, list[0].address, list[0].family);
    });
  };
}

/** A fetch whose sockets only ever connect to public addresses. */
export function createPinnedFetch(base?: LookupFn): FetchFn {
  const agent = new Agent({ connect: { lookup: guardedLookup(base) as never } });
  return (input, init) => {
    // IP literal hosts skip the lookup inside net.connect, so check them here.
    const host = new URL(input).hostname;
    if (/^[\d.]+$/.test(host) || host.startsWith("[")) {
      if (!isPublicIp(host)) return Promise.reject(new TypeError("fetch failed"));
    }
    return undiciFetch(input, { ...(init as object), dispatcher: agent }) as unknown as Promise<Response>;
  };
}

export const pinnedFetch: FetchFn = createPinnedFetch();
