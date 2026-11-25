import { useEffect, useState } from "react";
import type { Api } from "../api/client";
import type { RawRecord } from "../api/types";
import { toHexRows } from "../domain/hex";

interface Props {
  api: Api;
  rawRef: string;
  onClose: () => void;
}

export function RawRecordViewer({ api, rawRef, onClose }: Props) {
  const [record, setRecord] = useState<RawRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    setRecord(null);
    setError(null);
    api
      .raw(rawRef)
      .then((r) => live && setRecord(r))
      .catch((e: Error) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [api, rawRef]);

  const hex = record ? toHexRows(record.hex) : null;

  return (
    <section className="card" aria-label="Raw record">
      <header style={{ display: "flex", justifyContent: "space-between" }}>
        <strong className="data">{rawRef}</strong>
        <button type="button" onClick={onClose}>
          Close
        </button>
      </header>
      {error && <p role="alert">{error}</p>}
      {!record && !error && <p>Loading record.</p>}
      {record && (
        <>
          <p className="data">
            recording {record.recording_file_id} · record {record.record_index} · SAC {record.sac ?? "n/a"} · SIC{" "}
            {record.sic ?? "n/a"}
          </p>
          <p style={{ color: "var(--text-muted)" }}>
            Item byte ranges are not in the API response. The whole record is shown.
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <table className="data">
              <tbody>
                {Object.entries(record.decoded).map(([k, v]) => (
                  <tr key={k}>
                    <td style={{ color: "var(--text-muted)", paddingRight: 8 }}>{k}</td>
                    <td>{typeof v === "object" ? JSON.stringify(v) : String(v)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="data" style={{ background: "var(--bg-raised)", padding: 8, borderRadius: 4 }}>
              {hex && !hex.ok && <p role="alert">{hex.error}</p>}
              {hex && hex.ok && hex.rows.map((r) => (
                <div key={r.offset} style={{ whiteSpace: "pre" }}>
                  {r.offset.toString(16).padStart(4, "0")} {r.bytes.join(" ").padEnd(47, " ")} {r.ascii}
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
