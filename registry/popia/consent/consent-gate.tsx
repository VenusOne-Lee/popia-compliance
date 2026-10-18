"use client";

/**
 * ConsentGate, loadScript and Google Consent Mode v2 helpers.
 *
 * Nothing in the analytics or marketing category may load before the person
 * opts in. That covers pixels, tag managers, session replay and ad scripts
 * (s69 and the Regulator's Direct Marketing Guidance Note, Dec 2024; s18 notice).
 * Server-side tracking (Meta CAPI, server GTM) is still processing of personal
 * information and needs the same consent. Hashing is not anonymisation.
 *
 * Usage:
 *   <ConsentGate category="marketing" src="https://connect.facebook.net/en_US/fbevents.js" />
 *   <ConsentGate category="analytics" fallback={<p>Enable analytics cookies to see this.</p>}>
 *     <EmbeddedDashboard />
 *   </ConsentGate>
 *
 * Google tag:
 *   // Before any Google tag runs, as early as possible:
 *   initGoogleConsentMode();
 *   // Inside ConsentProvider:
 *   <GoogleConsentModeSync />
 */

import * as React from "react";
import { useConsent, type ConsentCategory, type ConsentState } from "@/components/popia/consent-provider";

/* ------------------------------------------------------------------ */
/* loadScript                                                          */
/* ------------------------------------------------------------------ */

export interface LoadScriptOptions {
  /** Used to de-duplicate. Defaults to the src. */
  id?: string;
  async?: boolean;
  defer?: boolean;
  /** Extra attributes, for example data-domain for Plausible. */
  attributes?: Record<string, string>;
  /** Subresource integrity hash, when the vendor publishes one. */
  integrity?: string;
  crossOrigin?: "anonymous" | "use-credentials";
  nonce?: string;
}

const loaded = new Map<string, Promise<void>>();

/**
 * Inject a script tag once. Returns a promise that resolves on load.
 * Only call this after consent for the script's category.
 */
export function loadScript(src: string, options: LoadScriptOptions = {}): Promise<void> {
  if (typeof document === "undefined") return Promise.resolve();
  const key = options.id ?? src;
  const existing = loaded.get(key);
  if (existing) return existing;

  const p = new Promise<void>((resolve, reject) => {
    try {
      const s = document.createElement("script");
      s.src = src;
      s.async = options.async ?? true;
      if (options.defer) s.defer = true;
      if (options.id) s.id = options.id;
      if (options.integrity) s.integrity = options.integrity;
      if (options.crossOrigin) s.crossOrigin = options.crossOrigin;
      if (options.nonce) s.nonce = options.nonce;
      for (const [k, v] of Object.entries(options.attributes ?? {})) s.setAttribute(k, v);
      s.onload = () => resolve();
      s.onerror = () => {
        loaded.delete(key);
        reject(new Error(`Failed to load script ${key}`));
      };
      document.head.appendChild(s);
    } catch (err) {
      loaded.delete(key);
      reject(err instanceof Error ? err : new Error("Failed to load script"));
    }
  });
  loaded.set(key, p);
  return p;
}

/* ------------------------------------------------------------------ */
/* ConsentGate                                                         */
/* ------------------------------------------------------------------ */

export interface ConsentGateProps {
  category: ConsentCategory;
  /** Rendered only after consent for this category. */
  children?: React.ReactNode;
  /** Rendered while consent is missing. Keep it neutral, no pressure copy. */
  fallback?: React.ReactNode;
  /** Optional script to load after consent. */
  src?: string;
  scriptOptions?: LoadScriptOptions;
  /** Called once after consent is present (and after the script loads, if src is set). */
  onConsented?: () => void;
}

