import { describe, expect, it } from "vitest";
import { formatAltitude, formatDegrees, formatPoint, formatTime, formatWindow, formatWindowTitle } from "../src/domain/format";

describe("format", () => {
  it("shows the window with UTC and its length in seconds", () => {
    expect(formatWindow("2026-10-13T08:00:20Z", "2026-10-13T08:00:40Z")).toBe(
      "08:00:20 to 08:00:40 UTC (20 s)",
    );
  });
  it("counts across a minute", () => {
    expect(formatWindow("2026-10-13T08:00:50Z", "2026-10-13T08:02:10Z")).toBe(
      "08:00:50 to 08:02:10 UTC (80 s)",
    );
  });
  it("drops the length when a time cannot be read", () => {
    expect(formatWindow("2026-10-13T08:00:20Z", "bad")).not.toContain("(");
  });
  it("keeps the full ISO times for the tooltip", () => {
    expect(formatWindowTitle("2026-10-13T08:00:20Z", "2026-10-13T08:00:40Z")).toBe(
      "2026-10-13T08:00:20Z to 2026-10-13T08:00:40Z",
    );
  });
});

describe("point text", () => {
  it("shows altitude with unit and datum", () => {
    expect(formatAltitude(1250)).toBe("1,250 ft, barometric");
  });
  it("says so when altitude is missing", () => {
    expect(formatAltitude(null)).toBe("altitude not reported");
  });
  it("builds the hover text", () => {
    expect(
      formatPoint({ ts: "2026-10-13T08:00:30Z", lat: -6.15, lon: 106.65, alt_ft: 900, raw_ref: "rec01:3" }),
    ).toEqual({
      time: "08:00:30 UTC",
      position: "-6.1500°, 106.6500°",
      altitude: "900 ft, barometric",
      rawRef: "rec01:3",
    });
  });
});

describe("point text details", () => {
  it("keeps fractions of a second in I021/071 time", () => {
    expect(formatTime("2026-10-13T08:00:30.250Z")).toBe("08:00:30.250 UTC");
  });
  it("writes degrees with four decimals", () => {
    expect(formatDegrees(106.65)).toBe("106.6500°");
    expect(formatDegrees(-6.1203)).toBe("-6.1203°");
  });
  it("keeps the thousands separator for high altitudes", () => {
    expect(formatAltitude(35000)).toBe("35,000 ft, barometric");
  });
});
