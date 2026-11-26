import { useEffect, useState } from "react";
import type { Api } from "../api/client";
import type { Recipe, Recording } from "../api/uploadTypes";
import { StateBox } from "../components/StateBox";
import { recipeTotals, smallerText } from "../domain/recipe";
import { formatSize } from "../domain/upload";
import { STR } from "../strings";

const nf = (n: number) => n.toLocaleString("en-US");

export interface ExportFile {
  name: string;
  note: string;
  /** "41.2 MB" or "7 rows", or null when the API has not said. */
  size: string | null;
}

/** The four files in the export zip and what each holds. */
export function exportFiles(recipe: Recipe | null, eventCount: number | null, quarantineTotal: number | null): ExportFile[] {
  return [
    { name: "cleaned.csv", note: STR.fileCleanedNote, size: recipe ? formatSize(recipe.stored_bytes) : null },
    { name: "events.csv", note: STR.fileEventsNote, size: eventCount === null ? null : `${nf(eventCount)} ${eventCount === 1 ? "row" : STR.rows}` },
    { name: "quarantine.csv", note: STR.fileQuarantineNote, size: quarantineTotal === null ? null : `${nf(quarantineTotal)} ${quarantineTotal === 1 ? "row" : STR.rows}` },
    { name: "recipe.json", note: STR.fileRecipeNote, size: null },
  ];
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Export (Figma frame 8): the four files and one download. */
export function ExportView({ api, recording }: { api: Api; recording: Recording }) {
  const [recipe, setRecipe] = useState<Recipe | null>(null);
  const [quarantine, setQuarantine] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    api.recordingRecipe(recording.id).then((r) => live && setRecipe(r)).catch(() => {});
    api.recordingQuarantine(recording.id, 0, 1).then((q) => live && setQuarantine(q.total)).catch(() => {});
    return () => {
      live = false;
    };
  }, [api, recording.id]);

  async function download() {
    setBusy(true);
    setError(null);
    try {
      const blob = await api.exportRecording(recording.id);
      const base = recording.filename.replace(/\.[^.]+$/, "");
      downloadBlob(blob, `${base}-export.zip`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const totals = recipe ? recipeTotals(recipe) : null;
  const files = exportFiles(recipe, recording.event_count, quarantine);
  const ready = recording.status === "ready";
  return (
    <div className="wrap">
      <div className="pagehead">
        <div>
          <h1>{STR.exportTitle}</h1>
          <p className="muted">{ready ? STR.exportIntro : STR.exportNotReady}</p>
        </div>
        <button type="button" className="fbtn lg solid" disabled={!ready || busy} onClick={() => void download()}>
          {busy ? STR.exporting : STR.exportFourFiles}
        </button>
      </div>
      {error && <StateBox kind="error" title={STR.exportError} text={error} />}
      {recipe && totals && (
        <div className="stats cols3">
          <div className="card">
            <div className="muted">{STR.sizeBefore}</div>
            <div className="big">{formatSize(recipe.raw_bytes)}</div>
            <div className="muted cap">{nf(totals.decoded)} records</div>
          </div>
          <div className="card">
            <div className="muted">{STR.sizeAfter}</div>
            <div className="big">{formatSize(recipe.stored_bytes)}</div>
            <div className="muted cap">stored after reduction</div>
          </div>
          <div className="card">
            <div className="muted">Smaller by</div>
            <div className="big">{smallerText(totals.smallerBy).replace(" smaller", "")}</div>
            <div className="muted cap">events kept at full resolution</div>
          </div>
        </div>
      )}
      <div className="card evtable" style={{ padding: 0 }}>
        <h2 className="cardtitle">{STR.exportFiles}</h2>
        <ul className="files">
          {files.map((f) => (
            <li key={f.name}>
              <div>
                <div className="mono filename">{f.name}</div>
                <div className="muted small">{f.note}</div>
              </div>
              <span className="muted">{f.size ?? ""}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
