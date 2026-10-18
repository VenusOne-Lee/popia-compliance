"use client";

/**
 * Privacy centre for signed-in users.
 *
 * Builds the data subject rights into the product (references/02-build-patterns.md, section 10):
 *   - Download my data              s23(1)(b) access
 *   - Delete my account             s24 deletion, with a note on legally retained records (s14)
 *   - Marketing preferences         s69, s11(3)(b) stop marketing
 *   - Withdraw consent              s11(2)(b)
 *   - Object to processing          s11(3), Form 1 (free of charge)
 *   - Complain to the Regulator     s74, Form 5
 *
 * Identity: the person is already signed in. Endpoints must derive the user
 * from the session JWT, never from the request body. Ask for re-authentication
 * before destructive actions if your auth provider supports it.
 *
 * Endpoints default to the Supabase edge functions in this registry.
 */

import * as React from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useOptionalConsent } from "@/components/popia/consent-provider";

export type MarketingPurpose = "marketing_email" | "marketing_sms" | "marketing_whatsapp" | "marketing_phone";

export interface PrivacyCentreEndpoints {
  /** POST, returns the export (JSON). Default: /functions/v1/dsar-export */
  exportData: string;
  /** POST, starts deletion. Default: /functions/v1/dsar-delete */
  deleteAccount: string;
  /** GET returns current consent, POST records an event. Default: /functions/v1/consent */
  consent: string;
}

export interface PrivacyCentreProps {
  /** Base URL, for example import.meta.env.VITE_SUPABASE_URL. Prepended to relative endpoints. */
  baseUrl?: string;
  endpoints?: Partial<PrivacyCentreEndpoints>;
  /** Returns the current access token. For Supabase: (await supabase.auth.getSession()).data.session?.access_token */
  getAccessToken: () => Promise<string | null | undefined>;
  /** Extra headers, for example { apikey: SUPABASE_ANON_KEY }. The anon key is public by design. */
  headers?: Record<string, string>;
  companyName: string;
  privacyNoticeUrl: string;
  /** Your Form 1 objection page or PDF. */
  objectionFormUrl: string;
  /** Contact for privacy requests, for example privacy@yourcompany.co.za */
  privacyContact: string;
  /** VERIFY: confirm the Information Regulator's current complaint page before launch. */
  regulatorComplaintUrl?: string;
  /** Plain description of what you keep after deletion and for how long. s14(1)(a). */
  retainedDataNote?: string;
  /** Marketing channels you actually use. */
  marketingChannels?: MarketingPurpose[];
  /** Called after deletion succeeds, for example to sign out and redirect. */
  onDeleted?: () => void;
  className?: string;
}

const DEFAULT_ENDPOINTS: PrivacyCentreEndpoints = {
  exportData: "/functions/v1/dsar-export",
  deleteAccount: "/functions/v1/dsar-delete",
  consent: "/functions/v1/consent",
};

const CHANNEL_LABEL: Record<MarketingPurpose, string> = {
  marketing_email: "Email",
  marketing_sms: "SMS",
  marketing_whatsapp: "WhatsApp",
  marketing_phone: "Phone calls",
};

type Status = { kind: "idle" } | { kind: "busy" } | { kind: "ok"; message: string } | { kind: "error"; message: string };

