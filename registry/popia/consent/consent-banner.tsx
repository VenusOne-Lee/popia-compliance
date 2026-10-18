"use client";

/**
 * Cookie and tracker consent banner.
 *
 * Design rules (no dark patterns):
 *   - "Accept all" and "Reject all" use the same size and the same visual weight.
 *   - "Choose" opens a dialog with one switch per optional category.
 *   - Optional switches start off. Nothing non-essential loads before a choice.
 *   - The banner does not block the page and has no countdown or nagging copy.
 *   - Links to the privacy notice and cookie notice sit in the banner (s18).
 *
 * Consent must be voluntary, specific and informed (s1). Marketing pixels need
 * opt-in (s69, Regulator Direct Marketing Guidance Note, Dec 2024).
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
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useConsent, type OptionalCategory } from "@/components/popia/consent-provider";

export interface ConsentCategoryCopy {
  title: string;
  description: string;
}

export interface ConsentBannerProps {
  /** Responsible party name as it appears in the privacy notice. */
  companyName: string;
  privacyNoticeUrl: string;
  cookieNoticeUrl: string;
  /** Override default copy. Keep it plain and specific. */
  copy?: {
    heading?: string;
    body?: string;
    necessary?: ConsentCategoryCopy;
    analytics?: ConsentCategoryCopy;
    marketing?: ConsentCategoryCopy;
  };
  className?: string;
}

const DEFAULT_COPY = {
  heading: "Cookies and similar tools",
  body:
    "We use necessary cookies to run this site. With your permission we also use analytics cookies to understand how the site is used, and marketing cookies to measure and show adverts. You can change your mind at any time.",
  necessary: {
    title: "Necessary",
    description: "Needed for the site to work, for example to keep you signed in and to protect forms. Always on.",
  },
  analytics: {
    title: "Analytics",
    description: "Counts visits and shows us which pages are used, so we can improve the site.",
  },
  marketing: {
    title: "Marketing",
    description: "Lets advertising partners measure our adverts and show you relevant ones on other sites.",
  },
} as const;

export function ConsentBanner({
  companyName,
  privacyNoticeUrl,
  cookieNoticeUrl,
  copy,
  className,
}: ConsentBannerProps) {
  const { ready, hasDecided, acceptAll, rejectAll, save, consent, preferencesOpen, setPreferencesOpen, openPreferences } =
    useConsent();

  const text = {
    heading: copy?.heading ?? DEFAULT_COPY.heading,
    body: copy?.body ?? DEFAULT_COPY.body,
    necessary: copy?.necessary ?? DEFAULT_COPY.necessary,
    analytics: copy?.analytics ?? DEFAULT_COPY.analytics,
    marketing: copy?.marketing ?? DEFAULT_COPY.marketing,
  };

  // Draft state for the dialog. Starts from the stored choice, or all off.
  const [draft, setDraft] = React.useState<Record<OptionalCategory, boolean>>({
    analytics: false,
    marketing: false,
  });
  React.useEffect(() => {
    if (preferencesOpen) {
      setDraft({ analytics: consent?.analytics ?? false, marketing: consent?.marketing ?? false });
    }
  }, [preferencesOpen, consent]);

  const headingId = React.useId();
  const bodyId = React.useId();

  const showBanner = ready && !hasDecided;

  return (
    <>
      {showBanner && (
        <section
          role="region"
          aria-labelledby={headingId}
          aria-describedby={bodyId}
          className={[
            "fixed inset-x-0 bottom-0 z-50 border-t bg-background p-4 shadow-lg sm:p-6",
            className ?? "",
          ].join(" ")}
        >
          <div className="mx-auto flex max-w-5xl flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div className="space-y-2 text-sm">
              <h2 id={headingId} className="text-base font-semibold">
                {text.heading}
              </h2>
              <p id={bodyId} className="text-muted-foreground">
                {text.body}
              </p>
              <p className="text-muted-foreground">
                {companyName} is responsible for this site. Read our{" "}
                <a href={privacyNoticeUrl} className="underline underline-offset-4">
                  Privacy Notice
                </a>{" "}
                and{" "}
                <a href={cookieNoticeUrl} className="underline underline-offset-4">
                  Cookie Notice
                </a>
                .
              </p>
            </div>
            {/* Equal prominence: same variant and size for accept and reject. */}
            <div className="flex flex-col gap-2 sm:flex-row sm:shrink-0">
              <Button type="button" variant="outline" onClick={openPreferences} aria-haspopup="dialog">
                Choose
              </Button>
              <Button type="button" onClick={rejectAll}>
                Reject all
              </Button>
              <Button type="button" onClick={acceptAll}>
                Accept all
              </Button>
            </div>
          </div>
        </section>
      )}

      <Dialog open={preferencesOpen} onOpenChange={setPreferencesOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Cookie preferences</DialogTitle>
            <DialogDescription>
              Choose which optional cookies {companyName} may use. Optional cookies are off until you switch them on.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <CategoryRow
              id="popia-consent-necessary"
              title={text.necessary.title}
              description={text.necessary.description}
              checked
              disabled
            />
            <CategoryRow
              id="popia-consent-analytics"
              title={text.analytics.title}
              description={text.analytics.description}
              checked={draft.analytics}
              onCheckedChange={(v) => setDraft((d) => ({ ...d, analytics: v }))}
            />
            <CategoryRow
              id="popia-consent-marketing"
              title={text.marketing.title}
              description={text.marketing.description}
              checked={draft.marketing}
              onCheckedChange={(v) => setDraft((d) => ({ ...d, marketing: v }))}
            />
          </div>

          <p className="text-xs text-muted-foreground">
            More detail in our{" "}
            <a href={cookieNoticeUrl} className="underline underline-offset-4">
              Cookie Notice
            </a>
            .
          </p>

          <DialogFooter className="gap-2 sm:gap-2">
            <Button type="button" variant="outline" onClick={rejectAll}>
              Reject all
            </Button>
            <Button type="button" variant="outline" onClick={acceptAll}>
              Accept all
            </Button>
            <Button type="button" onClick={() => save(draft)}>
              Save choices
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

interface CategoryRowProps {
  id: string;
  title: string;
  description: string;
  checked: boolean;
  disabled?: boolean;
  onCheckedChange?: (checked: boolean) => void;
}

function CategoryRow({ id, title, description, checked, disabled, onCheckedChange }: CategoryRowProps) {
  const descId = `${id}-desc`;
  return (
    <div className="flex items-start justify-between gap-4 rounded-md border p-3">
      <div className="space-y-1">
        <Label htmlFor={id} className="font-medium">
          {title}
          {disabled ? <span className="ml-2 text-xs font-normal text-muted-foreground">(always on)</span> : null}
        </Label>
        <p id={descId} className="text-sm text-muted-foreground">
          {description}
        </p>
      </div>
      <Switch
        id={id}
        checked={checked}
        disabled={disabled}
        onCheckedChange={onCheckedChange}
        aria-describedby={descId}
      />
    </div>
  );
}

/**
 * A footer link that reopens preferences. Withdrawal must be as easy as
 * giving consent (s11(2)(b)), so put this on every page.
 */
export function ConsentPreferencesLink({ className, children }: { className?: string; children?: React.ReactNode }) {
  const { openPreferences } = useConsent();
  return (
    <button
      type="button"
      onClick={openPreferences}
      aria-haspopup="dialog"
      className={className ?? "text-sm underline underline-offset-4"}
    >
      {children ?? "Cookie preferences"}
    </button>
  );
}
