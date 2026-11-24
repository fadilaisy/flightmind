import { ApiError, type Api } from "./client";
import type { EventDetail, FlightEvent, Meta, RawRecord, Track } from "./types";

export interface MockData {
  meta: Meta;
  events: FlightEvent[];
  tracks: Record<string, Track>;
  raw: Record<string, RawRecord>;
}

// Serves the same shapes as contracts/openapi.yaml from in-memory data.
// The data comes from fixtures/ once Role 2 or Role 3 supplies it.
export function mockApi(data: MockData): Api {
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
    raw: async (rawRef) => {
      const r = data.raw[rawRef];
      if (!r) throw new ApiError(404, `/api/raw/${rawRef}`, `Record not found: ${rawRef}`);
      return r;
    },
  };
}
