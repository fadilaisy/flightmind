import type { FlightEvent } from "../api/types";
import { isSquawk } from "../domain/eventLabels";
import { styleColor, type PointStyle } from "../domain/pointStyle";
import { STR } from "../strings";

const ITEMS: { style: PointStyle; label: string }[] = [
  { style: "kept", label: STR.legendKept },
  { style: "eventWindow", label: STR.legendEventWindow },
  { style: "flagged", label: STR.legendFlagged },
];

/** Every colour carries a label. A squawk event draws flagged points in red. */
export function Legend({ eventType }: { eventType: FlightEvent["type"] }) {
  return (
    <div className="legend" aria-label={STR.legendLabel}>
      {ITEMS.map((i) => (
        <span key={i.style}>
          <i style={{ background: styleColor(i.style, eventType) }} />
          {i.label}
        </span>
      ))}
      {isSquawk(eventType) && <span className="muted">{STR.legendSquawk}</span>}
    </div>
  );
}
