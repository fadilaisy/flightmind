import { useRef, useState } from "react";
import { KINDS, type Kind, type Timeline, type TimelineCommit } from "../domain/kiroTimeline";
import timelineJson from "../kiro/timeline.json";
import { STR } from "../strings";
import "../styles/kiro.css";

const GENERATED = timelineJson as unknown as Timeline;

type KindKey = Kind | "missing";
type Filter = "all" | KindKey;

const KIND_LABEL: Record<KindKey, string> = {
  spec: STR.kiroKindSpec,
  vibe: STR.kiroKindVibe,
  hook: STR.kiroKindHook,
  none: STR.kiroKindNone,
  missing: STR.kiroKindMissing,
};
const KIND_NOTE: Record<Kind, string> = {
  spec: STR.kiroKindSpecNote,
  vibe: STR.kiroKindVibeNote,
  hook: STR.kiroKindHookNote,
  none: STR.kiroKindNoneNote,
};
const BADGE: Record<KindKey, string> = {
  spec: "b-ok",
  vibe: "b-event",
  hook: "b-hook",
  none: "b-grey",
  missing: "b-missing",
};

function baseName(path: string): string {
  return path.slice(path.lastIndexOf("/") + 1);
}

/** "Built with Kiro" page. Needs no recording and no API: it reads the generated timeline. */
export function KiroView({ data = GENERATED }: { data?: Timeline }) {
  const repo = data.repo.replace(/\/$/, "");
  const blob = (path: string) => `${repo}/blob/main/${path}`;
  const commitUrl = (sha: string) => `${repo}/commit/${sha}`;

  const [filter, setFilter] = useState<Filter>("all");
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const timelineRef = useRef<HTMLElement>(null);

  const bySha = new Map(data.commits.map((c) => [c.sha, c] as const));
  const total = data.commits.length;
  const kinds: KindKey[] = data.unclassified > 0 ? [...KINDS, "missing"] : [...KINDS];
  const countOf = (k: KindKey): number => (k === "missing" ? data.unclassified : data.mix[k]);

  const shown = data.commits.filter((c) => filter === "all" || c.kind === filter);
  const days: { date: string; items: TimelineCommit[] }[] = [];
  for (const c of shown) {
    const last = days[days.length - 1];
    if (last && last.date === c.date) last.items.push(c);
    else days.push({ date: c.date, items: [c] });
  }

  function showKind(k: KindKey) {
    setFilter(k);
    timelineRef.current?.scrollIntoView?.();
  }

  return (
    <div className="wrap kiro">
      <div>
        <h1>{STR.kiroTitle}</h1>
        <p className="intro">{STR.kiroIntro}</p>
      </div>

      <section className="card kcard" aria-labelledby="kiro-mix">
        <h2 id="kiro-mix">{STR.kiroMixTitle}</h2>
        <div className="kbar" role="img" aria-label={STR.kiroMixLabel}>
          {kinds
            .filter((k) => countOf(k) > 0)
            .map((k) => (
              <i key={k} className={`kseg-${k}`} style={{ flexGrow: countOf(k) }} title={`${KIND_LABEL[k]}: ${countOf(k)}`} />
            ))}
        </div>
        <ul className="kcounts">
          {kinds.map((k) => (
            <li key={k}>
              {countOf(k) > 0 ? (
                <button type="button" className="linklike" data-kind={k} onClick={() => showKind(k)} aria-label={`${countOf(k)} ${KIND_LABEL[k]}`}>
                  {countOf(k)}
                </button>
              ) : (
                <span className="linklike" data-kind={k}>0</span>
              )}
              <b>{KIND_LABEL[k]}</b>
              <span className="note">{k === "missing" ? "" : KIND_NOTE[k]}</span>
            </li>
          ))}
        </ul>
        <div className="kmeta">
          <span data-testid="kiro-total">
            <b>{total}</b> {STR.kiroTotal}
          </span>
          <span>
            {STR.kiroGenerated}{" "}
            <a className="sha" href={commitUrl(data.head)} target="_blank" rel="noreferrer">
              {data.head.slice(0, 7)}
            </a>
          </span>
        </div>
        <p className="khint">{STR.kiroMixHint}</p>
      </section>

      <section aria-labelledby="kiro-specs">
        <h2 id="kiro-specs">{STR.kiroSpecsTitle}</h2>
        <div className="kspecs">
          {data.specs.map((s) => {
            const commits = s.commits.map((sha) => bySha.get(sha)).filter((c): c is TimelineCommit => !!c);
            const isOpen = !!open[s.name];
            const listId = `kiro-spec-${s.name}-commits`;
            return (
              <article key={s.name} className="card kcard kspec" data-spec={s.name}>
                <div>
                  <h3>{s.title.replace(/^Requirements:\s*/, "")}</h3>
                  <span className="name">{s.name}</span>
                </div>
                <div className="tasks">
                  {s.files.tasks ? (
                    <a href={blob(s.files.tasks)} target="_blank" rel="noreferrer">
                      {s.tasksDone} / {s.tasksTotal}
                    </a>
                  ) : (
                    <span>
                      {s.tasksDone} / {s.tasksTotal}
                    </span>
                  )}{" "}
                  <span className="muted" style={{ fontSize: 12, fontWeight: 400 }}>{STR.kiroTasksOf}</span>
                </div>
                <div className="links">
                  {s.files.requirements && <a href={blob(s.files.requirements)} target="_blank" rel="noreferrer">{STR.kiroRequirements}</a>}
                  {s.files.design && <a href={blob(s.files.design)} target="_blank" rel="noreferrer">{STR.kiroDesign}</a>}
                  {s.files.tasks && <a href={blob(s.files.tasks)} target="_blank" rel="noreferrer">{STR.kiroTasksFile}</a>}
                </div>
                {commits.length > 0 ? (
                  <>
                    <button
                      type="button"
                      className="klinkbtn"
                      aria-expanded={isOpen}
                      aria-controls={listId}
                      onClick={() => setOpen((o) => ({ ...o, [s.name]: !o[s.name] }))}
                    >
                      {commits.length} {commits.length === 1 ? STR.kiroCommitWord : STR.kiroCommitsWord}
                    </button>
                    {isOpen && (
                      <ul id={listId}>
                        {commits.map((c) => (
                          <li key={c.sha}>
                            <a className="sha" href={commitUrl(c.sha)} target="_blank" rel="noreferrer">{c.short}</a>
                            <span className="date">{c.date}</span>
                            <span>{c.subject}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </>
                ) : (
                  <p className="khint">{STR.kiroNoSpecCommits}</p>
                )}
              </article>
            );
          })}
        </div>
      </section>

      <section className="card kcard" ref={timelineRef} aria-labelledby="kiro-timeline" id="kiro-timeline">
        <div className="kfilter">
          <h2 id="kiro-timeline">{STR.kiroTimelineTitle}</h2>
          <div className="seg" role="group" aria-label={STR.kiroFilterLabel}>
            {(["all", ...kinds] as Filter[]).map((f) => (
              <button key={f} type="button" className={f === filter ? "on" : undefined} aria-pressed={f === filter} onClick={() => setFilter(f)}>
                {f === "all" ? STR.kiroFilterAll : KIND_LABEL[f]}
              </button>
            ))}
          </div>
        </div>
        {days.length === 0 && <p className="khint">{STR.kiroNoCommits}</p>}
        {days.map((d, i) => (
          <div key={`${d.date}:${i}`} className="kday">
            <h3>{d.date}</h3>
            <ul>
              {d.items.map((c) => (
                <li key={c.sha} data-kind={c.kind}>
                  <span className={`badge kbadge ${BADGE[c.kind]}`}>{KIND_LABEL[c.kind]}</span>
                  <a className="sha" href={commitUrl(c.sha)} target="_blank" rel="noreferrer">{c.short}</a>
                  <span className="subject">{c.subject}</span>
                  {c.corrected && (
                    <a className="corr" href={blob("KIRO.md")} target="_blank" rel="noreferrer">{STR.kiroClassified}</a>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </section>

      <section className="card kcard" aria-labelledby="kiro-more">
        <h2 id="kiro-more">{STR.kiroEvidenceTitle}</h2>
        <div className="kfoot">
          <div>
            <h3>{STR.kiroHooks}</h3>
            <ul>
              {data.hooks.map((h) => (
                <li key={h.file}>
                  <a href={blob(h.file)} target="_blank" rel="noreferrer">{baseName(h.file)}</a>{" "}
                  <span className="when">{h.when}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3>{STR.kiroSteering}</h3>
            <ul>
              {data.steering.map((f) => (
                <li key={f}>
                  <a href={blob(f)} target="_blank" rel="noreferrer">{baseName(f)}</a>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3>{STR.kiroSessions}</h3>
            <ul>
              <li>
                <a href={blob("docs/kiro/sessions/cli/README.md")} target="_blank" rel="noreferrer">{STR.kiroSessionsLink}</a>{" "}
                <span className="when">{data.sessions} {STR.kiroLogs}</span>
              </li>
              <li>
                <a href={blob("KIRO.md")} target="_blank" rel="noreferrer">{STR.kiroLogFile}</a>
              </li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
