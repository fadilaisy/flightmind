import { useEffect, useMemo, useState } from "react";
import type { Api } from "../api/client";
import type { FlightEvent, RawRecord } from "../api/types";
import { HexPane } from "../components/HexPane";
import { StateBox } from "../components/StateBox";
import { parseRawRef } from "../domain/citations";
import { byteCount } from "../domain/hex";
import { itemRanges, recordItems, type RecordItem } from "../domain/recordItems";
import { eventChipLabel, wiresharkFilter } from "../domain/wireshark";
import { getStore, useStore } from "../state/store";
import { STR } from "../strings";
import { navigate } from "./nav";
import "../styles/records.css";

interface Props {
  api: Api;
  events: FlightEvent[];
  eventId: string | null;
}

type Loaded =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; record: RawRecord };

/** Loads /api/raw/{raw_ref} whenever rawRef changes. */
function useRecord(api: Api, rawRef: string | null): Loaded {
  const [state, setState] = useState<Loaded>({ status: "idle" });
  useEffect(() => {
    if (!rawRef) {
      setState({ status: "idle" });
      return;
    }
    let live = true;
    setState({ status: "loading" });
    api
      .raw(rawRef)
      .then((record) => live && setState({ status: "ready", record }))
      .catch((e: Error) => live && setState({ status: "error", message: e.message }));
    return () => {
      live = false;
    };
  }, [api, rawRef]);
  return state;
}

const Muted = ({ children = STR.notInApi }: { children?: string }) => <span className="muted faint">{children}</span>;

