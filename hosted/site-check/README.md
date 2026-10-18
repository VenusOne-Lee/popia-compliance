# POPIA site check, Supabase Edge Function

A public endpoint where anyone can paste a URL and get a passive POPIA and security check of the site.
It is a port of `popia-compliance/scripts/site_check.py` (v1.0.1), hardened for untrusted input.

Passive only. The function makes ordinary GET requests. It never submits forms, never authenticates and never probes for vulnerabilities.

Results are leads for review, not legal conclusions. Engineering guidance only, not legal advice.

## Files

| Path | What it is |
|---|---|
| `supabase/functions/site-check/core.ts` | All logic, runtime agnostic. No imports, no `Deno` or Node globals, only Web APIs. Exports `createHandler`. |
| `supabase/functions/site-check/index.ts` | Thin Deno entry for Supabase. Imports `npm:@supabase/supabase-js@2` for the rate limit RPC and starts `Deno.serve`. |
| `adapters/node-supabase-rate-limit.ts` | The same rate limit RPC for Node 20.3+ hosts (TanStack Start and similar), with a bare `@supabase/supabase-js` import. |
| `adapters/node-pinned-fetch.ts` | A fetch for Node that checks the address of every socket it opens. Closes the DNS rebinding window on Node. Needs `undici`. |
| `adapters/package.json`, `adapters/deno.json` | Node dev dependencies and a type check config for the adapters. Kept out of the repo root on purpose, see Node below. |
| `adapters/test/node.smoke.ts` | Node tests: core under Node, the pinned fetch against a real socket, the Node rate limit adapter. |
| `supabase/migrations/site_check_rate.sql` | Rate limit table and the `site_check_hit` function. |
| `tests/guard.test.ts` | IP, hostname, URL, DNS, redirect, timeout and body cap tests. |
| `tests/checks.test.ts` | Finding logic, including the cases from the Python tests. |
| `tests/handler.test.ts` | CORS, Turnstile, rate limiting, error hygiene, no logging, copy rules. |
| `report/actions.json` | Proposed actions for each finding, the title of each cited section of the Act, and the copy for a downloadable report. `tests/actions.test.ts` checks it covers every rule. |
| `tests/hardening.test.ts` | Client IP selection, the global cap, regex cost bounds, slow bodies, the hard overall budget, more host notations. |
| `tests/helpers.ts` | Mock fetch, fake DNS resolver, small asserts. |
| `tests/sql/run_sql_tests.sh` | Applies the migration to a throwaway local Postgres and tests it. |
| `deno.json` | Tasks for test, check and lint. |

## API

`POST /functions/v1/site-check` with `content-type: application/json`.

```json
{ "url": "https://example.co.za", "turnstileToken": "<token from the widget>" }
```

A URL without a scheme gets `https://`. A successful response is HTTP 200:

```json
{
  "url": "https://example.co.za/",
  "final_url": "https://www.example.co.za/",
  "checked_at": "2026-10-18T09:00:00+00:00",
  "summary": { "critical": 0, "high": 1, "medium": 2, "low": 3, "info": 1 },
  "findings": [
    { "rule_id": "WEB-015", "title": "No privacy notice link found", "severity": "high", "popia": "s18",
      "evidence": "No link or common path", "fix": "Publish a privacy notice and link it in the footer and next to every form." }
  ],
  "cookies": [ { "name": "_ga", "secure": false, "httponly": false, "samesite": null, "tracking": true } ],
  "notices": { "privacy": false, "paia": true, "cookie": false, "information_officer": false },
  "disclaimer": "Passive automated check of initial HTML and headers. Leads for review, not legal conclusions. Engineering guidance only, not legal advice."
}
```

Errors return only a generic message and a type, for example `{"error": "This address cannot be checked.", "type": "blocked_target"}`.

| Status | type |
|---|---|
| 400 | `invalid_request`, `invalid_url`, `blocked_target` |
| 403 | `origin_not_allowed`, `turnstile_failed` |
| 405 | `method_not_allowed` |
| 429 | `rate_limited` (per-IP limit, global cap, or the rate limit backend failing) |
| 502 | `dns_failed`, `fetch_failed`, `too_many_redirects` |
| 504 | `timeout` |
| 500 | `internal_error` |

Finding IDs WEB-001 to WEB-021, titles, severities and POPIA sections are the same as in `site_check.py`.

## Environment variables

