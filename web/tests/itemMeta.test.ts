import { describe, expect, it } from "vitest";
import { describeDecoded, itemForKey, itemMeta } from "../src/domain/itemMeta";

describe("itemMeta", () => {
  it("names I021/071 with unit, LSB and datum", () => {
    expect(itemMeta("I021/071")).toMatchObject({ unit: "s", lsb: "1/128 s", datum: "UTC, since midnight" });
  });
  it("gives I021/040 a name and no unit", () => {
    const m = itemMeta("I021/040");
    expect(m?.name).toBe("Target report descriptor");
    expect(m?.unit).toBeNull();
  });
  it("covers the items the UI shows", () => {
    for (const id of ["I021/070", "I021/080", "I021/130", "I021/140", "I021/145", "I021/170"]) {
      expect(itemMeta(id), id).toBeDefined();
    }
  });
  it("returns nothing for an unknown item", () => {
    expect(itemMeta("I021/999")).toBeUndefined();
    expect(itemForKey("synthetic")).toBeUndefined();
  });
  it("maps the mock plain keys to items", () => {
    expect(itemForKey("lat")?.id).toBe("I021/130");
    expect(itemForKey("baro_alt_ft")?.id).toBe("I021/145");
    expect(itemForKey("icao24")?.id).toBe("I021/080");
  });
});

describe("describeDecoded", () => {
  it("merges latitude and longitude into one I021/130 row", () => {
    const rows = describeDecoded({ "I021/130": { lat: -6.15, lon: 106.65 } });
    expect(rows.map((r) => [r.path, r.value])).toEqual([["I021/130", "\u22126.15000, 106.65000"]]);
  });
  it("uses the ft unit for the plain altitude key and keeps unknown keys raw", () => {
    const rows = describeDecoded({ baro_alt_ft: 1250, synthetic: true });
    expect(rows[0]).toMatchObject({ value: "1,250", unit: "ft" });
    expect(rows[1]).toMatchObject({ item: undefined, value: "true", unit: null });
  });
});
