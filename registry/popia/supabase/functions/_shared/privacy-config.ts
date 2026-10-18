// Shared configuration and helpers for the POPIA edge functions.
// Deno (Supabase Edge Runtime). Engineering guidance, not legal advice.
//
// Edit PRIVACY_TABLES to describe where each user's personal information lives.
// Keep it in step with privacy.data_inventory (s17).

import { createClient, type SupabaseClient, type User } from "npm:@supabase/supabase-js@2.45.4";

export type DeletionStrategy =
  /** Delete matching rows. */
  | { mode: "delete" }
  /** Null or overwrite the listed columns and keep the row (s14(4) de-identify). */
  | { mode: "deidentify"; columns: Record<string, null | string>; markColumn?: string }
  /** Keep the row because a law requires it, but strip non-required columns (s14(6) restrict). */
  | { mode: "retain"; reason: string; columns?: Record<string, null | string> };

export interface PrivacyTable {
  /** Schema name, usually "public". */
  schema: string;
  table: string;
  /** Column that holds the auth user id. */
  userColumn: string;
  /** Columns to include in a "download my data" export (s23). Use ["*"] for all. */
  exportColumns: string[];
  /** What dsar-delete does with this table (s24, s14). */
  onDelete: DeletionStrategy;
}

/**
 * EXAMPLE CONFIG. Replace with your own tables before deploying.
 * Order matters for deletion: children before parents if you have foreign keys.
 */
export const PRIVACY_TABLES: PrivacyTable[] = [
  {
    schema: "public",
    table: "profiles",
    userColumn: "id",
    exportColumns: ["*"],
    onDelete: {
      mode: "deidentify",
      columns: { full_name: null, email: null, phone: null, avatar_url: null },
      markColumn: "deidentified_at",
    },
  },
  {
    schema: "public",
    table: "orders",
    userColumn: "user_id",
    exportColumns: ["id", "created_at", "total", "status"],
    // Tax records: commonly kept 5 years (Tax Administration Act). VERIFY for your sector.
    onDelete: {
      mode: "retain",
      reason: "Tax record retention",
      columns: { shipping_address: null, phone: null, notes: null },
    },
  },
  {
    schema: "public",
    table: "support_messages",
    userColumn: "user_id",
    exportColumns: ["*"],
    onDelete: { mode: "delete" },
  },
];

/** Storage buckets whose objects live under a "<user_id>/" prefix. */
export const PRIVACY_BUCKETS: string[] = [
  // "avatars",
  // "documents",
];

/** Delete the auth user after de-identifying their data. */
export const DELETE_AUTH_USER = true;

// ---------------------------------------------------------------------------
// Environment
// ---------------------------------------------------------------------------

export function env(name: string, required = true): string {
  const v = Deno.env.get(name) ?? "";
  if (required && !v) throw new Error(`Missing environment variable ${name}`);
  return v;
}

