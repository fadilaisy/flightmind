import { describe, expect, it } from "vitest";

// Reads every source file as text through Vite, so no Node typings are needed.
const modules = import.meta.glob("../src/**/*.{ts,tsx}", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

const src = Object.entries(modules).map(([f, text]) => ({ f, text }));

describe("wording rules (ui.md)", () => {
  it("reads the source files", () => {
    expect(src.length).toBeGreaterThan(5);
  });

  it("never says went around or no touchdown", () => {
    for (const { f, text } of src) {
      expect(text.toLowerCase(), f).not.toContain("went around");
      expect(text.toLowerCase(), f).not.toContain("no touchdown");
    }
  });

  it("has no all-caps label strings", () => {
    for (const { f, text } of src) {
      const caps = text.match(/>\s*[A-Z]{4,}(\s[A-Z]{2,})*\s*</g);
      expect(caps, f).toBeNull();
    }
  });
});
