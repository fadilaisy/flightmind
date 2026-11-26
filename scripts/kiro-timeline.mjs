#!/usr/bin/env node
// Writes web/src/kiro/timeline.json from git history (non-merge commits on HEAD), the trailer
// corrections in KIRO.md and .kiro/specs/*/ (SCRUM-70). Run: node scripts/kiro-timeline.mjs
// The first five functions repeat web/src/domain/kiroTimeline.ts so this runs on plain Node;
// web/tests/kiroTimeline.test.ts checks that both copies agree.
import { execFileSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const KINDS = ["spec", "vibe", "hook", "none"];
const TRAILER = /^Kiro: (?:spec ([a-z0-9-]+)\/([A-Za-z0-9.,_-]+)|(vibe|hook|none))\s*$/;

export function parseTrailer(message) {
  let found = null;
  for (const raw of message.split("\n")) {
    const line = raw.replace(/\r$/, "");
    if (line.startsWith("#")) continue;
    const m = TRAILER.exec(line);
    if (!m) continue;
    found = m[3] ? { kind: m[3] } : { kind: "spec", spec: m[1], task: m[2] };
  }
  return found;
}

export function parseCorrections(kiroMd) {
  const text = kiroMd.replace(/\r/g, "");
  const start = text.indexOf("## Trailer corrections");
  if (start < 0) return [];
  const out = [];
  for (const line of text.slice(start).split("\n")) {
    if (!/^[0-9a-f]{7,40} \|/.test(line)) continue;
    const [sha, was, now, ...reason] = line.split("|").map((s) => s.trim());
    if (!sha || !was || !now) continue;
    out.push({ sha, was: was.replace(/ /g, ""), now: now.replace(/ /g, ""), reason: reason.join(" | ").trim() });
  }
  return out;
}

export function classify(sha, trailer, corrections) {
  const actual = trailer ? trailer.kind : "missing";
  for (const c of corrections) {
    if (!sha.startsWith(c.sha) || c.was !== actual) continue;
    if (KINDS.includes(c.now)) return { kind: c.now, corrected: true };
  }
  return { kind: actual, corrected: false };
}

export function countTasks(tasksMd) {
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

export function specTitle(requirementsMd) {
  for (const line of requirementsMd.replace(/\r/g, "").split("\n")) {
    const m = /^# (.+)$/.exec(line);
    if (m) return m[1].trim();
  }
  return null;
}

// ---------------------------------------------------------------------------------------

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const REPO = "https://github.com/fadilaisy/flightmind";

function git(...args) {
  return execFileSync("git", args, { cwd: root, encoding: "utf8", maxBuffer: 256 * 1024 * 1024 });
}

function read(rel) {
  return readFileSync(join(root, rel), "utf8");
}

function listDir(rel) {
  const dir = join(root, rel);
  return existsSync(dir) ? readdirSync(dir).sort() : [];
}

function hookWhen(when) {
  if (!when || !when.type) return "";
  const patterns = Array.isArray(when.patterns) && when.patterns.length ? `: ${when.patterns.join(", ")}` : "";
  return `${when.type}${patterns}`;
}

export function build() {
  const head = git("rev-parse", "HEAD").trim();
  const corrections = parseCorrections(read("KIRO.md"));

  const raw = git("log", "--no-merges", "--format=%H%x1f%an%x1f%aI%x1f%s%x1f%B%x1e").split("\x1e");
  const commits = [];
  for (const rec of raw) {
    const text = rec.replace(/^\n+/, "");
    if (!text.trim()) continue;
    const [sha, author, iso, subject, body] = text.split("\x1f");
    const trailer = parseTrailer(body ?? "");
    const { kind, corrected } = classify(sha, trailer, corrections);
    const c = { sha, short: sha.slice(0, 7), date: iso.slice(0, 10), author, subject, kind };
    if (trailer && trailer.kind === "spec" && kind === "spec") {
      c.spec = trailer.spec;
      c.task = trailer.task;
    }
    if (corrected) c.corrected = true;
    commits.push(c);
  }

  const mix = { spec: 0, vibe: 0, hook: 0, none: 0 };
  let unclassified = 0;
  for (const c of commits) {
    if (c.kind in mix) mix[c.kind] += 1;
    else unclassified += 1;
  }

  const specs = listDir(".kiro/specs")
    .filter((n) => existsSync(join(root, ".kiro/specs", n)) && !n.includes("."))
    .map((name) => {
      const file = (f) => (existsSync(join(root, `.kiro/specs/${name}/${f}.md`)) ? `.kiro/specs/${name}/${f}.md` : null);
      const files = { requirements: file("requirements"), design: file("design"), tasks: file("tasks") };
      const counts = files.tasks ? countTasks(read(files.tasks)) : { done: 0, total: 0 };
      return {
        name,
        title: (files.requirements && specTitle(read(files.requirements))) || name,
        tasksDone: counts.done,
        tasksTotal: counts.total,
        files,
        commits: commits.filter((c) => c.spec === name).map((c) => c.sha),
      };
    });

  const hooks = listDir(".kiro/hooks")
    .filter((f) => f.endsWith(".kiro.hook"))
    .map((f) => {
      const j = JSON.parse(read(`.kiro/hooks/${f}`));
      return { file: `.kiro/hooks/${f}`, name: j.name ?? f, when: hookWhen(j.when) };
    });

  const steering = listDir(".kiro/steering")
    .filter((f) => f.endsWith(".md"))
    .map((f) => `.kiro/steering/${f}`);

  const sessions = listDir("docs/kiro/sessions/cli").filter((f) => f.endsWith(".md") && f !== "README.md").length;

  return {
    generatedAt: new Date().toISOString(),
    head,
    repo: REPO,
    mix,
    unclassified,
    specs,
    commits,
    hooks,
    steering,
    sessions,
  };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const out = join(root, "web/src/kiro/timeline.json");
  mkdirSync(dirname(out), { recursive: true });
  const t = build();
  writeFileSync(out, JSON.stringify(t, null, 2) + "\n");
  console.log(
    `wrote web/src/kiro/timeline.json: ${t.commits.length} commits, ${t.specs.length} specs, mix ` +
      `spec=${t.mix.spec} vibe=${t.mix.vibe} hook=${t.mix.hook} none=${t.mix.none}, unclassified=${t.unclassified}`,
  );
}
