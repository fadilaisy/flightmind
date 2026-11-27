import { useCallback, useEffect, useState } from "react";
import type { Api } from "../api/client";
import type { Recording, RecordingStatus } from "../api/uploadTypes";
import { formatSize, stageLabel } from "../domain/upload";
import { STR } from "../strings";
import { DropZone } from "./DropZone";
import { StateBox } from "./StateBox";

interface Props {
  api: Api;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onFile: (file: File) => void;
  onClose: () => void;
}

export function statusChip(status: RecordingStatus): { label: string; className: string } {
  if (status === "ready") return { label: STR.statusReady, className: "badge b-ok" };
  if (status === "failed") return { label: STR.statusFailed, className: "badge b-red" };
  if (status === "uploading") return { label: STR.statusUploading, className: "badge b-grey" };
  return { label: stageLabel(status) === "Queued" ? STR.statusProcessing : stageLabel(status), className: "badge b-event" };
}

/** The date a recording row shows: when the data starts if known, otherwise when it was added. */
export function recordingDate(r: Recording): string {
  return (r.first_ts ?? r.created_at).slice(0, 10);
}

type Load = { status: "loading" } | { status: "error"; message: string } | { status: "ready"; list: Recording[] };

/** Panel opened by "Load recording": a drop zone and the recordings already on the server. */
export function RecordingPicker({ api, selectedId, onSelect, onFile, onClose }: Props) {
  const [load, setLoad] = useState<Load>({ status: "loading" });
  const fetchList = useCallback(() => {
    setLoad({ status: "loading" });
    api
      .listRecordings()
      .then((list) => setLoad({ status: "ready", list }))
      .catch((e: Error) => setLoad({ status: "error", message: e.message }));
  }, [api]);
  useEffect(fetchList, [fetchList]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <>
      <div className="pickerback" onClick={onClose} />
      <section className="picker" role="dialog" aria-label={STR.recordingsTitle}>
        <div className="pickerhead">
          <h2>{STR.recordingsTitle}</h2>
          <button type="button" className="fbtn plain" onClick={onClose}>
            {STR.recordingsClose}
          </button>
        </div>
        <DropZone compact onFile={onFile} />
        <div className="pickerlist">
          {load.status === "loading" && <StateBox kind="loading" title={STR.recordingsLoading} />}
          {load.status === "error" && (
            <StateBox kind="error" title={STR.recordingsError} text={load.message}>
              <button type="button" className="btn sm" onClick={fetchList}>
                {STR.retry}
              </button>
            </StateBox>
          )}
          {load.status === "ready" && load.list.length === 0 && <p className="listmsg">{STR.recordingsEmpty}</p>}
          {load.status === "ready" && (
            <ul>
              {load.list.map((r) => {
                const chip = statusChip(r.status);
                return (
                  <li key={r.id}>
                    <button
                      type="button"
                      className={`pickrow${r.id === selectedId ? " sel" : ""}`}
                      aria-current={r.id === selectedId ? "true" : undefined}
                      onClick={() => onSelect(r.id)}
                    >
                      <span className="pickname">{r.filename}</span>
                      <span className="pickmeta">
                        {formatSize(r.size_bytes)} · {recordingDate(r)}
                      </span>
                      <span className={chip.className}>{chip.label}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </section>
    </>
  );
}