| Name | Required | Default | Purpose |
|---|---|---|---|
| `ALLOWED_ORIGINS` | yes | none | Comma separated list of exact origins, for example `https://venusone.co.za,https://www.venusone.co.za`. Requests without an allowed `Origin` get 403. Empty means everything is refused. |
| `RATE_LIMIT_SALT` | yes | none | Secret salt for hashing client IPs. Use 32 or more random bytes. If missing, every request gets 429. |
| `RATE_LIMIT_PER_HOUR` | no | `10` | Checks per client IP bucket per hour. |
| `GLOBAL_LIMIT_PER_HOUR` | no | `300` | Checks per hour for all clients together. Checked after the per-IP limit, through the same `site_check_hit` function with a fixed salted key. Fails closed. |
| `TURNSTILE_SECRET` | recommended | unset | Cloudflare Turnstile secret key. When set, a valid `turnstileToken` is required before anything else happens. |
| `SUPABASE_URL` | yes | injected | Provided to hosted Edge Functions by Supabase. |
| `SUPABASE_SERVICE_ROLE_KEY` | yes | injected | Provided by Supabase. Used only to call `site_check_hit`. |
| `PROBE_NOTICE_PATHS` | no | `false` | Set to `true` to also request `/privacy`, `/paia`, `/cookies` and five similar paths, like the Python tool does. Adds up to 8 GETs per check. |
| `CLIENT_IP_HEADER` | no | unset | Header that carries the client IP. Unset means the first present of `cf-connecting-ip`, `x-real-ip`, then the last `x-forwarded-for` entry. When set, only that header is read. In any comma separated value the last entry is used, never the first. Ports are stripped. See residual risks. |
| `SITE_CHECK_DISABLE_SERVE` | tests only | unset | Set to `1` so importing the module does not start a server. |

## Deploy

1. Apply the migration. The Supabase CLI only picks up files named `<timestamp>_<name>.sql`, so copy it first:

   ```sh
   cp supabase/migrations/site_check_rate.sql supabase/migrations/20261018000000_site_check_rate.sql
   supabase link --project-ref <ref>
   supabase db push
   ```

   Or paste the file into the SQL editor. It must run as `postgres` (or another role with BYPASSRLS). It stops with a clear error otherwise.

2. Set secrets:

   ```sh
   supabase secrets set ALLOWED_ORIGINS="https://venusone.co.za,https://www.venusone.co.za" \
     RATE_LIMIT_SALT="$(openssl rand -hex 32)" RATE_LIMIT_PER_HOUR=10 GLOBAL_LIMIT_PER_HOUR=300 \
     TURNSTILE_SECRET="<secret>"
   ```

3. Deploy:

   ```sh
   supabase functions deploy site-check --no-verify-jwt
   ```

   `--no-verify-jwt` is the simple option for a public tool. The anon or publishable key is public anyway, so JWT verification adds no real protection here. Turnstile and the rate limit are the gates. If you keep JWT verification on, send the anon key as `Authorization: Bearer` and `apikey`. The allowed CORS headers already include both.

4. Front end. Add the Turnstile widget, then:

   ```js
   const res = await fetch("https://<ref>.supabase.co/functions/v1/site-check", {
     method: "POST",
     headers: { "content-type": "application/json" },
     body: JSON.stringify({ url, turnstileToken }),
   });
   ```

   Render every field as text (`textContent`), never as HTML. Evidence, cookie names and header values come from the scanned site and can contain markup.

5. Try it:

   ```sh
   curl -s -X POST https://<ref>.supabase.co/functions/v1/site-check \
     -H 'origin: https://venusone.co.za' -H 'content-type: application/json' \
     -d '{"url":"example.co.za","turnstileToken":"<token>"}'
   ```

## Node (TanStack Start and other Node 20.3+ hosts)

`core.ts` has no imports and uses only Web APIs, so a Node server route can use it directly. Copy `core.ts` and the two adapters into your app, add `@supabase/supabase-js` and `undici` to its dependencies, and wire it in server only code:

```ts
import { createHandler } from "./site-check/core.ts";
import { nodeSupabaseRateLimit } from "./site-check/adapters/node-supabase-rate-limit.ts";
import { pinnedFetch } from "./site-check/adapters/node-pinned-fetch.ts";

const handler = createHandler({ fetch: pinnedFetch, env: (k) => process.env[k], rateLimit: nodeSupabaseRateLimit });

// In your server route for POST and OPTIONS, hand over the Fetch API Request:
//   return handler(request);
```

Use `pinnedFetch`, not the global `fetch`. It is what closes the DNS rebinding window on Node (residual risk 1). Keep the service role key and these imports out of anything bundled for the browser.

The Node files live in `adapters/` with their own `package.json` on purpose. A `package.json` at the repo root makes Deno resolve `npm:` imports from `node_modules`, which breaks the Edge Function wherever `node_modules` is not installed.

## Tests

