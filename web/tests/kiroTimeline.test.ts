import { describe, expect, it } from "vitest";
import { classify, countTasks, parseCorrections, parseTrailer, specTitle } from "../src/domain/kiroTimeline";

describe("parseTrailer", () => {
  it("reads a spec trailer with a task number", () => {
    expect(parseTrailer("web-ui/3: app bar\n\nKiro: spec web-ui/3\n")).toEqual({ kind: "spec", spec: "web-ui", task: "3" });
  });
  it("reads a task range", () => {
    expect(parseTrailer("feat\n\nKiro: spec agent-mcp/10-21")).toEqual({ kind: "spec", spec: "agent-mcp", task: "10-21" });
  });
  it("reads the other three kinds", () => {
    expect(parseTrailer("x\n\nKiro: vibe")).toEqual({ kind: "vibe" });
    expect(parseTrailer("x\n\nKiro: hook\r\n")).toEqual({ kind: "hook" });
    expect(parseTrailer("x\n\nKiro: none")).toEqual({ kind: "none" });
  });
  it("returns null for no trailer, an empty template line, an unknown form and a # line", () => {
    expect(parseTrailer("just a subject")).toBeNull();
    expect(parseTrailer("x\n\nKiro: ")).toBeNull();
    expect(parseTrailer("x\n\nKiro: spec bad")).toBeNull();
    expect(parseTrailer("x\n\n# Kiro: vibe")).toBeNull();
  });
  it("uses the last trailer when there are two", () => {
    expect(parseTrailer("x\n\nKiro: none\nKiro: vibe")).toEqual({ kind: "vibe" });
  });
});

const KIRO_MD = [
  "# How we built it",
  "2026-11-26 | Fadil | x/1 | a | nothing",
  "",
  "## Trailer corrections",
  "",
  "Line format: `sha | was | now | reason`",
  "",
  "b35126b | hook | vibe | chat wrote it",
  "c170f6a | missing | none | initial commit | by GitHub",
  "2766b21 | spec scrum-19/1-4 | none | typed by hand",
  "",
].join("\r\n");

describe("corrections", () => {
  it("parses lines, including a missing was value and a reason with a pipe", () => {
    const list = parseCorrections(KIRO_MD);
    expect(list.map((c) => [c.sha, c.was, c.now])).toEqual([
      ["b35126b", "hook", "vibe"],
      ["c170f6a", "missing", "none"],
      ["2766b21", "specscrum-19/1-4", "none"],
    ]);
    expect(list[1].reason).toBe("initial commit | by GitHub");
  });
  it("returns nothing without the section", () => {
    expect(parseCorrections("# no section\nb35126b | hook | vibe | x")).toEqual([]);
  });
  it("moves a commit only when its real trailer still says was", () => {
    const list = parseCorrections(KIRO_MD);
    const full = "c170f6a" + "0".repeat(33);
    expect(classify(full, null, list)).toEqual({ kind: "none", corrected: true });
    expect(classify(full, { kind: "vibe" }, list)).toEqual({ kind: "vibe", corrected: false });
    expect(classify("b35126b" + "1".repeat(33), { kind: "hook" }, list)).toEqual({ kind: "vibe", corrected: true });
    expect(classify("ffffff0" + "1".repeat(33), null, list)).toEqual({ kind: "missing", corrected: false });
  });
});

describe("tasks and titles", () => {
  it("counts ticked and open boxes", () => {
    const md = ["# Tasks", "- [x] 1. a", "  - Files: x", "- [ ] 2. b", "- [X] 3. c", "  - [ ] sub", "text [x]"].join("\n");
    expect(countTasks(md)).toEqual({ done: 2, total: 4 });
    expect(countTasks("nothing here")).toEqual({ done: 0, total: 0 });
  });
  it("takes the first # heading as the title", () => {
    expect(specTitle("\n# Requirements: web-ui (SCRUM-39)\n\n## Sub\n# Later")).toBe("Requirements: web-ui (SCRUM-39)");
    expect(specTitle("no heading\n## only sub")).toBeNull();
  });
});

describe("scripts/kiro-timeline.mjs repeats the same parsing", () => {
  it("gives the same answers as the TypeScript copy", async () => {
    const path: string = "../../scripts/kiro-timeline.mjs";
    const lib = await import(/* @vite-ignore */ path);
    for (const m of ["a\n\nKiro: spec web-ui/3", "a\n\nKiro: spec agent-mcp/10-21", "a\n\nKiro: vibe", "a", "a\n\nKiro: spec bad"]) {
      expect(lib.parseTrailer(m)).toEqual(parseTrailer(m));
    }
    expect(lib.parseCorrections(KIRO_MD)).toEqual(parseCorrections(KIRO_MD));
    const md = "- [x] 1\n- [ ] 2\n  - [ ] 3";
    expect(lib.countTasks(md)).toEqual(countTasks(md));
    expect(lib.specTitle("# T\n")).toBe(specTitle("# T\n"));
    const full = "c170f6a" + "0".repeat(33);
    expect(lib.classify(full, null, lib.parseCorrections(KIRO_MD))).toEqual(classify(full, null, parseCorrections(KIRO_MD)));
  });
});
