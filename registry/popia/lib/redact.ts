/**
 * Redact personal information before it reaches logs, error trackers or
 * analytics. Logs are a second database, often held by an offshore operator
 * (s19 security, s20/s21 operators, s72 cross-border), and they outlive your
 * retention schedule (s14).
 *
 * Use at the logger or in Sentry beforeSend, not at each call site.
 *
 *   console.error(redact(err));
 *   Sentry.init({ sendDefaultPii: false, beforeSend: (e) => redact(e) });
 *
 * This is pattern-based. It reduces leakage. It does not guarantee that no
 * personal information remains. Log IDs and events, not values.
 */

export const REDACTED = "[REDACTED]";

export interface RedactOptions {
  /** Extra object keys (case-insensitive, matched on the normalised key) to blank out. */
  extraKeys?: string[];
  /** Replacement text. Defaults to "[REDACTED]". */
  replacement?: string;
  /** Maximum depth when walking objects. Defaults to 8. */
  maxDepth?: number;
}

/**
 * Object keys whose values are always removed, whatever they contain.
 * Matched after lower-casing and stripping "_", "-" and spaces.
 */
const SENSITIVE_KEYS = new Set([
  "password",
  "passwd",
  "secret",
  "token",
  "accesstoken",
  "refreshtoken",
  "idtoken",
  "apikey",
  "authorization",
  "cookie",
  "setcookie",
  "email",
  "emailaddress",
  "phone",
  "phonenumber",
  "mobile",
  "cell",
  "cellphone",
  "msisdn",
  "whatsapp",
  "idnumber",
  "said",
  "saidnumber",
  "nationalid",
  "passport",
  "passportnumber",
  "taxnumber",
  "dob",
  "dateofbirth",
  "accountnumber",
  "bankaccount",
  "iban",
  "cardnumber",
  "pan",
  "cvv",
  "cvc",
  "address",
  "streetaddress",
  "ipaddress",
  "ip",
]);

