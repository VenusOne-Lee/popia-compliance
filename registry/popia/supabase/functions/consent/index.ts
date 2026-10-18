// consent: record and read consent events (s11(2)(a) burden of proof, s69, s11(2)(b) withdrawal).
// Deno edge function. Engineering guidance, not legal advice.
//
// GET   returns the caller's current consent per purpose (from privacy.consent_current).
// POST  { purpose, action: "granted"|"withdrawn", wording, channel, notice_version?, source_url? }
//       or { events: [ ...same shape ] } for several at once.
//
// Identity comes from the JWT only. For visitors who are not signed in, use
// Supabase anonymous sign-ins so they also carry a JWT, then link the
// anonymous user to the real account on sign-up.
//
// The IP address is hashed with CONSENT_IP_SALT before storage. The raw IP is
// never stored or logged (s10 minimality, s19).
// The server computes notice_version from the wording hash when it is not supplied,
// so the record always pins the exact text.

import {
  adminClient,
  assertOrigin,
  clientIp,
  corsHeaders,
  env,
  errorResponse,
  HttpError,
  json,
  requireUser,
  sha256Hex,
} from "../_shared/privacy-config.ts";

const METHODS = "GET, POST, OPTIONS";
const PURPOSE_RE = /^[a-z0-9_]{1,100}$/;
const CHANNEL_RE = /^[a-z0-9_]{1,50}$/;

interface IncomingEvent {
  purpose?: unknown;
  action?: unknown;
  wording?: unknown;
  channel?: unknown;
  notice_version?: unknown;
  source_url?: unknown;
  competent_person_id?: unknown;
}

function str(v: unknown, max: number): string | null {
  return typeof v === "string" && v.length > 0 && v.length <= max ? v : null;
}

function cleanUrl(v: unknown): string | null {
  const s = str(v, 2000);
  if (!s) return null;
  try {
    const u = new URL(s);
    // Drop query and fragment: they often carry email addresses or tokens.
    return `${u.origin}${u.pathname}`;
  } catch {
    return null;
  }
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders(req, METHODS) });
  try {
    assertOrigin(req);
    const admin = adminClient();
    const user = await requireUser(req, admin);

    if (req.method === "GET") {
      const { data, error } = await admin
        .schema("privacy")
        .from("consent_current")
        .select("purpose, action, notice_version, channel, created_at")
        .eq("subject_id", user.id);
      if (error) throw new Error("consent_read_failed");
      return json(req, { current: data ?? [] }, 200, METHODS);
    }

    if (req.method !== "POST") throw new HttpError(405, "Use GET or POST.");

    let body: { events?: IncomingEvent[] } & IncomingEvent;
    try {
      body = await req.json();
    } catch {
      throw new HttpError(400, "Send a JSON body.");
    }
    const incoming: IncomingEvent[] = Array.isArray(body.events) ? body.events : [body];
    if (incoming.length === 0 || incoming.length > 20) throw new HttpError(400, "Send between 1 and 20 events.");

    const salt = env("CONSENT_IP_SALT");
    const ip = clientIp(req);
    const ipHash = ip ? await sha256Hex(`${salt}:${ip}`) : null;
    const ua = req.headers.get("User-Agent")?.slice(0, 500) ?? null;

    const rows = [];
    for (const e of incoming) {
      const purpose = str(e.purpose, 100);
      const channel = str(e.channel, 50) ?? "web_form";
      const wording = str(e.wording, 5000);
      if (!purpose || !PURPOSE_RE.test(purpose)) throw new HttpError(400, "Invalid purpose.");
      if (!CHANNEL_RE.test(channel)) throw new HttpError(400, "Invalid channel.");
      if (e.action !== "granted" && e.action !== "withdrawn") throw new HttpError(400, "Action must be granted or withdrawn.");
      if (!wording) throw new HttpError(400, "Include the exact wording shown.");
      const normalised = wording.replace(/\s+/g, " ").trim();
      const version = str(e.notice_version, 200) ?? `sha256:${(await sha256Hex(normalised)).slice(0, 12)}`;
      rows.push({
        subject_id: user.id, // from JWT, never from body
        purpose,
        action: e.action,
        notice_version: version,
        wording,
        channel,
        source_url: cleanUrl(e.source_url),
        ip_hash: ipHash,
        user_agent: ua,
        competent_person_id: typeof e.competent_person_id === "string" ? e.competent_person_id : null,
      });
    }

    const { error } = await admin.schema("privacy").from("consent_events").insert(rows);
    if (error) throw new Error("consent_insert_failed");
    return json(req, { recorded: rows.length }, 201, METHODS);
  } catch (err) {
    return errorResponse(req, err, METHODS);
  }
});
