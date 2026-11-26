// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { Scrubber, snapIndex, windowIndexes } from "../src/components/Scrubber";
import { getStore } from "../src/state/store";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const points = Array.from({ length: 25 }, (_, i) => ({
  ts: new Date(Date.UTC(2026, 9, 13, 8, 0, i * 10)).toISOString().replace(".000Z", "Z"),
  lat: -6.2 + i * 0.004,
  lon: 106.6 + i * 0.004,
  alt_ft: 3000 - i * 50,
  raw_ref: `rec01:${i}`,
}));
const event = { start_ts: points[3].ts, end_ts: points[5].ts };

let host: HTMLDivElement;
let root: Root;
const slider = () => host.querySelector<HTMLInputElement>('input[type="range"]')!;

function key(k: string, shiftKey = false) {
  act(() => {
    slider().dispatchEvent(new KeyboardEvent("keydown", { key: k, shiftKey, bubbles: true, cancelable: true }));
  });
}

beforeEach(() => {
  getStore().setScrubTs(null);
  host = document.createElement("div");
  document.body.appendChild(host);
  root = createRoot(host);
  act(() => root.render(<Scrubber points={points} event={event} />));
});
afterEach(() => {
  act(() => root.unmount());
  host.remove();
});

describe("snapIndex", () => {
  it("takes the nearest point at or before the time", () => {
    expect(snapIndex(points, "2026-10-13T08:00:29Z")).toBe(2);
    expect(snapIndex(points, points[4].ts)).toBe(4);
    expect(snapIndex(points, "2026-10-13T07:00:00Z")).toBe(0);
    expect(snapIndex(points, null)).toBe(0);
  });
  it("finds the flagged window by index, edges included", () => {
    expect(windowIndexes(points, event)).toEqual([3, 5]);
    expect(windowIndexes(points, { start_ts: "2030-01-01T00:00:00Z", end_ts: "2030-01-01T00:00:10Z" })).toBeNull();
  });
});

describe("Scrubber", () => {
  it("starts on the first point and writes scrubTs", () => {
    expect(getStore().getState().scrubTs).toBe(points[0].ts);
    expect(host.textContent).toContain("08:00:00 UTC");
    expect(host.textContent).toContain("08:00:00 to 08:04:00 UTC");
  });
  it("moves one point with an arrow key", () => {
    key("ArrowRight");
    expect(getStore().getState().scrubTs).toBe(points[1].ts);
    key("ArrowLeft");
    expect(getStore().getState().scrubTs).toBe(points[0].ts);
  });
  it("moves ten points with Shift and stops at the ends", () => {
    key("ArrowRight", true);
    expect(getStore().getState().scrubTs).toBe(points[10].ts);
    key("ArrowRight", true);
    key("ArrowRight", true);
    expect(getStore().getState().scrubTs).toBe(points[24].ts);
    key("ArrowLeft", true);
    expect(getStore().getState().scrubTs).toBe(points[14].ts);
  });
  it("snaps a time between points to the one before it", () => {
    act(() => getStore().setScrubTs("2026-10-13T08:00:34Z"));
    expect(slider().value).toBe("3");
  });
  it("moves when the slider is dragged", () => {
    const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
    act(() => {
      set.call(slider(), "7");
      slider().dispatchEvent(new Event("input", { bubbles: true }));
    });
    expect(getStore().getState().scrubTs).toBe(points[7].ts);
  });
  it("shades the flagged window on the slider", () => {
    const band = host.querySelector<HTMLElement>(".scrubband")!;
    expect(band.style.left).toBe("12.5%");
  });
});
