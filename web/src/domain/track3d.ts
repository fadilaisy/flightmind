import { BufferGeometry, Float32BufferAttribute } from "three";
import { LineSegmentsGeometry } from "three/examples/jsm/lines/LineSegmentsGeometry.js";
import type { FlightEvent, Track } from "../api/types";
import { styleColor, type PointStyle } from "./pointStyle";

type TrackPoint = Track["points"][number];

const FT_TO_M = 0.3048;
const M_PER_DEG_LAT = 110574;
const M_PER_DEG_LON_AT_EQUATOR = 111320;

/** Colours of the line. The flagged window is amber, the rest cyan (same values as pointStyle). */
export const LINE_KEPT = "#0aa2c0";
export const LINE_FLAGGED = "#d98a0b";

export interface Bounds3D {
  /** [west, south, east, north] in degrees. */
  west: number;
  south: number;
  east: number;
  north: number;
}

export interface Track3D {
  /** Altitude is multiplied by this before drawing. Shown on screen. */
  exaggeration: number;
  /** Scene units are metres from the centre of `bounds`. Half the side of the square ground grid. */
  half: number;
  gridStep: number;
  maxAltFt: number;
  /** Height of the altitude axis in scene units (metres, already exaggerated). */
  axisHeight: number;
  /** Where the altitude axis stands: just outside the south-west corner of the track. */
  axisX: number;
  axisZ: number;
  tickStepFt: number;
  /** x, y, z per track point. y is 0 for a point with no altitude. */
  world: Float32Array;
  hasAlt: Uint8Array;
  /** Points (circles) with altitude; `pointIndex[k]` is the track index of vertex k. */
  pointGeometry: BufferGeometry;
  pointIndex: Int32Array;
  /** Segments between consecutive points that both have altitude. */
  lineGeometry: LineSegmentsGeometry;
  /** Only the segments inside the flagged window, drawn wider and soft behind the line. */
  glowGeometry: LineSegmentsGeometry;
  /** One vertical segment per point, from the point down to the grid. */
  dropGeometry: BufferGeometry;
  /** The track projected on the grid (dashed). */
  groundGeometry: BufferGeometry;
  /** [x, z] of a lon, lat pair. */
  toXZ: (lon: number, lat: number) => [number, number];
}

/** Largest of 1, 2, 3, 5, 10, 20, 50 that keeps the track at about 45 percent of the ground width. */
export function chooseExaggeration(extentM: number, maxAltM: number): number {
  if (!(maxAltM > 0) || !(extentM > 0)) return 1;
  const raw = (extentM * 0.45) / maxAltM;
  const options = [1, 2, 3, 5, 10, 20, 50];
  let pick = 1;
  for (const o of options) if (o <= raw) pick = o;
  return pick;
}

function niceStep(rawM: number): number {
  const pow = 10 ** Math.floor(Math.log10(rawM));
  const f = rawM / pow;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * pow;
}

export function boundsOf(points: TrackPoint[], extra: [number, number][] = []): Bounds3D {
  let west = Infinity;
  let east = -Infinity;
  let south = Infinity;
  let north = -Infinity;
  const add = (lon: number, lat: number) => {
    if (lon < west) west = lon;
    if (lon > east) east = lon;
    if (lat < south) south = lat;
    if (lat > north) north = lat;
  };
  for (const p of points) add(p.lon, p.lat);
  for (const [lon, lat] of extra) add(lon, lat);
  return { west, south, east, north };
}

