import type { FlightEvent } from "../api/types";
import { EVENT_LABEL, isSquawk } from "../domain/eventLabels";
import { STATE_LABEL, type EventState } from "../domain/eventState";

interface Props {
  events: FlightEvent[];
  states: Record<string, EventState>;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onSetState: (id: string, state: EventState) => void;
}

export function EventFeed({ events, states, selectedId, onSelect, onSetState }: Props) {
  if (events.length === 0) return <p>No events in this recording.</p>;
  return (
    <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 8 }}>
      {events.map((e) => {
        const state = states[e.id] ?? "to_review";
        const selected = e.id === selectedId;
        return (
          <li
            key={e.id}
            className="card"
            style={{
              borderColor: selected ? "var(--border-strong)" : undefined,
              borderLeft: `4px solid ${isSquawk(e.type) ? "var(--alert-red)" : "var(--event-amber)"}`,
            }}
          >
            <button
              type="button"
              onClick={() => onSelect(e.id)}
              style={{ all: "unset", cursor: "pointer", display: "block", width: "100%" }}
            >
              <strong>{EVENT_LABEL[e.type]}</strong>
              <div className="data">
                {e.callsign ?? "no callsign"} · {e.icao24}
                {e.airport ? ` · ${e.airport}` : ""}
              </div>
              <div className="data" style={{ color: "var(--text-muted)" }}>
                {e.start_ts} to {e.end_ts} · {e.raw_refs.length} records
              </div>
            </button>
            <div style={{ display: "flex", gap: 6, marginTop: 8, alignItems: "center" }}>
              <span>{STATE_LABEL[state]}</span>
              <button type="button" onClick={() => onSetState(e.id, "confirmed")} disabled={state === "confirmed"}>
                Confirm
              </button>
              <button type="button" onClick={() => onSetState(e.id, "dismissed")} disabled={state === "dismissed"}>
                Dismiss
              </button>
              <button type="button" onClick={() => onSetState(e.id, "to_review")} disabled={state === "to_review"}>
                Back to review
              </button>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
