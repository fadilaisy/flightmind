// Pure parsing for the "Built with Kiro" page and scripts/kiro-timeline.mjs (SCRUM-70).
// scripts/kiro-timeline.mjs repeats parseTrailer, parseCorrections, countTasks and specTitle so it
// runs on plain Node; tests/kiroTimeline.test.ts checks that both copies agree.

export const KINDS = ["spec", "vibe", "hook", "none"] as const;
export type Kind = (typeof KINDS)[number];

export interface Trailer {
  kind: Kind;
  spec?: string;
  task?: string;
}

export interface Correction {
  sha: string;
  /** What the commit's own trailer says, with spaces removed, or "missing" when it has none. */
  was: string;
  now: string;
  reason: string;
}

const TRAILER = /^Kiro: (?:spec ([a-z0-9-]+)\/([A-Za-z0-9.,_-]+)|(vibe|hook|none))\s*$/;

/** The last valid `Kiro:` line of a commit message. Lines starting with # are ignored. */
export function parseTrailer(message: string): Trailer | null {
  let found: Trailer | null = null;
  for (const raw of message.split("\n")) {
    const line = raw.replace(/\r$/, "");
    if (line.startsWith("#")) continue;
    const m = TRAILER.exec(line);
    if (!m) continue;
    found = m[3] ? { kind: m[3] as Kind } : { kind: "spec", spec: m[1], task: m[2] };
  }
  return found;
}

/** Lines `sha | was | now | reason` under "## Trailer corrections" in KIRO.md. */
export function parseCorrections(kiroMd: string): Correction[] {
  const text = kiroMd.replace(/\r/g, "");
  const start = text.indexOf("## Trailer corrections");
  if (start < 0) return [];
  const out: Correction[] = [];
  for (const line of text.slice(start).split("\n")) {
    if (!/^[0-9a-f]{7,40} \|/.test(line)) continue;
    const [sha, was, now, ...reason] = line.split("|").map((s) => s.trim());
    if (!sha || !was || !now) continue;
    out.push({ sha, was: was.replace(/ /g, ""), now: now.replace(/ /g, ""), reason: reason.join(" | ").trim() });
  }
  return out;
}

/** The kind a commit counts as, after applying KIRO.md corrections the way scripts/kiro-stats does. */
export function classify(
  sha: string,
  trailer: Trailer | null,
  corrections: Correction[],
): { kind: Kind | "missing"; corrected: boolean } {
  const actual = trailer?.kind ?? "missing";
  for (const c of corrections) {
    if (!sha.startsWith(c.sha) || c.was !== actual) continue;
    if ((KINDS as readonly string[]).includes(c.now)) return { kind: c.now as Kind, corrected: true };
  }
  return { kind: actual, corrected: false };
}

/** Checkbox lines in a tasks.md, the same lines scripts/kiro-stats counts. */
export function countTasks(tasksMd: string): { done: number; total: number } {
  let done = 0;
  let total = 0;
  for (const line of tasksMd.split("\n")) {
    const m = /^\s*- \[([ xX])\]/.exec(line);
    if (!m) continue;
    total += 1;
    if (m[1] !== " ") done += 1;
  }
  return { done, total };
}

/** First `# ` heading of a markdown file, or null. */
export function specTitle(requirementsMd: string): string | null {
  for (const line of requirementsMd.replace(/\r/g, "").split("\n")) {
    const m = /^# (.+)$/.exec(line);
    if (m) return m[1].trim();
  }
  return null;
}

// ---- shape of web/src/kiro/timeline.json -------------------------------------------------

export interface TimelineCommit {
  sha: string;
  short: string;
  date: string;
  author: string;
  subject: string;
  kind: Kind | "missing";
  spec?: string;
  task?: string;
  corrected?: boolean;
}

export interface TimelineSpec {
  name: string;
  title: string;
  tasksDone: number;
  tasksTotal: number;
  files: { requirements: string | null; design: string | null; tasks: string | null };
  commits: string[];
}

export interface Timeline {
  generatedAt: string;
  head: string;
  repo: string;
  mix: Record<Kind, number>;
  unclassified: number;
  specs: TimelineSpec[];
  commits: TimelineCommit[];
  hooks: { file: string; name: string; when: string }[];
  steering: string[];
  sessions: number;
}
