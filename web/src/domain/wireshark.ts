import type { FlightEvent } from "../api/types";
import { EVENT_LABEL } from "./eventLabels";

/** "14:02:30Z" from an ISO time. */
function clockZ(iso: string): string {
  return `${iso.slice(11, 19)}Z`;
}

/** Wireshark display filter for an event's flagged window and aircraft. */
export function wiresharkFilter(event: Pick<FlightEvent, "icao24" | "start_ts" | "end_ts">): string {
  return `asterix.021_080 == 0x${event.icao24.toUpperCase()} && i021_071 >= ${clockZ(event.start_ts)} && i021_071 <= ${clockZ(event.end_ts)}`;
}

/** Short name of an event for a chip, e.g. "GIA412 go-around flag". */
export function eventChipLabel(event: Pick<FlightEvent, "callsign" | "icao24" | "type">): string {
  return `${event.callsign ?? event.icao24} ${EVENT_LABEL[event.type].toLowerCase()}`;
}
