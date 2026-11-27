import type { Recording, RecordingStream } from "../api/uploadTypes";
import { formatSize } from "../domain/upload";
import { STR } from "../strings";

const nf = (n: number) => n.toLocaleString("en-US");

interface Props {
  recording: Recording;
  /** "Use" on a row, or "Decode CAT021 stream" for the first supported one. */
  onUse: (streamId: string) => void;
  onAnotherFile: () => void;
}

/** "UDP streams found": source to destination, category, SAC/SIC, frames, records. */
export function StreamsView({ recording, onUse, onAnotherFile }: Props) {
  const first = recording.streams.find((s) => s.supported);
  return (
    <div className="wrap">
      <div className="pagehead">
        <div>
          <h1>{recording.filename}</h1>
          <p className="muted">
            {formatSize(recording.size_bytes)}. {STR.streamsIntro}
          </p>
        </div>
        <div className="rowbtns">
          <button type="button" className="fbtn lg" onClick={onAnotherFile}>
            {STR.loadAnotherFile}
          </button>
          <button type="button" className="fbtn lg solid" disabled={!first} onClick={() => first && onUse(first.id)}>
            {STR.decodeStream}
          </button>
        </div>
      </div>
      <div className="card evtable" style={{ padding: 0 }}>
        <h2 className="cardtitle">{STR.streamsTitle}</h2>
        {recording.streams.length === 0 ? (
          <p style={{ padding: 16 }}>{STR.streamsNone}</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>{STR.colSourceDest}</th>
                <th>{STR.colCategory}</th>
                <th>{STR.colSacSic}</th>
                <th>{STR.colFrames}</th>
                <th>{STR.colStreamRecords}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {recording.streams.map((s) => (
                <StreamRow key={s.id} s={s} onUse={onUse} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function StreamRow({ s, onUse }: { s: RecordingStream; onUse: (id: string) => void }) {
  return (
    <tr>
      <td className="mono">{s.src && s.dst ? `${s.src} \u2192 ${s.dst}` : "raw file"}</td>
      <td>CAT{String(s.category).padStart(3, "0")}</td>
      <td className="mono">
        {s.sac} / {s.sic}
      </td>
      <td>{nf(s.frames)}</td>
      <td>{nf(s.records)}</td>
      <td className="revcell">
        {s.supported ? (
          <button type="button" className="fbtn" onClick={() => onUse(s.id)}>
            {STR.useStream}
          </button>
        ) : (
          <span className="muted">{STR.notSupportedYet}</span>
        )}
      </td>
    </tr>
  );
}
