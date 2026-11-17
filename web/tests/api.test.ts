import { describe, expect, it } from "vitest";
import mini from "./fixtures/mini.json";
import { mockApi, type MockData } from "../src/api/mockClient";

const api = mockApi(mini as unknown as MockData);

describe("mock api", () => {
  it("serves meta, events, a track and a raw record", async () => {
    expect((await api.meta()).mode).toBe("replay");
    const events = await api.events();
    expect(events).toHaveLength(1);
    const track = await api.track(events[0].icao24);
    expect(track.points.length).toBeGreaterThan(3);
    expect((await api.raw(track.points[3].raw_ref)).hex).toMatch(/^[0-9A-F]+$/);
  });

  it("returns a clear message for an unknown raw_ref", async () => {
    await expect(api.raw("rec01:999")).rejects.toThrow("Record not found: rec01:999");
  });
});
