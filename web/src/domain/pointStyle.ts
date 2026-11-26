import type { FlightEvent, Track } from "../api/types";
import { isSquawk } from "./eventLabels";
import { inWindow } from "./window";

export type PointStyle = "flagged" | "eventWindow" | "kept";
type Point = Track["points"][number];

/**
 * flagged: inside the window and its raw_ref is one of the event's raw_refs.
 * eventWindow: inside the window without being cited, or marked kept_for_event.
 * kept: every other point.
 */
export function pointStyle(
  point: Pick<Point, "ts" | "raw_ref" | "kept_for_event">,
  event: Pick<FlightEvent, "start_ts" | "end_ts" | "raw_refs">,
): PointStyle {
  const inside = inWindow(point.ts, event);
  if (inside && event.raw_refs.includes(point.raw_ref)) return "flagged";
  if (inside || point.kept_for_event) return "eventWindow";
  return "kept";
}

// Same values as docs/design/prototype-v2.html. Canvas and WebGL layers cannot read CSS variables.
const COLOR = {
  kept: "#0aa2c0",
  eventWindow: "#48cae4",
  flagged: "#d98a0b",
  squawk: "#c8322a",
} as const;

export function styleColor(style: PointStyle, eventType: FlightEvent["type"]): string {
  if (style === "flagged") return isSquawk(eventType) ? COLOR.squawk : COLOR.flagged;
  return COLOR[style];
}