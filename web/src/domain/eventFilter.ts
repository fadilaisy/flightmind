import type { FlightEvent } from "../api/types";

export type TypeFilter = FlightEvent["type"] | "all";

/** Filters by event type and by callsign or ICAO24 text (case does not matter). */
export function filterEvents(events: FlightEvent[], type: TypeFilter, query: string): FlightEvent[] {
  const q = query.trim().toLowerCase();
  return events.filter(
    (e) =>
      (type === "all" || e.type === type) &&
      (!q || e.icao24.toLowerCase().includes(q) || (e.callsign ?? "").toLowerCase().includes(q)),
  );
}