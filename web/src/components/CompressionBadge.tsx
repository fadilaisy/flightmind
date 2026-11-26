import { useCallback, useEffect, useState } from "react";
import type { Api } from "../api/client";
import { ApiError } from "../api/client";
import type { CompressionReport } from "../api/types";
import { STR } from "../strings";

/** "312.0 MB", "41 KB" from a byte count (decimal units). */
export function formatBytes(n: number): string {
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)} MB`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)} KB`;
  return `${n} B`;
}

/** Reduction factor "7.6×" is raw_bytes / stored_bytes. The API's `ratio` is the inverse. */
export function reductionFactor(r: CompressionReport): string {
  if (r.stored_bytes <= 0) return "n/a";
  return `${(r.raw_bytes / r.stored_bytes).toFixed(1)}\u00d7`;
}

type State =
  | { status: "idle" | "loading" }
  | { status: "empty" }
  | { status: "error"; message: string }
  | { status: "ready"; report: CompressionReport };

function useCompression(api: Api, recordingId: string | null) {
  const [state, setState] = useState<State>({ status: "idle" });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!recordingId) {
      setState({ status: "idle" });
      return;
    }
    let current = true;
    setState({ status: "loading" });
    api
      .compression(recordingId)
      .then((report) => current && setState({ status: "ready", report }))
      .catch((e: Error) => {
        if (!current) return;
        if (e instanceof ApiError && e.status === 404) setState({ status: "empty" });
        else setState({ status: "error", message: e.message });
      });
    return () => {
      current = false;
    };
  }, [api, recordingId, attempt]);
  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  return { state, retry };
}

interface Props {
  api: Api;
  recordingId: string | null;
}

/** The right-hand "Reduction" card: before/after size from GET /api/compression/{recording_id}. */
export function CompressionBadge({ api, recordingId }: Props) {
  const { state, retry } = useCompression(api, recordingId);
  return (
    <section className="rcard compression" aria-label={STR.reduction}>
      <div className="rhead">
        <span>{STR.reduction}</span>
        <span>{STR.measured}</span>
      </div>
      {(state.status === "idle" || state.status === "loading") && (
        <p className="empty" role="status">{state.status === "idle" ? STR.compressionNoRecording : STR.loadingCompression}</p>
      )}
      {state.status === "empty" && <p className="empty" role="status">{STR.compressionNone}</p>}
      {state.status === "error" && (
        <div role="alert">
          <p className="empty">{state.message}</p>
          <button type="button" className="btn sm" onClick={retry}>{STR.retry}</button>
        </div>
      )}
      {state.status === "ready" && <Report r={state.report} />}
    </section>
  );
}

function Report({ r }: { r: CompressionReport }) {
  const storedPct = r.raw_bytes > 0 ? Math.max(2, Math.min(100, (r.stored_bytes / r.raw_bytes) * 100)) : 0;
  return (
    <>
      <div className="cbig">
        <span className="cratio" data-testid="reduction-factor">{reductionFactor(r)}</span>
        <span className="csizes">{formatBytes(r.raw_bytes)} {"\u2192"} {formatBytes(r.stored_bytes)}</span>
      </div>
      <div className="cbars">
        <span>{STR.rawBar}</span>
        <span className="bar"><i style={{ width: "100%" }} /></span>
        <span>{STR.storedBar}</span>
        <span className="bar"><i style={{ width: `${storedPct}%` }} /></span>
      </div>
      <dl>
        <div className="pkv">
          <dt>{STR.maxPositionError}</dt>
          <dd>{Math.round(r.max_position_error_m).toLocaleString("en-US")} m</dd>
        </div>
        <div className="pkv">
          <dt>{STR.pointsKept}</dt>
          <dd>{r.points_kept.toLocaleString("en-US")} of {r.points_in.toLocaleString("en-US")}</dd>
        </div>
      </dl>
      <div className="cpill" role="status">
        <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
          <path d="M2 6.5l2.5 2.5L10 3.5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        {r.events_kept} of {r.events_total} flagged windows preserved
      </div>
    </>
  );
}