```sh
deno task test             # 100 unit tests, no network
deno task test:sql         # 27 migration tests on a throwaway local Postgres 14+ cluster
deno task test:node        # 5 Node tests (npm install in adapters/, then node --test; Node 22.18+ to run .ts directly)
deno task check            # type check the function and the Deno tests
deno task check:adapters   # type check the Node adapters (after npm install in adapters/)
deno task lint
```

Network calls are injected. `createHandler({ fetch, env, rateLimit, resolve })` takes a fetch function, an env getter, a rate limit function and an optional DNS resolver. The default resolver is DNS over HTTPS through the injected fetch.

## How the guard works

Every request the function makes to the target goes through one guarded fetch. That covers the main page, every redirect hop, the `http://` redirect probe, `/.well-known/security.txt` and the optional notice paths.

For every hop:

1. Parse with the WHATWG URL parser. It normalises tricks like `http://2130706433/`, `http://0x7f.1/` and `http://127.1/` into dotted quads, so they are caught.
2. Allow only `http` and `https`, and only ports 80 and 443 or none.
3. Drop `user:pass@` and the fragment.
4. IP literal hosts must be public unicast. IPv6 must be in `2000::/3` and outside the documentation, Teredo, IETF and 6to4-of-private ranges. IPv4-mapped and NAT64 addresses are judged by the embedded IPv4 address.
5. Refuse `localhost`, `*.localhost`, `*.local`, `*.internal`, `*.lan`, `*.home.arpa` and single-label names. Also `*.arpa`, `*.localdomain`, `*.test`, `*.invalid`, `*.example`, `*.onion` and numeric TLDs.
6. Resolve A and AAAA with Cloudflare DNS over HTTPS. Refuse if any answer is private, loopback, link-local (including 169.254.169.254), CGNAT, multicast, reserved, unspecified, unique-local, documentation, the Azure WireServer address 168.63.129.16, or a mapped form of those. CNAME targets must pass the hostname rules too. A CNAME with no addresses is resolved again, up to 8 levels. SERVFAIL or no addresses fails closed.
7. Fetch with `redirect: "manual"`, 8 s per request and a 20 s overall budget. Follow at most 5 redirects, repeating steps 1 to 6 for each.
8. Read at most 1.5 MB, streaming, then cancel. Only `text/html` bodies on 2xx responses are parsed. `security.txt` is read only when it is `text/plain`, up to 32 KB. The read itself honours the per-request timeout, so a body that trickles forever is cut off even if the fetch implementation ignores its signal. The cap applies to decompressed bytes.
9. On Node with `pinnedFetch`, the socket lookup is checked as well: every address the system resolver returns must be public, and the socket connects only to those.

Around the checks:

- The JSON request body must arrive within 5 s and declare at most 8 KB. The 20 s overall budget is hard: the handler answers 504 at the deadline even if an injected dependency hangs.
- Report URLs keep at most 512 path characters. A token cut at that boundary is dropped, not shortened, so a partial secret cannot slip past the redaction rules. This also bounds the cost of the redaction regexes on hostile input (a 1.4 MB script `src` or a long `Location`).
- WEB-009 scans at most 256 characters of `server` and `x-powered-by`, and WEB-012 stops building evidence after 20 findings.

The function never logs. It does not store the URL, the response or the findings. The only stored data is a salted SHA-256 of the client IP bucket, a window start and a count. Rows older than 2 hours are deleted on every call.

## Downloadable report

`report/actions.json` turns a result into a report people can act on. Build the report in the visitor's browser from the API response and this file. Nothing is sent or stored.

- Group findings into the three `bands` by severity, and show each finding's `why`, `actions` and `kit` link.
- List the findings again by section of the Act, using `sections` for the titles.
- Include `covers`, `not_covered` and `disclaimer` as written.
- Render every value from the API as text. Never make a URL from the scanned site clickable in the report.
- Name the file with the checked host and date, for example `popia-site-check-example.co.za-2026-10-18.pdf`.

## Residual risks

These are real and worth knowing before you put the endpoint on the open internet.

