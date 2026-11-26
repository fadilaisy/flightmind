import type { Track } from "../api/types";
import { altitudeDatum } from "./itemMeta";

/** "08:00:20" from an ISO time. */
function clock(iso: string): string {
  return iso.slice(11, 19);
}

/** Flagged window as "08:00:20 to 08:00:40 UTC (20 s)". */
export function formatWindow(startIso: string, endIso: string): string {
  const seconds = Math.round((Date.parse(endIso) - Date.parse(startIso)) / 1000);
  const length = Number.isFinite(seconds) ? ` (${seconds} s)` : "";
  return `${clock(startIso)} to ${clock(endIso)} UTC${length}`;
}

/** Flagged window as "08:00:20-08:00:40Z" (with an en dash), for tight spots like the chart header. */
export function formatWindowCompact(startIso: string, endIso: string): string {
  return `${clock(startIso)}\u2013${clock(endIso)}Z`;
}

/** Full ISO times, for a title tooltip. */
export function formatWindowTitle(startIso: string, endIso: string): string {
  return `${startIso} to ${endIso}`;
}

/** Altitude with its unit and datum, for example "1,250 ft, barometric". */
export function formatAltitude(altFt: number | null | undefined): string {
  if (altFt === null || altFt === undefined) return "altitude not reported";
  return `${altFt.toLocaleString("en-US")} ft, ${altitudeDatum()}`;
}

export function formatDegrees(value: number): string {
  return `${value.toFixed(4)}°`;
}

/** Time of I021/071 as "08:00:20 UTC" (keeps fractions of a second when the ISO time has them). */
export function formatTime(iso: string): string {
  return `${iso.slice(11).replace(/Z$/, "")} UTC`;
}

export interface PointText {
  time: string;
  position: string;
  altitude: string;
  rawRef: string;
}

/** The text a point shows on hover. Time is I021/071. */
export function formatPoint(p: Track["points"][number]): PointText {
  return {
    time: formatTime(p.ts),
    position: `${formatDegrees(p.lat)}, ${formatDegrees(p.lon)}`,
    altitude: formatAltitude(p.alt_ft),
    rawRef: p.raw_ref,
  };
}
