// @vitest-environment jsdom
import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import type { Timeline } from "../src/domain/kiroTimeline";

// The App imports every view. These stubs let it mount in jsdom (same as smoke.test.ts).
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
vi.mock("uplot", () => ({ default: class {} }));
// No recording and no API: every call fails.
vi.mock("../src/api/client", async (importOriginal) => {
  const real = await importOriginal<typeof import("../src/api/client")>();
  const down = new Proxy({}, { get: () => () => Promise.reject(new Error("API down")) });
  return { ...real, createApi: () => down };
});

import { App } from "../src/App";
import { KiroView } from "../src/views/KiroView";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const REPO = "https://github.com/example/flightmind";
const SHA = (n: number) => String(n).repeat(40).slice(0, 40);

const fixture: Timeline = {
  generatedAt: "2026-11-26T08:00:00.000Z",
  head: SHA(1),
  repo: REPO,
  mix: { spec: 2, vibe: 1, hook: 0, none: 1 },
  unclassified: 0,
  specs: [
    {
      name: "web-ui",
      title: "Requirements: web-ui (SCRUM-39)",
      tasksDone: 18,
      tasksTotal: 19,
      files: {
        requirements: ".kiro/specs/web-ui/requirements.md",
        design: ".kiro/specs/web-ui/design.md",
        tasks: ".kiro/specs/web-ui/tasks.md",
      },
      commits: [SHA(2), SHA(3)],
    },
  ],
  commits: [
    { sha: SHA(1), short: SHA(1).slice(0, 7), date: "2026-11-26", author: "a", subject: "chat fix", kind: "vibe" },
    { sha: SHA(2), short: SHA(2).slice(0, 7), date: "2026-11-26", author: "a", subject: "web-ui/4: store", kind: "spec", spec: "web-ui", task: "4" },
    { sha: SHA(3), short: SHA(3).slice(0, 7), date: "2026-11-25", author: "a", subject: "web-ui/3: app bar", kind: "spec", spec: "web-ui", task: "3" },
    { sha: SHA(4), short: SHA(4).slice(0, 7), date: "2026-11-12", author: "b", subject: "Initial commit", kind: "none", corrected: true },
  ],
  hooks: [{ file: ".kiro/hooks/raw-ref-guard.kiro.hook", name: "raw_ref guard", when: "fileEdited: services/**/*.py" }],
  steering: [".kiro/steering/ui.md"],
  sessions: 9,
};

let root: Root | null = null;
afterEach(() => {
  if (root) act(() => root!.unmount());
  root = null;
  document.body.replaceChildren();
});

async function mount(node: ReturnType<typeof createElement>): Promise<HTMLElement> {
  const host = document.createElement("div");
  document.body.appendChild(host);
  root = createRoot(host);
  await act(async () => {
    root!.render(node);
  });
  return host;
}

const links = (host: HTMLElement) => [...host.querySelectorAll("a")];
const timelineRows = (host: HTMLElement) => [...host.querySelectorAll("#kiro-timeline li[data-kind]")];

