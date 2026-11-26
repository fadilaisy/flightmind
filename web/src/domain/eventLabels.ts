import type { FlightEvent } from "../api/types";

// Says what the detector flagged, not what the aircraft did (ui.md wording rule).
export const EVENT_LABEL: Record<FlightEvent["type"], string> = {
  go_around: "Go-around flag",
  holding: "Holding flag",
  squawk_7500: "Squawk 7500 flag",
  squawk_7600: "Squawk 7600 flag",
  squawk_7700: "Squawk 7700 flag",
};

export function isSquawk(type: FlightEvent["type"]): boolean {
  return type.startsWith("squawk_");
}

// Short labels for badges and chips (Figma). Squawk badges name the code.
export const SHORT_LABEL: Record<FlightEvent["type"], string> = {
  go_around: "Go-around",
  holding: "Holding",
  squawk_7500: "Squawk 7500",
  squawk_7600: "Squawk 7600",
  squawk_7700: "Squawk 7700",
};

/** "go-around flag", lower case, for running text. */
export function phrase(type: FlightEvent["type"]): string {
  return EVENT_LABEL[type].toLowerCase();
}