export function RecordsView({ api, events, eventId }: Props) {
  const store = getStore();
  const rawRef = useStore((s) => s.rawRef);
  const event = events.find((e) => e.id === eventId) ?? null;
  const loaded = useRecord(api, rawRef);
  const record = loaded.status === "ready" ? loaded.record : null;
  const items = useMemo(() => (record ? recordItems(record) : []), [record]);
  const ranges = useMemo(() => (record ? itemRanges(record) : []), [record]);
  const [path, setPath] = useState<string | null>(null);
  const [selectedByte, setSelectedByte] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);

  // Open the first record of the event when none is selected yet.
  useEffect(() => {
    if (!rawRef && event && event.raw_refs.length > 0) store.setRawRef(event.raw_refs[0]);
  }, [rawRef, event, store]);

  // A new record starts on its first item.
  useEffect(() => {
    setPath(items.length > 0 ? items[0].path : null);
    setSelectedByte(null);
  }, [items]);

  const filter = event ? wiresharkFilter(event) : null;
  const refs = event ? (rawRef && !event.raw_refs.includes(rawRef) ? [...event.raw_refs, rawRef] : event.raw_refs) : rawRef ? [rawRef] : [];
  const recordingId = record?.recording_file_id ?? (rawRef ? parseRawRef(rawRef)?.recordingFileId : undefined) ?? null;
  const item: RecordItem | undefined = items.find((i) => i.path === path);
  const citedBy = rawRef ? events.filter((e) => e.raw_refs.includes(rawRef)) : [];

  async function copyFilter() {
    if (!filter) return;
    try {
      await navigator.clipboard.writeText(filter);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  function openEvent(e: FlightEvent) {
    store.selectEvent(e.id, e.icao24);
    navigate({ tab: "trajectory" });
  }

  return (
    <div className="recpage">
      <div className="rechead">
        <div>
          <h1>{STR.recordsTitle}</h1>
          <p className="muted">{STR.recordsIntro}</p>
        </div>
        <div className="recbtns">
          <button type="button" className="btn" disabled={!filter} onClick={copyFilter}>
            {copied ? STR.copied : STR.copyFilter}
          </button>
          <button type="button" className="btn" disabled title={STR.exportNotBuilt}>
            {STR.exportSlice}
          </button>
          <button type="button" className="btn primary" disabled title={STR.exportNotBuilt}>
            {STR.exportRecord}
          </button>
        </div>
      </div>

      <section className="card recstrip" aria-label={STR.capture}>
        <div>
          <span className="lbl">{STR.capture}</span>
          <span className="mono">{recordingId ?? <Muted />}</span>
        </div>
        <div>
          <span className="lbl">{STR.udpStream}</span>
          <Muted />
        </div>
        <div>
          <span className="lbl">{STR.category}</span>
          <span className="mono">CAT021</span>
        </div>
        <div>
          <span className="lbl">{STR.timeSource}</span>
          <span className="mono">I021/071 · UTC</span>
        </div>
        <div>
          <span className="lbl">{STR.decoder}</span>
          <Muted />
        </div>
      </section>

      <div className="recfilter" aria-label={STR.filterLabel}>
        <span className="muted">{STR.filterLabel}</span>
        <code className="mono recfilterText">{filter ?? <Muted>{STR.selectEvent}</Muted>}</code>
        {event && (
          <>
            <span className="muted">{STR.filterFrom}</span>
            <button type="button" className="chip ev" onClick={() => openEvent(event)} title={`Open ${eventChipLabel(event)}`}>
              evt {eventChipLabel(event)}
            </button>
          </>
        )}
        <button type="button" className="btn sm" disabled title={STR.applyDisabled}>
          {STR.apply}
        </button>
      </div>

      <div className="reccols">
        <div className="reccol">
          <section className="reccard" aria-label={STR.framesTitle}>
            <header>
              <b>{STR.framesTitle}</b> <span className="muted">{refs.length} records in the flagged window</span>
            </header>
            <table>
              <thead>
                <tr>
                  <th>No.</th>
                  <th>Time (UTC)</th>
                  <th>Source → destination</th>
                  <th>Len</th>
                  <th>Info</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td colSpan={5}>
                    <Muted>{STR.framesMissing}</Muted>
                  </td>
                </tr>
              </tbody>
            </table>
          </section>

          <div className="recpair">
            <section className="reccard" aria-label={STR.blocksTitle}>
              <header>
                <b>{STR.blocksTitle}</b> <span className="muted" title={STR.blocksMissing}>in recording {recordingId ?? "n/a"}</span>
              </header>
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Offset</th>
                    <th>Length</th>
                    <th>CAT</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="sel">
                    <td className="mono">1</td>
                    <td title={STR.notInApi}><Muted>n/a</Muted></td>
                    <td title={STR.notInApi}><Muted>n/a</Muted></td>
                    <td className="mono">021</td>
                  </tr>
                </tbody>
              </table>
            </section>

            <section className="reccard" aria-label={STR.recordsTableTitle}>
              <header>
                <b>{STR.recordsTableTitle}</b> <span className="muted" title={STR.notInApi}>in block 1</span>
              </header>
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Offset</th>
                    <th>Length</th>
                    <th>Fields</th>
                    <th>Target</th>
                  </tr>
                </thead>
                <tbody>
                  {refs.map((r) => {
                    const parsed = parseRawRef(r);
                    const selected = r === rawRef;
                    return (
                      <tr
                        key={r}
                        className={`click${selected ? " sel" : ""}`}
                        aria-selected={selected}
                        onClick={() => store.setRawRef(r)}
                        title={r}
                      >
                        <td className="mono">{parsed ? parsed.recordIndex : r}</td>
                        <td title={STR.notInApi}>
                          <Muted>n/a</Muted>
                        </td>
                        <td className="mono">{selected && record ? byteCount(record.hex) : ""}</td>
                        <td className="mono">{selected && record ? Object.keys(record.decoded).length : ""}</td>
                        <td className="mono">{event ? event.icao24.toUpperCase() : ""}</td>
                      </tr>
                    );
                  })}
                  {refs.length === 0 && (
                    <tr>
                      <td colSpan={5}>
                        <Muted>{STR.selectEvent}</Muted>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </section>
          </div>

          <section className="reccard" aria-label={STR.itemsTitle}>
            <header>
              <b>{STR.itemsTitle}</b>{" "}
              <span className="muted">
                {record ? `record ${record.record_index} · ${byteCount(record.hex)} bytes · ${STR.itemFieldsMissing}` : ""}
              </span>
            </header>
            {loaded.status === "error" && <StateBox kind="error" title={STR.recordError} text={loaded.message} />}
            {loaded.status === "loading" && <p className="muted pad">{STR.recordLoading}</p>}
            {loaded.status === "idle" && <p className="muted pad">{STR.selectRecord}</p>}
            {record && (
              <table>
                <thead>
                  <tr>
                    <th>Offset</th>
                    <th>Len</th>
                    <th>FRN</th>
                    <th>Item</th>
                    <th>Description</th>
                    <th>Value</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((it) => (
                    <tr
                      key={it.path}
                      className={`click${it.path === path ? " sel" : ""}`}
                      aria-selected={it.path === path}
                      onClick={() => setPath(it.path)}
                    >
                      <td title={STR.notInApi}><Muted>n/a</Muted></td>
                      <td title={STR.notInApi}><Muted>n/a</Muted></td>
                      <td title={STR.notInApi}><Muted>n/a</Muted></td>
                      <td className="mono">{it.id}</td>
                      <td className="sans">{it.known ? it.name : it.path}</td>
                      <td className="mono">{it.value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </div>

        <div className="reccol">
          <section className="reccard itemcard" aria-label="Selected item">
            {item ? (
              <>
                <header className="itemhead">
                  <h2>
                    {item.id} · {item.name}
                  </h2>
                  <p className="muted">
                    item byte range <Muted /> · FRN <Muted />
                  </p>
                </header>
                <div className="itembody">
                  {item.definition ? <p className="muted">Definition: {item.definition}</p> : <p className="muted">No definition in the item table.</p>}
                  <p className="muted">
                    {STR.itemBits}: <Muted />
                  </p>
                  <div className="valueband">
                    <span className="mono">
                      <Muted>{`${STR.rawValue} ${STR.notInApi}`}</Muted>
                    </span>
                    <span className="mono">{item.lsb ? `× ${item.lsb}` : "× 1"}</span>
                    <span className="mono">= {item.value}</span>
                    <span className="muted datum">{item.datum ?? ""}</span>
                  </div>
                  <div className="citedby">
                    <span className="muted">{STR.citedBy}</span>
                    {citedBy.length === 0 && <span className="muted faint">{STR.notCited}</span>}
                    {citedBy.map((e) => (
                      <button key={e.id} type="button" className="chip ev" onClick={() => openEvent(e)} title={`Open ${eventChipLabel(e)}`}>
                        evt {eventChipLabel(e)}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <p className="muted pad">{STR.selectRecord}</p>
            )}
          </section>

          <section className="reccard bytescard" aria-label={STR.bytesTitle}>
            <header>
              <b>{STR.bytesTitle}</b>{" "}
              <span className="muted">{record ? `record ${record.record_index} · offset · hex · ASCII` : ""}</span>
            </header>
            {record ? (
              <div className="bytesbody">
                <HexPane
                  hex={record.hex}
                  ranges={ranges}
                  selectedPath={path}
                  onSelectPath={setPath}
                  selectedByte={selectedByte}
                  onSelectByte={setSelectedByte}
                />
                <div className="hexlegend">
                  <span>
                    <i className="sw rec" />
                    {STR.legendRecord}
                  </span>
                  <span>
                    <i className="sw sel" />
                    {STR.legendSelected}
                  </span>
                </div>
                <div className="rawrefbox mono">
                  raw_ref {record.raw_ref} · record {record.record_index} · SAC {record.sac ?? "n/a"} / SIC {record.sic ?? "n/a"}
                </div>
              </div>
            ) : (
              <p className="muted pad">{STR.selectRecord}</p>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
