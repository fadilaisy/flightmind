import type { Feature, FeatureCollection, LineString, Point } from "geojson";
import type { FlightEvent, Track } from "../api/types";
import { pointStyle, styleColor } from "./pointStyle";

type TrackPoint = Track["points"][number];

/** One GeoJSON point per track point, with its style and colour. Coordinates are [lon, lat]. */
export function trackPoints(points: TrackPoint[], event: FlightEvent): FeatureCollection<Point> {
  return {
    type: "FeatureCollection",
    features: points.map((p, i): Feature<Point> => {
      const style = pointStyle(p, event);
      return {
        type: "Feature",
        geometry: { type: "Point", coordinates: [p.lon, p.lat] },
        properties: { index: i, style, color: styleColor(style, event.type), raw_ref: raw(p), ts: p.ts },
      };
    }),
  };
}

function raw(p: TrackPoint): string {
  return p.raw_ref;
}

export function trackLine(points: TrackPoint[]): Feature<LineString> {
  return {
    type: "Feature",
    properties: {},
    geometry: { type: "LineString", coordinates: points.map((p) => [p.lon, p.lat]) },
  };
}

export type Bounds = [[number, number], [number, number]];

/** Bounds of the points that are not plain "kept". Falls back to all points. Null for no points. */
export function windowBounds(points: TrackPoint[], event: FlightEvent): Bounds | null {
  const inside = points.filter((p) => pointStyle(p, event) !== "kept");
  const use = inside.length > 0 ? inside : points;
  if (use.length === 0) return null;
  const lons = use.map((p) => p.lon);
  const lats = use.map((p) => p.lat);
  return [
    [Math.min(...lons), Math.min(...lats)],
    [Math.max(...lons), Math.max(...lats)],
  ];
}

/** Bounds of every track point plus the runway features. Null when there are no points. */
export function trackFitBounds(points: TrackPoint[], runway: FeatureCollection): Bounds | null {
  if (points.length === 0) return null;
  const lons = points.map((p) => p.lon);
  const lats = points.map((p) => p.lat);
  for (const f of runway.features) {
    if (f.geometry.type !== "LineString") continue;
    for (const [lon, lat] of f.geometry.coordinates) {
      lons.push(lon);
      lats.push(lat);
    }
  }
  return [
    [Math.min(...lons), Math.min(...lats)],
    [Math.max(...lons), Math.max(...lats)],
  ];
}

/** The part of the track inside the flagged window, as a line. Empty when no point is inside. */
export function windowLine(points: TrackPoint[], event: FlightEvent): Feature<LineString> {
  const coordinates = points.filter((p) => pointStyle(p, event) !== "kept").map((p) => [p.lon, p.lat]);
  return { type: "Feature", properties: {}, geometry: { type: "LineString", coordinates } };
}
