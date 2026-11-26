import { ApiError, type Api } from "../api/client";
import {
  ACCEPTED_EXTENSIONS,
  MAX_SIZE_MB,
  RAW_EXTENSIONS,
  type Recording,
  type RecordingStatus,
} from "../api/uploadTypes";

export const POLL_MS = 2000;
export const MAX_PART_RETRIES = 3;

export const STAGES = ["Uploading", "Scanning", "Decoding", "Filtering", "Detecting events", "Storing"] as const;

const STAGE_INDEX: Record<RecordingStatus, number> = {
  uploading: 0,
  scanning: 1,
  scanned: 1,
  queued: 2,
  decoding: 2,
  filtering: 3,
  detecting: 4,
  storing: 5,
  ready: STAGES.length,
  failed: -1,
};

/** Index into STAGES of the stage in progress. STAGES.length once ready, -1 when failed. */
export function stageIndex(status: RecordingStatus): number {
  return STAGE_INDEX[status];
}

export function stageLabel(status: RecordingStatus): string {
  if (status === "queued") return "Queued";
  if (status === "ready") return "Ready";
  if (status === "failed") return "Failed";
  return STAGES[STAGE_INDEX[status]];
}

export const MSG = {
  tooLarge: "This file is larger than 2 GB.",
  badType: "FlightMind reads .pcap, .pcapng, .atx, .ast and .bin files.",
  notCat021: "The start of this file is not pcap, pcapng or ASTERIX CAT021 data.",
  noSupportedStream: "This recording has no CAT021 stream FlightMind can read.",
  severalStreams: "This recording has more than one CAT021 stream. Choosing a stream is not built yet.",
} as const;

export function extensionOf(name: string): string {
  const i = name.lastIndexOf(".");
  return i < 0 ? "" : name.slice(i).toLowerCase();
}

export function isRawFormat(name: string): boolean {
  return (RAW_EXTENSIONS as readonly string[]).includes(extensionOf(name));
}

/** The sentence to show when the file cannot be sent, or null when it can. */
export function checkFile(name: string, sizeBytes: number): string | null {
  if (!(ACCEPTED_EXTENSIONS as readonly string[]).includes(extensionOf(name))) return MSG.badType;
  if (sizeBytes > MAX_SIZE_MB * 1024 * 1024) return MSG.tooLarge;
  return null;
}

export function formatMb(bytes: number): string {
  return (bytes / 1_048_576).toFixed(1);
}

/** "48.0 of 312.0 MB" */
export function bytesLine(sent: number, total: number): string {
  return `${formatMb(sent)} of ${formatMb(total)} MB`;
}

/** The file's last-modified date as YYYY-MM-DD, the default for "Recording date". */
export function defaultRecordingDate(lastModifiedMs: number): string {
  return new Date(lastModifiedMs).toISOString().slice(0, 10);
}

export function formatSize(bytes: number): string {
  return bytes >= 1_073_741_824 ? `${(bytes / 1_073_741_824).toFixed(1)} GB` : `${formatMb(bytes)} MB`;
}

/** The sentence for an error from the API, by the step that raised it. */
export function errorText(e: unknown, step: "create" | "part" | "complete" | "process" | "poll"): string {
  if (e instanceof ApiError) {
    if (e.status === 413) return MSG.tooLarge;
    if (e.status === 415) return step === "complete" ? MSG.notCat021 : MSG.badType;
    return e.message;
  }
  return e instanceof Error ? e.message : String(e);
}

export interface UploadProgress {
  sent: number;
  total: number;
  recording: Recording;
}

export interface UploadOptions {
  recordingDate?: string;
  onProgress?: (p: UploadProgress) => void;
  /** Stop between parts when this returns true. */
  shouldStop?: () => boolean;
  /** Wait before a retry. Tests pass a no-op. */
  delay?: (ms: number) => Promise<void>;
}

const wait = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

/** True for errors a retry cannot fix (the server understood and refused). */
function permanent(e: unknown): boolean {
  return e instanceof ApiError && e.status >= 400 && e.status < 500;
}

