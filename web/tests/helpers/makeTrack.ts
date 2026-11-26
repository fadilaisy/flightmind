import type { Track } from "../../src/api/types";

/** Test-only: a long synthetic track (a spiral climbing then descending), `n` points 1 s apart. */
export function makeTrack(n: number): Track["points"] {
  const t0 = Date.UTC(2026, 9, 13, 8, 0, 0);
  return Array.from({ length: n }, (_, i) => {
    const a = (i / n) * Math.PI * 6;
    return {
      ts: new Date(t0 + i * 1000).toISOString().replace(".000Z", "Z"),
      lat: -6.2 + (i / n) * 0.1 + Math.sin(a) * 0.01,
      lon: 106.6 + (i / n) * 0.1 + Math.cos(a) * 0.01,
      alt_ft: i % 997 === 0 ? null : Math.round(1000 + 4000 * Math.sin((i / n) * Math.PI)),
      raw_ref: `rec01:${i}`,
    };
  });
}