describe("Built with Kiro page", () => {
  it("shows the title, the mix counts, the total and the head commit link", async () => {
    const host = await mount(createElement(KiroView, { data: fixture }));
    expect(host.querySelector("h1")?.textContent).toBe("Built with Kiro");
    const counts = Object.fromEntries(
      [...host.querySelectorAll(".kcounts li")].map((li) => [li.querySelector("b")?.textContent, li.querySelector(".linklike")?.textContent]),
    );
    expect(counts).toEqual({ spec: "2", vibe: "1", hook: "0", none: "1" });
    expect(host.querySelector("[data-testid=kiro-total]")?.textContent).toContain("4");
    const head = links(host).find((a) => a.closest(".kmeta") !== null);
    expect(head?.textContent).toBe(SHA(1).slice(0, 7));
    expect(head?.getAttribute("href")).toBe(`${REPO}/commit/${SHA(1)}`);
  });

  it("links a spec card to its tasks.md and expands its commits", async () => {
    const host = await mount(createElement(KiroView, { data: fixture }));
    const card = host.querySelector('[data-spec="web-ui"]') as HTMLElement;
    expect(card.textContent).toContain("18 / 19");
    const tasks = links(card).filter((a) => a.getAttribute("href") === `${REPO}/blob/main/.kiro/specs/web-ui/tasks.md`);
    expect(tasks.length).toBeGreaterThan(0);
    expect(card.querySelector("ul")).toBeNull();
    const toggle = [...card.querySelectorAll("button")].find((b) => b.textContent === "2 commits")!;
    await act(async () => toggle.click());
    expect(card.querySelectorAll("li").length).toBe(2);
    expect(links(card).some((a) => a.getAttribute("href") === `${REPO}/commit/${SHA(2)}`)).toBe(true);
  });

  it("links each timeline commit to its GitHub commit URL, grouped by date", async () => {
    const host = await mount(createElement(KiroView, { data: fixture }));
    const tl = host.querySelector("#kiro-timeline") as HTMLElement;
    expect([...tl.querySelectorAll(".kday h3")].map((h) => h.textContent)).toEqual(["2026-11-26", "2026-11-25", "2026-11-12"]);
    const a = links(tl).find((x) => x.textContent === SHA(3).slice(0, 7))!;
    expect(a.getAttribute("href")).toBe(`${REPO}/commit/${SHA(3)}`);
  });

  it("shows one heading per date even when dates are not consecutive", async () => {
    const mk = (n: number, date: string) => ({ sha: SHA(n), short: SHA(n).slice(0, 7), date, author: "a", subject: `c${n}`, kind: "vibe" as const });
    const data: Timeline = {
      ...fixture,
      mix: { spec: 0, vibe: 3, hook: 0, none: 0 },
      specs: [],
      commits: [mk(5, "2026-11-26"), mk(6, "2026-11-25"), mk(7, "2026-11-26")],
    };
    const errors = vi.spyOn(console, "error").mockImplementation(() => {});
    const host = await mount(createElement(KiroView, { data }));
    const tl = host.querySelector("#kiro-timeline") as HTMLElement;
    expect([...tl.querySelectorAll(".kday h3")].map((h) => h.textContent)).toEqual(["2026-11-26", "2026-11-25"]);
    const first = tl.querySelectorAll(".kday")[0];
    expect(first.querySelectorAll("li[data-kind]").length).toBe(2);
    expect(tl.querySelectorAll(".kday")[1].querySelectorAll("li[data-kind]").length).toBe(1);
    expect(errors).not.toHaveBeenCalled();
    errors.mockRestore();
  });

  it("shows 'classified in KIRO.md' with a link on corrected commits only", async () => {
    const host = await mount(createElement(KiroView, { data: fixture }));
    const corr = links(host).filter((a) => a.textContent === "classified in KIRO.md");
    expect(corr.length).toBe(1);
    expect(corr[0].getAttribute("href")).toBe(`${REPO}/blob/main/KIRO.md`);
  });

  it("filters the timeline by kind", async () => {
    const host = await mount(createElement(KiroView, { data: fixture }));
    expect(timelineRows(host).length).toBe(4);
    const pick = async (label: string) => {
      const b = [...host.querySelectorAll(".seg button")].find((x) => x.textContent === label) as HTMLElement;
      await act(async () => b.click());
    };
    await pick("spec");
    expect(timelineRows(host).map((r) => r.getAttribute("data-kind"))).toEqual(["spec", "spec"]);
    await pick("none");
    expect(timelineRows(host).length).toBe(1);
    await pick("hook");
    expect(timelineRows(host).length).toBe(0);
    expect(host.querySelector("#kiro-timeline")?.textContent).toContain("No commits of this kind.");
    await pick("All");
    expect(timelineRows(host).length).toBe(4);
  });

  it("opening a mix count filters the timeline to that kind", async () => {
    const host = await mount(createElement(KiroView, { data: fixture }));
    const vibe = host.querySelector('.kcounts button[data-kind="vibe"]') as HTMLElement;
    await act(async () => vibe.click());
    expect(timelineRows(host).map((r) => r.getAttribute("data-kind"))).toEqual(["vibe"]);
  });

  it("footer links the hooks, steering files, session logs and KIRO.md", async () => {
    const host = await mount(createElement(KiroView, { data: fixture }));
    const hrefs = links(host).map((a) => a.getAttribute("href"));
    expect(hrefs).toContain(`${REPO}/blob/main/.kiro/hooks/raw-ref-guard.kiro.hook`);
    expect(hrefs).toContain(`${REPO}/blob/main/.kiro/steering/ui.md`);
    expect(hrefs).toContain(`${REPO}/blob/main/docs/kiro/sessions/cli/README.md`);
    expect(hrefs).toContain(`${REPO}/blob/main/KIRO.md`);
  });
});

describe("?tab=kiro", () => {
  beforeAll(() => {
    (globalThis as { ResizeObserver?: unknown }).ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    };
  });

  it("renders without a recording, even when every API call fails", async () => {
    window.history.replaceState(null, "", "/?tab=kiro");
    const errors = vi.spyOn(console, "error").mockImplementation(() => {});
    const host = await mount(createElement(App));
    for (let i = 0; i < 4; i++) await act(async () => {});
    expect(host.querySelector("h1")?.textContent).toBe("Built with Kiro");
    expect(host.querySelector(".statebox.error")).toBeNull();
    const tab = host.querySelector("#tab-kiro");
    expect(tab?.textContent).toBe("Built with Kiro");
    expect(tab?.getAttribute("aria-selected")).toBe("true");
    errors.mockRestore();
  });
});
