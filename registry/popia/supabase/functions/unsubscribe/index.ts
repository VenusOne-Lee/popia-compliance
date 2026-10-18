// unsubscribe: one-click marketing opt-out (s69(4), s11(3)(b), s11(2)(b)).
// Deno edge function. Engineering guidance, not legal advice.
//
// Every marketing message must give the recipient a way to stop it (s69(4)).
// Withdrawal must be as easy as giving consent: no login wall.
//
// Deploy without JWT verification, because the person is not signed in:
//   supabase functions deploy unsubscribe --no-verify-jwt
// The HMAC-signed token is the authorisation. Secret: UNSUBSCRIBE_SECRET.
//
// Endpoints:
//   GET  ?t=<token>   Validates the token and returns { valid, purposes }. Does NOT
//                     unsubscribe, because mail scanners prefetch links. Your app's
//                     /unsubscribe page calls this, shows a single "Unsubscribe"
//                     button, and POSTs.
//   POST ?t=<token>   Unsubscribes. Accepts RFC 8058 one-click bodies
//                     ("List-Unsubscribe=One-Click", form-encoded) sent by mail
//                     providers, and JSON or empty bodies from your page.
//
// Email headers to send with every marketing email:
//   List-Unsubscribe: <https://<project>.supabase.co/functions/v1/unsubscribe?t=TOKEN>, <mailto:privacy@example.co.za?subject=unsubscribe>
//   List-Unsubscribe-Post: List-Unsubscribe=One-Click
//
// Make tokens on your server with signUnsubscribeToken() from _shared/privacy-config.ts.
// Put only a subject id and purposes in the token, never an email address.
//
// After this runs, suppress the person in every tool that sends marketing
// (email platform, SMS, WhatsApp, dialler) promptly (DM-07). Check
// privacy.consent_current at send time.

import {
  MARKETING_PURPOSES,
  adminClient,
  clientIp,
  env,
  HttpError,
  sha256Hex,
  verifyUnsubscribeToken,
} from "../_shared/privacy-config.ts";

const WORDING = "Unsubscribe from marketing.";

function respond(body: unknown, status = 200): Response {
  // Mail providers and your own page may call from any origin. The token
  // carries the authority, so a permissive CORS header is acceptable here
  // and avoids breaking the one-click flow. No cookies or credentials are used.
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "content-type",
      "Referrer-Policy": "no-referrer",
    },
  });
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return respond(null, 204);
  try {
    const url = new URL(req.url);
    let token = url.searchParams.get("t") ?? "";
    const secret = env("UNSUBSCRIBE_SECRET");

    if (req.method === "GET") {
      const payload = token ? await verifyUnsubscribeToken(token, secret) : null;
      if (!payload) return respond({ valid: false }, 400);
      return respond({ valid: true, purposes: payload.p.length ? payload.p : MARKETING_PURPOSES });
    }

    if (req.method !== "POST") throw new HttpError(405, "Use GET or POST.");

    // Read the body once. One-click posts are form-encoded (RFC 8058).
    const contentType = req.headers.get("Content-Type") ?? "";
    let channel = "unsubscribe_link";
    try {
      if (contentType.includes("application/x-www-form-urlencoded") || contentType.includes("multipart/form-data")) {
        const form = await req.formData();
        if (form.get("List-Unsubscribe") === "One-Click") channel = "list_unsubscribe_one_click";
        const t = form.get("t");
        if (!token && typeof t === "string") token = t;
      } else if (contentType.includes("application/json")) {
        const body = (await req.json()) as { t?: unknown };
        if (!token && typeof body.t === "string") token = body.t;
      }
    } catch {
      // Empty or malformed body. The token in the query string is enough.
    }

    const payload = token ? await verifyUnsubscribeToken(token, secret) : null;
    if (!payload) return respond({ error: "This unsubscribe link is not valid. Contact us and we will remove you." }, 400);

    const purposes = payload.p.length ? payload.p.filter((p) => /^[a-z0-9_]{1,100}$/.test(p)) : MARKETING_PURPOSES;

    const salt = Deno.env.get("CONSENT_IP_SALT") ?? "";
    const ip = clientIp(req);
    const ipHash = ip && salt ? await sha256Hex(`${salt}:${ip}`) : null;
    const notice = `sha256:${(await sha256Hex(WORDING)).slice(0, 12)}`;

    const admin = adminClient();
    const { error } = await admin
      .schema("privacy")
      .from("consent_events")
      .insert(
        purposes.map((purpose) => ({
          subject_id: payload.s,
          purpose,
          action: "withdrawn",
          notice_version: notice,
          wording: WORDING,
          channel,
          ip_hash: ipHash,
          user_agent: req.headers.get("User-Agent")?.slice(0, 500) ?? null,
        })),
      );
    if (error) throw new Error("unsubscribe_insert_failed");

    // Repeat clicks simply add another withdrawn event. That is harmless.
    return respond({ unsubscribed: true, purposes });
  } catch (err) {
    if (err instanceof HttpError) return respond({ error: err.message }, err.status);
    console.error("unsubscribe error", err instanceof Error ? err.name : typeof err);
    return respond({ error: "Something went wrong. Contact us and we will remove you." }, 500);
  }
});

