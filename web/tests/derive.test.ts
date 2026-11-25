import { describe, expect, it } from "vitest";
import { derive, haversineM } from "../src/domain/derive";

const p = (ts: string, lat: number, lon: number, alt: number | null) => ({ ts, lat, lon, alt_ft: alt, raw_ref: "r:0" });

describe("haversineM", () => {
  it("is about 111,195 m for one degree of latitude", () => {
    expect(haversineM(0, 0, 1, 0)).toBeCloseTo(111_195, -1);
  });
});

describe("derive", () => {
  it("gives kt and ft/min from two points", () => {
    // 1 minute of latitude is 1 NM, in 60 s that is 60 kt.
    const d = derive([p("2026-10-13T08:00:00Z", 0, 0, 1000), p("2026-10-13T08:01:00Z", 1 / 60, 0, 2000)]);
    expect(d.speedKt[0]).toBeNull();
    expect(d.speedKt[1]).toBeCloseTo(60, 0);
    expect(d.verticalRateFpm[1]).toBeCloseTo(1000, 5);
  });
  it("gives a negative rate when descending", () => {
    const d = derive([p("2026-10-13T08:00:00Z", 0, 0, 2000), p("2026-10-13T08:00:30Z", 0, 0.01, 1500)]);
    expect(d.verticalRateFpm[1]).toBeCloseTo(-1000, 5);
  });
  it("gives null rate for null altitude but keeps speed", () => {
    const d = derive([p("2026-10-13T08:00:00Z", 0, 0, null), p("2026-10-13T08:00:10Z", 0, 0.01, 1000)]);
    expect(d.verticalRateFpm[1]).toBeNull();
    expect(d.speedKt[1]).not.toBeNull();
  });
  it("gives null for a step under 0.5 s", () => {
    const d = derive([p("2026-10-13T08:00:00.000Z", 0, 0, 1000), p("2026-10-13T08:00:00.400Z", 0, 0.01, 1100)]);
    expect(d.speedKt[1]).toBeNull();
    expect(d.verticalRateFpm[1]).toBeNull();
  });
  it("accepts a step of exactly 0.5 s", () => {
    const d = derive([p("2026-10-13T08:00:00.000Z", 0, 0, 1000), p("2026-10-13T08:00:00.500Z", 0, 0.001, 1010)]);
    expect(d.speedKt[1]).not.toBeNull();
  });
});
