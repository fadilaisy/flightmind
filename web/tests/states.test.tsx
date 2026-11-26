// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { describe, expect, it } from "vitest";
import type { Api } from "../src/api/client";
import { RecordsView } from "../src/views/RecordsView";
import { getStore } from "../src/state/store";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

describe("error state", () => {
  it("shows the message and a Retry button when the API fails, and Retry calls again", async () => {
    let calls = 0;
    const failing = {
      raw: () => {
        calls += 1;
        return Promise.reject(new Error("Request failed: 500 /api/raw/rec01:3"));
      },
    } as unknown as Api;
    getStore().setRawRef("rec01:3");
    const host = document.createElement("div");
    document.body.appendChild(host);
    const root = createRoot(host);
    await act(async () => {
      root.render(<RecordsView api={failing} events={[]} eventId={null} />);
    });
    const box = host.querySelector(".statebox.error");
    expect(box?.textContent).toContain("Request failed: 500");
    const retry = [...host.querySelectorAll("button")].find((b) => b.textContent === "Retry");
    expect(retry).toBeTruthy();
    await act(async () => {
      retry!.click();
    });
    expect(calls).toBe(2);
    act(() => root.unmount());
  });
});
