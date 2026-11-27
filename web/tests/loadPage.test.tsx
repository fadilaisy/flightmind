// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { describe, expect, it, vi } from "vitest";
import type { Api } from "../src/api/client";
import type { Recording } from "../src/api/uploadTypes";
import { STR } from "../src/strings";
import { LoadView } from "../src/views/LoadView";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function rec(over: Partial<Recording> = {}): Recording {
  return {
    id: "r0123456789", filename: "a.pcap", size_bytes: 10, bytes_received: 10, part_size_bytes: 4, format: "pcap",
    status: "ready", progress: null, error: null, record_count: null, event_count: null, first_ts: null, last_ts: null,
    created_at: "2026-11-26T07:00:00Z", streams: [], ...over,
  };
}
const flush = () => act(async () => { await new Promise((r) => setTimeout(r, 0)); });

async function mount(list: () => Promise<Recording[]>, onReady = vi.fn()) {
  const api = { listRecordings: list, getRecording: async () => rec({ status: "decoding" }) } as unknown as Api;
  const el = document.createElement("div");
  document.body.appendChild(el);
  const root = createRoot(el);
  await act(async () => {
    root.render(<LoadView api={api} onReady={onReady} onScanned={() => {}} onReset={() => {}} />);
  });
  await flush();
  return { el, onReady };
}
const click = (b: Element | undefined) => act(async () => void b?.dispatchEvent(new MouseEvent("click", { bubbles: true })));
const button = (el: HTMLElement, text: string) => [...el.querySelectorAll("button")].find((b) => b.textContent === text);

describe("Load page, choose phase", () => {
  it("shows the four capability cards", async () => {
    const { el } = await mount(async () => []);
    for (const t of [STR.capTracksTitle, STR.capEventsTitle, STR.cap4dTitle, STR.capRawTitle]) expect(el.textContent).toContain(t);
    expect(el.querySelectorAll(".capcard")).toHaveLength(4);
  });

  it("renders ready, processing and failed rows", async () => {
    const { el } = await mount(async () => [
      rec({ id: "rready", filename: "ready.pcap", event_count: 3, record_count: 1420318 }),
      rec({ id: "rproc", filename: "proc.pcap", status: "detecting", progress: { records_done: 40, records_total: 100 }, created_at: "2026-11-25T07:00:00Z" }),
      rec({ id: "rfail", filename: "bad.bin", status: "failed", error: "No CAT021 records found", created_at: "2026-11-24T07:00:00Z" }),
    ]);
    expect(el.textContent).toContain("3 events");
    expect(el.textContent).toContain("1,420,318 records");
    expect(button(el, "Open")).toBeTruthy();
    expect(button(el, "Follow")).toBeTruthy();
    expect(el.querySelector('[role="progressbar"]')?.getAttribute("aria-valuenow")).toBe("40");
    await click(button(el, "Details"));
    expect(el.querySelector(".rerror")?.textContent).toBe("No CAT021 records found");
  });

  it("Open calls onReady with the id", async () => {
    const { el, onReady } = await mount(async () => [rec({ id: "rready", event_count: 3 })]);
    await click(button(el, "Open"));
    expect(onReady).toHaveBeenCalledWith("rready");
  });

  it("says so when there are no recordings", async () => {
    const { el } = await mount(async () => []);
    expect(el.textContent).toContain(STR.recentEmpty);
  });

  it("shows an error with Retry", async () => {
    let fail = true;
    const { el } = await mount(async () => {
      if (fail) throw new Error("boom");
      return [];
    });
    expect(el.textContent).toContain("boom");
    fail = false;
    await click(button(el, "Retry"));
    await flush();
    expect(el.textContent).toContain(STR.recentEmpty);
  });
});