import { describe, expect, it } from "vitest";
import mini from "./fixtures/mini.json";
import { MOCK_TIMELINE, mockApi, type MockData } from "../src/api/mockClient";
import { ApiError } from "../src/api/client";
import { crc32 } from "../src/domain/zip";

function setup() {
  let t = 1_000_000;
  const api = mockApi(mini as unknown as MockData, { now: () => t });
  return { api, advance: (ms: number) => (t += ms) };
}

async function scanned(name: string) {
  const s = setup();
  const { id } = await s.api.createRecording({ filename: name, size_bytes: 327_155_712 });
  await s.api.completeRecording(id);
  s.advance(MOCK_TIMELINE.scanMs);
  return { ...s, id };
}

describe("mock preview, recipe, quarantine and export (upload plan 6.1)", () => {
  it("offers two streams for a pcap and the single stream raw for a raw file", async () => {
    const pcap = await scanned("a.pcapng");
    const r = await pcap.api.getRecording(pcap.id);
    expect(r.streams.map((s) => [s.category, s.supported])).toEqual([[21, true], [62, false]]);
    const raw = await scanned("a.ast");
    expect((await raw.api.getRecording(raw.id)).streams.map((s) => s.id)).toEqual(["raw"]);
  });

  it("previews the first 8 records with field quality, and refuses an unsupported stream", async () => {
    const { api, id } = await scanned("a.pcapng");
    const p = await api.recordingPreview(id, "s1", 8);
    expect(p.records).toHaveLength(8);
    expect(p.field_quality.map((f) => f.item)).toEqual(["I021/130", "I021/140", "I021/145", "I021/170", "I021/040"]);
    expect(p.sample_size).toBeGreaterThan(0);
    await expect(api.recordingPreview(id, "s2")).rejects.toMatchObject({ status: 409 });
    // Every preview raw_ref opens.
    for (const r of p.records) expect((await api.raw(r.raw_ref)).raw_ref).toBe(r.raw_ref);
  });

  it("has a recipe whose set_aside counts add up to the quarantine total", async () => {
    const { api, id } = await scanned("a.pcapng");
    const recipe = await api.recordingRecipe(id);
    expect(recipe.steps.length).toBeGreaterThanOrEqual(3);
    expect(recipe.steps.length).toBeLessThanOrEqual(4);
    const sum = recipe.steps.reduce((s, x) => s + x.set_aside, 0);
    expect((await api.recordingQuarantine(id, 0, 1)).total).toBe(sum);
    // records_in falls by the previous step's set_aside.
    for (let i = 1; i < recipe.steps.length; i++) {
      expect(recipe.steps[i].records_in).toBe(recipe.steps[i - 1].records_in - recipe.steps[i - 1].set_aside);
    }
    expect(recipe.ratio).toBeCloseTo(recipe.stored_bytes / recipe.raw_bytes, 6);
  });

  it("pages the quarantine list with raw_refs that open", async () => {
    const { api, id } = await scanned("a.pcapng");
    const a = await api.recordingQuarantine(id, 0, 20);
    const b = await api.recordingQuarantine(id, 20, 20);
    expect(a.items).toHaveLength(20);
    expect(b.items).toHaveLength(20);
    expect(a.items[0].raw_ref).not.toBe(b.items[0].raw_ref);
    const last = await api.recordingQuarantine(id, a.total - 5, 20);
    expect(last.items).toHaveLength(5);
    await expect(api.raw(a.items[0].raw_ref)).resolves.toBeTruthy();
    await expect(api.recordingQuarantine("rnope", 0, 1)).rejects.toBeInstanceOf(ApiError);
  });

  it("exports a zip with the four files", async () => {
    const { api, id } = await scanned("a.pcapng");
    const blob = await api.exportRecording(id);
    const bytes = new Uint8Array(await blob.arrayBuffer());
    const text = new TextDecoder().decode(bytes);
    for (const name of ["cleaned.csv", "events.csv", "quarantine.csv", "recipe.json"]) expect(text).toContain(name);
    expect(String.fromCharCode(bytes[0], bytes[1])).toBe("PK");
    // End of central directory says 4 entries.
    const eocd = bytes.length - 22;
    expect(new DataView(bytes.buffer).getUint16(eocd + 10, true)).toBe(4);
  });

  it("computes the CRC-32 the zip format expects", () => {
    expect(crc32(new TextEncoder().encode("123456789"))).toBe(0xcbf43926);
  });
});