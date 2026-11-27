import { useEffect, useState } from "react";
import type { Api } from "../api/client";
import type { Recording, RecordingPreview } from "../api/uploadTypes";
import { CitationChip } from "../components/CitationChip";
import { RawRecordViewer } from "../components/RawRecordViewer";
import { StateBox } from "../components/StateBox";
import { percent, previewRow, qualityScope } from "../domain/preview";
import { formatSize } from "../domain/upload";
import { STR } from "../strings";
import { navigate } from "./nav";

const nf = (n: number) => n.toLocaleString("en-US");
const LIMIT = 8;

interface Props {
  api: Api;
  recording: Recording;
  streamId: string;
  onContinue: () => void;
  onAnotherFile: () => void;
}

/** Decoded preview (Figma frame 2): the first records of the chosen stream and the quality of each field. */
export function PreviewView({ api, recording, streamId, onContinue, onAnotherFile }: Props) {
  const [data, setData] = useState<RecordingPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rawRef, setRawRef] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const stream = recording.streams.find((s) => s.id === streamId);

  useEffect(() => {
    let live = true;
    setData(null);
    setError(null);
    api
      .recordingPreview(recording.id, streamId, LIMIT)
      .then((d) => live && setData(d))
      .catch((e: Error) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [api, recording.id, streamId, attempt]);

  const scope = qualityScope(data?.sample_size);
  return (
    <div className="wrap">
      <div className="pagehead">
        <div>
          <h1>{recording.filename}</h1>
          <p className="muted">{STR.previewIntro}</p>
        </div>
        <div className="rowbtns">
          <button type="button" className="fbtn lg" onClick={onAnotherFile}>
            {STR.loadAnotherFile}
          </button>
          <button type="button" className="fbtn lg solid" disabled={!data} onClick={onContinue}>
            {STR.continueCleaning}
          </button>
        </div>
      </div>
      <div className="stats cols3">
        <div className="card">
          <div className="muted">File size</div>
          <div className="big">{formatSize(recording.size_bytes)}</div>
          <div className="muted cap">{recording.format === "asterix_raw" ? "raw CAT021" : "capture file"}</div>
        </div>
        <div className="card">
          <div className="muted">{STR.colStreamRecords}</div>
          <div className="big">{stream ? nf(stream.records) : "\u2014"}</div>
          <div className="muted cap">in the chosen stream</div>
        </div>
        <div className="card">
          <div className="muted">Data source</div>
          <div className="big">{stream ? `${stream.sac} / ${stream.sic}` : "\u2014"}</div>
          <div className="muted cap">SAC / SIC</div>
        </div>
      </div>
      {error ? (
        <StateBox kind="error" title={STR.previewError} text={error}>
          <button type="button" className="btn sm" onClick={() => setAttempt((n) => n + 1)}>
            {STR.retry}
          </button>
        </StateBox>
      ) : !data ? (
        <StateBox kind="loading" title={STR.previewLoading} />
      ) : (
        <>
          <div className="card evtable" style={{ padding: 0 }}>
            <h2 className="cardtitle">
              {STR.previewTitle} <span className="muted small">{STR.previewFirst} {data.records.length}</span>
            </h2>
            <table>
              <thead>
                <tr>
                  <th>{STR.colRawRef}</th>
                  <th>{STR.colTime}</th>
                  <th>{STR.colTarget}</th>
                  <th>{STR.colCallsign}</th>
                  <th>{STR.colLat}</th>
                  <th>{STR.colLon}</th>
                  <th>{STR.colHeight}</th>
                </tr>
              </thead>
              <tbody>
                {data.records.map((r) => {
                  const row = previewRow(r);
                  return (
                    <tr key={r.raw_ref}>
                      <td>
                        <CitationChip
                          citation={{ kind: "cat021_record", id: r.raw_ref, label: r.raw_ref.replace(/^rec/, "") }}
                          onOpenRecord={setRawRef}
                          onOpenEvent={() => {}}
                        />
                      </td>
                      <td className="mono">{row.time}</td>
                      <td className="mono">{row.target}</td>
                      <td>{row.callsign}</td>
                      <td className="mono">{row.lat}</td>
                      <td className="mono">{row.lon}</td>
                      <td>{row.height}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="card quality" aria-label={STR.fieldQualityTitle}>
            <h2 className="cardtitle flat">
              {STR.fieldQualityTitle} <span className="muted small">{scope ?? STR.fieldQualityNote}</span>
            </h2>
            {data.field_quality.map((f) => (
              <div className="qrow" key={f.item}>
                <span className="mono qitem">{f.item}</span>
                <span className="qlabel">{f.label}</span>
                <span
                  className="qbar"
                  role="meter"
                  aria-label={`${f.item} ${f.label}`}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={f.present_pct}
                >
                  <i style={{ width: `${f.present_pct}%` }} />
                </span>
                <span className="qpct">{percent(f.present_pct)}</span>
              </div>
            ))}
          </div>
        </>
      )}
      {rawRef && (
        <RawRecordViewer
          api={api}
          rawRef={rawRef}
          onClose={() => setRawRef(null)}
          onOpenInRecords={() => {
            setRawRef(null);
            navigate({ tab: "records" });
          }}
        />
      )}
    </div>
  );
}
