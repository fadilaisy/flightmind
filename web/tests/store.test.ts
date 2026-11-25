import { describe, expect, it, vi } from "vitest";
import { createStore } from "../src/state/store";
import type { KeyValueStorage } from "../src/domain/eventState";

function memory(): KeyValueStorage {
  const m = new Map<string, string>();
  return { getItem: (k) => m.get(k) ?? null, setItem: (k, v) => void m.set(k, v) };
}

describe("store", () => {
  it("tells every subscriber when scrubTs changes", () => {
    const s = createStore(memory());
    const a = vi.fn();
    const b = vi.fn();
    s.subscribe(a);
    s.subscribe(b);
    s.setScrubTs("2026-10-03T08:00:20Z");
    expect(a).toHaveBeenCalledTimes(1);
    expect(b).toHaveBeenCalledTimes(1);
    expect(s.getState().scrubTs).toBe("2026-10-03T08:00:20Z");
  });

  it("tells every subscriber when rawRef changes", () => {
    const s = createStore(memory());
    const a = vi.fn();
    const b = vi.fn();
    s.subscribe(a);
    s.subscribe(b);
    s.setRawRef("rec1:4");
    expect(a).toHaveBeenCalledTimes(1);
    expect(b).toHaveBeenCalledTimes(1);
    expect(s.getState().rawRef).toBe("rec1:4");
  });

  it("stops telling a subscriber after it unsubscribes", () => {
    const s = createStore(memory());
    const a = vi.fn();
    const off = s.subscribe(a);
    off();
    s.setRawRef("rec1:1");
    expect(a).not.toHaveBeenCalled();
  });

  it("sets event and aircraft together", () => {
    const s = createStore(memory());
    s.selectEvent("e1", "8a0213");
    expect(s.getState()).toMatchObject({ eventId: "e1", icao24: "8a0213" });
  });

  it("keeps event states after a reload", () => {
    const storage = memory();
    const first = createStore(storage);
    first.setEventState("e1", "confirmed");
    first.setEventState("e2", "dismissed");
    first.setEventState("e2", "to_review");
    const reloaded = createStore(storage);
    expect(reloaded.getState().eventStates).toEqual({ e1: "confirmed" });
  });
});
