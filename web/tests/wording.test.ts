import { describe, expect, it } from "vitest";

// Every strings file and component, read as text through Vite (no Node typings needed).
const modules = import.meta.glob("../src/**/*.{ts,tsx}", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

const files = Object.entries(modules).map(([f, text]) => ({ f, text }));

function check(re: RegExp, say: string, only?: string) {
  const hits = files.filter((x) => !only || x.f.endsWith(only)).flatMap(({ f, text }) => (text.match(re) ?? []).map((m) => `${f}: ${m}`));
  expect(hits, say).toEqual([]);
}

describe("wording rules (task 16)", () => {
  it("scans strings.ts and the components", () => {
    expect(files.some((x) => x.f.endsWith("strings.ts"))).toBe(true);
    expect(files.length).toBeGreaterThan(10);
  });

  it('never says "went around" or "no touchdown"', () => {
    check(/went around/gi, "went around");
    check(/no touchdown/gi, "no touchdown");
  });

  it("has no all-caps labels", () => {
    check(/>\s*[A-Z]{4,}(\s[A-Z]{2,})*\s*</g, "caps text in JSX");
    check(/:\s*"[A-Z]{4,}(\s[A-Z]{2,})*"/g, "caps string in strings.ts", "strings.ts");
  });

  it("has no trailing arrows on labels", () => {
    check(/(\u2192|->)\s*["'`<]/g, "trailing arrow");
  });

  it("has no mojibake", () => {
    // A capital A with circumflex or tilde followed by another symbol, as UTF-8 read as Latin-1 gives.
    check(/[\u00C2\u00C3][^A-Za-z0-9\s]/g, "mojibake");
  });
});

