import type { Recipe } from "../api/uploadTypes";
import { formatSize } from "./upload";

export interface RecipeTotals {
  decoded: number;
  setAside: number;
  afterCleaning: number;
  /** raw_bytes / stored_bytes, or null when nothing is stored. */
  smallerBy: number | null;
}

export function recipeTotals(r: Recipe): RecipeTotals {
  const decoded = r.steps[0]?.records_in ?? 0;
  const setAside = r.steps.reduce((s, x) => s + x.set_aside, 0);
  return {
    decoded,
    setAside,
    afterCleaning: decoded - setAside,
    smallerBy: r.stored_bytes > 0 ? r.raw_bytes / r.stored_bytes : null,
  };
}

/** "7.6x smaller", rounded to one decimal. */
export function smallerText(by: number | null): string {
  return by === null ? "" : `${by.toFixed(1)}\u00d7 smaller`;
}

/** "1.30% of records", from a count and the decoded total. */
export function shareText(count: number, total: number): string {
  if (total === 0) return "0% of records";
  const p = (count / total) * 100;
  return `${p < 0.01 && count > 0 ? "<0.01" : p.toFixed(p >= 10 ? 1 : 2)}% of records`;
}

export function sizeLine(r: Recipe): string {
  return `${formatSize(r.raw_bytes)} raw, ${formatSize(r.stored_bytes)} stored`;
}
