const BN_DIGITS = "০১২৩৪৫৬৭৮৯";

/** Convert Bangla digits to ASCII digits. */
export function toAsciiDigits(s: string): string {
  return s.replace(/[০-৯]/g, (d) => String(BN_DIGITS.indexOf(d)));
}

/** Convert ASCII digits to Bangla digits. */
export function toBanglaDigits(s: string): string {
  return s.replace(/[0-9]/g, (d) => BN_DIGITS[Number(d)] ?? d);
}

/**
 * Normalise text for matching: NFC, one form for nukta letters (য় ড় ঢ়), no zero-width
 * characters, ASCII digits, lower case, punctuation turned into spaces.
 */
export function normalize(s: string): string {
  return toAsciiDigits(
    s
      .normalize("NFC")
      .replace(/\u09DF/g, "\u09AF\u09BC")
      .replace(/\u09DC/g, "\u09A1\u09BC")
      .replace(/\u09DD/g, "\u09A2\u09BC")
      .replace(/[\u200B-\u200D\u2060\uFEFF\u00AD]/g, ""),
  )
    .toLowerCase()
    .replace(/[^\p{L}\p{M}\p{N}.]+/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** Split normalised text into search tokens (keeps "3.2" style numbers together). */
export function tokens(s: string): string[] {
  return normalize(s)
    .split(" ")
    .map((t) => t.replace(/^\.+|\.+$/g, ""))
    .filter((t) => t.length > 0);
}
