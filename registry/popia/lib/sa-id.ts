/**
 * South African ID number helpers. Port of scripts/sa_id.py.
 *
 * Format: YYMMDD SSSS C A Z
 *   YYMMDD  date of birth
 *   SSSS    sequence. 0000-4999 female, 5000-9999 male
 *   C       0 = SA citizen, 1 = permanent resident, 2 = refugee
 *   A       historically used, now usually 8 or 9
 *   Z       Luhn check digit
 *
 * An SA ID number is a unique identifier (s1) that reveals date of birth, sex and
 * citizenship status. Treat it as high-risk personal information (s19).
 * Linking it with other organisations' data for a new purpose may need
 * prior authorisation (s57(1)(a)).
 *
 * Rules: never use it as a primary key, URL parameter, username or log value.
 * Encrypt or tokenise at field level. Display masked.
 */

export type SaIdCitizenship = "sa_citizen" | "permanent_resident" | "refugee";

export interface ParsedSaId {
  valid: true;
  /** ISO date, YYYY-MM-DD */
  dateOfBirth: string;
  sex: "female" | "male";
  citizenship: SaIdCitizenship;
}

const CITIZENSHIP: Record<string, SaIdCitizenship> = {
  "0": "sa_citizen",
  "1": "permanent_resident",
  "2": "refugee",
};

/** Strip spaces and hyphens that people commonly type. */
export function normaliseSaId(input: string): string {
  return input.replace(/[\s-]/g, "");
}

function luhnOk(digits: string): boolean {
  let sum = 0;
  for (let i = 0; i < digits.length; i++) {
    let n = digits.charCodeAt(digits.length - 1 - i) - 48;
    if (i % 2 === 1) {
      n *= 2;
      if (n > 9) n -= 9;
    }
    sum += n;
  }
  return sum % 10 === 0;
}

/**
 * Resolve the two-digit year. Years up to the current two-digit year are read
 * as 2000s, later ones as 1900s. Same heuristic as scripts/sa_id.py.
 */
function parseDob(id: string, today: Date = new Date()): Date | null {
  const yy = Number(id.slice(0, 2));
  const mm = Number(id.slice(2, 4));
  const dd = Number(id.slice(4, 6));
  if (mm < 1 || mm > 12 || dd < 1 || dd > 31) return null;
  const century = yy <= today.getFullYear() % 100 ? 2000 : 1900;
  const year = century + yy;
  const d = new Date(Date.UTC(year, mm - 1, dd));
  if (d.getUTCFullYear() !== year || d.getUTCMonth() !== mm - 1 || d.getUTCDate() !== dd) {
    return null;
  }
  return d;
}

/** Structural check: 13 digits, real calendar date, known citizenship digit, Luhn. */
export function isValidSaId(input: string): boolean {
  const id = normaliseSaId(input);
  if (!/^\d{13}$/.test(id)) return false;
  if (parseDob(id) === null) return false;
  if (!(id.charAt(10) in CITIZENSHIP)) return false;
  return luhnOk(id);
}

/**
 * Parse the fields encoded in the number. Only call this when the purpose
 * genuinely needs DOB, sex or citizenship (s10 minimality). If you only need
 * an age check, derive it and discard the rest.
 */
export function parseSaId(input: string): ParsedSaId | { valid: false } {
  const id = normaliseSaId(input);
  if (!isValidSaId(id)) return { valid: false };
  const dob = parseDob(id) as Date;
  const citizenship = CITIZENSHIP[id.charAt(10)];
  if (!citizenship) return { valid: false };
  return {
    valid: true,
    dateOfBirth: dob.toISOString().slice(0, 10),
    sex: Number(id.slice(6, 10)) < 5000 ? "female" : "male",
    citizenship,
  };
}

/** Mask all but the last `keepLast` digits. Default shows the last 3. */
export function maskSaId(input: string, keepLast = 3): string {
  const id = normaliseSaId(input);
  if (id.length <= keepLast) return "*".repeat(id.length);
  return "*".repeat(id.length - keepLast) + id.slice(-keepLast);
}
