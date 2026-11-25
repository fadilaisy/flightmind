import { describe, expect, it } from "vitest";
import { formatWindow, formatWindowTitle } from "../src/domain/format";

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