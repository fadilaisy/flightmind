import type { FlightEvent } from "../api/types";
import { windowColor, KEPT_COLOR, GROUND_TRACK_COLOR } from "../domain/mapColors";
import { STR } from "../strings";

/** Three entries with the Figma line swatches. The event window turns red for a squawk. */
export function Legend({ eventType }: { eventType: FlightEvent["type"] }) {
  return (
    <div className="legend" aria-label={STR.legendLabel}>
      <span>
        <i style={{ background: KEPT_COLOR }} />
        {STR.threeLegendKept}
      </span>
      <span>
        <i style={{ background: windowColor(eventType) }} />
        {STR.threeLegendWindow}
      </span>
      <span>
        <i style={{ background: GROUND_TRACK_COLOR }} />
        {STR.threeLegendGround}
      </span>
    </div>
  );
}
