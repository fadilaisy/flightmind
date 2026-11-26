import type { FlightEvent } from "../api/types";
import { isSquawk } from "./eventLabels";

// Figma values. Canvas and WebGL layers cannot read CSS variables, so they are repeated here.
export const KEPT_COLOR = "#00b4d8";
export const AMBER_COLOR = "#f2b13c";
export const RED_COLOR = "#f0524f";
export const GROUND_TRACK_COLOR = "#0077b6";
export const SCRUB_RING = "#03045e";

/** Amber for routine events, red only for emergency squawks. */
export function windowColor(type: FlightEvent["type"]): string {
  return isSquawk(type) ? RED_COLOR : AMBER_COLOR;
}
