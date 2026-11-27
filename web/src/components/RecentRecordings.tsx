import { useCallback, useEffect, useState } from "react";
import type { Api } from "../api/client";
import type { Recording } from "../api/uploadTypes";
import { formatSize, stageLabel } from "../domain/upload";
import { STR } from "../strings";
import { recordingDate, statusChip } from "./RecordingPicker";
import { StateBox } from "./StateBox";

const MAX_ROWS = 5;
const nf = (n: number) => n.toLocaleString("en-US");

type Load = { status: "loading" } | { status: "error"; message: string } | { status: "ready"; list: Recording[] };

interface Props {
  api: Api;
  onOpen: (id: string) => void;
  onFollow: (id: string) => void;
}

/** The newest recordings on the server, with one action each (choose phase of the Load screen). */
export function RecentRecordings({ api, onOpen, onFollow }: Props) {
  const [load, setLoad] = useState<Load>({ status: "loading" });
  const [shown, setShown] = useState<string | null>(null);
  const fetchList = useCallback(() => {
    setLoad({ status: "loading" });
    api
      .listRecordings()
      .then((list) => setLoad({ status: "ready", list }))
      .catch((e: Error) => setLoad({ status: "error", message: e.message }));
  }, [api]);
  useEffect(fetchList, [fetchList]);

  return (
    <section className="loadsec" aria-label={STR.recentTitle}>
      <div className="loadsec-head">
        <h2>{STR.recentTitle}</h2>
        <span>{STR.recentFrom}</span>
      </div>
      {load.status === "loading" && <StateBox kind="loading" title={STR.recordingsLoading} />}
      {load.status === "error" && (
        <StateBox kind="error" title={STR.recordingsError} text={load.message}>
          <button type="button" className="btn sm" onClick={fetchList}>
            {STR.retry}
          </button>
        </StateBox>
      )}
      {load.status === "ready" && load.list.length === 0 && <StateBox kind="empty" title={STR.recentEmpty} />}
      {load.status === "ready" && load.list.length > 0 && (
        <ul className="recent">
          {[...load.list]
            .sort((a, b) => b.created_at.localeCompare(a.created_at))
            .slice(0, MAX_ROWS)
            .map((r) => (
              <li key={r.id}>
                <Row r={r} open={shown === r.id} onOpen={onOpen} onFollow={onFollow} onToggle={() => setShown(shown === r.id ? null : r.id)} />
              </li>
            ))}
        </ul>
      )}
    </section>
  );
}

function Row(props: { r: Recording; open: boolean; onOpen: (id: string) => void; onFollow: (id: string) => void; onToggle: () => void }) {
  const { r } = props;
  const chip = statusChip(r.status);
  const meta = [`${formatSize(r.size_bytes)} \u00b7 ${recordingDate(r)}`];
  if (r.record_count != null) meta.push(`${nf(r.record_count)} ${STR.recordsWord}`);
  if (r.status === "failed" && r.error) meta.push(r.error);

  let mid: React.ReactNode = <span className="rmid">{STR.noValue}</span>;
  let action: React.ReactNode;
  if (r.status === "ready") {
    if (r.event_count != null) mid = <span className="rmid amber">{r.event_count === 1 ? STR.eventsOne : `${nf(r.event_count)} ${STR.eventsMany}`}</span>;
    action = (
      <button type="button" className="ract arrow" onClick={() => props.onOpen(r.id)}>
        {STR.actionOpen}
      </button>
    );
  } else if (r.status === "failed") {
    action = (
      <button type="button" className="ract" aria-expanded={props.open} onClick={props.onToggle}>
        {STR.actionDetails}
      </button>
    );
  } else {
    const p = r.progress;
    const ratio = p && p.records_total > 0 ? Math.min(1, p.records_done / p.records_total) : null;
    mid = (
      <span className="rmid">
        {r.status === "uploading" ? STR.statusUploading : stageLabel(r.status)}
        {ratio != null && (
          <span className="rbar" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(ratio * 100)}>
            <i style={{ width: `${Math.round(ratio * 100)}%` }} />
          </span>
        )}
      </span>
    );
    action = (
      <button type="button" className="ract arrow" onClick={() => props.onFollow(r.id)}>
        {STR.actionFollow}
      </button>
    );
  }

  return (
    <>
      <div className="recentrow">
        <div style={{ minWidth: 0 }}>
          <div className="rname">{r.filename}</div>
          <div className="rmeta">{meta.join(" \u00b7 ")}</div>
        </div>
        {mid}
        <span className={chip.className}>{chip.label}</span>
        {action}
      </div>
      {props.open && r.error && <p className="rerror">{r.error}</p>}
    </>
  );
}