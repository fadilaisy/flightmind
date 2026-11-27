// @vitest-environment jsdom
import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

// maplibre, uPlot and WebGL need a real browser. These stubs let each view mount in jsdom.
vi.mock("maplibre-gl", () => {
  const chain: object = new Proxy(function () {}, { get: () => () => chain, apply: () => chain });
  class Stub {
    constructor() {
      return chain as unknown as Stub;
    }
  }
  return { Map: Stub, Popup: Stub, ScaleControl: Stub, setWorkerUrl: () => {} };
});
vi.mock("maplibre-gl/dist/maplibre-gl-worker.mjs?url", () => ({ default: "worker.js" }));
vi.mock("uplot", () => ({
  default: class {
    bbox = { left: 0, top: 0, width: 100, height: 40 };
    destroy() {}
    redraw() {}
    valToPos() {
      return 0;
    }
  },
}));
vi.mock("three", async (importOriginal) => {
  const real = await importOriginal<typeof import("three")>();
  class FakeRenderer {
    domElement = document.createElement("canvas");
    setPixelRatio() {}
    setClearColor() {}
    setSize() {}
    render() {}
    dispose() {}
    forceContextLoss() {}
  }
  return { ...real, WebGLRenderer: FakeRenderer };
});

import { App } from "../src/App";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

beforeAll(() => {
  class RO {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  (globalThis as { ResizeObserver?: unknown }).ResizeObserver = RO;
  const ctx = new Proxy({}, { get: () => () => ({ addColorStop() {} }), set: () => true });
  HTMLCanvasElement.prototype.getContext = (() => ctx) as unknown as typeof HTMLCanvasElement.prototype.getContext;
});

let root: Root | null = null;
afterEach(() => {
  if (root) act(() => root!.unmount());
  root = null;
  document.body.replaceChildren();
});

async function open(search: string, seed = true): Promise<HTMLElement> {
  // The app opens a recording first. Seed one that finished processing long ago, so each tab shows the sample data.
  localStorage.clear();
  if (seed) localStorage.setItem(
    "flightmind.mockRecordings",
    JSON.stringify([
      { id: "rsmoke", filename: "sample.pcap", size: 1, format: "pcap", createdMs: 0, received: 1, nextPart: 1, completedMs: 1, processedMs: 2 },
    ]),
  );
  window.history.replaceState(null, "", seed ? `/${search}&recording=rsmoke` : `/${search}`);
  const host = document.createElement("div");
  document.body.appendChild(host);
  root = createRoot(host);
  await act(async () => {
    root!.render(createElement(App));
  });
  // Let the mock API promises settle (events, event detail, track, record).
  for (let i = 0; i < 6; i++) await act(async () => {});
  return host;
}

describe("smoke: each tab renders with the mock client", () => {
  const cases: [string, string, string][] = [
    ["Events", "?tab=events", "GIA412"],
    ["Trajectory, map", "?tab=trajectory", "GIA412"],
    ["Trajectory, 3D", "?tab=trajectory&view=3d", "GIA412"],
    ["Records", "?tab=records", "Records"],
  ];
  for (const [name, search, text] of cases) {
    it(`${name} opens without throwing or console errors`, async () => {
      const errors = vi.spyOn(console, "error").mockImplementation(() => {});
      const host = await open(search);
      expect(host.textContent).toContain(text);
      expect(host.querySelector(".statebox.error")).toBeNull();
      expect(errors).not.toHaveBeenCalled();
      errors.mockRestore();
    });
  }
});

describe("smoke: Built with Kiro without a recording", () => {
  it("opens ?tab=kiro with nothing loaded, tab selected, no Load screen", async () => {
    const errors = vi.spyOn(console, "error").mockImplementation(() => {});
    const host = await open("?tab=kiro", false);
    expect(host.textContent).toContain("Built with Kiro");
    expect(host.querySelector("#tab-kiro")?.getAttribute("aria-selected")).toBe("true");
    expect(host.querySelector("#tab-load")?.getAttribute("aria-selected")).not.toBe("true");
    expect(host.textContent).not.toContain("Drop a CAT021 file");
    expect(host.textContent).not.toContain("Load a recording");
    expect(host.querySelector(".statebox.error")).toBeNull();
    expect(errors).not.toHaveBeenCalled();
    errors.mockRestore();
  });
});