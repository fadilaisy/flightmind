import { ApiError, type Api } from "./client";
import type { CompressionReport, EventDetail, FlightEvent, Meta, RawRecord, Track } from "./types";
import {
  ACCEPTED_EXTENSIONS,
  MAX_SIZE_MB,
  PART_SIZE_BYTES,
  type CreateRecordingRequest,
  type Recording,
  type RecordingFormat,
  type RecordingStatus,
  type RecordingStream,
} from "./uploadTypes";

export interface MockData {
  meta: Meta;
  events: FlightEvent[];
  tracks: Record<string, Track>;
  raw: Record<string, RawRecord>;
}

/** Where a mock recording is after each step, in milliseconds. About 10 s from process to ready. */
export const MOCK_TIMELINE = {
  scanMs: 1500,
  queuedMs: 1000,
  decodingMs: 3000,
  filteringMs: 2000,
  detectingMs: 2000,
  storingMs: 2000,
} as const;
const PROCESS_MS =
  MOCK_TIMELINE.queuedMs + MOCK_TIMELINE.decodingMs + MOCK_TIMELINE.filteringMs + MOCK_TIMELINE.detectingMs + MOCK_TIMELINE.storingMs;
const MOCK_RECORDS = 120_000;
const MOCK_KEY = "flightmind.mockRecordings";

export interface MockOptions {
  /** Clock in ms. Tests pass their own so stages move without waiting. */
  now?: () => number;
  /** When set, recordings survive a reload. */
  storage?: Pick<Storage, "getItem" | "setItem">;
}

interface Entry {
  id: string;
  filename: string;
  size: number;
  format: RecordingFormat;
  createdMs: number;
  received: number;
  nextPart: number;
  completedMs: number | null;
  processedMs: number | null;
}

function extensionOf(name: string): string {
  const i = name.lastIndexOf(".");
  return i < 0 ? "" : name.slice(i).toLowerCase();
}

function formatOf(name: string): RecordingFormat {
  const ext = extensionOf(name);
  return ext === ".pcap" ? "pcap" : ext === ".pcapng" ? "pcapng" : "asterix_raw";
}

function streamsFor(format: RecordingFormat): RecordingStream[] {
  const cat21: RecordingStream = {
    id: "s1", src: "10.4.1.20:8600", dst: "239.1.1.21:8600", category: 21,
    sac: 25, sic: 4, frames: 96_412, records: MOCK_RECORDS, supported: true,
  };
  if (format === "asterix_raw") return [{ ...cat21, src: "", dst: "", frames: 0 }];
  const cat62: RecordingStream = {
    id: "s2", src: "10.4.1.22:8610", dst: "239.1.1.62:8610", category: 62,
    sac: 25, sic: 9, frames: 41_077, records: 0, supported: false,
  };
  return [cat21, cat62];
}

function hex10(): string {
  let out = "";
  for (let i = 0; i < 10; i++) out += Math.floor(Math.random() * 16).toString(16);
  return out;
}

