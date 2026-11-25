import { describe, expect, it } from "vitest";
import { parseTab, tabUrl } from "../src/views/Shell";

describe("shell tabs", () => {
  it("defaults to map", () => {
    expect(parseTab("")).toBe("map");
    expect(parseTab("?tab=nope")).toBe("map");
  });
  it("reads the tab from the URL", () => {
    expect(parseTab("?tab=records")).toBe("records");
    expect(parseTab("?tab=3d")).toBe("3d");
  });
  it("keeps other params when switching tab", () => {
    expect(tabUrl("?x=1", "3d")).toBe("?x=1&tab=3d");
  });
});
