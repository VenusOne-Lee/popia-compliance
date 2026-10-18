/**
 * Consent record types and helpers.
 *
 * Consent must be voluntary, specific and informed (s1). The burden of proof
 * is on the responsible party (s11(2)(a)), so store evidence, not a boolean:
 * who, what wording and version, when, how, and every withdrawal.
 *
 * Records map to privacy.consent_events in
 * supabase/migrations/0001_privacy_schema.sql. That table is append-only.
 * A withdrawal is a new event, never an update (s11(2)(b)).
 */

/** Purposes are free text in the database. These are the defaults this registry emits. */
export type ConsentPurpose =
  | "analytics_cookies"
  | "marketing_cookies"
  | "marketing_email"
  | "marketing_sms"
  | "marketing_whatsapp"
  | "marketing_phone"
  | (string & {});

export type ConsentAction = "granted" | "withdrawn";

export type ConsentChannel = "web_form" | "cookie_banner" | "app" | "privacy_centre" | "form4_email" | (string & {});

/** Payload shape for an insert into privacy.consent_events (snake_case to match the table). */
export interface ConsentEventPayload {
  purpose: ConsentPurpose;
  action: ConsentAction;
  /** Hash or semver of the exact wording shown. */
  notice_version: string;
  /** The literal text shown to the person. */
  wording: string;
  channel: ConsentChannel;
  source_url?: string | null;
  user_agent?: string | null;
  /** s35: parent or guardian for a child. */
  competent_person_id?: string | null;
  /** Client-side timestamp. The database also sets created_at. */
  occurred_at: string;
}

/**
 * SHA-256 hex digest of the wording, using SubtleCrypto. Works in modern
 * browsers (secure contexts), Deno and Node 18+.
 *
 * Normalises whitespace first so formatting changes do not change the hash,
 * but any change to the words does.
 */
export async function hashWording(wording: string): Promise<string> {
  const normalised = wording.replace(/\s+/g, " ").trim();
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) {
    // Insecure context (plain http) or very old runtime. Fail loudly rather
    // than store an unverifiable record.
    throw new Error("SubtleCrypto is not available. Serve the page over HTTPS.");
  }
  const bytes = new TextEncoder().encode(normalised);
  const digest = await subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/** Short, human-friendly version label from a hash: "sha256:1a2b3c4d5e6f". */
export function versionFromHash(hash: string): string {
  return `sha256:${hash.slice(0, 12)}`;
}

export interface BuildConsentEventInput {
  purpose: ConsentPurpose;
  action: ConsentAction;
  wording: string;
  channel: ConsentChannel;
  /** If omitted, the version is derived from the wording hash. */
  noticeVersion?: string;
  competentPersonId?: string | null;
  /** Defaults to window.location.href without query string or hash, when available. */
  sourceUrl?: string | null;
  /** Defaults to navigator.userAgent when available. Set null to skip. */
  userAgent?: string | null;
}

function defaultSourceUrl(): string | null {
  try {
    if (typeof window === "undefined") return null;
    // Drop query and fragment: they often carry email addresses or tokens.
    return `${window.location.origin}${window.location.pathname}`;
  } catch {
    return null;
  }
}

function defaultUserAgent(): string | null {
  try {
    return typeof navigator === "undefined" ? null : navigator.userAgent;
  } catch {
    return null;
  }
}

/**
 * Build a consent event payload ready to insert. The subject is not included:
 * the server derives it from the authenticated session (never trust a
 * user id sent from the browser). IP is hashed server-side, see
 * supabase/functions/consent.
 */
export async function buildConsentEvent(input: BuildConsentEventInput): Promise<ConsentEventPayload> {
  const hash = await hashWording(input.wording);
  return {
    purpose: input.purpose,
    action: input.action,
    notice_version: input.noticeVersion ?? versionFromHash(hash),
    wording: input.wording,
    channel: input.channel,
    source_url: input.sourceUrl === undefined ? defaultSourceUrl() : input.sourceUrl,
    user_agent: input.userAgent === undefined ? defaultUserAgent() : input.userAgent,
    competent_person_id: input.competentPersonId ?? null,
    occurred_at: new Date().toISOString(),
  };
}

/** Build several events at once, for example one per marketing channel. */
export async function buildConsentEvents(inputs: BuildConsentEventInput[]): Promise<ConsentEventPayload[]> {
  return Promise.all(inputs.map(buildConsentEvent));
}
