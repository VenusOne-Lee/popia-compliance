"use client";

/**
 * ConsentProvider and useConsent.
 *
 * Categories:
 *   necessary  always on. Session, CSRF, load balancing. Disclosed, no consent needed.
 *   analytics  off until the person chooses. Notice plus a real choice.
 *   marketing  off until opt-in. Pixels and ad tags (s69, Regulator Direct
 *              Marketing Guidance Note, Dec 2024).
 *
 * Consent is versioned. When policyVersion changes, the stored choice no longer
 * applies and the banner shows again. Consent must be informed (s1), so a
 * choice made against old wording is not carried forward.
 *
 * Storage is localStorage, and every access is wrapped in try/catch. If storage
 * throws (private mode, blocked site data) the app still works: the choice
 * lives in memory for the session and nothing non-essential loads.
 *
 * Browser storage is a convenience, not evidence. Use onChange to record each
 * decision server-side (s11(2)(a): burden of proof is on the responsible party).
 */

import * as React from "react";

export type ConsentCategory = "necessary" | "analytics" | "marketing";
export type OptionalCategory = Exclude<ConsentCategory, "necessary">;

export interface ConsentState {
  necessary: true;
  analytics: boolean;
  marketing: boolean;
  /** The policy or notice version the person saw when choosing. */
  policyVersion: string;
  /** ISO timestamp of the choice. */
  decidedAt: string;
}

export type ConsentSource = "accept_all" | "reject_all" | "preferences" | "withdraw";

export interface ConsentChange {
  state: ConsentState;
  previous: ConsentState | null;
  source: ConsentSource;
  /** Categories whose value changed, with the new value. */
  changed: Array<{ category: OptionalCategory; granted: boolean }>;
}

export interface ConsentContextValue {
  /** null until the person has decided for the current policyVersion. */
  consent: ConsentState | null;
  /** True once storage has been read on the client. Avoids a banner flash on SSR. */
  ready: boolean;
  hasDecided: boolean;
  policyVersion: string;
  /** necessary is always true. Others are false until granted. */
  has: (category: ConsentCategory) => boolean;
  acceptAll: () => void;
  rejectAll: () => void;
  /** Save a specific set of choices from the preferences dialog. */
  save: (choices: Partial<Record<OptionalCategory, boolean>>) => void;
  /** Withdraw all optional consent (s11(2)(b)). As easy as giving it. */
  withdrawAll: () => void;
  preferencesOpen: boolean;
  openPreferences: () => void;
  closePreferences: () => void;
  setPreferencesOpen: (open: boolean) => void;
}

const ConsentContext = React.createContext<ConsentContextValue | null>(null);

export interface ConsentProviderProps {
  children: React.ReactNode;
  /**
   * Version of the cookie notice or privacy notice wording. Bump it whenever
   * the categories, vendors or purposes change. Use a semver or a hash.
   */
  policyVersion: string;
  /** localStorage key. Defaults to "popia_consent". */
  storageKey?: string;
  /**
   * Called after every decision. Use it to record the event server-side, for
   * example via the consent edge function or a Supabase insert. Errors thrown
   * here are caught and logged without personal information.
   */
  onChange?: (change: ConsentChange) => void | Promise<void>;
}

const OPTIONAL: OptionalCategory[] = ["analytics", "marketing"];

function safeRead(key: string): unknown {
  try {
    if (typeof window === "undefined") return null;
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as unknown) : null;
  } catch {
    return null;
  }
}

function safeWrite(key: string, value: ConsentState): void {
  try {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Storage unavailable. Choice stays in memory for this session.
  }
}

function isConsentState(v: unknown): v is ConsentState {
  if (!v || typeof v !== "object") return false;
  const o = v as Record<string, unknown>;
  return (
    o.necessary === true &&
    typeof o.analytics === "boolean" &&
    typeof o.marketing === "boolean" &&
    typeof o.policyVersion === "string" &&
    typeof o.decidedAt === "string"
  );
}

