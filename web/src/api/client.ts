import type { AskResponse, CompressionReport, EventDetail, FlightEvent, Meta, RawRecord, Track } from "./types";

export interface Api {
  meta(): Promise<Meta>;
  events(): Promise<FlightEvent[]>;
  event(id: string): Promise<EventDetail>;
  track(icao24: string): Promise<Track>;
  raw(rawRef: string): Promise<RawRecord>;
  ask(question: string): Promise<AskResponse>;
  compression(recordingId: string): Promise<CompressionReport>;
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

export function httpApi(baseUrl: string): Api {
  async function get<T>(path: string): Promise<T> {
    const url = `${baseUrl}${path}`;
    const res = await fetch(url);
    if (!res.ok) {
      throw new ApiError(res.status, url, `Request failed: ${res.status} ${url}`);
    }
    return (await res.json()) as T;
  }
  return {
    meta: () => get<Meta>("/api/meta"),
    events: () => get<FlightEvent[]>("/api/events"),
    event: (id) => get<EventDetail>(`/api/events/${encodeURIComponent(id)}`),
    track: (icao24) => get<Track>(`/api/tracks/${encodeURIComponent(icao24)}`),
    ask: async (question) => {
      const url = `${baseUrl}/api/ask`;
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) throw new ApiError(res.status, url, `Request failed: ${res.status} ${url}`);
      return (await res.json()) as AskResponse;
    },
    compression: async (recordingId) => {
      try {
        return await get<CompressionReport>(`/api/compression/${encodeURIComponent(recordingId)}`);
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) {
          throw new ApiError(404, e.url, `No compression report for this recording`);
        }
        throw e;
      }
    },
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
  };
}

// VITE_API_BASE selects the API. Empty means the mock API.
export function createApi(mock: () => Api): Api {
  const base = import.meta.env.VITE_API_BASE as string | undefined;
  return base ? httpApi(base) : mock();
}
