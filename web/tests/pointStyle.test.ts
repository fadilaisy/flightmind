import { describe, expect, it } from "vitest";
import { pointStyle, styleColor } from "../src/domain/pointStyle";
import { inWindow } from "../src/domain/window";

const event = {
  start_ts: "2026-10-13T08:00:20Z",
  end_ts: "2026-10-13T08:00:40Z",
  raw_refs: ["r:3", "r:4"],
};

describe("inWindow", () => {
  it("counts both edges as inside", () => {
    expect(inWindow("2026-10-13T08:00:20Z", event)).toBe(true);
    expect(inWindow("2026-10-13T08:00:40Z", event)).toBe(true);
  });
  it("is false just outside", () => {
    expect(inWindow("2026-10-13T08:00:19Z", event)).toBe(false);
    expect(inWindow("2026-10-13T08:00:41Z", event)).toBe(false);
  });
});

describe("pointStyle", () => {
  it("flags a cited point inside the window", () => {
    expect(pointStyle({ ts: "2026-10-13T08:00:30Z", raw_ref: "r:3" }, event)).toBe("flagged");
  });
  it("treats a point on the window edge as inside", () => {
    expect(pointStyle({ ts: "2026-10-13T08:00:40Z", raw_ref: "r:4" }, event)).toBe("flagged");
    expect(pointStyle({ ts: "2026-10-13T08:00:20Z", raw_ref: "r:9" }, event)).toBe("eventWindow");
  });
  it("marks an uncited point inside the window as event window", () => {
    expect(pointStyle({ ts: "2026-10-13T08:00:30Z", raw_ref: "r:9" }, event)).toBe("eventWindow");
  });
  it("marks kept_for_event as event window", () => {
    expect(pointStyle({ ts: "2026-10-13T08:00:10Z", raw_ref: "r:1", kept_for_event: true }, event)).toBe("eventWindow");
  });
  it("keeps every other point as kept", () => {
    expect(pointStyle({ ts: "2026-10-13T08:00:10Z", raw_ref: "r:1" }, event)).toBe("kept");
    expect(pointStyle({ ts: "2026-10-13T08:00:50Z", raw_ref: "r:3" }, event)).toBe("kept");
  });
});

describe("styleColor", () => {
  it("uses red only for flagged squawk points", () => {
    expect(styleColor("flagged", "squawk_7700")).toBe("#c8322a");
    expect(styleColor("flagged", "go_around")).toBe("#d98a0b");
    expect(styleColor("eventWindow", "squawk_7700")).toBe("#48cae4");
  });
});