export function ConsentProvider({
  children,
  policyVersion,
  storageKey = "popia_consent",
  onChange,
}: ConsentProviderProps) {
  const [consent, setConsent] = React.useState<ConsentState | null>(null);
  const [ready, setReady] = React.useState(false);
  const [preferencesOpen, setPreferencesOpen] = React.useState(false);
  const consentRef = React.useRef<ConsentState | null>(null);
  const onChangeRef = React.useRef(onChange);
  onChangeRef.current = onChange;

  // Read on the client only, after mount.
  React.useEffect(() => {
    const stored = safeRead(storageKey);
    // A choice made under a different policy version does not count.
    const valid = isConsentState(stored) && stored.policyVersion === policyVersion ? stored : null;
    consentRef.current = valid;
    setConsent(valid);
    setReady(true);
  }, [storageKey, policyVersion]);

  // Keep tabs in sync. A withdrawal in one tab applies to all.
  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const handler = (e: StorageEvent) => {
      if (e.key !== storageKey) return;
      const next = safeRead(storageKey);
      const valid = isConsentState(next) && next.policyVersion === policyVersion ? next : null;
      consentRef.current = valid;
      setConsent(valid);
    };
    try {
      window.addEventListener("storage", handler);
      return () => window.removeEventListener("storage", handler);
    } catch {
      return undefined;
    }
  }, [storageKey, policyVersion]);

  const commit = React.useCallback(
    (choices: Record<OptionalCategory, boolean>, source: ConsentSource) => {
      const previous = consentRef.current;
      const next: ConsentState = {
        necessary: true,
        analytics: choices.analytics,
        marketing: choices.marketing,
        policyVersion,
        decidedAt: new Date().toISOString(),
      };
      const changed = OPTIONAL.filter((c) => (previous ? previous[c] !== next[c] : true)).map((c) => ({
        category: c,
        granted: next[c],
      }));
      consentRef.current = next;
      setConsent(next);
      safeWrite(storageKey, next);
      setPreferencesOpen(false);
      const cb = onChangeRef.current;
      if (cb) {
        try {
          void Promise.resolve(cb({ state: next, previous, source, changed })).catch(() => {
            // Do not log the payload. It may be joined to a user id.
            console.warn("ConsentProvider: onChange failed");
          });
        } catch {
          console.warn("ConsentProvider: onChange failed");
        }
      }
    },
    [policyVersion, storageKey],
  );

  const value = React.useMemo<ConsentContextValue>(
    () => ({
      consent,
      ready,
      hasDecided: consent !== null,
      policyVersion,
      has: (category) => (category === "necessary" ? true : Boolean(consent?.[category])),
      acceptAll: () => commit({ analytics: true, marketing: true }, "accept_all"),
      rejectAll: () => commit({ analytics: false, marketing: false }, "reject_all"),
      save: (choices) =>
        commit(
          {
            analytics: choices.analytics ?? false,
            marketing: choices.marketing ?? false,
          },
          "preferences",
        ),
      withdrawAll: () => commit({ analytics: false, marketing: false }, "withdraw"),
      preferencesOpen,
      openPreferences: () => setPreferencesOpen(true),
      closePreferences: () => setPreferencesOpen(false),
      setPreferencesOpen,
    }),
    [consent, ready, policyVersion, preferencesOpen, commit],
  );

  return <ConsentContext.Provider value={value}>{children}</ConsentContext.Provider>;
}

export function useConsent(): ConsentContextValue {
  const ctx = React.useContext(ConsentContext);
  if (!ctx) {
    throw new Error("useConsent must be used inside <ConsentProvider>.");
  }
  return ctx;
}

/** Same as useConsent but returns null outside a provider. For optional integrations. */
export function useOptionalConsent(): ConsentContextValue | null {
  return React.useContext(ConsentContext);
}
