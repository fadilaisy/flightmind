import { useMemo, useState } from "react";
import type { FlightEvent } from "../api/types";
import { filterEvents, type TypeFilter } from "../domain/eventFilter";
import { STATE_LABEL, type EventState } from "../domain/eventState";
import { STR } from "../strings";
import { EventBadge } from "./EventBadge";
import { EventFilters } from "./EventFilters";

interface Props {
  events: FlightEvent[];
  states: Record<string, EventState>;
  selectedId: string | null;
  /** Called on every click, including a click on the row that is already selected. */
  onSelect: (id: string) => void;
}

const hhmm = (iso: string) => iso.slice(11, 19);

/** "Time 08:00:20–08:00:40Z · Airport WIII · Status all", built from the events. */
export function scopeLine(events: FlightEvent[]): string {
  const parts: string[] = [];
  if (events.length > 0) {
    const starts = events.map((e) => e.start_ts).sort();
    const ends = events.map((e) => e.end_ts).sort();
    parts.push(`${STR.searchTimeLabel} ${hhmm(starts[0])}–${hhmm(ends[ends.length - 1])}Z`);
    const airports = [...new Set(events.map((e) => e.airport).filter((a): a is string => !!a))];
    if (airports.length > 0) parts.push(`${STR.searchAirportLabel} ${airports.join(", ")}`);
  }
  parts.push(STR.searchStatusAll);
  return parts.join(" · ");
}

export function EventFeed({ events, states, selectedId, onSelect }: Props) {
  const [type, setType] = useState<TypeFilter>("all");
  const [query, setQuery] = useState("");

  const stateOf = (id: string): EventState => states[id] ?? "to_review";
  const confirmed = events.filter((e) => stateOf(e.id) === "confirmed").length;
  const dismissed = events.filter((e) => stateOf(e.id) === "dismissed").length;
  const types = [...new Set(events.map((e) => e.type))];
  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const e of events) c[e.type] = (c[e.type] ?? 0) + 1;
    return c;
  }, [events]);
  const shown = filterEvents(events, type, query);

  return (
    <aside className="side" aria-label={STR.eventsTitle}>
      <div className="sidehead">
        <div className="sidetitle">
          <h2>{STR.eventsTitle}</h2>
          <span>
            {events.length} flagged · {confirmed} confirmed · {dismissed} dismissed
          </span>
        </div>
        <EventFilters
          types={types}
          counts={counts}
          total={events.length}
          type={type}
          onType={setType}
          query={query}
          onQuery={setQuery}
          scope={scopeLine(events)}
        />
      </div>
      <div className="evlist">
        {events.length === 0 && <p className="listmsg">{STR.noEvents}</p>}
        {events.length > 0 && shown.length === 0 && <p className="listmsg">{STR.noMatches}</p>}
        {shown.map((e) => (
          <button
            key={e.id}
            type="button"
            className={`evrow${e.id === selectedId ? " sel" : ""}`}
            aria-current={e.id === selectedId ? "true" : undefined}
            onClick={() => onSelect(e.id)}
          >
            <div className="top">
              <EventBadge type={e.type} />
              <time dateTime={e.start_ts} title={e.start_ts}>
                {hhmm(e.start_ts)}Z
              </time>
            </div>
            <div className="who">
              <b>{e.callsign ?? STR.noCallsign}</b>
              <span className="icao">{e.icao24.toUpperCase()}</span>
              {e.airport && <span className="ap">· {e.airport}</span>}
            </div>
            <div className="st">
              {STATE_LABEL[stateOf(e.id)]} · {e.raw_refs.length} {STR.supportingRecords}
            </div>
          </button>
        ))}
      </div>
      <div className="foot">{STR.eventsDisclaimerShort}</div>
    </aside>
  );
}