/** Service-role client. Server only. Never expose this key to the browser (s19). */
export function adminClient(): SupabaseClient {
  return createClient(env("SUPABASE_URL"), env("SUPABASE_SERVICE_ROLE_KEY"), {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

// ---------------------------------------------------------------------------
// Identity: always from the JWT, never from the request body
// ---------------------------------------------------------------------------

export async function requireUser(req: Request, admin: SupabaseClient): Promise<User> {
  const header = req.headers.get("Authorization") ?? "";
  const jwt = header.startsWith("Bearer ") ? header.slice(7) : "";
  if (!jwt) throw new HttpError(401, "Sign in to continue.");
  const { data, error } = await admin.auth.getUser(jwt);
  if (error || !data?.user) throw new HttpError(401, "Your session has expired. Sign in again.");
  return data.user;
}

// ---------------------------------------------------------------------------
// CORS allow-list from ALLOWED_ORIGINS (comma-separated)
// ---------------------------------------------------------------------------

function allowedOrigins(): string[] {
  return (Deno.env.get("ALLOWED_ORIGINS") ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function corsHeaders(req: Request, methods = "POST, OPTIONS"): Record<string, string> {
  const origin = req.headers.get("Origin") ?? "";
  const headers: Record<string, string> = {
    "Access-Control-Allow-Methods": methods,
    "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
    "Access-Control-Max-Age": "600",
    Vary: "Origin",
  };
  if (origin && allowedOrigins().includes(origin)) {
    headers["Access-Control-Allow-Origin"] = origin;
  }
  return headers;
}

/** Reject browser requests from origins not on the allow-list. Server-to-server calls have no Origin. */
export function assertOrigin(req: Request): void {
  const origin = req.headers.get("Origin");
  if (origin && !allowedOrigins().includes(origin)) {
    throw new HttpError(403, "Origin not allowed.");
  }
}

// ---------------------------------------------------------------------------
// Responses and errors
// ---------------------------------------------------------------------------

export class HttpError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export function json(req: Request, body: unknown, status = 200, methods?: string): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      ...corsHeaders(req, methods),
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}

/** Map an error to a response without leaking internals or personal information. */
export function errorResponse(req: Request, err: unknown, methods?: string): Response {
  if (err instanceof HttpError) return json(req, { error: err.message }, err.status, methods);
  // Log the error type only. Never log request bodies, emails or tokens (s19).
  console.error("privacy function error", err instanceof Error ? err.name : typeof err);
  return json(req, { error: "Something went wrong. Try again later." }, 500, methods);
}

// ---------------------------------------------------------------------------
// Crypto helpers
// ---------------------------------------------------------------------------

const enc = new TextEncoder();

export function toHex(buf: ArrayBuffer): string {
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export async function sha256Hex(input: string): Promise<string> {
  return toHex(await crypto.subtle.digest("SHA-256", enc.encode(input)));
}

export async function hmacKey(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]);
}

export function base64UrlEncode(bytes: Uint8Array): string {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function base64UrlDecode(input: string): Uint8Array {
  const pad = input.length % 4 === 0 ? "" : "=".repeat(4 - (input.length % 4));
  const b64 = input.replace(/-/g, "+").replace(/_/g, "/") + pad;
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

// ---------------------------------------------------------------------------
// Unsubscribe tokens (s69(4), s11(3)(b))
// ---------------------------------------------------------------------------
// Format: base64url(JSON payload) + "." + base64url(HMAC-SHA256(payload)).
// No expiry by default: an unsubscribe link must keep working.
// Put only the subject id and purposes in the payload, never an email address.

export interface UnsubscribePayload {
  /** Subject id (auth user id or lead id). */
  s: string;
  /** Purposes to withdraw, for example ["marketing_email"]. Empty means all marketing. */
  p: string[];
  /** Issued at, seconds since epoch. */
  iat: number;
}

export const MARKETING_PURPOSES = ["marketing_email", "marketing_sms", "marketing_whatsapp", "marketing_phone"];

export async function signUnsubscribeToken(payload: Omit<UnsubscribePayload, "iat">, secret: string): Promise<string> {
  const full: UnsubscribePayload = { ...payload, iat: Math.floor(Date.now() / 1000) };
  const body = base64UrlEncode(enc.encode(JSON.stringify(full)));
  const sig = new Uint8Array(await crypto.subtle.sign("HMAC", await hmacKey(secret), enc.encode(body)));
  return `${body}.${base64UrlEncode(sig)}`;
}

export async function verifyUnsubscribeToken(token: string, secret: string): Promise<UnsubscribePayload | null> {
  const [body, sig] = token.split(".");
  if (!body || !sig) return null;
  try {
    // crypto.subtle.verify compares in constant time.
    const ok = await crypto.subtle.verify("HMAC", await hmacKey(secret), base64UrlDecode(sig), enc.encode(body));
    if (!ok) return null;
    const parsed = JSON.parse(new TextDecoder().decode(base64UrlDecode(body))) as UnsubscribePayload;
    if (typeof parsed.s !== "string" || !Array.isArray(parsed.p)) return null;
    return parsed;
  } catch {
    return null;
  }
}

/** Client IP from standard proxy headers. Only ever stored hashed. */
export function clientIp(req: Request): string | null {
  const xff = req.headers.get("x-forwarded-for");
  if (xff) return xff.split(",")[0].trim();
  return req.headers.get("x-real-ip") ?? req.headers.get("cf-connecting-ip");
}

// ---------------------------------------------------------------------------
// Audit
// ---------------------------------------------------------------------------

export async function audit(
  admin: SupabaseClient,
  entry: { actor_id: string | null; actor_role: string; action: string; data_store: string; subject_id: string | null; reason?: string; details?: Record<string, unknown> },
): Promise<void> {
  const { error } = await admin.schema("privacy").from("access_audit").insert({ ...entry, details: entry.details ?? {} });
  if (error) console.error("access_audit insert failed", error.code);
}
