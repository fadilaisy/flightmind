import { useEffect, useMemo, useState, type KeyboardEvent } from "react";
import type { FlightEvent, Track } from "../api/types";
import { formatTime } from "../domain/format";
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

const clock = (iso: string) => iso.slice(11, 19);
const PLAY_MS = 250;

interface Props {
  points: TrackPoint[];
  event: Pick<FlightEvent, "start_ts" | "end_ts">;
}

/** The only writer of scrubTs. Moves one point at a time. */
export function Scrubber({ points, event }: Props) {
  const store = getStore();
  const scrubTs = useStore((s) => s.scrubTs);
  const [playing, setPlaying] = useState(false);
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

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      const i = snapIndex(points, store.getState().scrubTs);
      if (i >= last) setPlaying(false);
      else moveTo(i + 1);
    }, PLAY_MS);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, points]);

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    const step = e.shiftKey ? 10 : 1;
    if (e.key === "ArrowRight" || e.key === "ArrowUp") moveTo(index + step);
    else if (e.key === "ArrowLeft" || e.key === "ArrowDown") moveTo(index - step);
    else return;
    e.preventDefault();
  }

  if (points.length === 0) return <div className="scrub" aria-label={STR.scrubberLabel} />;
  const pct = (i: number) => (last > 0 ? (i / last) * 100 : 0);
  return (
    <div className="scrub" aria-label={STR.scrubberLabel}>
      <button
        type="button"
        className="btn sm"
        aria-label={playing ? STR.pause : STR.play}
        onClick={() => setPlaying((p) => !p)}
      >
        {playing ? "❚❚" : "▶"}
      </button>
      <span className="mono scrubnow" title={STR.timeItem}>{formatTime(points[index].ts)}</span>
      <div className="scrubtrack">
        <input
          type="range"
          min={0}
          max={Math.max(0, last)}
          step={1}
          value={index}
          aria-label={STR.scrubberSlider}
          aria-valuetext={formatTime(points[index].ts)}
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
      </div>
      <span className="mono muted scrubrange">
        {clock(points[0].ts)} to {clock(points[last].ts)} UTC
      </span>
    </div>
  );
}
