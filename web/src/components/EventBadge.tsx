import dotAmber from "../assets/figma/dot.svg";
import dotRed from "../assets/figma/dot1.svg";
import type { FlightEvent } from "../api/types";
import { SHORT_LABEL, isSquawk } from "../domain/eventLabels";

/** Dark badge with a coloured dot. Amber for routine events, red only for squawks. */
export function EventBadge({ type }: { type: FlightEvent["type"] }) {
  const red = isSquawk(type);
  return (
    <span className={`ebadge${red ? " red" : ""}`}>
      <img src={red ? dotRed : dotAmber} alt="" />
      {SHORT_LABEL[type]}
    </span>
  );
}
