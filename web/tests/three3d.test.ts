import { describe, expect, it } from "vitest";
import { buildTrack3D, chooseExaggeration, formatAltTick } from "../src/domain/track3d";
import { makeTrack } from "./helpers/makeTrack";

const event = {
  type: "go_around" as const,
  start_ts: "2026-10-13T08:20:00Z",
  end_ts: "2026-10-13T08:40:00Z",
  raw_refs: ["rec01:1300", "rec01:1301"],
};

describe("track3d", () => {
  it("builds the geometry for 5,000 points in under 50 ms", () => {
    const points = makeTrack(5000);
    buildTrack3D(points, event); // warm up
    // Best of five, so a busy machine running other test files does not fail the budget.
    let ms = Infinity;
    let t = buildTrack3D(points, event);
    for (let r = 0; r < 5; r++) {
      const t0 = performance.now();
      t = buildTrack3D(points, event);
      ms = Math.min(ms, performance.now() - t0);
    }
    expect(t.pointGeometry.getAttribute("position").count).toBe(t.pointIndex.length);
    expect(t.pointIndex.length).toBeLessThan(5000); // points without altitude have no vertex
    expect(t.groundGeometry.getAttribute("position").count).toBe(5000);
    expect(ms).toBeLessThan(50);
  });

  it("scales altitude so the track keeps a readable height, and reports the factor", () => {
    expect(chooseExaggeration(12000, 900)).toBe(5);
    expect(chooseExaggeration(12000, 0)).toBe(1);
    expect(chooseExaggeration(1000, 9000)).toBe(1);
  });

  it("draws no line across a point with no altitude", () => {
    const points = makeTrack(5).map((p, i) => ({ ...p, alt_ft: i === 2 ? null : 1000 }));
    const t = buildTrack3D(points, event);
    // 5 points, one without altitude: segments 0-1 and 3-4 only.
    expect(t.lineGeometry.attributes.instanceStart.count).toBe(2);
  });

  it("formats altitude ticks in ft", () => {
    expect(formatAltTick(0)).toBe("0 ft");
    expect(formatAltTick(2000)).toBe("2k ft");
    expect(formatAltTick(1500)).toBe("1.5k ft");
  });
});
