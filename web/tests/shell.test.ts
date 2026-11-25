import { describe, expect, it } from "vitest";
import { parseTab, tabUrl } from "../src/views/Shell";

describe("shell tabs", () => {
  it("defaults to trajectory", () => {
    expect(parseTab("")).toBe("trajectory");
    expect(parseTab("?tab=nope")).toBe("trajectory");
  });
  it("reads the tab from the URL", () => {
    expect(parseTab("?tab=records")).toBe("records");
    expect(parseTab("?tab=events")).toBe("events");
  });
  it("keeps other params when switching tab", () => {
    expect(tabUrl("?x=1", "records")).toBe("?x=1&tab=records");
  });
});