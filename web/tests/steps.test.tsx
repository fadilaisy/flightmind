// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { describe, expect, it, vi } from "vitest";
import mini from "./fixtures/mini.json";
import type { Api } from "../src/api/client";
import { MOCK_TIMELINE, mockApi, type MockData } from "../src/api/mockClient";
import type { Recording } from "../src/api/uploadTypes";
import { pageLine } from "../src/components/QuarantineList";
import { rawStreamId } from "../src/domain/upload";
import { CleanView } from "../src/views/CleanView";
import { ExportView, exportFiles } from "../src/views/ExportView";
import { PreviewView } from "../src/views/PreviewView";
import { Shell } from "../src/views/Shell";
import { StreamsView } from "../src/views/StreamsView";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function mount(node: React.ReactNode) {
  const host = document.createElement("div");
  document.body.appendChild(host);
  const root = createRoot(host);
  act(() => root.render(node));
  return { host, done: () => act(() => root.unmount()) };
}
const flush = () => act(async () => { await new Promise((r) => setTimeout(r, 0)); });

async function scannedRecording(filename = "a.pcapng") {
  let t = 1_000_000;
  const api = mockApi(mini as unknown as MockData, { now: () => t });
  const { id } = await api.createRecording({ filename, size_bytes: 327_155_712 });
  await api.completeRecording(id);
  t += MOCK_TIMELINE.scanMs;
  return { api, id, advance: (ms: number) => (t += ms), recording: await api.getRecording(id) as Recording };
}

describe("StreamsView", () => {
  it("lists streams, offers Use on supported rows and says not supported yet on the rest", async () => {
    const { recording } = await scannedRecording();
    const onUse = vi.fn();
    const { host, done } = mount(<StreamsView recording={recording} onUse={onUse} onAnotherFile={() => {}} />);
    expect(host.textContent).toContain("UDP streams found");
    expect(host.querySelectorAll("tbody tr")).toHaveLength(2);
    expect(host.textContent).toContain("10.4.1.20:8600");
    expect(host.textContent).toContain("CAT021");
    expect(host.textContent).toContain("25 / 4");
    expect(host.textContent).toContain("not supported yet");
    expect(host.querySelectorAll("tbody button")).toHaveLength(1);
    act(() => (host.querySelector("tbody button") as HTMLElement).click());
    expect(onUse).toHaveBeenCalledWith("s1");
    const decode = [...host.querySelectorAll("button")].find((b) => b.textContent === "Decode CAT021 stream")!;
    act(() => decode.click());
    expect(onUse).toHaveBeenCalledTimes(2);
    done();
  });

  it("knows a raw file by its single stream raw", async () => {
    const raw = await scannedRecording("a.ast");
    expect(rawStreamId(raw.recording)).toBe("raw");
    const pcap = await scannedRecording("a.pcap");
    expect(rawStreamId(pcap.recording)).toBeNull();
  });
});

describe("PreviewView", () => {
  it("shows 8 records, the quality bars and the sample sentence, then continues", async () => {
    const { api, recording } = await scannedRecording();
    const onContinue = vi.fn();
    const { host, done } = mount(<PreviewView api={api} recording={recording} streamId="s1" onContinue={onContinue} onAnotherFile={() => {}} />);
    await flush();
    expect(host.querySelectorAll("tbody tr")).toHaveLength(8);
    expect(host.querySelectorAll("[role=meter]")).toHaveLength(5);
    expect(host.textContent).toContain("sample of 5,000 records");
    expect(host.textContent).toContain("I021/130");
    expect(host.textContent).toContain("99.9%");
    act(() => ([...host.querySelectorAll("button")].find((b) => b.textContent === "Continue to cleaning") as HTMLElement).click());
    expect(onContinue).toHaveBeenCalled();
    done();
  });

  it("opens the raw record dialog from a raw_ref chip", async () => {
    const { api, recording } = await scannedRecording();
    const { host, done } = mount(<PreviewView api={api} recording={recording} streamId="s1" onContinue={() => {}} onAnotherFile={() => {}} />);
    await flush();
    act(() => (host.querySelector("tbody .chip") as HTMLElement).click());
    await flush();
    expect(document.querySelector("[role=dialog]")?.textContent).toContain("Cited record");
    done();
  });

  it("omits the sample sentence when the API gives no sample_size", async () => {
    const { api, recording } = await scannedRecording();
    const noSample = { ...api, recordingPreview: async (...a: Parameters<Api["recordingPreview"]>) => ({ ...(await api.recordingPreview(...a)), sample_size: undefined }) } as Api;
    const { host, done } = mount(<PreviewView api={noSample} recording={recording} streamId="s1" onContinue={() => {}} onAnotherFile={() => {}} />);
    await flush();
    expect(host.textContent).not.toContain("sample of");
    done();
  });
});

