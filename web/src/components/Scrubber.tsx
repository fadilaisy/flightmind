import { useEffect, useMemo, useRef, useState, type CSSProperties, type KeyboardEvent } from "react";
import type { FlightEvent, Track } from "../api/types";
import { SHORT_LABEL, isSquawk } from "../domain/eventLabels";
import { clockZ } from "../domain/pointText";
import playIcon from "../assets/figma/icon-play.svg";
import { getStore, useStore } from "../state/store";
import { STR } from "../strings";

type TrackPoint = Track["points"][number];

/** Index of the last point at or before ts. Before the first point it gives 0. */
export function snapIndex(points: Pick<TrackPoint, "ts">[], ts: string | null): number {
  if (!ts || points.length === 0) return 0;
  const t = Date.parse(ts);
  let found = 0;
  for (let i = 0; i < points.length; i++) {
    if (Date.parse(points[i].ts) <= t) found = i;
    else break;
  }
  return found;
}

/** First and last point index inside the flagged window, or null when none is. */
export function windowIndexes(points: TrackPoint[], event: Pick<FlightEvent, "start_ts" | "end_ts">): [number, number] | null {
  const a = Date.parse(event.start_ts);
  const b = Date.parse(event.end_ts);
  let first = -1;
  let last = -1;
  points.forEach((p, i) => {
    const t = Date.parse(p.ts);
    if (t >= a && t <= b) {
      if (first < 0) first = i;
      last = i;
    }
  });
  return first < 0 ? null : [first, last];
}

const TICK_MS = 100;
const SPEEDS = [1, 2, 4, 8] as const;
const THUMB = 14;

interface Props {
  points: TrackPoint[];
  event: Pick<FlightEvent, "start_ts" | "end_ts">;
  /** Every event of this aircraft; each one gets a tick on the track. */
  events?: Pick<FlightEvent, "id" | "type" | "start_ts">[];
}

/** The only writer of scrubTs. Moves one point at a time. */
export function Scrubber({ points, event, events = [] }: Props) {
  const store = getStore();
  const scrubTs = useStore((s) => s.scrubTs);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(8);
  const simMs = useRef(0);
  const last = points.length - 1;
  const index = Math.min(snapIndex(points, scrubTs), Math.max(0, last));
  const band = useMemo(() => windowIndexes(points, event), [points, event]);

  function moveTo(i: number) {
    const p = points[Math.max(0, Math.min(last, i))];
    if (p && p.ts !== store.getState().scrubTs) store.setScrubTs(p.ts);
  }

  // Start on the first point of a new track.
  useEffect(() => {
    if (points.length === 0) return;
    const current = store.getState().scrubTs;
    if (!current || !points.some((p) => p.ts === current)) store.setScrubTs(points[0].ts);
  }, [points, store]);

  // Playback runs the shown time forward at x1, x2, x4 or x8 of the recording's own clock.
  useEffect(() => {
    if (!playing) return;
    simMs.current = Date.parse(points[snapIndex(points, store.getState().scrubTs)].ts);
    const end = Date.parse(points[last].ts);
    const id = window.setInterval(() => {
      simMs.current += TICK_MS * speed;
      if (simMs.current >= end) {
        moveTo(last);
        setPlaying(false);
      } else {
        moveTo(snapIndex(points, new Date(simMs.current).toISOString()));
      }
    }, TICK_MS);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, points, speed]);

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    const step = e.shiftKey ? 10 : 1;
    if (e.key === "ArrowRight" || e.key === "ArrowUp") moveTo(index + step);
    else if (e.key === "ArrowLeft" || e.key === "ArrowDown") moveTo(index - step);
    else return;
    e.preventDefault();
  }

  if (points.length === 0) return <div className="scrub" aria-label={STR.scrubberLabel} />;
  const pct = (i: number) => (last > 0 ? (i / last) * 100 : 0);
  // The native thumb travels from half its width to the other end, so marks use the same span.
  const at = (p: number) => `calc(${THUMB / 2}px + (100% - ${THUMB}px) * ${p / 100})`;
  const ticks = events.map((e) => {
    const t = Date.parse(e.start_ts);
    const found = points.findIndex((p) => Date.parse(p.ts) >= t);
    return { e, i: found < 0 ? last : found };
  });
  return (
    <div className="scrub" aria-label={STR.scrubberLabel}>
      <button type="button" className="playbtn" aria-label={playing ? STR.pause : STR.play} onClick={() => setPlaying((p) => !p)}>
        {playing ? (
          <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
            <path d="M3 1.5H5V10.5H3ZM7 1.5H9V10.5H7Z" fill="#03045E" />
          </svg>
        ) : (
          <img src={playIcon} alt="" />
        )}
      </button>
      <span className="scrubnow" title={STR.timeItem}>{clockZ(points[index].ts)}</span>
      <div className="scrubtrack">
        <input
          type="range"
          min={0}
          max={Math.max(0, last)}
          step={1}
          value={index}
          style={{ "--p": at(pct(index)) } as CSSProperties}
          aria-label={STR.scrubberSlider}
          aria-valuetext={clockZ(points[index].ts)}
          onChange={(e) => moveTo(Number(e.target.value))}
          onKeyDown={onKeyDown}
        />
        {band && (
          <span
            className="scrubband"
            aria-hidden="true"
            title={STR.flaggedWindow}
            style={{ left: `${pct(band[0])}%`, width: `${Math.max(pct(band[1]) - pct(band[0]), 0.8)}%` }}
          />
        )}
        {ticks.map(({ e, i }) => (
          <button
            key={e.id}
            type="button"
            className={`scrubtick${isSquawk(e.type) ? " red" : ""}`}
            style={{ left: at(pct(i)) }}
            title={`${SHORT_LABEL[e.type]} ${clockZ(e.start_ts)}`}
            aria-label={`${SHORT_LABEL[e.type]} ${clockZ(e.start_ts)}`}
            onClick={() => moveTo(i)}
          />
        ))}
      </div>
      <span className="scrubrange">
        {clockZ(points[0].ts)} → {clockZ(points[last].ts)}
      </span>
      <button
        type="button"
        className="speed"
        title={STR.speedLabel}
        aria-label={`${STR.speedLabel} x${speed}`}
        onClick={() => setSpeed(SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length])}
      >
        ×{speed}
      </button>
    </div>
  );
}