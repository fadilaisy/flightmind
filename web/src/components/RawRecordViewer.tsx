import { useEffect, useMemo, useState } from "react";
import type { Api } from "../api/client";
import type { FlightEvent, RawRecord } from "../api/types";
import { byteCount } from "../domain/hex";
import { itemRanges, recordItems } from "../domain/recordItems";
import { wiresharkFilter } from "../domain/wireshark";
import { STR } from "../strings";
import { HexPane } from "./HexPane";
import { RecordTree } from "./RecordTree";
import "../styles/records.css";

interface Props {
  api: Api;
  rawRef: string;
  /** The selected event, for the Wireshark filter in the footer. */
  event?: Pick<FlightEvent, "icao24" | "start_ts" | "end_ts"> | null;
  onClose: () => void;
  onOpenInRecords: (rawRef: string) => void;
}

/** The cited record: decode tree on the left, item and record bytes on the right (Figma frame 7b). */
export function RawRecordViewer({ api, rawRef, event = null, onClose, onOpenInRecords }: Props) {
  const [record, setRecord] = useState<RawRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [path, setPath] = useState<string | null>(null);
  const [selectedByte, setSelectedByte] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let live = true;
    setRecord(null);
    setError(null);
    api
      .raw(rawRef)
      .then((r) => {
        if (!live) return;
        setRecord(r);
        setPath(recordItems(r)[0]?.path ?? null);
        setSelectedByte(null);
      })
      .catch((e: Error) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [api, rawRef]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const items = useMemo(() => (record ? recordItems(record) : []), [record]);
  const ranges = useMemo(() => (record ? itemRanges(record) : []), [record]);
  const item = items.find((i) => i.path === path);
  const filter = event ? wiresharkFilter(event) : null;

  async function copy() {
    if (!filter) return;
    try {
      await navigator.clipboard.writeText(filter);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="dlgback" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="dlg" role="dialog" aria-modal="true" aria-label={STR.citedRecord}>
        <header className="dlghead">
          <div className="titlecol">
            <div className="small">{STR.citedRecord}</div>
            <h2>
              {rawRef}
              {item ? ` · ${item.id}` : ""}
            </h2>
          </div>
          <div className="meta">
            <span className="lbl">{STR.capture}</span>
            <span className="mono">{record?.recording_file_id ?? "…"}</span>
          </div>
          <div className="meta">
            <span className="lbl">Stream</span>
            <span className="muted">{STR.notInApi}</span>
          </div>
          <div className="meta">
            <span className="lbl">CAT / ed.</span>
            <span className="mono">021</span> <span className="muted">/ {STR.notInApi}</span>
          </div>
          <button type="button" className="dlgx" aria-label={STR.close} onClick={onClose}>
            ×
          </button>
        </header>

        {error && (
          <p role="alert" style={{ padding: 24, margin: 0 }}>
            {error}
          </p>
        )}
        {!record && !error && <p style={{ padding: 24, margin: 0 }}>Loading record.</p>}
        {record && (
          <div className="dlgbody">
            <div className="dlgleft">
              <div className="dlgsec">
                <b>{STR.decodeTree}</b>
                <span>{STR.likeWireshark}</span>
              </div>
              <RecordTree record={record} selectedPath={path} onSelectPath={setPath} />
            </div>
            <div className="dlgright">
              <div className="dlgsec">
                <b>{item ? `${item.id} · bits` : STR.itemBits}</b>
                <span>{STR.notInApi}</span>
              </div>
              {item && (
                <div className="valueband">
                  <span className="mono muted">{STR.rawValue}</span>
                  <span className="mono">{item.lsb ? `× ${item.lsb}` : "× 1"}</span>
                  <span className="mono">= {item.value}</span>
                  <span className="muted datum">{item.datum ?? ""}</span>
                </div>
              )}
              <div className="dlgsec" style={{ marginTop: 14 }}>
                <b>Record bytes</b>
                <span>{byteCount(record.hex)} bytes</span>
              </div>
              <div className="dlgbytes">
                <HexPane
                  hex={record.hex}
                  ranges={ranges}
                  selectedPath={path}
                  onSelectPath={setPath}
                  selectedByte={selectedByte}
                  onSelectByte={setSelectedByte}
                />
              </div>
            </div>
          </div>
        )}

        <footer className="dlgfoot">
          <span className="muted" style={{ fontSize: 12 }}>
            Wireshark
          </span>
          <code className="filter mono" title={filter ?? STR.notInApi}>
            {filter ?? STR.notInApi}
          </code>
          <div className="spacer" />
          <button type="button" className="btn ghost" disabled={!filter} onClick={copy}>
            {copied ? STR.copied : STR.copyFilterShort}
          </button>
          <button type="button" className="btn alt" onClick={() => onOpenInRecords(rawRef)}>
            {STR.openInRecords}
          </button>
          <button type="button" className="btn primary" onClick={onClose} autoFocus>
            {STR.done}
          </button>
        </footer>
      </div>
    </div>
  );
}