describe("CleanView", () => {
  it("shows the recipe, the tolerance note as text and no 10, 25 or 50 m buttons", async () => {
    const { api, recording } = await scannedRecording();
    const { host, done } = mount(<CleanView api={api} recording={recording} streamId="s1" onReady={() => {}} onReviewEvents={() => {}} />);
    await flush();
    expect(host.querySelectorAll(".steps li")).toHaveLength(4);
    expect(host.textContent).toContain("Duplicate records");
    expect(host.textContent).toContain("Tracks are reduced within 25 m");
    expect(host.textContent).toContain("smaller");
    expect([...host.querySelectorAll("button")].some((b) => /^\d+ m$/.test(b.textContent ?? ""))).toBe(false);
    done();
  });

  it("opens the paged quarantine list from a count and pages it", async () => {
    const { api, recording } = await scannedRecording();
    const { host, done } = mount(<CleanView api={api} recording={recording} streamId="s1" onReady={() => {}} onReviewEvents={() => {}} />);
    await flush();
    act(() => (host.querySelector(".countbtn") as HTMLElement).click());
    await flush();
    expect(host.querySelectorAll(".quarantine tbody tr")).toHaveLength(20);
    expect(host.textContent).toContain("1 to 20 of 1,860");
    act(() => ([...host.querySelectorAll("button")].find((b) => b.textContent === "Next") as HTMLElement).click());
    await flush();
    expect(host.textContent).toContain("21 to 40 of 1,860");
    done();
  });

  it("calls process with the chosen stream, follows the stages and calls onReady", async () => {
    const { api, id, recording } = await scannedRecording();
    const process = vi.spyOn(api, "processRecording");
    vi.useFakeTimers();
    const onReady = vi.fn();
    const { host, done } = mount(<CleanView api={api} recording={recording} streamId="s1" onReady={onReady} onReviewEvents={() => {}} />);
    await act(async () => { await vi.advanceTimersByTimeAsync(5); });
    const apply = [...host.querySelectorAll("button")].find((b) => b.textContent === "Apply and find events") as HTMLButtonElement;
    expect(apply.disabled).toBe(false);
    await act(async () => { apply.click(); await vi.advanceTimersByTimeAsync(5); });
    expect(process).toHaveBeenCalledWith(id, "s1");
    expect(host.querySelector(".applying li.now")).toBeTruthy();
    expect(onReady).not.toHaveBeenCalled();
    done();
    vi.useRealTimers();
  });

  it("reports a processing that is already done by calling onReady", async () => {
    const { api, recording } = await scannedRecording();
    const stub = { ...api, recordingRecipe: api.recordingRecipe, getRecording: async () => ({ ...recording, status: "ready" }) } as unknown as Api;
    const onReady = vi.fn();
    const { done } = mount(<CleanView api={stub} recording={{ ...recording, status: "decoding" }} streamId="s1" onReady={onReady} onReviewEvents={() => {}} />);
    await flush();
    expect(onReady).toHaveBeenCalled();
    done();
  });
});

describe("pageLine", () => {
  it("says which rows are shown", () => {
    expect(pageLine(0, 20, 1860)).toBe("1 to 20 of 1,860");
    expect(pageLine(1840, 20, 1860)).toBe("1,841 to 1,860 of 1,860");
    expect(pageLine(0, 0, 0)).toBe("0 of 0");
  });
});

describe("ExportView", () => {
  it("lists the four files and downloads the zip from Export 4 files", async () => {
    const { api, recording } = await scannedRecording();
    const ready = { ...recording, status: "ready" as const, event_count: 7 };
    const exportSpy = vi.spyOn(api, "exportRecording");
    const click = vi.fn();
    const create = vi.fn(() => "blob:x");
    (URL as unknown as { createObjectURL: unknown }).createObjectURL = create;
    (URL as unknown as { revokeObjectURL: unknown }).revokeObjectURL = () => {};
    const orig = HTMLAnchorElement.prototype.click;
    HTMLAnchorElement.prototype.click = click;
    const { host, done } = mount(<ExportView api={api} recording={ready} />);
    await flush();
    for (const n of ["cleaned.csv", "events.csv", "quarantine.csv", "recipe.json"]) expect(host.textContent).toContain(n);
    expect(host.textContent).toContain("7 rows");
    expect(host.textContent).toContain("1,860 rows");
    await act(async () => { (host.querySelector("button.solid") as HTMLElement).click(); });
    await flush();
    expect(exportSpy).toHaveBeenCalledWith(ready.id);
    expect(click).toHaveBeenCalled();
    HTMLAnchorElement.prototype.click = orig;
    done();
  });

  it("gives no size for files the API has not sized", () => {
    expect(exportFiles(null, null, null).map((f) => f.size)).toEqual([null, null, null, null]);
  });
});

describe("Shell tabs", () => {
  const api = { meta: async () => ({ mode: "replay", sim_time: "2026-10-13T08:00:00Z", recordings: ["rec01"], airports: [] }) } as unknown as Api;
  it("shows Load, Events, Trajectory and Records without a recording, and adds Preview, Clean and Export with one", () => {
    const a = mount(<Shell api={api} usingSample={false} hasRecording={false}>{() => null}</Shell>);
    expect([...a.host.querySelectorAll("[role=tab]")].map((t) => t.textContent)).toEqual(["Load", "Events", "Trajectory", "Records"]);
    a.done();
    const b = mount(<Shell api={api} usingSample={false} hasRecording>{() => null}</Shell>);
    expect([...b.host.querySelectorAll("[role=tab]")].map((t) => t.textContent)).toEqual(["Load", "Preview", "Clean", "Events", "Trajectory", "Records", "Export"]);
    b.done();
  });

  it("underlines Load on the Load screen, whatever ?tab= says", () => {
    window.history.replaceState(null, "", "?tab=trajectory");
    const { host, done } = mount(<Shell api={api} usingSample={false} hasRecording={false} activeTab="load">{(t) => <i id="t">{t}</i>}</Shell>);
    expect(host.querySelector("[role=tab].on")?.textContent).toBe("Load");
    expect(host.querySelector("#t")?.textContent).toBe("load");
    done();
  });

  it("shows sample data only when told the sample is on screen", async () => {
    const off = mount(<Shell api={api} usingSample={false}>{() => null}</Shell>);
    await flush();
    expect(off.host.textContent).not.toContain("sample data");
    off.done();
    const on = mount(<Shell api={api} usingSample recordingName="a.pcapng">{() => null}</Shell>);
    await flush();
    expect(on.host.textContent).toContain("sample data");
    on.done();
  });
});