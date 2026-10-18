"use client";

/**
 * Direct marketing opt-in, substantially similar to Form 4 (Reg 6, s69(2)).
 *
 * What Form 4 content needs to be covered (see references/05-direct-marketing.md):
 *   - identity and contact details of the responsible party
 *   - the goods or services to be marketed
 *   - the channels (email, SMS, WhatsApp, phone)
 *   - a real choice to consent or not
 *   - confirmation and date (captured in the consent record)
 *
 * Rules enforced here:
 *   - s69: opt-in only. Every channel box starts unticked.
 *   - Separate from terms and conditions. Never bundle.
 *   - Amended Regulations (2025): an opt-out mechanism is not consent.
 *   - The Regulator treats calls as electronic communication. Phone is a
 *     separate opt-in here (default: treat calls as s69).
 *   - s69(2): a non-customer may be asked once. Record that you asked, and do
 *     not show this form to the same person again if they declined.
 *
 * The component emits consent records with the exact wording and a SHA-256
 * hash of that wording, so you can prove what was shown (s11(2)(a)).
 */

import * as React from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import {
  buildConsentEvent,
  hashWording,
  versionFromHash,
  type ConsentEventPayload,
} from "@/lib/popia/consent-record";

export type MarketingChannel = "email" | "sms" | "whatsapp" | "phone";

const CHANNEL_LABEL: Record<MarketingChannel, string> = {
  email: "email",
  sms: "SMS",
  whatsapp: "WhatsApp",
  phone: "phone calls",
};

export interface MarketingBusinessIdentity {
  /** Registered name, for example "Venus ARC (Pty) Ltd". */
  legalName: string;
  /** Contact for stop requests (s69(4)). Email or address. */
  contact: string;
  /** Optional registration number. */
  registrationNumber?: string;
}

export interface MarketingOptInRecord {
  /** One event per channel offered, granted or not chosen. Only "granted" events should be stored as consent. */
  events: ConsentEventPayload[];
  /** Channels the person ticked. */
  granted: MarketingChannel[];
  /** The full wording shown, exactly. */
  wording: string;
  /** SHA-256 hex digest of the wording. */
  wordingHash: string;
  /** Short version label derived from the hash, or the override. */
  wordingVersion: string;
}

export interface MarketingOptInProps {
  business: MarketingBusinessIdentity;
  /** What will be marketed, in plain words. For example "automation and Salesforce services". */
  marketedGoods: string;
  /** Channels to offer. Defaults to all four. Offer only channels you actually use. */
  channels?: MarketingChannel[];
  /** How to withdraw, in plain words. Defaults to unsubscribe link, reply STOP, or contact. */
  withdrawalText?: string;
  /** Override the computed version label, for example a semver from your CMS. */
  wordingVersion?: string;
  /** Called whenever the selection changes, with a fresh record. */
  onChange?: (record: MarketingOptInRecord) => void;
  /** Optional heading. */
  heading?: string;
  /** Name attribute prefix for native form posts. Defaults to "marketing_opt_in". */
  name?: string;
  className?: string;
}

/** Build the exact consent wording. Exported so servers can rebuild and compare. */
export function buildMarketingWording(opts: {
  business: MarketingBusinessIdentity;
  marketedGoods: string;
  channels: MarketingChannel[];
  withdrawalText?: string;
}): { intro: string; perChannel: Record<MarketingChannel, string>; withdrawal: string; full: string } {
  const who = opts.business.registrationNumber
    ? `${opts.business.legalName} (registration number ${opts.business.registrationNumber})`
    : opts.business.legalName;
  const intro = `${who} would like to send you marketing about ${opts.marketedGoods}. Tick the ways you agree to be contacted. You do not have to tick any. This does not affect our service to you.`;
  const perChannel = {} as Record<MarketingChannel, string>;
  for (const c of opts.channels) {
    perChannel[c] = `Yes, ${opts.business.legalName} may send me marketing about ${opts.marketedGoods} by ${CHANNEL_LABEL[c]}.`;
  }
  const withdrawal =
    opts.withdrawalText ??
    `You can withdraw at any time. Use the unsubscribe link in any email, reply STOP to any SMS or WhatsApp message, ask us to stop on any call, or contact ${opts.business.contact}.`;
  const full = [intro, ...opts.channels.map((c) => perChannel[c]), withdrawal].join("\n");
  return { intro, perChannel, withdrawal, full };
}

export function MarketingOptIn({
  business,
  marketedGoods,
  channels = ["email", "sms", "whatsapp", "phone"],
  withdrawalText,
  wordingVersion,
  onChange,
  heading = "Marketing (optional)",
  name = "marketing_opt_in",
  className,
}: MarketingOptInProps) {
  const groupId = React.useId();
  const channelsKey = channels.join(",");
  const wording = React.useMemo(
    () => buildMarketingWording({ business, marketedGoods, channels, withdrawalText }),
    // channelsKey stands in for the channels array identity.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [business.legalName, business.contact, business.registrationNumber, marketedGoods, channelsKey, withdrawalText],
  );

  // s69: unticked by default. Never pre-fill from earlier sessions.
  const [selected, setSelected] = React.useState<Record<MarketingChannel, boolean>>({
    email: false,
    sms: false,
    whatsapp: false,
    phone: false,
  });

  const onChangeRef = React.useRef(onChange);
  onChangeRef.current = onChange;

  React.useEffect(() => {
    const cb = onChangeRef.current;
    if (!cb) return;
    let cancelled = false;
    (async () => {
      try {
        const hash = await hashWording(wording.full);
        const version = wordingVersion ?? versionFromHash(hash);
        const events = await Promise.all(
          channels.map((c) =>
            buildConsentEvent({
              purpose: `marketing_${c}`,
              action: selected[c] ? "granted" : "withdrawn",
              // Store the full wording so the channel line is read in context.
              wording: wording.full,
              noticeVersion: version,
              channel: "web_form",
            }),
          ),
        );
        if (cancelled) return;
        cb({
          events,
          granted: channels.filter((c) => selected[c]),
          wording: wording.full,
          wordingHash: hash,
          wordingVersion: version,
        });
      } catch {
        console.warn("MarketingOptIn: could not build consent record");
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected, wording, wordingVersion, channelsKey]);

  return (
    <fieldset className={["space-y-3 rounded-md border p-4", className ?? ""].join(" ")} aria-describedby={`${groupId}-intro ${groupId}-withdraw`}>
      <legend className="px-1 text-sm font-medium">{heading}</legend>
      <p id={`${groupId}-intro`} className="text-sm text-muted-foreground">
        {wording.intro}
      </p>
      <div className="space-y-2">
        {channels.map((c) => {
          const id = `${groupId}-${c}`;
          return (
            <div key={c} className="flex items-start gap-3">
              <Checkbox
                id={id}
                name={`${name}_${c}`}
                value="yes"
                checked={selected[c]}
                onCheckedChange={(v) => setSelected((s) => ({ ...s, [c]: v === true }))}
              />
              <Label htmlFor={id} className="text-sm font-normal leading-snug">
                {wording.perChannel[c]}
              </Label>
            </div>
          );
        })}
      </div>
      <p id={`${groupId}-withdraw`} className="text-xs text-muted-foreground">
        {wording.withdrawal}
      </p>
    </fieldset>
  );
}
