import { describe, expect, it } from "vitest";
import { buildAskQuestion } from "../src/domain/askContext";

const base = {
  id: "e1",
  type: "go_around" as const,
  icao24: "8a0213",
  start_ts: "2026-10-13T08:00:20Z",
  end_ts: "2026-10-13T08:00:40Z",
};

describe("buildAskQuestion", () => {
  it("names the event before the question", () => {
    expect(buildAskQuestion({ ...base, callsign: "GIA412" }, "Why?")).toBe(
      "About event e1 (go_around, GIA412, 2026-10-13T08:00:20Z to 2026-10-13T08:00:40Z): Why?",
    );
  });
  it("uses icao24 when there is no callsign", () => {
    expect(buildAskQuestion({ ...base, callsign: null }, "Why?")).toContain("(go_around, 8a0213,");
  });
});