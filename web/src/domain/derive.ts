import type { Track } from "../api/types";

type Point = Track["points"][number];

const EARTH_RADIUS_M = 6_371_008.8;
const M_PER_S_PER_KT = 1852 / 3600;
const MIN_STEP_S = 0.5;

export function haversineM(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const r = (d: number) => (d * Math.PI) / 180;
  const dLat = r(lat2 - lat1);
  const dLon = r(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(r(lat1)) * Math.cos(r(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(a)));
}

export interface Derived {
  /** Ground speed in kt per point. Null for the first point and for steps under 0.5 s. */
  speedKt: (number | null)[];
  /** Vertical rate in ft/min per point. Also null when either altitude is null. */
  verticalRateFpm: (number | null)[];
}

/** Each value comes from the step between a point and the one before it. */
export function derive(points: Point[]): Derived {
  const speedKt: (number | null)[] = [null];
  const verticalRateFpm: (number | null)[] = [null];
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1];
    const b = points[i];
    const dt = (Date.parse(b.ts) - Date.parse(a.ts)) / 1000;
    if (!(dt >= MIN_STEP_S)) {
      speedKt.push(null);
      verticalRateFpm.push(null);
      continue;
    }
    speedKt.push(haversineM(a.lat, a.lon, b.lat, b.lon) / dt / M_PER_S_PER_KT);
    verticalRateFpm.push(a.alt_ft == null || b.alt_ft == null ? null : ((b.alt_ft - a.alt_ft) / dt) * 60);
  }
  return { speedKt, verticalRateFpm };
}
