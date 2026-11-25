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

/** Full ISO times, for a title tooltip. */
export function formatWindowTitle(startIso: string, endIso: string): string {
  return `${startIso} to ${endIso}`;
}