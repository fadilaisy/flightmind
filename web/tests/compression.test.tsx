// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { describe, expect, it } from "vitest";
import { ApiError, type Api } from "../src/api/client";
import type { CompressionReport } from "../src/api/types";
import { CompressionBadge, formatBytes, reductionFactor } from "../src/components/CompressionBadge";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const report: CompressionReport = {
  recording_id: "rec01",
  raw_bytes: 312_000_000,
  stored_bytes: 41_200_000,
  ratio: 0.132,
  max_position_error_m: 25.4,
  points_in: 270,
  points_kept: 131,
  events_total: 4,
  events_kept: 4,
};

async function mount(compression: Api["compression"]) {
  const host = document.createElement("div");
  document.body.appendChild(host);
  const root = createRoot(host);
  await act(async () => {
    root.render(<CompressionBadge api={{ compression } as unknown as Api} recordingId="rec01" />);
  });
  return { host, root };
}

describe("CompressionBadge", () => {
  it("formats sizes and the raw/stored factor", () => {
    expect(formatBytes(312_000_000)).toBe("312.0 MB");
    expect(formatBytes(41_000)).toBe("41.0 KB");
    expect(reductionFactor(report)).toBe("7.6\u00d7");
  });

  it("shows the factor, sizes, max error, points kept and the preserved pill", async () => {
    const { host, root } = await mount(() => Promise.resolve(report));
    const text = host.textContent ?? "";
    expect(host.querySelector("[data-testid=reduction-factor]")?.textContent).toBe("7.6\u00d7");
    expect(text).toContain("312.0 MB");
    expect(text).toContain("41.2 MB");
    expect(text).toContain("25 m");
    expect(text).toContain("131 of 270");
    expect(text).toContain("4 of 4 flagged windows preserved");
    expect(text).not.toContain("Mean position error");
    act(() => root.unmount());
  });

  it("says there is no report on 404", async () => {
    const { host, root } = await mount(() => Promise.reject(new ApiError(404, "/x", "No compression report for this recording")));
    expect(host.textContent).toContain("No compression report for this recording");
    act(() => root.unmount());
  });

  it("shows the error and Retry calls again", async () => {
    let calls = 0;
    const { host, root } = await mount(() => {
      calls += 1;
      return Promise.reject(new Error("Request failed: 500 /api/compression/rec01"));
    });
    expect(host.querySelector("[role=alert]")?.textContent).toContain("Request failed: 500");
    const retry = [...host.querySelectorAll("button")].find((b) => b.textContent === "Retry");
    await act(async () => retry!.click());
    expect(calls).toBe(2);
    act(() => root.unmount());
  });

  it("shows a loading line while the request is pending", async () => {
    const { host, root } = await mount(() => new Promise(() => {}));
    expect(host.textContent).toContain("Loading compression report.");
    act(() => root.unmount());
  });
});