// Order matters: specific token shapes first, then identifiers, then generic digits.
const PATTERNS: Array<[RegExp, string]> = [
  // JWTs (header.payload.signature, base64url)
  [/\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\b/g, "jwt"],
  // Authorization headers
  [/\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}/gi, "auth"],
  // Common provider secret prefixes (Stripe, GitHub, Slack, OpenAI-style, Supabase)
  [/\b(sk|pk|rk)_(live|test)_[A-Za-z0-9]{8,}\b/g, "key"],
  [/\b(ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{16,}\b/g, "key"],
  [/\bxox[abposr]-[A-Za-z0-9-]{10,}\b/g, "key"],
  [/\bsk-[A-Za-z0-9_-]{20,}\b/g, "key"],
  [/\bsbp_[A-Za-z0-9]{20,}\b/g, "key"],
  // key=value secrets in query strings or config dumps
  [/\b(access_token|refresh_token|id_token|api_key|apikey|token|secret|password)=([^&\s"']+)/gi, "kv"],
  // Email addresses
  [/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g, "email"],
  // SA ID numbers: 13 digits starting with a plausible YYMMDD
  [/\b\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{7}\b/g, "said"],
  // Payment card numbers: 13 to 19 digits, optionally grouped by spaces or hyphens
  [/\b(?:\d[ -]?){12,18}\d\b/g, "card"],
  // SA phone numbers: +27 or 0027 international form
  [/(?:\+|\b00)27[\s-]?\(?0?\)?[1-9]\d(?:[\s-]?\d){7}\b/g, "phone"],
  // SA mobile numbers in national form: 06x, 07x, 08x
  [/\b0[6-8]\d(?:[\s-]?\d){7}\b/g, "phone"],
  // SA landlines in national form: 01x to 05x
  [/\b0[1-5]\d(?:[\s-]?\d){7}\b/g, "phone"],
  // Bank account numbers when labelled (unlabelled 7 to 11 digit runs are too ambiguous)
  [/\b(acc(?:ount)?(?:\s*(?:no|number|#))?\s*[:=#]?\s*)\d{6,16}\b/gi, "account"],
  // Long hex or base64 blobs that look like secrets (32+ chars)
  [/\b[A-Fa-f0-9]{32,}\b/g, "hex"],
];

function normaliseKey(key: string): string {
  return key.toLowerCase().replace(/[\s_-]/g, "");
}

/** Redact personal information and secrets from a single string. */
export function redactString(input: string, replacement: string = REDACTED): string {
  let out = input;
  for (const [re, kind] of PATTERNS) {
    if (kind === "kv") {
      out = out.replace(re, (_m, k: string) => `${k}=${replacement}`);
    } else if (kind === "account") {
      out = out.replace(re, (_m, label: string) => `${label}${replacement}`);
    } else if (kind === "auth") {
      out = out.replace(re, (_m, scheme: string) => `${scheme} ${replacement}`);
    } else {
      out = out.replace(re, replacement);
    }
  }
  return out;
}

/**
 * Deep-redact any value. Strings are pattern-scrubbed, values under sensitive
 * keys are replaced entirely, Errors keep name and a scrubbed message and stack.
 * Returns a new value. The input is not mutated. Circular references are cut.
 */
export function redact<T>(value: T, options: RedactOptions = {}): T {
  const replacement = options.replacement ?? REDACTED;
  const maxDepth = options.maxDepth ?? 8;
  const extra = new Set((options.extraKeys ?? []).map(normaliseKey));
  const seen = new WeakSet<object>();

  const isSensitiveKey = (key: string): boolean => {
    const k = normaliseKey(key);
    return SENSITIVE_KEYS.has(k) || extra.has(k);
  };

  const walk = (v: unknown, depth: number): unknown => {
    if (v === null || v === undefined) return v;
    if (typeof v === "string") return redactString(v, replacement);
    if (typeof v === "number") {
      // A 13 to 19 digit number is likely an ID or card number.
      return String(Math.trunc(Math.abs(v))).length >= 13 ? replacement : v;
    }
    if (typeof v === "bigint") return replacement;
    if (typeof v !== "object") return v;
    if (depth >= maxDepth) return "[TRUNCATED]";
    if (seen.has(v as object)) return "[CIRCULAR]";
    seen.add(v as object);

    if (v instanceof Error) {
      return {
        name: v.name,
        message: redactString(v.message, replacement),
        stack: v.stack ? redactString(v.stack, replacement) : undefined,
      };
    }
    if (v instanceof Date) return v;
    if (Array.isArray(v)) return v.map((item) => walk(item, depth + 1));

    const out: Record<string, unknown> = {};
    for (const [key, val] of Object.entries(v as Record<string, unknown>)) {
      out[key] = isSensitiveKey(key) && val !== null && val !== undefined && val !== ""
        ? replacement
        : walk(val, depth + 1);
    }
    return out;
  };

  return walk(value, 0) as T;
}

/**
 * Wrap a console-like logger so every argument is redacted first.
 *
 *   const log = createSafeLogger(console);
 *   log.info("signup", { email: "a@b.co.za" }); // email is [REDACTED]
 */
export function createSafeLogger<L extends Pick<Console, "log" | "info" | "warn" | "error" | "debug">>(
  logger: L,
  options: RedactOptions = {},
): Pick<Console, "log" | "info" | "warn" | "error" | "debug"> {
  const wrap =
    (fn: (...args: unknown[]) => void) =>
    (...args: unknown[]) =>
      fn(...args.map((a) => redact(a, options)));
  return {
    log: wrap(logger.log.bind(logger)),
    info: wrap(logger.info.bind(logger)),
    warn: wrap(logger.warn.bind(logger)),
    error: wrap(logger.error.bind(logger)),
    debug: wrap(logger.debug.bind(logger)),
  };
}
