/** Number text for the Figma point card and tooltip. Minus is U+2212, as in the design. */
const MINUS = "\u2212";

export function signedDeg(value: number): string {
  const text = Math.abs(value).toFixed(4);
  return value < 0 ? `${MINUS}${text}` : text;
}

export function thousands(value: number): string {
  return Math.round(value).toLocaleString("en-US");
}

/** "+1,900" or "−300" (U+2212). Zero has no sign. */
export function signedInt(value: number): string {
  const r = Math.round(value);
  if (r === 0) return "0";
  return r > 0 ? `+${thousands(r)}` : `${MINUS}${thousands(-r)}`;
}

/** "08:00:30Z" from an ISO time. */
export function clockZ(iso: string): string {
  return `${iso.slice(11).replace(/Z$/, "")}Z`;
}

/** "↑ 1,900 fpm" or "↓ 300 fpm"; empty when the rate is unknown. */
export function rateArrow(fpm: number | null | undefined): string {
  if (fpm === null || fpm === undefined || !Number.isFinite(fpm)) return "";
  const r = Math.round(fpm);
  if (r === 0) return "level";
  return `${r > 0 ? "\u2191" : "\u2193"} ${thousands(Math.abs(r))} fpm`;
}

/** The tooltip body line: "−6.1203, 106.6518 · 1,250 ft · ↑ 1,900 fpm". */
export function pointLine(p: { lat: number; lon: number; alt_ft?: number | null }, fpm: number | null | undefined): string {
  const parts = [`${signedDeg(p.lat)}, ${signedDeg(p.lon)}`];
  parts.push(p.alt_ft === null || p.alt_ft === undefined ? "altitude not reported" : `${thousands(p.alt_ft)} ft`);
  const rate = rateArrow(fpm);
  if (rate) parts.push(rate);
  return parts.join(" \u00b7 ");
}
