import type { FlightEvent } from "../api/types";

/** POST /api/ask takes only `question`, so the event goes in as a prefix. */
export function buildAskQuestion(
  event: Pick<FlightEvent, "id" | "callsign" | "icao24" | "start_ts" | "end_ts">,
  question: string,
): string {
  const who = event.callsign ?? event.icao24;
  return `About event ${event.id} (${who}, ${event.start_ts} to ${event.end_ts}): ${question}`;
}