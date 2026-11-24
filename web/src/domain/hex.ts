export interface HexRow {
  offset: number;
  bytes: string[];
  ascii: string;
}

export type HexResult = { ok: true; rows: HexRow[] } | { ok: false; error: string };

// Splits a hex string into rows of 16 bytes with an ASCII column.
// Non-printable bytes show as ".". Bad input returns an error, never throws.
export function toHexRows(hex: string): HexResult {
  const clean = hex.replace(/\s+/g, "");
  if (clean.length === 0) return { ok: true, rows: [] };
  if (clean.length % 2 !== 0 || !/^[0-9a-fA-F]+$/.test(clean)) {
    return { ok: false, error: "Hex is not a whole number of bytes." };
  }
  const bytes = clean.match(/../g)!.map((b) => b.toUpperCase());
  const rows: HexRow[] = [];
  for (let i = 0; i < bytes.length; i += 16) {
    const chunk = bytes.slice(i, i + 16);
    const ascii = chunk
      .map((b) => {
        const n = parseInt(b, 16);
        return n >= 0x20 && n <= 0x7e ? String.fromCharCode(n) : ".";
      })
      .join("");
    rows.push({ offset: i, bytes: chunk, ascii });
  }
  return { ok: true, rows };
}
