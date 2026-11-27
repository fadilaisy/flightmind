// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { describe, expect, it, vi } from "vitest";
import { ApiError, type Api } from "../src/api/client";
import type { Recording } from "../src/api/uploadTypes";
import { RecordingPicker } from "../src/components/RecordingPicker";
import { MSG, POLL_MS, followRecording, nextAction, uploadRecording, UploadError } from "../src/domain/upload";
import { LoadView } from "../src/views/LoadView";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function rec(over: Partial<Recording> = {}): Recording {
  return {
    id: "r0123456789", filename: "a.pcap", size_bytes: 10, bytes_received: 0, part_size_bytes: 4, format: "pcap",
    status: "uploading", progress: null, error: null, record_count: null, event_count: null, first_ts: null, last_ts: null,
    created_at: "2026-11-26T07:00:00Z", streams: [], ...over,
  };
}
const stream = (id: string, supported: boolean) => ({
  id, src: "a", dst: "b", category: supported ? 21 : 62, sac: 1, sic: 2, frames: 1, records: 1, supported,
});
const file = (name: string, size: number) => new File([new Uint8Array(size)], name, { lastModified: Date.UTC(2026, 9, 3) });
const noDelay = () => Promise.resolve();
const flush = () => act(async () => { await new Promise((r) => setTimeout(r, 0)); });

describe("part upload", () => {
  it("sends part_size_bytes slices one after another, then completes", async () => {
    const calls: string[] = [];
    const api = {
      createRecording: async () => rec(),
      uploadPart: async (_id: string, n: number, b: Blob) => void calls.push(`${n}:${b.size}`),
      completeRecording: async () => (calls.push("complete"), rec({ status: "scanning" })),
    } as unknown as Api;
    const progress: number[] = [];
    const out = await uploadRecording(api, file("a.pcap", 10), { delay: noDelay, onProgress: (p) => progress.push(p.sent) });
    expect(calls).toEqual(["0:4", "1:4", "2:2", "complete"]);
    expect(progress).toEqual([0, 4, 8, 10]);
    expect(out.status).toBe("scanning");
  });

  it("retries a failed part up to 3 times", async () => {
    let fails = 3;
    const uploadPart = vi.fn(async (_i: string, n: number) => {
      if (n === 1 && fails-- > 0) throw new ApiError(503, "u", "Request failed: 503");
    });
    const api = { createRecording: async () => rec(), uploadPart, completeRecording: async () => rec() } as unknown as Api;
    await uploadRecording(api, file("a.pcap", 10), { delay: noDelay });
    expect(uploadPart.mock.calls.filter((c) => c[1] === 1)).toHaveLength(4);
  });

  it("gives up after the third retry", async () => {
    const uploadPart = vi.fn(async () => {
      throw new ApiError(503, "u", "Request failed: 503 u");
    });
    const complete = vi.fn();
    const api = { createRecording: async () => rec(), uploadPart, completeRecording: complete } as unknown as Api;
    await expect(uploadRecording(api, file("a.pcap", 10), { delay: noDelay })).rejects.toBeInstanceOf(UploadError);
    expect(uploadPart).toHaveBeenCalledTimes(4);
    expect(complete).not.toHaveBeenCalled();
  });

  it("does not retry a 409", async () => {
    const uploadPart = vi.fn(async () => {
      throw new ApiError(409, "u", "Request failed: 409 u");
    });
    const api = { createRecording: async () => rec(), uploadPart } as unknown as Api;
    await expect(uploadRecording(api, file("a.pcap", 10), { delay: noDelay })).rejects.toThrow("409");
    expect(uploadPart).toHaveBeenCalledTimes(1);
  });

  it.each([408, 429, 503])("retries a %i", async (status) => {
    const uploadPart = vi.fn()
      .mockRejectedValueOnce(new ApiError(status, "u", `Request failed: ${status} u`))
      .mockResolvedValue(undefined);
    const api = { createRecording: async () => rec(), uploadPart, completeRecording: async () => rec({ status: "scanning" }) } as unknown as Api;
    await uploadRecording(api, file("a.pcap", 4), { delay: noDelay });
    expect(uploadPart).toHaveBeenCalledTimes(2);
  });
  it("turns 413 and 415 into their own sentences", async () => {
    const mk = (status: number) => ({ createRecording: async () => Promise.reject(new ApiError(status, "u", "x")) }) as unknown as Api;
    await expect(uploadRecording(mk(413), file("a.pcap", 1))).rejects.toThrow(MSG.tooLarge);
    await expect(uploadRecording(mk(415), file("a.pcap", 1))).rejects.toThrow(MSG.badType);
    const bad = { createRecording: async () => rec(), uploadPart: async () => {}, completeRecording: async () => Promise.reject(new ApiError(415, "u", "x")) } as unknown as Api;
    await expect(uploadRecording(bad, file("a.pcap", 1), { delay: noDelay })).rejects.toThrow(MSG.notCat021);
  });
});

