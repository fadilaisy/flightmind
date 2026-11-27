import { STAGES, stageIndex } from "../domain/upload";
import type { RecordingStatus } from "../api/uploadTypes";
import { STR } from "../strings";

/** The stage pills: Uploading, Scanning, Decoding, Filtering, Detecting events, Storing. */
export function StageList({ status }: { status: RecordingStatus }) {
  const current = stageIndex(status);
  return (
    <ol className="stages" aria-label={STR.stagesLabel}>
      {STAGES.map((label, i) => (
        <li key={label} className={i < current ? "done" : i === current ? "now" : undefined} aria-current={i === current ? "step" : undefined}>
          <span>{i + 1}</span>
          {label}
        </li>
      ))}
    </ol>
  );
}