/** Create the recording, send each part in order, retry a failed part up to 3 times, then complete. */
export async function uploadRecording(api: Api, file: File, options: UploadOptions = {}): Promise<Recording> {
  const delay = options.delay ?? wait;
  let created: Recording;
  try {
    created = await api.createRecording({
      filename: file.name,
      size_bytes: file.size,
      ...(options.recordingDate ? { recording_date: options.recordingDate } : {}),
    });
  } catch (e) {
    throw new UploadError(errorText(e, "create"), e);
  }
  const part = created.part_size_bytes;
  const parts = Math.max(1, Math.ceil(file.size / part));
  let sent = 0;
  options.onProgress?.({ sent, total: file.size, recording: created });
  for (let n = 0; n < parts; n++) {
    if (options.shouldStop?.()) throw new UploadError("Upload stopped.", null);
    const slice = file.slice(n * part, Math.min(file.size, (n + 1) * part));
    for (let attempt = 0; ; attempt++) {
      try {
        await api.uploadPart(created.id, n, slice);
        break;
      } catch (e) {
        if (permanent(e) || attempt >= MAX_PART_RETRIES) {
          throw new UploadError(errorText(e, "part"), e);
        }
        await delay(500 * (attempt + 1));
      }
    }
    sent += slice.size;
    options.onProgress?.({ sent, total: file.size, recording: created });
  }
  try {
    return await api.completeRecording(created.id);
  } catch (e) {
    throw new UploadError(errorText(e, "complete"), e);
  }
}

export class UploadError extends Error {
  constructor(
    message: string,
    public cause: unknown,
  ) {
    super(message);
  }
}

export type NextAction =
  | { kind: "wait" }
  | { kind: "process"; streamId: string }
  | { kind: "ready" }
  | { kind: "failed"; error: string }
  | { kind: "choose"; message: string };

/** What to do with a recording after a poll. */
export function nextAction(r: Recording): NextAction {
  if (r.status === "failed") return { kind: "failed", error: r.error ?? "Processing failed." };
  if (r.status === "ready") return { kind: "ready" };
  if (r.status === "scanned") {
    const supported = r.streams.filter((s) => s.supported);
    if (supported.length === 1) return { kind: "process", streamId: supported[0].id };
    return { kind: "choose", message: supported.length === 0 ? MSG.noSupportedStream : MSG.severalStreams };
  }
  return { kind: "wait" };
}

export interface FollowOptions {
  onUpdate: (r: Recording) => void;
  shouldStop?: () => boolean;
  /** Wait between polls. Tests pass a recorder. */
  sleep?: (ms: number) => Promise<void>;
}

export type FollowResult =
  | { kind: "ready"; recording: Recording }
  | { kind: "failed"; recording: Recording; error: string }
  | { kind: "choose"; recording: Recording; message: string }
  | { kind: "stopped" };

/** Poll GET /api/recordings/{id} every 2 s. Calls process once when exactly one stream is supported. */
export async function followRecording(api: Api, id: string, options: FollowOptions): Promise<FollowResult> {
  const sleep = options.sleep ?? wait;
  let processed = false;
  for (;;) {
    if (options.shouldStop?.()) return { kind: "stopped" };
    let r: Recording;
    try {
      r = await api.getRecording(id);
    } catch (e) {
      throw new UploadError(errorText(e, "poll"), e);
    }
    options.onUpdate(r);
    const action = nextAction(r);
    if (action.kind === "ready") return { kind: "ready", recording: r };
    if (action.kind === "failed") return { kind: "failed", recording: r, error: action.error };
    if (action.kind === "choose") return { kind: "choose", recording: r, message: action.message };
    if (action.kind === "process" && !processed) {
      processed = true;
      try {
        options.onUpdate(await api.processRecording(id, action.streamId));
      } catch (e) {
        throw new UploadError(errorText(e, "process"), e);
      }
    }
    await sleep(POLL_MS);
  }
}
