import type { FlightEvent } from "../api/types";

/** True when ts is inside the event's flagged window. Both edges count as inside. */
export function inWindow(ts: string, event: Pick<FlightEvent, "start_ts" | "end_ts">): boolean {
  const t = Date.parse(ts);
  return t >= Date.parse(event.start_ts) && t <= Date.parse(event.end_ts);
}