describe("polling", () => {
  it("polls every 2 s and stops at scanned without processing", async () => {
    const seq = [rec({ status: "scanning" }), rec({ status: "scanned", streams: [stream("s1", true), stream("s2", false)] })];
    let i = 0;
    const processRecording = vi.fn();
    const api = { getRecording: async () => seq[Math.min(i++, seq.length - 1)], processRecording } as unknown as Api;
    const sleeps: number[] = [];
    const out = await followRecording(api, "r0123456789", { onUpdate: () => {}, sleep: async (ms) => void sleeps.push(ms) });
    expect(out.kind).toBe("scanned");
    expect(sleeps).toEqual([POLL_MS]);
    expect(POLL_MS).toBe(2000);
    expect(processRecording).not.toHaveBeenCalled();
  });

  it("polls until ready when the recording is already being processed", async () => {
    const seq = [rec({ status: "decoding" }), rec({ status: "filtering" }), rec({ status: "ready" })];
    let i = 0;
    const api = { getRecording: async () => seq[Math.min(i++, seq.length - 1)] } as unknown as Api;
    const out = await followRecording(api, "r0123456789", { onUpdate: () => {}, sleep: noDelay });
    expect(out.kind).toBe("ready");
  });

  it("never starts processing on its own, whatever the streams are", () => {
    expect(nextAction(rec({ status: "scanned", streams: [stream("a", true)] })).kind).toBe("scanned");
    expect(nextAction(rec({ status: "scanned", streams: [stream("a", true), stream("b", true)] })).kind).toBe("scanned");
    expect(nextAction(rec({ status: "scanned", streams: [stream("b", false)] })).kind).toBe("scanned");
  });
  it("returns the error text of a failed recording as written", async () => {
    const api = { listRecordings: async () => [], getRecording: async () => rec({ status: "failed", error: "No CAT021 records found in bad.pcap" }) } as unknown as Api;
    const out = await followRecording(api, "r0123456789", { onUpdate: () => {}, sleep: noDelay });
    expect(out).toMatchObject({ kind: "failed", error: "No CAT021 records found in bad.pcap" });
  });

  it("stops when asked", async () => {
    const api = { getRecording: async () => rec({ status: "decoding" }) } as unknown as Api;
    let n = 0;
    const out = await followRecording(api, "r0123456789", { onUpdate: () => {}, sleep: noDelay, shouldStop: () => n++ > 2 });
    expect(out.kind).toBe("stopped");
  });
});

function mount(node: React.ReactNode) {
  const host = document.createElement("div");
  document.body.appendChild(host);
  const root = createRoot(host);
  act(() => root.render(node));
  return { host, root, done: () => act(() => root.unmount()) };
}

