import type { RawRecord } from "./types";

// Temporary types for the recording upload contract (SCRUM-62, upload plan section 1).
// They get replaced by `contracts/types.ts` once SCRUM-62 merges. Keep them identical to the contract until then.

export const PART_SIZE_BYTES = 52_428_800;
export const MAX_SIZE_MB = 2048;
export const ACCEPTED_EXTENSIONS = [".pcap", ".pcapng", ".atx", ".ast", ".bin"] as const;
/** Extensions that carry no capture time, so the analyst gives a recording date. */
export const RAW_EXTENSIONS = [".atx", ".ast", ".bin"] as const;

export type RecordingFormat = "pcap" | "pcapng" | "asterix_raw";

export type RecordingStatus =
  | "uploading"
  | "scanning"
  | "scanned"
  | "queued"
  | "decoding"
  | "filtering"
  | "detecting"
  | "storing"
  | "ready"
  | "failed";

export interface RecordingStream {
  id: string;
  src: string;
  dst: string;
  category: number;
  sac: number;
  sic: number;
  frames: number;
  records: number;
  supported: boolean;
}

export interface RecordingProgress {
  records_done: number;
  records_total: number;
}

export interface Recording {
  /** "r" followed by 10 hex digits. */
  id: string;
  filename: string;
  size_bytes: number;
  bytes_received: number;
  part_size_bytes: number;
  format: RecordingFormat;
  status: RecordingStatus;
  progress: RecordingProgress | null;
  error: string | null;
  record_count: number | null;
  event_count: number | null;
  first_ts: string | null;
  last_ts: string | null;
  created_at: string;
  streams: RecordingStream[];
}

export interface CreateRecordingRequest {
  filename: string;
  size_bytes: number;
  recording_date?: string;
}

export interface ProcessRecordingRequest {
  stream_id: string;
}

// Upload plan 6.1: decoded preview, cleaning recipe, quarantine and export.

export interface FieldQuality {
  /** For example "I021/130". */
  item: string;
  label: string;
  present_pct: number;
}

export interface RecordingPreview {
  records: RawRecord[];
  field_quality: FieldQuality[];
  /** Set when the quality figures come from a sample, not every record. */
  sample_size?: number;
}

export interface RecipeStep {
  code: string;
  label: string;
  records_in: number;
  set_aside: number;
  reason: string;
}

export interface Recipe {
  input_sha256: string;
  steps: RecipeStep[];
  tolerance_note: string;
  raw_bytes: number;
  stored_bytes: number;
  ratio: number;
}

export interface QuarantineItem {
  raw_ref: string;
  step_code: string;
  reason: string;
}

export interface QuarantinePage {
  total: number;
  items: QuarantineItem[];
}

