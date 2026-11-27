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
  uploadUnfinished: "This upload did not finish. Try another file.",
  notCat021: "The start of this file is not pcap, pcapng or ASTERIX CAT021 data.",
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

/** True for errors a retry cannot fix (the server understood and refused). 408, 429, 5xx and network errors are retried. */
function permanent(e: unknown): boolean {
  return e instanceof ApiError && e.status >= 400 && e.status < 500 && e.status !== 408 && e.status !== 429;
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
  | { kind: "scanned" }
  | { kind: "ready" }
  | { kind: "failed"; error: string };

/** What to do with a recording after a poll. */
export function nextAction(r: Recording): NextAction {
  if (r.status === "failed") return { kind: "failed", error: r.error ?? "Processing failed." };
  if (r.status === "ready") return { kind: "ready" };
  if (r.status === "scanned") return { kind: "scanned" };
  return { kind: "wait" };
}

/** The id of the stream to preview at once, for a raw file that has the single stream "raw". Otherwise null. */
export function rawStreamId(r: Recording): string | null {
  return r.streams.length === 1 && r.streams[0].id === "raw" && r.streams[0].supported ? "raw" : null;
}

export interface FollowOptions {
  onUpdate: (r: Recording) => void;
  shouldStop?: () => boolean;
  /** Wait between polls. Tests pass a recorder. */
  sleep?: (ms: number) => Promise<void>;
  /** True when this tab is not sending the parts: an `uploading` recording will never finish, so fail instead of polling. */
  abandonUploading?: boolean;
}

export type FollowResult =
  | { kind: "scanned"; recording: Recording }
  | { kind: "ready"; recording: Recording }
  | { kind: "failed"; recording: Recording; error: string }
  | { kind: "stopped" };

/** Poll GET /api/recordings/{id} every 2 s until the recording is scanned, ready or failed. Never starts processing. */
export async function followRecording(api: Api, id: string, options: FollowOptions): Promise<FollowResult> {
  const sleep = options.sleep ?? wait;
  for (;;) {
    if (options.shouldStop?.()) return { kind: "stopped" };
    let r: Recording;
    try {
      r = await api.getRecording(id);
    } catch (e) {
      throw new UploadError(errorText(e, "poll"), e);
    }
    options.onUpdate(r);
    if (options.abandonUploading && r.status === "uploading") {
      return { kind: "failed", recording: r, error: MSG.uploadUnfinished };
    }
    const action = nextAction(r);
    if (action.kind === "ready") return { kind: "ready", recording: r };
    if (action.kind === "scanned") return { kind: "scanned", recording: r };
    if (action.kind === "failed") return { kind: "failed", recording: r, error: action.error };
    await sleep(POLL_MS);
  }
}

/** Statuses while the server works on a chosen stream. */
export const PROCESSING_STATUSES: readonly RecordingStatus[] = ["queued", "decoding", "filtering", "detecting", "storing"];

export function isProcessing(status: RecordingStatus): boolean {
  return PROCESSING_STATUSES.includes(status);
}