describe("LoadView", () => {
  it("shows the drop zone with Choose file and the accepted types", () => {
    const { host, done } = mount(<LoadView api={{ listRecordings: async () => [] } as unknown as Api} onScanned={() => {}} onReady={() => {}} onReset={() => {}} />);
    expect(host.textContent).toContain("Choose file");
    expect(host.textContent).toContain("up to 2 GB");
    expect(host.querySelector("input[type=file]")?.getAttribute("accept")).toBe(".pcap,.pcapng,.atx,.ast,.bin");
    done();
  });

  it("asks for a recording date on a raw file, defaulting to its modified date", async () => {
    const { host, done } = mount(<LoadView api={{} as Api} onScanned={() => {}} onReady={() => {}} onReset={() => {}} start={{ file: file("a.ast", 5) }} />);
    await flush();
    expect(host.textContent).toContain("Recording date");
    expect((host.querySelector("input[type=date]") as HTMLInputElement).value).toBe("2026-10-03");
    done();
  });

  it("shows a failed recording's error and Try another file, which calls onReset", async () => {
    const api = { listRecordings: async () => [], getRecording: async () => rec({ status: "failed", error: "No CAT021 records found in bad.pcap" }) } as unknown as Api;
    const onReset = vi.fn();
    const { host, done } = mount(<LoadView api={api} follow="r0123456789" onScanned={() => {}} onReady={() => {}} onReset={onReset} />);
    await flush();
    expect(host.querySelector(".statebox.error")?.textContent).toContain("No CAT021 records found in bad.pcap");
    const btn = [...host.querySelectorAll("button")].find((b) => b.textContent === "Try another file")!;
    act(() => btn.click());
    expect(onReset).toHaveBeenCalled();
    expect(host.textContent).toContain("Choose file");
    done();
  });

  it("fails a recording left in uploading instead of polling forever", async () => {
    const getRecording = vi.fn(async () => rec({ status: "uploading", bytes_received: 4 }));
    const onReset = vi.fn();
    const { host, done } = mount(<LoadView api={{ listRecordings: async () => [], getRecording } as unknown as Api} follow="r0123456789" onScanned={() => {}} onReady={() => {}} onReset={onReset} />);
    await flush();
    expect(getRecording).toHaveBeenCalledTimes(1);
    expect(host.querySelector(".statebox.error")?.textContent).toContain("This upload did not finish. Try another file.");
    const btn = [...host.querySelectorAll("button")].find((b) => b.textContent === "Try another file")!;
    act(() => btn.click());
    expect(onReset).toHaveBeenCalled();
    done();
  });
  it("says the file is larger than 2 GB for a 413 and names the types for a 415", async () => {
    const big = file("a.pcap", 1);
    Object.defineProperty(big, "size", { value: 3 * 1024 ** 3 });
    const a = mount(<LoadView api={{} as Api} start={{ file: big }} onScanned={() => {}} onReady={() => {}} onReset={() => {}} />);
    await flush();
    expect(a.host.querySelector(".statebox.error")?.textContent).toContain("This file is larger than 2 GB.");
    a.done();
    const b = mount(<LoadView api={{} as Api} start={{ file: file("notes.txt", 1) }} onScanned={() => {}} onReady={() => {}} onReset={() => {}} />);
    await flush();
    expect(b.host.querySelector(".statebox.error")?.textContent).toContain("FlightMind reads .pcap, .pcapng, .atx, .ast and .bin files.");
    b.done();
    const server = { createRecording: async () => Promise.reject(new ApiError(413, "u", "x")) } as unknown as Api;
    const c = mount(<LoadView api={server} start={{ file: file("a.pcap", 1) }} onScanned={() => {}} onReady={() => {}} onReset={() => {}} />);
    await flush();
    expect(c.host.querySelector(".statebox.error")?.textContent).toContain("This file is larger than 2 GB.");
    c.done();
  });

  it("uploads, shows bytes sent and the stage, and calls onReady", async () => {
    let polls = 0;
    const api = {
      createRecording: async () => rec({ size_bytes: 3 }),
      uploadPart: async () => {},
      completeRecording: async () => rec({ status: "scanning" }),
      getRecording: async () => rec({ status: ++polls > 1 ? "ready" : "decoding", progress: { records_done: 1200, records_total: 5000 }, size_bytes: 3 }),
    } as unknown as Api;
    const onReady = vi.fn();
    vi.useFakeTimers();
    const { host, done } = mount(<LoadView api={api} start={{ file: file("a.pcap", 3) }} onScanned={() => {}} onReady={onReady} onReset={() => {}} />);
    await act(async () => { await vi.advanceTimersByTimeAsync(10); });
    expect(host.textContent).toContain("1,200 of 5,000 records");
    expect(host.querySelector("li.now")?.textContent).toContain("Decoding");
    await act(async () => { await vi.advanceTimersByTimeAsync(2100); });
    expect(onReady).toHaveBeenCalledWith("r0123456789");
    vi.useRealTimers();
    done();
  });
});

describe("RecordingPicker", () => {
  it("lists recordings with filename, size, date and status, and picking one reports its id", async () => {
    const list = [
      rec({ id: "r1111111111", filename: "wiii.pcapng", size_bytes: 327_155_712, status: "ready", first_ts: "2026-10-03T00:00:00Z" }),
      rec({ id: "r2222222222", filename: "bad.pcap", status: "failed" }),
    ];
    const api = { listRecordings: async () => list } as unknown as Api;
    const onSelect = vi.fn();
    const { host, done } = mount(<RecordingPicker api={api} selectedId={null} onSelect={onSelect} onFile={() => {}} onClose={() => {}} />);
    await flush();
    const rows = [...host.querySelectorAll("button.pickrow")];
    expect(rows).toHaveLength(2);
    expect(rows[0].textContent).toContain("wiii.pcapng");
    expect(rows[0].textContent).toContain("312.0 MB");
    expect(rows[0].textContent).toContain("2026-10-03");
    expect(rows[0].textContent).toContain("Ready");
    expect(rows[1].textContent).toContain("Failed");
    act(() => (rows[1] as HTMLElement).click());
    expect(onSelect).toHaveBeenCalledWith("r2222222222");
    expect(host.textContent).toContain("Choose file");
    done();
  });
});
