import { describe, expect, it } from "vitest";
import { buildRecordTree } from "../src/components/RecordTree";
import { recordItems, itemRanges } from "../src/domain/recordItems";
import { eventChipLabel, wiresharkFilter } from "../src/domain/wireshark";
import mini from "./fixtures/mini.json";

const record = mini.raw["rec01:3"];
const event = mini.events[0];

describe("records", () => {
  it("builds the Wireshark filter for the flagged window of the event", () => {
    expect(wiresharkFilter(event)).toBe("asterix.021_080 == 0x8A0213 && i021_071 >= 08:00:20Z && i021_071 <= 08:00:40Z");
  });

  it("names an event on a chip without saying what the aircraft did", () => {
    expect(eventChipLabel({ callsign: "GIA412", icao24: "8a0213", type: "go_around" })).toBe("GIA412 go-around flag");
    expect(eventChipLabel({ callsign: null, icao24: "8a0213", type: "holding" })).toBe("8a0213 holding flag");
  });

  it("lists one item per decoded value with name, unit and LSB from itemMeta", () => {
    const items = recordItems(record);
    expect(items.map((i) => i.id)).toEqual(["I021/071", "I021/130"]);
    expect(items[0]).toMatchObject({ name: "Time of applicability for position", lsb: "1/128 s", value: "08:00:30.00Z" });
    expect(items[1].value).toBe("\u22126.15000, " + items[1].value.split(", ")[1]);
    expect(items[1].value).not.toContain("deg");
    expect(items[0].definition).toContain("seconds since midnight UTC");
  });

  it("has no item byte ranges, because the API gives none", () => {
    expect(itemRanges(record)).toEqual([]);
  });

  it("builds the Block > Record > Item tree", () => {
    const tree = buildRecordTree(record as never);
    expect(tree.label).toContain("recording rec01");
    const rec = tree.children[0];
    expect(rec.label).toContain("Record 3");
    expect(rec.label).toContain("10 bytes");
    expect(rec.children).toHaveLength(2);
    expect(rec.children[0].children.map((c) => c.label)).toContain("Raw: not in the API response");
  });
});
