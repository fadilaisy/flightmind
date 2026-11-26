import type { AskResponse, CompressionReport, EventDetail, FlightEvent, Meta, RawRecord, Track } from "./types";
import type { CreateRecordingRequest, QuarantinePage, Recipe, Recording, RecordingPreview } from "./uploadTypes";

export interface Api {
  meta(): Promise<Meta>;
  /** `recording` is the ?recording= id. Omitted means the server's default recording. */
  events(recording?: string | null): Promise<FlightEvent[]>;
  event(id: string): Promise<EventDetail>;
  track(icao24: string, recording?: string | null): Promise<Track>;
  raw(rawRef: string): Promise<RawRecord>;
  ask(question: string, recording?: string | null): Promise<AskResponse>;
  compression(recordingId: string): Promise<CompressionReport>;
  /** URL of the server-sent events stream. The caller opens it. */
  streamUrl(recording?: string | null): string;

  createRecording(body: CreateRecordingRequest): Promise<Recording>;
  /** Part n (0-based). Resolves when the server answers 204. */
  uploadPart(id: string, n: number, bytes: Blob): Promise<void>;
  completeRecording(id: string): Promise<Recording>;
  processRecording(id: string, streamId: string): Promise<Recording>;
  listRecordings(): Promise<Recording[]>;
  getRecording(id: string): Promise<Recording>;
  recordingPreview(id: string, stream: string, limit?: number): Promise<RecordingPreview>;
  recordingRecipe(id: string): Promise<Recipe>;
  recordingQuarantine(id: string, offset: number, limit: number): Promise<QuarantinePage>;
  /** The export zip: cleaned.csv, events.csv, quarantine.csv, recipe.json. */
  exportRecording(id: string): Promise<Blob>;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public url: string,
    message: string,
  ) {
    super(message);
  }
}

function withRecording(path: string, recording?: string | null): string {
  return recording ? `${path}${path.includes("?") ? "&" : "?"}recording=${encodeURIComponent(recording)}` : path;
}

export function httpApi(baseUrl: string): Api {
  async function send<T>(path: string, init?: RequestInit, parse = true): Promise<T> {
    const url = `${baseUrl}${path}`;
    const res = await fetch(url, init);
    if (!res.ok) {
      throw new ApiError(res.status, url, `Request failed: ${res.status} ${url}`);
    }
    return (parse ? await res.json() : undefined) as T;
  }
  const get = <T>(path: string) => send<T>(path);
  const postJson = <T>(path: string, body: unknown) =>
    send<T>(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  const rec = (id: string) => `/api/recordings/${encodeURIComponent(id)}`;

  return {
    meta: () => get<Meta>("/api/meta"),
    events: (recording) => get<FlightEvent[]>(withRecording("/api/events", recording)),
    event: (id) => get<EventDetail>(`/api/events/${encodeURIComponent(id)}`),
    track: (icao24, recording) =>
      get<Track>(withRecording(`/api/tracks/${encodeURIComponent(icao24)}`, recording)),
    ask: (question, recording) =>
      postJson<AskResponse>("/api/ask", recording ? { question, recording_id: recording } : { question }),
    compression: (recordingId) =>
      get<CompressionReport>(`/api/compression/${encodeURIComponent(recordingId)}`),
    streamUrl: (recording) => `${baseUrl}${withRecording("/api/stream", recording)}`,
    raw: async (rawRef) => {
      try {
        return await get<RawRecord>(`/api/raw/${encodeURIComponent(rawRef)}`);
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) {
          throw new ApiError(404, e.url, `Record not found: ${rawRef}`);
        }
        throw e;
      }
    },
    createRecording: (body) => postJson<Recording>("/api/recordings", body),
    uploadPart: (id, n, bytes) =>
      send<void>(
        `${rec(id)}/parts/${n}`,
        { method: "PUT", headers: { "Content-Type": "application/octet-stream" }, body: bytes },
        false,
      ),
    completeRecording: (id) => postJson<Recording>(`${rec(id)}/complete`, {}),
    processRecording: (id, streamId) => postJson<Recording>(`${rec(id)}/process`, { stream_id: streamId }),
    listRecordings: () => get<Recording[]>("/api/recordings"),
    getRecording: (id) => get<Recording>(rec(id)),
    recordingPreview: (id, stream, limit = 8) =>
      get<RecordingPreview>(`${rec(id)}/preview?stream=${encodeURIComponent(stream)}&limit=${limit}`),
    recordingRecipe: (id) => get<Recipe>(`${rec(id)}/recipe`),
    recordingQuarantine: (id, offset, limit) =>
      get<QuarantinePage>(`${rec(id)}/quarantine?offset=${offset}&limit=${limit}`),
    exportRecording: async (id) => {
      const url = `${baseUrl}${rec(id)}/export`;
      const res = await fetch(url);
      if (!res.ok) throw new ApiError(res.status, url, `Request failed: ${res.status} ${url}`);
      return res.blob();
    },
  };
}

// VITE_API_BASE selects the API. Empty means the mock API.
export function createApi(mock: () => Api): Api {
  const base = import.meta.env.VITE_API_BASE as string | undefined;
  return base ? httpApi(base) : mock();
}

