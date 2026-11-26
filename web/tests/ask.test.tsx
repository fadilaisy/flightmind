// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { describe, expect, it, vi } from "vitest";
import type { Api } from "../src/api/client";
import { EventPanel } from "../src/components/EventPanel";
import type { EventDetail } from "../src/api/types";
import mini from "./fixtures/mini.json";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

describe("ask box", () => {
  it("sends the askContext prefix but shows only what the user typed", async () => {
    const ask = vi.fn().mockResolvedValue({ status: "not_enough_evidence" });
    const api = { ask } as unknown as Api;
    const event = { ...mini.events[0], reviewed: false } as unknown as EventDetail;
    const host = document.createElement("div");
    document.body.appendChild(host);
    const root = createRoot(host);
    await act(async () => {
      root.render(
        <EventPanel api={api} event={event} state="to_review" points={null} onSetState={() => {}} onOpenRecord={() => {}} onOpenEvent={() => {}} onClose={() => {}} />,
      );
    });
    const fold = [...host.querySelectorAll("button")].find((b) => b.textContent?.includes("Ask about this event"))!;
    await act(async () => fold.click());
    const input = host.querySelector<HTMLInputElement>("input")!;
    await act(async () => {
      const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
      set.call(input, "Why was it flagged?");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await act(async () => {
      host.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });
    expect(ask).toHaveBeenCalledTimes(1);
    expect(ask.mock.calls[0][0]).toMatch(/^About event 1111.*: Why was it flagged\?$/);
    expect(input.value).toBe("Why was it flagged?");
    expect(host.textContent).not.toContain("About event");
    act(() => root.unmount());
  });
});