/** Builds every geometry the 3D view draws. One BufferGeometry per kind, never one mesh per point. */
export function buildTrack3D(
  points: TrackPoint[],
  event: Pick<FlightEvent, "start_ts" | "end_ts" | "raw_refs" | "type">,
  extra: [number, number][] = [],
): Track3D {
  const b = boundsOf(points, extra);
  const lon0 = (b.west + b.east) / 2;
  const lat0 = (b.south + b.north) / 2;
  const mPerLon = M_PER_DEG_LON_AT_EQUATOR * Math.cos((lat0 * Math.PI) / 180);
  // North is -z, so that the default camera looks at the track from the south.
  const toXZ = (lon: number, lat: number): [number, number] => [(lon - lon0) * mPerLon, -(lat - lat0) * M_PER_DEG_LAT];

  const widthM = (b.east - b.west) * mPerLon;
  const depthM = (b.north - b.south) * M_PER_DEG_LAT;
  const extent = Math.max(widthM, depthM, 1000);
  const gridStep = niceStep(extent / 6);
  const half = Math.ceil((extent * 0.62) / gridStep) * gridStep;

  let maxAltFt = 0;
  for (const p of points) if (p.alt_ft != null && p.alt_ft > maxAltFt) maxAltFt = p.alt_ft;
  const exaggeration = chooseExaggeration(extent, maxAltFt * FT_TO_M);
  const tickStepFt = niceStep(Math.max(maxAltFt, 500) / 3);
  const axisTop = Math.ceil(maxAltFt / tickStepFt) * tickStepFt || tickStepFt;

  const n = points.length;
  const world = new Float32Array(n * 3);
  const hasAlt = new Uint8Array(n);
  const inside = new Uint8Array(n);
  const start = Date.parse(event.start_ts);
  const end = Date.parse(event.end_ts);
  const cited = new Set(event.raw_refs);
  const styleOf = new Uint8Array(n); // 0 kept, 1 eventWindow, 2 flagged: same rules as pointStyle()
  let withAlt = 0;
  for (let i = 0; i < n; i++) {
    const p = points[i];
    const [x, z] = toXZ(p.lon, p.lat);
    const alt = p.alt_ft;
    world[i * 3] = x;
    world[i * 3 + 1] = alt == null ? 0 : alt * FT_TO_M * exaggeration;
    world[i * 3 + 2] = z;
    hasAlt[i] = alt == null ? 0 : 1;
    const ts = Date.parse(p.ts);
    const inn = ts >= start && ts <= end;
    inside[i] = inn ? 1 : 0;
    styleOf[i] = inn ? (cited.has(p.raw_ref) ? 2 : 1) : p.kept_for_event ? 1 : 0;
    if (alt != null) withAlt++;
  }

  // Points with altitude.
  const pointIndex = new Int32Array(withAlt);
  const pPos = new Float32Array(withAlt * 3);
  const pCol = new Float32Array(withAlt * 3);
  const dropPos = new Float32Array(withAlt * 6);
  const dropCol = new Float32Array(withAlt * 6);
  const color = (hex: string): [number, number, number] => [
    parseInt(hex.slice(1, 3), 16) / 255,
    parseInt(hex.slice(3, 5), 16) / 255,
    parseInt(hex.slice(5, 7), 16) / 255,
  ];
  const STYLES: PointStyle[] = ["kept", "eventWindow", "flagged"];
  const styleRgb = STYLES.map((s) => color(styleColor(s, event.type)));
  const dropKept = color(LINE_KEPT);
  const dropFlagged = color(LINE_FLAGGED);
  let k = 0;
  for (let i = 0; i < n; i++) {
    if (!hasAlt[i]) continue;
    const c = styleRgb[styleOf[i]];
    pointIndex[k] = i;
    pPos.set(world.subarray(i * 3, i * 3 + 3), k * 3);
    pCol.set(c, k * 3);
    // Drop line: thin, pale. Flagged-window points drop in amber.
    const dc = inside[i] ? dropFlagged : dropKept;
    dropPos.set(world.subarray(i * 3, i * 3 + 3), k * 6);
    dropPos[k * 6 + 3] = world[i * 3];
    dropPos[k * 6 + 4] = 0;
    dropPos[k * 6 + 5] = world[i * 3 + 2];
    for (let s = 0; s < 2; s++) {
      dropCol[k * 6 + s * 3] = dc[0];
      dropCol[k * 6 + s * 3 + 1] = dc[1];
      dropCol[k * 6 + s * 3 + 2] = dc[2];
    }
    k++;
  }
  const pointGeometry = new BufferGeometry();
  pointGeometry.setAttribute("position", new Float32BufferAttribute(pPos, 3));
  pointGeometry.setAttribute("color", new Float32BufferAttribute(pCol, 3));
  const dropGeometry = new BufferGeometry();
  dropGeometry.setAttribute("position", new Float32BufferAttribute(dropPos, 3));
  dropGeometry.setAttribute("color", new Float32BufferAttribute(dropCol, 3));

  // Line segments between neighbours that both have altitude.
  const segs: number[] = [];
  const segCol: number[] = [];
  const glow: number[] = [];
  for (let i = 0; i + 1 < n; i++) {
    if (!hasAlt[i] || !hasAlt[i + 1]) continue;
    const flagged = inside[i] && inside[i + 1];
    const c = flagged ? dropFlagged : dropKept;
    for (const j of [i, i + 1]) {
      segs.push(world[j * 3], world[j * 3 + 1], world[j * 3 + 2]);
      segCol.push(c[0], c[1], c[2]);
    }
    if (flagged) {
      glow.push(world[i * 3], world[i * 3 + 1], world[i * 3 + 2], world[i * 3 + 3], world[i * 3 + 4], world[i * 3 + 5]);
    }
  }
  const lineGeometry = new LineSegmentsGeometry();
  if (segs.length) {
    lineGeometry.setPositions(segs);
    lineGeometry.setColors(segCol);
  }
  const glowGeometry = new LineSegmentsGeometry();
  if (glow.length) glowGeometry.setPositions(glow);

  // Ground track: every point, altitude 0.
  const ground = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    ground[i * 3] = world[i * 3];
    ground[i * 3 + 2] = world[i * 3 + 2];
  }
  const groundGeometry = new BufferGeometry();
  groundGeometry.setAttribute("position", new Float32BufferAttribute(ground, 3));

  let minX = Infinity;
  let maxX = -Infinity;
  let minZ = Infinity;
  let maxZ = -Infinity;
  for (let i = 0; i < n; i++) {
    minX = Math.min(minX, world[i * 3]);
    maxX = Math.max(maxX, world[i * 3]);
    minZ = Math.min(minZ, world[i * 3 + 2]);
    maxZ = Math.max(maxZ, world[i * 3 + 2]);
  }
  const axisPad = Math.max(gridStep * 0.5, Math.max(maxX - minX, maxZ - minZ) * 0.08);
  const axisX = (n ? minX : 0) - axisPad;
  const axisZ = (n ? maxZ : 0) + axisPad;

  return {
    exaggeration,
    half,
    gridStep,
    maxAltFt: axisTop,
    axisHeight: axisTop * FT_TO_M * exaggeration,
    tickStepFt,
    axisX,
    axisZ,
    world,
    hasAlt,
    pointGeometry,
    pointIndex,
    lineGeometry,
    glowGeometry,
    dropGeometry,
    groundGeometry,
    toXZ,
  };
}

