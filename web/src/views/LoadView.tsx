import { useEffect, useRef, useState } from "react";
import { ApiError, type Api } from "../api/client";
import type { Recording } from "../api/uploadTypes";
import { DropZone } from "../components/DropZone";
import { StateBox } from "../components/StateBox";
import {
  STAGES,
  UploadError,
  bytesLine,
  checkFile,
  defaultRecordingDate,
  followRecording,
  formatSize,
  isRawFormat,
  stageIndex,
  stageLabel,
  uploadRecording,
} from "../domain/upload";
import { STR } from "../strings";

export interface StartUpload {
  file: File;
  date?: string;
}

interface Props {
  api: Api;
  /** A recording that is already on the server and not ready. The view follows it. */
  follow?: string | null;
  /** A file picked somewhere else (the header panel). The view uploads it at once. */
  start?: StartUpload | null;
  onReady: (id: string) => void;
  /** The scan finished: the analyst picks a stream next. */
  onScanned: (recording: Recording) => void;
  /** "Try another file" was pressed. */
  onReset: () => void;
}

type Phase =
  | { name: "choose" }
  | { name: "date"; file: File; date: string }
  | { name: "working"; filename: string; size: number; sent: number; recording: Recording | null }
  | { name: "failed"; message: string };

const nf = (n: number) => n.toLocaleString("en-US");

