// @vitest-environment jsdom
import { act, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HexPane } from "../src/components/HexPane";
import { RawRecordViewer } from "../src/components/RawRecordViewer";
import { mockApi, type MockData } from "../src/api/mockClient";
import type { ItemRange } from "../src/domain/hex";
import mini from "./fixtures/mini.json";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

// 20 bytes, so the pane has two rows. 41 = "A", so the ASCII column has a letter.
const HEX = "0018130000C82F019E0B41424344454647484950";
const RANGES: ItemRange[] = [
  { path: "time", start: 3, end: 6 },
  { path: "height", start: 8, end: 10 },
];

let host: HTMLDivElement;
let root: Root;
const q = (sel: string) => [...host.querySelectorAll<HTMLElement>(sel)];
const marked = (kind: "hex" | "ascii") => q(`[data-${kind}].sel`).map((e) => Number(e.getAttribute(`data-${kind}`)));

beforeEach(() => {
  host = document.createElement("div");
  document.body.appendChild(host);
  root = createRoot(host);
});
afterEach(() => {
  act(() => root.unmount());
  host.remove();
});

function Harness({ ranges, initial = null, onPath }: { ranges: ItemRange[]; initial?: string | null; onPath?: (p: string) => void }) {
  const [path, setPath] = useState<string | null>(initial);
  return (
    <HexPane
      hex={HEX}
      ranges={ranges}
      selectedPath={path}
      onSelectPath={(p) => {
        setPath(p);
        onPath?.(p);
      }}
    />
  );
}

describe("HexPane", () => {
  it("draws rows of 16 with an offset column and an ASCII column", () => {
    act(() => root.render(<Harness ranges={RANGES} />));
    const rows = q(".hexrow");
    expect(rows).toHaveLength(2);
    expect(rows[0].querySelector(".hexoff")!.textContent).toBe("0000");
    expect(rows[1].querySelector(".hexoff")!.textContent).toBe("0010");
    expect(rows[0].querySelectorAll("[data-hex]")).toHaveLength(16);
    expect(rows[1].querySelectorAll("[data-hex]")).toHaveLength(4);
    expect(q("[data-ascii]")[10].textContent).toBe("A");
  });

  it("marks the bytes of the selected item in the hex and the ASCII pane", () => {
    act(() => root.render(<Harness ranges={RANGES} initial="height" />));
    expect(marked("hex")).toEqual([8, 9]);
    expect(marked("ascii")).toEqual([8, 9]);
  });

  it("selects the item when a byte inside its range is clicked, in either pane", () => {
    const seen = vi.fn();
    act(() => root.render(<Harness ranges={RANGES} onPath={seen} />));
    act(() => q('[data-hex="4"]')[0].click());
    expect(seen).toHaveBeenLastCalledWith("time");
    expect(marked("hex")).toEqual([3, 4, 5]);
    act(() => q('[data-ascii="9"]')[0].click());
    expect(seen).toHaveBeenLastCalledWith("height");
    expect(marked("ascii")).toEqual([8, 9]);
  });

  it("marks the whole record and says why when the API gives no byte ranges", () => {
    act(() => root.render(<Harness ranges={[]} initial="time" />));
    expect(marked("hex")).toHaveLength(20);
    expect(host.textContent).toContain("Item byte ranges are not in the API response.");
  });

  it("marks nothing when no item is selected", () => {
    act(() => root.render(<Harness ranges={[]} />));
    expect(marked("hex")).toHaveLength(0);
    expect(host.textContent).not.toContain("Item byte ranges");
  });
});

describe("RawRecordViewer (cited record dialog)", () => {
  const api = mockApi(mini as unknown as MockData);
  const flush = () => act(async () => void (await new Promise((r) => setTimeout(r, 0))));

  it("shows the raw_ref, the tree, the bytes and the footer, and closes on Escape", async () => {
    const onClose = vi.fn();
    const onOpen = vi.fn();
    act(() => root.render(<RawRecordViewer api={api} rawRef="rec01:3" event={mini.events[0]} onClose={onClose} onOpenInRecords={onOpen} />));
    await flush();
    const text = host.textContent ?? "";
    expect(text).toContain("Cited record");
    expect(text).toContain("rec01:3");
    expect(text).toContain("Decode tree");
    expect(text).toContain("I021/071 Time of applicability for position");
    expect(text).toContain("asterix.021_080 == 0x8A0213");
    expect(text).toContain("Item byte ranges are not in the API response.");
    expect(text).not.toContain("\u00c2");
    expect(q("[data-hex]")).toHaveLength(10);
    act(() => void [...host.querySelectorAll("button")].find((b) => b.textContent === "Open in Records")!.click());
    expect(onOpen).toHaveBeenCalledWith("rec01:3");
    act(() => void window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" })));
    expect(onClose).toHaveBeenCalled();
  });

  it("says when the record is not found", async () => {
    act(() => root.render(<RawRecordViewer api={api} rawRef="rec01:999" onClose={() => {}} onOpenInRecords={() => {}} />));
    await flush();
    expect(host.textContent).toContain("Record not found: rec01:999");
  });
});