/** "0 ft", "2k ft", "1.5k ft". */
export function formatAltTick(ft: number): string {
  if (ft < 1000) return `${ft} ft`;
  return `${Number((ft / 1000).toFixed(1))}k ft`;
}

export function disposeTrack3D(t: Track3D): void {
  t.pointGeometry.dispose();
  t.lineGeometry.dispose();
  t.glowGeometry.dispose();
  t.dropGeometry.dispose();
  t.groundGeometry.dispose();
}


export interface Frame {
  center: [number, number, number];
  /** Radius of a sphere that holds everything to keep in view, padding included. */
  radius: number;
  /** The box the sphere was made from, for an exact projected fit. */
  min: [number, number, number];
  max: [number, number, number];
}

/**
 * The sphere the camera must fit: the track, the altitude axis and its tick labels, and the runway when
 * it lies within three quarters of the track's size from the track. Padding is 18 percent.
 */
export function frameTrack(t: Track3D, runwayXZ: [number, number][] = []): Frame {
  const min = [Infinity, Infinity, Infinity];
  const max = [-Infinity, -Infinity, -Infinity];
  const add = (x: number, y: number, z: number) => {
    min[0] = Math.min(min[0], x);
    max[0] = Math.max(max[0], x);
    min[1] = Math.min(min[1], y);
    max[1] = Math.max(max[1], y);
    min[2] = Math.min(min[2], z);
    max[2] = Math.max(max[2], z);
  };
  const n = t.hasAlt.length;
  for (let i = 0; i < n; i++) add(t.world[i * 3], t.world[i * 3 + 1], t.world[i * 3 + 2]);
  if (n === 0) add(0, 0, 0);
  const span = Math.max(max[0] - min[0], max[2] - min[2], 1);
  for (const [x, z] of runwayXZ) {
    const dx = Math.max(min[0] - x, 0, x - max[0]);
    const dz = Math.max(min[2] - z, 0, z - max[2]);
    if (Math.hypot(dx, dz) <= span * 0.75) add(x, 0, z);
  }
  add(t.axisX, 0, t.axisZ);
  add(t.axisX, t.axisHeight, t.axisZ);
  // Room on the left of the axis for the tick labels and ALT.
  add(t.axisX - span * 0.12, 0, t.axisZ);
  const center: [number, number, number] = [(min[0] + max[0]) / 2, (min[1] + max[1]) / 2, (min[2] + max[2]) / 2];
  const diag = Math.hypot(max[0] - min[0], max[1] - min[1], max[2] - min[2]);
  return { center, radius: Math.max((diag / 2) * 1.18, 50), min: [min[0], min[1], min[2]], max: [max[0], max[1], max[2]] };
}

/** Distance at which a sphere of `radius` fits the view in both directions. */
export function fitDistance(radius: number, vfovDeg: number, aspect: number): number {
  const v = (vfovDeg * Math.PI) / 180;
  const h = 2 * Math.atan(Math.tan(v / 2) * aspect);
  return radius / Math.sin(Math.min(v, h) / 2);
}