1. **DNS rebinding window on Deno.** The DoH check and the runtime's own DNS lookup inside `fetch` are separate. A hostile name with a very short TTL could answer DoH with a public address and the runtime with a private one. If that works, parts of the internal response (headers, cookie names, some HTML) come back in the findings. Per-hop checks narrow this but cannot close it on Deno, because Deno's `fetch` cannot be pinned to a resolved IP without a custom TLS client. The remaining exposure depends on what the hosted edge runtime can reach. Supabase runs Edge Functions on shared infrastructure outside your database network, so there should be little private to reach. That is a property of the platform, not of this code, and it has not been verified here. Treat it as a mitigation, not a guarantee. On Node, `adapters/node-pinned-fetch.ts` closes this window. Use it, because a Node server often sits inside a VPC with plenty to reach.
2. **Split-horizon DNS.** Cloudflare's public answer can differ from the runtime's resolver. Names that only resolve internally fail at the DoH step. Public names with a different internal answer get the same mitigation and caveat as point 1, and `pinnedFetch` closes it on Node.
3. **Client IP trust.** With no `CLIENT_IP_HEADER`, the rate limit keys on `cf-connecting-ip`, then `x-real-ip`, then the last `x-forwarded-for` entry. Each is only as good as the proxy in front: `cf-connecting-ip` and `x-real-ip` are safe only if your edge overwrites them, otherwise a client can send its own and rotate it. The last `x-forwarded-for` entry cannot be forged by the client, but behind two proxies it can be the outer proxy's address, which puts everyone in one bucket. Check what your project receives, then set `CLIENT_IP_HEADER` to the one header your platform guarantees. Turnstile is the stronger control, so keep `TURNSTILE_SECRET` set. IPv6 clients are bucketed per /64, so a client with a /48 has many buckets. Requests with no usable IP share one `unknown` bucket.
4. **The global cap cuts both ways.** `GLOBAL_LIMIT_PER_HOUR` bounds the outbound traffic and cost that many IPs, or a bypass of point 3, can drive. It also means one determined client with many addresses can use up the hour for everyone. Each check sends 2 or 3 requests to the target (10 or 11 with notice probes), each with up to 5 redirects. Each new IP bucket also adds a table row until the 2 hour prune. Function invocations themselves are not capped by this, so keep a Supabase spend alert.
5. **Turnstile is optional.** Without `TURNSTILE_SECRET`, the only gates are the two rate limits. Set it for a public deployment. The siteverify answer's `hostname` is not compared to your domain; restrict the widget's domains in the Cloudflare dashboard instead.
6. **Origin is not authentication.** The allowlist stops other websites from calling the endpoint from a visitor's browser. Scripts can send any `Origin` header, so Turnstile and the rate limits are the real gates.
7. **The function makes requests on your behalf.** Target sites see Supabase egress addresses and the user agent `popia-site-check/1.0`. Someone could point it at a site they do not own. The requests are ordinary GETs, at low volume, but the abuse report would come to you. Say on the page that people should only check sites they own or are allowed to assess.
8. **Third parties.** Cloudflare sees the hostnames resolved through DoH and the Turnstile tokens. The client IP is not sent to Turnstile.
9. **Salted IP hashes.** IPv4 space is small. Anyone with the table and the salt can recover IPs by brute force. Keep the salt secret. Rows are pruned after 2 hours. The table is not readable by `anon`, `authenticated` or `service_role`.
10. **Platform logs.** The function writes no logs. The Supabase gateway still records request metadata such as time, path, status and possibly IP. The submitted URL is in the POST body, so it does not appear in path logs.
11. **Content from the target.** Evidence strings, header values, cookie names and input names come from the scanned site. They are capped in length but not escaped. Render them as text.
12. **Parser differences.** The HTML tokenizer is a small linear scanner that mirrors Python's `html.parser` on the cases the checks use. It is not a full HTML5 parser. Odd markup can be read differently from a browser.
13. **Passive limits.** Only the initial HTML and headers are seen. Single-page apps render links, banners and some trackers in JavaScript, so notice and banner findings need a manual check in a browser with a clean profile. Sites with broken TLS return `fetch_failed` instead of a finding.

## Differences from site_check.py

- Private targets are always blocked, with a stricter check than Python's `--block-private` (DoH, CNAME targets, CGNAT, NAT64, 6to4, documentation ranges, more blocked names). Ports other than 80 and 443 are refused.
- The 8 notice path probes are off by default. Turn them on with `PROBE_NOTICE_PATHS=true`. Without them, WEB-015, WEB-016 and WEB-017 rely on links in the initial HTML.
- The response has only the fields listed in the API section. `tool`, `version`, `status`, `spa_suspected`, `trackers`, `third_party_script_hosts`, `consent_tool`, `consent_mode_default` and `probed_paths` are dropped. Trackers are still listed as WEB-014 findings. There is no Markdown output.
- Only `text/html` bodies are parsed, capped at 1.5 MB (Python read 2,000,000 bytes of any type).
- Cookies are parsed with browser rules (RFC 6265) instead of `SimpleCookie`. Results match on the Python test cases.
- `max-age` in HSTS and `http://` in script sources are matched case-insensitively.
- At most 20 findings per rule, 50 cookies and 300 characters of evidence.
- The migration file needs a timestamp prefix for `supabase db push`.