/** The Load screen (Figma frame 1) and what follows a file: upload, processing, failure. */
export function LoadView({ api, follow = null, start = null, onReady, onScanned, onReset }: Props) {
  const [phase, setPhase] = useState<Phase>(() =>
    start || follow ? { name: "working", filename: start?.file.name ?? "", size: start?.file.size ?? 0, sent: 0, recording: null } : { name: "choose" },
  );
  const alive = useRef(true);
  const started = useRef(false);
  const live = () => alive.current;

  async function track(id: string) {
    try {
      const result = await followRecording(api, id, {
        shouldStop: () => !live(),
        onUpdate: (r) =>
          live() &&
          setPhase((p) =>
            p.name === "working"
              ? { ...p, recording: r, filename: r.filename, size: r.size_bytes, sent: r.status === "uploading" ? Math.max(p.sent, r.bytes_received) : r.size_bytes }
              : p,
          ),
      });
      if (!live()) return;
      if (result.kind === "ready") onReady(id);
      else if (result.kind === "scanned") onScanned(result.recording);
      else if (result.kind === "failed") setPhase({ name: "failed", message: result.error });
    } catch (e) {
      if (live()) setPhase({ name: "failed", message: describe(e) });
    }
  }

  async function submit(file: File, date?: string) {
    const problem = checkFile(file.name, file.size);
    if (problem) {
      setPhase({ name: "failed", message: problem });
      return;
    }
    setPhase({ name: "working", filename: file.name, size: file.size, sent: 0, recording: null });
    try {
      const rec = await uploadRecording(api, file, {
        recordingDate: date,
        shouldStop: () => !live(),
        onProgress: (p) =>
          live() && setPhase((cur) => (cur.name === "working" ? { ...cur, sent: p.sent, recording: p.recording } : cur)),
      });
      if (!live()) return;
      await track(rec.id);
    } catch (e) {
      if (live()) setPhase({ name: "failed", message: describe(e) });
    }
  }

  function pick(file: File) {
    if (isRawFormat(file.name) && !checkFile(file.name, file.size)) {
      setPhase({ name: "date", file, date: defaultRecordingDate(file.lastModified) });
    } else {
      void submit(file);
    }
  }

  useEffect(() => {
    alive.current = true;
    if (!started.current) {
      started.current = true;
      if (start) {
        if (isRawFormat(start.file.name) && !start.date) pick(start.file);
        else void submit(start.file, start.date);
      } else if (follow) {
        void track(follow);
      }
    }
    return () => {
      alive.current = false;
    };
    // The view starts its work once, on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="loadpage">
      <div className="loadbox">
        <h1>{STR.loadTitle}</h1>
        <p className="loadintro">{STR.loadIntro}</p>
        {phase.name === "choose" && <DropZone onFile={pick} />}
        {phase.name === "date" && (
          <DateStep
            file={phase.file}
            date={phase.date}
            onDate={(date) => setPhase({ ...phase, date })}
            onStart={() => void submit(phase.file, phase.date)}
            onBack={() => setPhase({ name: "choose" })}
          />
        )}
        {phase.name === "working" && <Working phase={phase} />}
        {phase.name === "failed" && (
          <StateBox kind="error" title={STR.uploadFailed} text={phase.message}>
            <button
              type="button"
              className="fbtn lg"
              onClick={() => {
                setPhase({ name: "choose" });
                onReset();
              }}
            >
              {STR.tryAnotherFile}
            </button>
          </StateBox>
        )}
        <div className="loadsteps">
          <Step n={1} title={STR.step1Title} text={STR.step1Text} />
          <Step n={2} title={STR.step2Title} text={STR.step2Text} />
          <Step n={3} title={STR.step3Title} text={STR.step3Text} />
        </div>
        <p className="loadfoot">
          <b>{STR.whatIsCat021}</b> {STR.whatIsCat021Text}
        </p>
      </div>
    </div>
  );
}

function describe(e: unknown): string {
  if (e instanceof UploadError && e.cause instanceof ApiError && e.cause.status === 404) return STR.recordingNotFound;
  return e instanceof Error ? e.message : String(e);
}

function Step({ n, title, text }: { n: number; title: string; text: string }) {
  return (
    <div className="loadstep">
      <div className="loadstep-head">
        <span>{n}</span>
        <b>{title}</b>
      </div>
      <p>{text}</p>
    </div>
  );
}

function DateStep(props: {
  file: File;
  date: string;
  onDate: (d: string) => void;
  onStart: () => void;
  onBack: () => void;
}) {
  return (
    <div className="dropzone datestep">
      <h2>{props.file.name}</h2>
      <p className="dropnote">
        {formatSize(props.file.size)}. {STR.recordingDateNote}
      </p>
      <label className="datefield">
        <span>{STR.recordingDate}</span>
        <input type="date" value={props.date} onChange={(e) => props.onDate(e.target.value)} />
      </label>
      <div className="rowbtns">
        <button type="button" className="fbtn lg solid" disabled={!props.date} onClick={props.onStart}>
          {STR.startUpload}
        </button>
        <button type="button" className="fbtn lg" onClick={props.onBack}>
          {STR.chooseAnother}
        </button>
      </div>
    </div>
  );
}

function Working({ phase }: { phase: Extract<Phase, { name: "working" }> }) {
  const r = phase.recording;
  const status = r?.status ?? "uploading";
  const current = stageIndex(status);
  let detail: string;
  let ratio = 0;
  if (status === "uploading") {
    detail = bytesLine(phase.sent, phase.size);
    ratio = phase.size > 0 ? phase.sent / phase.size : 0;
  } else if (r?.progress) {
    detail = `${nf(r.progress.records_done)} of ${nf(r.progress.records_total)} ${STR.recordsOf}`;
    ratio = r.progress.records_total > 0 ? r.progress.records_done / r.progress.records_total : 0;
  } else {
    detail = `${stageLabel(status)}.`;
  }
  return (
    <div className="dropzone working" role="status" aria-label={STR.processingLabel}>
      <h2>{phase.filename || STR.loadingRecording}</h2>
      {phase.size > 0 && <p className="dropnote">{formatSize(phase.size)}</p>}
      <ol className="stages" aria-label={STR.stagesLabel}>
        {STAGES.map((label, i) => (
          <li key={label} className={i < current ? "done" : i === current ? "now" : undefined} aria-current={i === current ? "step" : undefined}>
            <span>{i + 1}</span>
            {label}
          </li>
        ))}
      </ol>
      <div className="bar" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(ratio * 100)}>
        <i style={{ width: `${Math.round(ratio * 100)}%` }} />
      </div>
      <p className="mono workdetail">{detail}</p>
    </div>
  );
}