// Serves the same shapes as contracts/openapi.yaml from in-memory data.
// The data comes from fixtures/ once Role 2 or Role 3 supplies it.
export function mockApi(data: MockData, options: MockOptions = {}): Api {
  const now = options.now ?? Date.now;
  const entries = new Map<string, Entry>();
  if (options.storage) {
    try {
      const saved = JSON.parse(options.storage.getItem(MOCK_KEY) ?? "[]") as Entry[];
      for (const e of saved) entries.set(e.id, e);
    } catch {
      // A broken saved value is the same as an empty one.
    }
  }
  const save = () => options.storage?.setItem(MOCK_KEY, JSON.stringify([...entries.values()]));

  const points = Object.values(data.tracks).flatMap((t) => t.points);
  const firstTs = points.map((p) => p.ts).sort()[0] ?? null;
  const lastTs = points.map((p) => p.ts).sort().at(-1) ?? null;

  function view(e: Entry): Recording {
    const t = now();
    let status: RecordingStatus = "uploading";
    let progress: Recording["progress"] = null;
    let error: string | null = null;
    let streams: RecordingStream[] = [];
    if (e.completedMs !== null) {
      const sinceComplete = t - e.completedMs;
      if (sinceComplete < MOCK_TIMELINE.scanMs) {
        status = "scanning";
      } else if (e.filename.toLowerCase() === "bad.pcap") {
        status = "failed";
        error = "No CAT021 records found in bad.pcap";
      } else if (e.processedMs === null) {
        status = "scanned";
        streams = streamsFor(e.format);
      } else {
        streams = streamsFor(e.format);
        const since = t - e.processedMs;
        const { queuedMs, decodingMs, filteringMs, detectingMs } = MOCK_TIMELINE;
        if (since < queuedMs) status = "queued";
        else if (since < queuedMs + decodingMs) status = "decoding";
        else if (since < queuedMs + decodingMs + filteringMs) status = "filtering";
        else if (since < queuedMs + decodingMs + filteringMs + detectingMs) status = "detecting";
        else if (since < PROCESS_MS) status = "storing";
        else status = "ready";
        if (status !== "queued" && status !== "ready") {
          progress = { records_done: Math.floor((MOCK_RECORDS * (since - queuedMs)) / (PROCESS_MS - queuedMs)), records_total: MOCK_RECORDS };
        }
        if (status === "ready") progress = { records_done: MOCK_RECORDS, records_total: MOCK_RECORDS };
      }
    }
    const ready = status === "ready";
    return {
      id: e.id,
      filename: e.filename,
      size_bytes: e.size,
      bytes_received: e.received,
      part_size_bytes: PART_SIZE_BYTES,
      format: e.format,
      status,
      progress,
      error,
      record_count: ready ? MOCK_RECORDS : null,
      event_count: ready ? data.events.length : null,
      first_ts: ready ? firstTs : null,
      last_ts: ready ? lastTs : null,
      created_at: new Date(e.createdMs).toISOString(),
      streams,
    };
  }

  function entry(id: string): Entry {
    const e = entries.get(id);
    if (!e) throw new ApiError(404, `/api/recordings/${id}`, `Recording not found: ${id}`);
    return e;
  }

  return {
    meta: async () => data.meta,
    events: async () => data.events,
    event: async (id) => {
      const ev = data.events.find((e) => e.id === id);
      if (!ev) throw new ApiError(404, `/api/events/${id}`, `Event not found: ${id}`);
      const detail: EventDetail = { ...ev, track: data.tracks[ev.icao24], similar: [] };
      return detail;
    },
    track: async (icao24) => {
      const t = data.tracks[icao24];
      if (!t) throw new ApiError(404, `/api/tracks/${icao24}`, `Track not found: ${icao24}`);
      return t;
    },
    ask: async () => ({
      answer_md: "",
      citations: [],
      status: "not_enough_evidence" as const,
    }),
    compression: async (recordingId) => {
      const e = entries.get(recordingId);
      if (e && view(e).status !== "ready") {
        throw new ApiError(404, `/api/compression/${recordingId}`, `Recording not ready: ${recordingId}`);
      }
      const pointsIn = points.length;
      const kept = Math.ceil(pointsIn / 2);
      const report: CompressionReport = {
        recording_id: recordingId,
        raw_bytes: pointsIn * 16,
        stored_bytes: kept * 16,
        ratio: pointsIn === 0 ? 0 : kept / pointsIn,
        max_position_error_m: 0,
        points_in: pointsIn,
        points_kept: kept,
        events_total: data.events.length,
        events_kept: data.events.length,
      };
      return report;
    },
    streamUrl: (recording) => `/api/stream${recording ? `?recording=${encodeURIComponent(recording)}` : ""}`,
    raw: async (rawRef) => {
      const r = data.raw[rawRef];
      if (!r) throw new ApiError(404, `/api/raw/${rawRef}`, `Record not found: ${rawRef}`);
      return r;
    },

    createRecording: async (body: CreateRecordingRequest) => {
      const ext = extensionOf(body.filename);
      if (!(ACCEPTED_EXTENSIONS as readonly string[]).includes(ext)) {
        throw new ApiError(415, "/api/recordings", "Unsupported file extension");
      }
      if (body.size_bytes > MAX_SIZE_MB * 1024 * 1024) {
        throw new ApiError(413, "/api/recordings", "File is larger than 2048 MB");
      }
      const e: Entry = {
        id: `r${hex10()}`,
        filename: body.filename,
        size: body.size_bytes,
        format: formatOf(body.filename),
        createdMs: now(),
        received: 0,
        nextPart: 0,
        completedMs: null,
        processedMs: null,
      };
      entries.set(e.id, e);
      save();
      return view(e);
    },
    uploadPart: async (id, n, bytes) => {
      const e = entry(id);
      if (e.completedMs !== null || n !== e.nextPart) {
        throw new ApiError(409, `/api/recordings/${id}/parts/${n}`, `Part ${n} is out of order`);
      }
      // The bytes are accepted and discarded.
      e.received = Math.min(e.size, e.received + bytes.size);
      e.nextPart += 1;
      save();
    },
    completeRecording: async (id) => {
      const e = entry(id);
      if (e.completedMs === null) e.completedMs = now();
      save();
      return view(e);
    },
    processRecording: async (id, streamId) => {
      const e = entry(id);
      const v = view(e);
      const stream = v.streams.find((s) => s.id === streamId);
      if (v.status !== "scanned" || !stream?.supported) {
        throw new ApiError(409, `/api/recordings/${id}/process`, `Recording ${id} cannot be processed now`);
      }
      e.processedMs = now();
      save();
      return view(e);
    },
    // Newest first. The reverse keeps later inserts first when two share a millisecond.
    listRecordings: async () =>
      [...entries.values()]
        .reverse()
        .sort((a, b) => b.createdMs - a.createdMs)
        .map(view),
    getRecording: async (id) => view(entry(id)),
  };
}
