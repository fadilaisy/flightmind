import { useState } from "react";
import type { FlightEvent } from "../api/types";
import { EVENT_LABEL, isSquawk } from "../domain/eventLabels";
import { STATE_LABEL, type EventState } from "../domain/eventState";
import { STR } from "../strings";

interface Props {
  events: FlightEvent[];
  states: Record<string, EventState>;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function EventFeed({ events, states, selectedId, onSelect }: Props) {
  const [type, setType] = useState<FlightEvent["type"] | "all">("all");
  const [query, setQuery] = useState("");

  const stateOf = (id: string): EventState => states[id] ?? "to_review";
  const confirmed = events.filter((e) => stateOf(e.id) === "confirmed").length;
  const dismissed = events.filter((e) => stateOf(e.id) === "dismissed").length;
  const types = [...new Set(events.map((e) => e.type))];
  const q = query.trim().toLowerCase();
  const shown = events.filter(
    (e) =>
      (type === "all" || e.type === type) &&
      (!q || e.icao24.toLowerCase().includes(q) || (e.callsign ?? "").toLowerCase().includes(q)),
  );

  return (
    <aside className="side" aria-label={STR.eventsTitle}>
      <div className="sidehead">
        <h2 style={{ margin: 0 }}>{STR.eventsTitle}</h2>
        <div className="muted" style={{ fontSize: 12.5 }}>
          {events.length} flagged · {confirmed} confirmed · {dismissed} dismissed
        </div>
      </div>
      <input
        className="search"
        type="search"
        aria-label={STR.searchLabel}
        placeholder={STR.searchLabel}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <div className="filters">
        <button type="button" className={type === "all" ? "on" : undefined} onClick={() => setType("all")}>
          {STR.filterAll}
        </button>
        {types.map((t) => (
          <button key={t} type="button" className={type === t ? "on" : undefined} onClick={() => setType(t)}>
            {EVENT_LABEL[t]}
          </button>
        ))}
      </div>
      <div>
        {events.length === 0 && <p style={{ padding: "0 16px" }}>{STR.noEvents}</p>}
        {events.length > 0 && shown.length === 0 && <p style={{ padding: "0 16px" }}>{STR.noMatches}</p>}
        {shown.map((e) => (
          <button
            key={e.id}
            type="button"
            className={`evrow${e.id === selectedId ? " sel" : ""}`}
            onClick={() => onSelect(e.id)}
          >
            <div className="top">
              <span className={`badge ${isSquawk(e.type) ? "b-red" : "b-event"}`}>{EVENT_LABEL[e.type]}</span>
              <span className="mono muted" title={e.start_ts}>
                {e.start_ts.slice(11, 19)}Z
              </span>
            </div>
            <div className="who">
              {e.callsign ?? STR.noCallsign} <span className="mono muted" style={{ fontWeight: 400 }}>{e.icao24}</span>
            </div>
            <div className="st">
              {STATE_LABEL[stateOf(e.id)]} · {e.raw_refs.length} {STR.records}
            </div>
          </button>
        ))}
      </div>
      <div className="foot">{STR.eventsDisclaimer}</div>
    </aside>
  );
}