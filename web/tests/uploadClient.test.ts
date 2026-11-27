// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { httpApi } from "../src/api/client";

afterEach(() => vi.unstubAllGlobals());

function stubFetch(status = 200, body: unknown = {}) {
  const fetchMock = vi.fn().mockResolvedValue({ ok: status < 400, status, json: async () => body });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("http client recording calls", () => {
  const api = httpApi("http://x");

  it("adds ?recording= to events, tracks and stream", async () => {
    const f = stubFetch(200, []);
    await api.events("r1");
    await api.events();
    await api.track("8a0213", "r1");
    expect(f.mock.calls.map((c) => c[0])).toEqual([
      "http://x/api/events?recording=r1",
      "http://x/api/events",
      "http://x/api/tracks/8a0213?recording=r1",
    ]);
    expect(api.streamUrl("r1")).toBe("http://x/api/stream?recording=r1");
  });

  it("sends recording_id with ask and keys compression by id", async () => {
    const f = stubFetch();
    await api.ask("q", "r1");
    expect(JSON.parse(f.mock.calls[0][1].body)).toEqual({ question: "q", recording_id: "r1" });
    await api.ask("q");
    expect(JSON.parse(f.mock.calls[1][1].body)).toEqual({ question: "q" });
    await api.compression("r1");
    expect(f.mock.calls[2][0]).toBe("http://x/api/compression/r1");
  });

  it("PUTs raw bytes to the part URL and POSTs create, complete and process", async () => {
    const f = stubFetch(204);
    const blob = new Blob(["abc"]);
    await api.uploadPart("r1", 2, blob);
    expect(f.mock.calls[0][0]).toBe("http://x/api/recordings/r1/parts/2");
    expect(f.mock.calls[0][1].method).toBe("PUT");
    expect(f.mock.calls[0][1].body).toBe(blob);
    stubFetch(201, { id: "r1" });
    await api.createRecording({ filename: "a.pcap", size_bytes: 3 });
    const g = stubFetch(200, {});
    await api.processRecording("r1", "s1");
    expect(g.mock.calls[0][0]).toBe("http://x/api/recordings/r1/process");
    expect(JSON.parse(g.mock.calls[0][1].body)).toEqual({ stream_id: "s1" });
  });

  it("throws an ApiError that carries the status", async () => {
    stubFetch(413);
    await expect(api.createRecording({ filename: "a.pcap", size_bytes: 1 })).rejects.toMatchObject({ status: 413 });
  });
});
