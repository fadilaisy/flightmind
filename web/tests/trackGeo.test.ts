import { describe, expect, it } from "vitest";
import { trackFitBounds, trackLine, trackPoints, windowBounds } from "../src/domain/trackGeo";
import type { FlightEvent } from "../src/api/types";

const event: FlightEvent = {
  id: "e1",
  type: "go_around",
  icao24: "8a0213",
  callsign: "GIA412",
  start_ts: "2026-10-13T08:00:20Z",
  end_ts: "2026-10-13T08:00:40Z",
  raw_refs: ["r:2", "r:3"],
};
const pts = [
  { ts: "2026-10-13T08:00:00Z", lat: -6.2, lon: 106.6, alt_ft: 3000, raw_ref: "r:0" },
  { ts: "2026-10-13T08:00:20Z", lat: -6.16, lon: 106.64, alt_ft: 1500, raw_ref: "r:2" },
  { ts: "2026-10-13T08:00:30Z", lat: -6.15, lon: 106.65, alt_ft: 900, raw_ref: "r:3" },
  { ts: "2026-10-13T08:01:00Z", lat: -6.1, lon: 106.7, alt_ft: 2600, raw_ref: "r:6" },
];

describe("trackGeo", () => {
  it("writes [lon, lat] with style, colour and raw_ref", () => {
    const f = trackPoints(pts, event).features;
    expect(f[1].geometry.coordinates).toEqual([106.64, -6.16]);
    expect(f.map((x) => x.properties?.style)).toEqual(["kept", "flagged", "flagged", "kept"]);
    expect(f[1].properties).toMatchObject({ raw_ref: "r:2", color: "#d98a0b" });
  });
  it("draws one line through every point", () => {
    expect(trackLine(pts).geometry.coordinates).toHaveLength(4);
  });
  it("bounds the flagged window", () => {
    expect(windowBounds(pts, event)).toEqual([[106.64, -6.16], [106.65, -6.15]]);
  });
  it("falls back to all points and to null", () => {
    expect(windowBounds(pts, { ...event, start_ts: "2030-01-01T00:00:00Z", end_ts: "2030-01-01T00:00:10Z" })).toEqual([[106.6, -6.2], [106.7, -6.1]]);
    expect(windowBounds([], event)).toBeNull();
  });
  it("fits every point and the runway", () => {
    const rw = { type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: [[106.55, -6.3], [106.66, -6.12]] } }] } as const;
    expect(trackFitBounds(pts, rw as never)).toEqual([[106.55, -6.3], [106.7, -6.1]]);
    expect(trackFitBounds([], rw as never)).toBeNull();
  });
});
