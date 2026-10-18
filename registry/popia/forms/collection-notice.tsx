/**
 * Short notice at the point of collection (s18).
 *
 * s18(1) requires reasonably practicable steps to make the person aware of,
 * among other things: what is collected, who the responsible party is, the
 * purpose, whether supply is voluntary or mandatory, the consequences of not
 * supplying it, any law requiring it, any cross-border transfer, and the
 * rights to access, correct, object (s11(3)) and complain to the Information
 * Regulator. This short notice covers the headline items and links to the
 * full Privacy Notice for the rest.
 *
 * Place it directly above or below the submit button of every form that
 * collects personal information.
 */

export interface CollectionNoticeProps {
  /** Responsible party, for example "Venus One (Pty) Ltd". s18(1)(b). */
  company: string;
  /** Plain purpose, for example "to reply to your enquiry and book a call". s18(1)(c). */
  purpose: string;
  privacyNoticeUrl: string;
  /**
   * s18(1)(d)-(e): voluntary or mandatory, and what happens if not supplied.
   * For example "Fields marked optional can be left blank. Without your email we cannot reply."
   */
  optionalMandatoryNote?: string;
  /** s18(1)(f): law that requires the collection, if any. For example "FICA". */
  lawRequiringCollection?: string;
  /**
   * s18(1)(g): countries outside South Africa the information goes to, if any.
   * For example ["Ireland", "United States"]. Record the s72 basis in your ROPA.
   */
  crossBorderCountries?: string[];
  /** Optional link to the PAIA manual or objection form. */
  objectionUrl?: string;
  className?: string;
}

export function CollectionNotice({
  company,
  purpose,
  privacyNoticeUrl,
  optionalMandatoryNote,
  lawRequiringCollection,
  crossBorderCountries,
  objectionUrl,
  className,
}: CollectionNoticeProps) {
  const transfer =
    crossBorderCountries && crossBorderCountries.length > 0
      ? `Some of it is stored or processed outside South Africa, in ${formatList(crossBorderCountries)}, with safeguards described in our Privacy Notice.`
      : null;

  return (
    <div className={["space-y-1 text-xs text-muted-foreground", className ?? ""].join(" ")} role="note" aria-label="How we use your information">
      <p>
        {company} uses the information on this form {purpose}.
        {lawRequiringCollection ? ` We are required to collect some of it under ${lawRequiringCollection}.` : ""}
        {transfer ? ` ${transfer}` : ""}
      </p>
      {optionalMandatoryNote ? <p>{optionalMandatoryNote}</p> : null}
      <p>
        You can ask to see, correct or delete your information, object to how we use it
        {objectionUrl ? (
          <>
            {" "}
            (
            <a href={objectionUrl} className="underline underline-offset-4">
              objection form
            </a>
            )
          </>
        ) : null}
        , and complain to the Information Regulator. See our{" "}
        <a href={privacyNoticeUrl} className="underline underline-offset-4">
          Privacy Notice
        </a>
        .
      </p>
    </div>
  );
}

function formatList(items: string[]): string {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}
