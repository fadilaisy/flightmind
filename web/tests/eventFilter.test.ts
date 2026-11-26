import { describe, expect, it } from "vitest";
import { filterEvents } from "../src/domain/eventFilter";
import type { FlightEvent } from "../src/api/types";

const mk = (id: string, type: FlightEvent["type"], callsign: string | null, icao24: string): FlightEvent => ({
  id, type, callsign, icao24, start_ts: "2026-10-13T08:00:20Z", end_ts: "2026-10-13T08:00:40Z", raw_refs: [],
});
const list = [mk("1", "go_around", "GIA412", "8a0213"), mk("2", "holding", "LNI760", "8a0377"), mk("3", "squawk_7700", null, "8a04f1")];

describe("filterEvents", () => {
  it("returns all with no filter", () => expect(filterEvents(list, "all", "")).toHaveLength(3));
  it("filters by type", () => expect(filterEvents(list, "holding", "").map((e) => e.id)).toEqual(["2"]));
  it("matches callsign without case", () => expect(filterEvents(list, "all", "gia").map((e) => e.id)).toEqual(["1"]));
  it("matches icao24 when there is no callsign", () => expect(filterEvents(list, "all", "04F1").map((e) => e.id)).toEqual(["3"]));
  it("combines type and text", () => expect(filterEvents(list, "holding", "gia")).toHaveLength(0));
});