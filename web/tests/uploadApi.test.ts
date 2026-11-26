import { describe, expect, it } from "vitest";
import mini from "./fixtures/mini.json";
import { ApiError } from "../src/api/client";
import { MOCK_TIMELINE, mockApi, type MockData } from "../src/api/mockClient";
import { PART_SIZE_BYTES } from "../src/api/uploadTypes";

function setup() {
  let t = 1_000_000;
  const api = mockApi(mini as unknown as MockData, { now: () => t });
  return { api, advance: (ms: number) => (t += ms) };
}

async function status(err: Promise<unknown>): Promise<number> {
  try {
    await err;
  } catch (e) {
    return (e as ApiError).status;
  }
  return 0;
}

describe("mock recordings", () => {
  it("creates an uploading recording with the contract part size", async () => {
    const { api } = setup();
    const r = await api.createRecording({ filename: "a.pcap", size_bytes: 100 });
    expect(r.id).toMatch(/^r[0-9a-f]{10}$/);
    expect(r.status).toBe("uploading");
    expect(r.part_size_bytes).toBe(PART_SIZE_BYTES);
    expect(r.format).toBe("pcap");
    expect(r.streams).toEqual([]);
  });

  it("moves through the stages to ready in about 10 s", async () => {
    const { api, advance } = setup();
    const { id } = await api.createRecording({ filename: "a.pcapng", size_bytes: 10 });
    await api.uploadPart(id, 0, new Blob([new Uint8Array(10)]));
    expect((await api.getRecording(id)).bytes_received).toBe(10);
    expect((await api.completeRecording(id)).status).toBe("scanning");
    advance(MOCK_TIMELINE.scanMs);
    const scanned = await api.getRecording(id);
    expect(scanned.status).toBe("scanned");
    expect(scanned.streams.filter((s) => s.supported)).toHaveLength(1);

    await api.processRecording(id, "s1");
    const seen: string[] = [];
    let total = 0;
    for (let i = 0; i < 12; i++) {
      const r = await api.getRecording(id);
      if (seen.at(-1) !== r.status) seen.push(r.status);
      if (r.status === "ready") break;
      advance(1000);
      total += 1000;
    }
    expect(seen).toEqual(["queued", "decoding", "filtering", "detecting", "storing", "ready"]);
    expect(total).toBeGreaterThanOrEqual(9000);
    expect(total).toBeLessThanOrEqual(11000);
    const ready = await api.getRecording(id);
    expect(ready.progress).toEqual({ records_done: ready.record_count, records_total: ready.record_count });
    expect(ready.event_count).toBe(1);
    expect(ready.first_ts).toBe("2026-10-13T08:00:00Z");
  });

  it("reports progress while decoding", async () => {
    const { api, advance } = setup();
    const { id } = await api.createRecording({ filename: "a.ast", size_bytes: 10 });
    await api.completeRecording(id);
    advance(MOCK_TIMELINE.scanMs);
    await api.processRecording(id, "s1");
    advance(MOCK_TIMELINE.queuedMs + 1500);
    const r = await api.getRecording(id);
    expect(r.status).toBe("decoding");
    expect(r.progress!.records_done).toBeGreaterThan(0);
    expect(r.progress!.records_done).toBeLessThan(r.progress!.records_total);
  });

  it("ends bad.pcap in failed with the error text", async () => {
    const { api, advance } = setup();
    const { id } = await api.createRecording({ filename: "bad.pcap", size_bytes: 10 });
    await api.completeRecording(id);
    advance(MOCK_TIMELINE.scanMs);
    const r = await api.getRecording(id);
    expect(r.status).toBe("failed");
    expect(r.error).toBe("No CAT021 records found in bad.pcap");
  });

  it("gives 413 over 2048 MB and 415 for a wrong extension", async () => {
    const { api } = setup();
    expect(await status(api.createRecording({ filename: "big.pcap", size_bytes: 3 * 1024 ** 3 }))).toBe(413);
    expect(await status(api.createRecording({ filename: "notes.txt", size_bytes: 10 }))).toBe(415);
    expect(await api.listRecordings()).toEqual([]);
  });

  it("answers 409 for an out of order part and 404 for an unknown id", async () => {
    const { api } = setup();
    const { id } = await api.createRecording({ filename: "a.pcap", size_bytes: 10 });
    expect(await status(api.uploadPart(id, 1, new Blob([])))).toBe(409);
    expect(await status(api.getRecording("r0000000000"))).toBe(404);
  });

  it("refuses to process before the scan is done", async () => {
    const { api } = setup();
    const { id } = await api.createRecording({ filename: "a.pcap", size_bytes: 10 });
    expect(await status(api.processRecording(id, "s1"))).toBe(409);
  });

  it("lists newest first and survives a reload through storage", async () => {
    const store = new Map<string, string>();
    const storage = { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => void store.set(k, v) };
    const first = mockApi(mini as unknown as MockData, { now: () => 5, storage });
    const a = await first.createRecording({ filename: "a.pcap", size_bytes: 1 });
    const b = await first.createRecording({ filename: "b.pcap", size_bytes: 1 });
    expect((await first.listRecordings()).map((r) => r.id)).toEqual([b.id, a.id]);
    const reloaded = mockApi(mini as unknown as MockData, { now: () => 5, storage });
    expect((await reloaded.getRecording(a.id)).filename).toBe("a.pcap");
  });

  it("serves the sample dataset and builds recording URLs", async () => {
    const { api } = setup();
    expect(await api.events("rabc")).toHaveLength(1);
    expect((await api.compression("rec01")).events_kept).toBe(1);
    expect(api.streamUrl("rabc")).toBe("/api/stream?recording=rabc");
  });
});
