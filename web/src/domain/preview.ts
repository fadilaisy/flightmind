import type { RawRecord } from "../api/types";

export interface PreviewRow {
  rawRef: string;
  time: string;
  target: string;
  callsign: string;
  lat: string;
  lon: string;
  height: string;
}

const DASH = "\u2014";

function str(v: unknown): string {
  return typeof v === "string" && v !== "" ? v : DASH;
}

/** One row of the decoded preview table. A missing item shows a dash, never a guess. */
export function previewRow(r: RawRecord): PreviewRow {
  const d = r.decoded as Record<string, unknown>;
  const pos = d["I021/130"] as { lat?: number; lon?: number } | undefined;
  const h = d["I021/140"];
  return {
    rawRef: r.raw_ref,
    time: str(d["I021/071"]),
    target: str(d["I021/080"]),
    callsign: str(d["I021/170"]),
    lat: typeof pos?.lat === "number" ? pos.lat.toFixed(5) : DASH,
    lon: typeof pos?.lon === "number" ? pos.lon.toFixed(5) : DASH,
    height: typeof h === "number" ? `${Math.round(h).toLocaleString("en-US")} ft` : DASH,
  };
}

/** "99.9%" for a share, "100%" for a full one. */
export function percent(p: number): string {
  return `${Number.isInteger(p) ? p : p.toFixed(1)}%`;
}

/** "sample of 5,000 records", or "first 8 records" when every record counted. */
export function qualityScope(sampleSize: number | undefined): string | null {
  return sampleSize === undefined ? null : `sample of ${sampleSize.toLocaleString("en-US")} records`;
}
