import { describe, expect, it } from "vitest";
import { loadState, saveState, type KeyValueStorage } from "../src/domain/eventState";
import { toHexRows } from "../src/domain/hex";
import { parseRawRef } from "../src/domain/citations";

function memoryStorage(): KeyValueStorage {
  const m = new Map<string, string>();
  return { getItem: (k) => m.get(k) ?? null, setItem: (k, v) => void m.set(k, v) };
}

describe("event state", () => {
  it("defaults to To review and survives a save", () => {
    const s = memoryStorage();
    expect(loadState(s, "a")).toBe("to_review");
    saveState(s, "a", "confirmed");
    expect(loadState(s, "a")).toBe("confirmed");
    saveState(s, "a", "to_review");
    expect(loadState(s, "a")).toBe("to_review");
  });

  it("ignores broken storage", () => {
    const s = memoryStorage();
    s.setItem("flightmind.eventStates", "{not json");
    expect(loadState(s, "a")).toBe("to_review");
  });
});

describe("hex rows", () => {
  it("makes rows of 16 with offset and ASCII", () => {
    const r = toHexRows("41424300" + "00".repeat(12) + "FF");
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.rows).toHaveLength(2);
      expect(r.rows[0].ascii.startsWith("ABC.")).toBe(true);
      expect(r.rows[1].offset).toBe(16);
      expect(r.rows[1].bytes).toEqual(["FF"]);
    }
  });

  it("returns an error for odd or non-hex input", () => {
    expect(toHexRows("ABC").ok).toBe(false);
    expect(toHexRows("ZZ").ok).toBe(false);
  });
});

describe("raw_ref", () => {
  it("parses recording id and index", () => {
    expect(parseRawRef("rec01:12")).toEqual({ recordingFileId: "rec01", recordIndex: 12 });
    expect(parseRawRef("nope")).toBeNull();
    expect(parseRawRef("rec01:x")).toBeNull();
  });
});
