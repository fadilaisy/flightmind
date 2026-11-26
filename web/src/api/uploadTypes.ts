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