export function ConsentGate({ category, children, fallback = null, src, scriptOptions, onConsented }: ConsentGateProps) {
  const { ready, has } = useConsent();
  const allowed = ready && has(category);
  const firedRef = React.useRef(false);
  const onConsentedRef = React.useRef(onConsented);
  onConsentedRef.current = onConsented;
  const optionsKey = JSON.stringify(scriptOptions ?? {});

  React.useEffect(() => {
    if (!allowed || firedRef.current) return;
    let cancelled = false;
    const done = () => {
      if (cancelled || firedRef.current) return;
      firedRef.current = true;
      onConsentedRef.current?.();
    };
    if (src) {
      loadScript(src, scriptOptions).then(done, () => {
        console.warn("ConsentGate: script failed to load");
      });
    } else {
      done();
    }
    return () => {
      cancelled = true;
    };
    // optionsKey stands in for scriptOptions identity.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allowed, src, optionsKey]);

  // Note: a script that has already run cannot be unloaded. On withdrawal,
  // children unmount and the GoogleConsentModeSync update fires. For other
  // vendors call their opt-out API (for example fbq('consent', 'revoke')) in
  // the ConsentProvider onChange callback, and reload the page if needed.
  if (!allowed) return <>{fallback}</>;
  return <>{children}</>;
}

/* ------------------------------------------------------------------ */
/* Google Consent Mode v2                                              */
/* ------------------------------------------------------------------ */

type ConsentValue = "granted" | "denied";

export interface GoogleConsentSignals {
  ad_storage: ConsentValue;
  ad_user_data: ConsentValue;
  ad_personalization: ConsentValue;
  analytics_storage: ConsentValue;
  functionality_storage?: ConsentValue;
  personalization_storage?: ConsentValue;
  security_storage?: ConsentValue;
}

type Gtag = (...args: unknown[]) => void;

declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: Gtag;
  }
}

function ensureGtag(): Gtag | null {
  if (typeof window === "undefined") return null;
  window.dataLayer = window.dataLayer ?? [];
  if (!window.gtag) {
    // Standard gtag shim. It must push the arguments object, not an array.
    window.gtag = function gtag() {
      // eslint-disable-next-line prefer-rest-params
      (window.dataLayer as unknown[]).push(arguments);
    };
  }
  return window.gtag;
}

export const DENIED_DEFAULTS: GoogleConsentSignals = {
  ad_storage: "denied",
  ad_user_data: "denied",
  ad_personalization: "denied",
  analytics_storage: "denied",
  functionality_storage: "granted", // necessary only
  personalization_storage: "denied",
  security_storage: "granted", // necessary only
};

/**
 * Set Consent Mode defaults to denied. Call this before any Google tag loads,
 * ideally in an inline script in index.html or the Next.js root layout.
 * Defaults to denied is the POPIA-safe starting point (opt-in, s69).
 */
export function initGoogleConsentMode(options: { waitForUpdateMs?: number; urlPassthrough?: boolean } = {}): void {
  const gtag = ensureGtag();
  if (!gtag) return;
  gtag("consent", "default", {
    ...DENIED_DEFAULTS,
    wait_for_update: options.waitForUpdateMs ?? 500,
  });
  // Redact ad click identifiers while ad_storage is denied.
  gtag("set", "ads_data_redaction", true);
  if (options.urlPassthrough) gtag("set", "url_passthrough", true);
}

/** Map our categories to Google's consent signals. */
export function toGoogleSignals(consent: Pick<ConsentState, "analytics" | "marketing"> | null): GoogleConsentSignals {
  const a: ConsentValue = consent?.analytics ? "granted" : "denied";
  const m: ConsentValue = consent?.marketing ? "granted" : "denied";
  return {
    ad_storage: m,
    ad_user_data: m,
    ad_personalization: m,
    analytics_storage: a,
    functionality_storage: "granted",
    personalization_storage: m,
    security_storage: "granted",
  };
}

/** Push a consent update. Call on every change, including withdrawal. */
export function updateGoogleConsent(consent: Pick<ConsentState, "analytics" | "marketing"> | null): void {
  const gtag = ensureGtag();
  if (!gtag) return;
  gtag("consent", "update", toGoogleSignals(consent));
}

/**
 * Keeps Google Consent Mode in step with ConsentProvider. Render once inside
 * the provider. Renders nothing.
 */
export function GoogleConsentModeSync() {
  const { ready, consent } = useConsent();
  const analytics = consent?.analytics ?? false;
  const marketing = consent?.marketing ?? false;
  React.useEffect(() => {
    if (!ready) return;
    updateGoogleConsent({ analytics, marketing });
  }, [ready, analytics, marketing]);
  return null;
}

/**
 * Inline snippet for index.html or a Next.js <Script strategy="beforeInteractive">.
 * Paste it above the Google tag so defaults are set first.
 */
export const GOOGLE_CONSENT_DEFAULTS_SNIPPET = `window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('consent','default',{ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied',analytics_storage:'denied',functionality_storage:'granted',personalization_storage:'denied',security_storage:'granted',wait_for_update:500});gtag('set','ads_data_redaction',true);`;