export function PrivacyCentre({
  baseUrl = "",
  endpoints,
  getAccessToken,
  headers,
  companyName,
  privacyNoticeUrl,
  objectionFormUrl,
  privacyContact,
  regulatorComplaintUrl = "https://inforegulator.org.za/", // VERIFY current complaints page
  retainedDataNote = "We keep some records after you delete your account where the law requires it, for example invoices for tax purposes. We keep only what is required, restrict access to it, and delete it when the retention period ends.",
  marketingChannels = ["marketing_email", "marketing_sms", "marketing_whatsapp", "marketing_phone"],
  onDeleted,
  className,
}: PrivacyCentreProps) {
  const ep = { ...DEFAULT_ENDPOINTS, ...endpoints };
  const url = (p: string) => (/^https?:\/\//.test(p) ? p : `${baseUrl.replace(/\/$/, "")}${p}`);
  const cookieConsent = useOptionalConsent();

  const call = React.useCallback(
    async (path: string, init: RequestInit = {}) => {
      const token = await getAccessToken();
      if (!token) throw new Error("You need to be signed in.");
      const res = await fetch(url(path), {
        ...init,
        headers: {
          "Content-Type": "application/json",
          ...headers,
          ...(init.headers as Record<string, string> | undefined),
          Authorization: `Bearer ${token}`,
        },
      });
      if (!res.ok) {
        let msg = `Request failed (${res.status}).`;
        try {
          const body = (await res.json()) as { error?: string };
          if (body?.error) msg = body.error;
        } catch {
          // ignore
        }
        throw new Error(msg);
      }
      return res;
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [getAccessToken, baseUrl, JSON.stringify(headers ?? {})],
  );

  /* ---------------- marketing preferences ---------------- */

  const [marketing, setMarketing] = React.useState<Partial<Record<MarketingPurpose, boolean>>>({});
  const [marketingLoaded, setMarketingLoaded] = React.useState(false);
  const [marketingStatus, setMarketingStatus] = React.useState<Status>({ kind: "idle" });

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await call(ep.consent, { method: "GET" });
        const body = (await res.json()) as { current?: Array<{ purpose: string; action: string }> };
        if (cancelled) return;
        const next: Partial<Record<MarketingPurpose, boolean>> = {};
        for (const row of body.current ?? []) {
          if ((marketingChannels as string[]).includes(row.purpose)) {
            next[row.purpose as MarketingPurpose] = row.action === "granted";
          }
        }
        setMarketing(next);
      } catch {
        if (!cancelled) setMarketingStatus({ kind: "error", message: "Could not load your marketing preferences." });
      } finally {
        if (!cancelled) setMarketingLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [call, ep.consent]);

  const recordConsent = async (purpose: string, granted: boolean, wording: string) => {
    await call(ep.consent, {
      method: "POST",
      body: JSON.stringify({
        purpose,
        action: granted ? "granted" : "withdrawn",
        wording,
        channel: "privacy_centre",
      }),
    });
  };

  const toggleMarketing = async (purpose: MarketingPurpose, granted: boolean) => {
    const before = marketing[purpose] ?? false;
    setMarketing((m) => ({ ...m, [purpose]: granted }));
    setMarketingStatus({ kind: "busy" });
    try {
      // s69: the wording stored with the event is the text next to the switch.
      const wording = `${companyName} may send me marketing by ${CHANNEL_LABEL[purpose].toLowerCase()}.`;
      await recordConsent(purpose, granted, wording);
      setMarketingStatus({ kind: "ok", message: "Saved." });
    } catch (err) {
      setMarketing((m) => ({ ...m, [purpose]: before }));
      setMarketingStatus({ kind: "error", message: err instanceof Error ? err.message : "Could not save." });
    }
  };

  const [withdrawStatus, setWithdrawStatus] = React.useState<Status>({ kind: "idle" });
  const withdrawAll = async () => {
    setWithdrawStatus({ kind: "busy" });
    try {
      // s11(2)(b): withdrawal is a new event per purpose, never an update.
      await Promise.all(
        marketingChannels.map((p) => recordConsent(p, false, "I withdraw my consent to marketing on this channel.")),
      );
      const off: Partial<Record<MarketingPurpose, boolean>> = {};
      for (const p of marketingChannels) off[p] = false;
      setMarketing(off);
      cookieConsent?.withdrawAll();
      setWithdrawStatus({ kind: "ok", message: "Your optional consents are withdrawn. This does not affect processing before today." });
    } catch (err) {
      setWithdrawStatus({ kind: "error", message: err instanceof Error ? err.message : "Could not withdraw consent." });
    }
  };

  /* ---------------- export ---------------- */

  const [exportStatus, setExportStatus] = React.useState<Status>({ kind: "idle" });
  const exportData = async () => {
    setExportStatus({ kind: "busy" });
    try {
      const res = await call(ep.exportData, { method: "POST", body: "{}" });
      const blob = await res.blob();
      const href = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = href;
      a.download = `my-data-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(href), 1000);
      setExportStatus({ kind: "ok", message: "Your download has started. Keep the file somewhere safe." });
    } catch (err) {
      setExportStatus({ kind: "error", message: err instanceof Error ? err.message : "Could not export your data." });
    }
  };

  /* ---------------- delete ---------------- */

  const [deleteOpen, setDeleteOpen] = React.useState(false);
  const [confirmText, setConfirmText] = React.useState("");
  const [deleteStatus, setDeleteStatus] = React.useState<Status>({ kind: "idle" });
  const CONFIRM_WORD = "DELETE";
  const deleteAccount = async () => {
    setDeleteStatus({ kind: "busy" });
    try {
      await call(ep.deleteAccount, { method: "POST", body: JSON.stringify({ confirm: true }) });
      setDeleteStatus({ kind: "ok", message: "Your account deletion has been processed." });
      setDeleteOpen(false);
      onDeleted?.();
    } catch (err) {
      setDeleteStatus({ kind: "error", message: err instanceof Error ? err.message : "Could not delete your account." });
    }
  };

  return (
    <div className={["space-y-8", className ?? ""].join(" ")}>
      <header className="space-y-1">
        <h2 className="text-xl font-semibold">Privacy</h2>
        <p className="text-sm text-muted-foreground">
          Manage the personal information {companyName} holds about you. Read our{" "}
          <a href={privacyNoticeUrl} className="underline underline-offset-4">
            Privacy Notice
          </a>{" "}
          for details.
        </p>
      </header>

      {/* s23(1)(b) access */}
      <Section title="Download your data" description="Get a copy of the personal information linked to your account, as a JSON file.">
        <Button type="button" variant="outline" onClick={exportData} disabled={exportStatus.kind === "busy"}>
          {exportStatus.kind === "busy" ? "Preparing download" : "Download my data"}
        </Button>
        <StatusLine status={exportStatus} />
      </Section>

      {/* s69, s11(3)(b) */}
      <Section
        title="Marketing"
        description="Choose how we may contact you with marketing. Switching a channel off stops marketing on that channel. Service messages about your account still reach you."
      >
        <div className="space-y-3">
          {marketingChannels.map((p) => {
            const id = `popia-pc-${p}`;
            return (
              <div key={p} className="flex items-center justify-between gap-4">
                <Label htmlFor={id} className="font-normal">
                  {CHANNEL_LABEL[p]}
                </Label>
                <Switch
                  id={id}
                  checked={marketing[p] ?? false}
                  disabled={!marketingLoaded || marketingStatus.kind === "busy"}
                  onCheckedChange={(v) => void toggleMarketing(p, v)}
                />
              </div>
            );
          })}
        </div>
        <StatusLine status={marketingStatus} />
      </Section>

      {/* s11(2)(b) */}
      <Section
        title="Withdraw consent"
        description="Withdraw all optional consent in one step: marketing on every channel, and analytics and marketing cookies on this device."
      >
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" onClick={withdrawAll} disabled={withdrawStatus.kind === "busy"}>
            Withdraw all optional consent
          </Button>
          {cookieConsent ? (
            <Button type="button" variant="outline" onClick={cookieConsent.openPreferences}>
              Cookie preferences
            </Button>
          ) : null}
        </div>
        <StatusLine status={withdrawStatus} />
      </Section>

      {/* s11(3), Form 1 */}
      <Section
        title="Object to processing"
        description="You can object to us using your information for our legitimate interests or for direct marketing. Objecting is free."
      >
        <p className="text-sm">
          Use our{" "}
          <a href={objectionFormUrl} className="underline underline-offset-4">
            objection form (Form 1)
          </a>{" "}
          or write to{" "}
          <a href={contactHref(privacyContact)} className="underline underline-offset-4">
            {privacyContact}
          </a>
          .
        </p>
      </Section>

      {/* s24 deletion */}
      <Section title="Delete your account" description="This removes your account and the personal information linked to it.">
        <p className="text-sm text-muted-foreground">{retainedDataNote}</p>
        <Button type="button" variant="destructive" onClick={() => setDeleteOpen(true)} aria-haspopup="dialog">
          Delete my account
        </Button>
        <StatusLine status={deleteStatus} />
      </Section>

      {/* s74 complaints */}
      <Section
        title="Not happy with how we handle your information"
        description={`Contact us first at ${privacyContact} so we can try to fix it. You also have the right to complain to the Information Regulator.`}
      >
        <a href={regulatorComplaintUrl} className="text-sm underline underline-offset-4" rel="noopener noreferrer" target="_blank">
          Information Regulator (opens in a new tab)
        </a>
      </Section>

      <Dialog
        open={deleteOpen}
        onOpenChange={(o) => {
          setDeleteOpen(o);
          if (!o) setConfirmText("");
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete your account</DialogTitle>
            <DialogDescription>
              This cannot be undone. Your profile and personal information will be deleted or de-identified.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 text-sm">
            <p className="text-muted-foreground">{retainedDataNote}</p>
            <p className="text-muted-foreground">
              Consider downloading your data first. Backups expire on their normal cycle, as set out in our Privacy Notice.
            </p>
            <div className="space-y-1.5">
              <Label htmlFor="popia-delete-confirm">Type {CONFIRM_WORD} to confirm</Label>
              <Input
                id="popia-delete-confirm"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                autoComplete="off"
              />
            </div>
          </div>
          <DialogFooter className="gap-2 sm:gap-2">
            <Button type="button" variant="outline" onClick={() => setDeleteOpen(false)}>
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={deleteAccount}
              disabled={confirmText.trim().toUpperCase() !== CONFIRM_WORD || deleteStatus.kind === "busy"}
            >
              {deleteStatus.kind === "busy" ? "Deleting" : "Delete account"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function contactHref(contact: string): string {
  return contact.includes("@") && !contact.startsWith("mailto:") ? `mailto:${contact}` : contact;
}

function Section({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  const id = React.useId();
  return (
    <section aria-labelledby={id} className="space-y-3 rounded-lg border p-4">
      <div className="space-y-1">
        <h3 id={id} className="font-medium">
          {title}
        </h3>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      {children}
    </section>
  );
}

function StatusLine({ status }: { status: Status }) {
  if (status.kind === "ok") {
    return (
      <p role="status" className="text-sm text-muted-foreground">
        {status.message}
      </p>
    );
  }
  if (status.kind === "error") {
    return (
      <p role="alert" className="text-sm text-destructive">
        {status.message}
      </p>
    );
  }
  return null;
}
