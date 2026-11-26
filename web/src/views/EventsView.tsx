import { useState } from "react";
import type { FlightEvent } from "../api/types";
import { scopeLine } from "../components/EventFeed";
import { EventFilters } from "../components/EventFilters";
import { filterEvents, type TypeFilter } from "../domain/eventFilter";
import { EventBadge } from "../components/EventBadge";
import { STATE_LABEL, type EventState } from "../domain/eventState";
import { formatWindow, formatWindowTitle } from "../domain/format";
import { getStore } from "../state/store";
import { STR } from "../strings";
import { navigate } from "./nav";

interface Props {
  events: FlightEvent[];
  states: Record<string, EventState>;
}

export function EventsView({ events, states }: Props) {
  const store = getStore();
  const [type, setType] = useState<TypeFilter>("all");
  const [query, setQuery] = useState("");
  const stateOf = (id: string): EventState => states[id] ?? "to_review";
  const count = (s: EventState) => events.filter((e) => stateOf(e.id) === s).length;
  const shown = filterEvents(events, type, query);
  const types = [...new Set(events.map((e) => e.type))];
  const counts: Record<string, number> = {};
  for (const e of events) counts[e.type] = (counts[e.type] ?? 0) + 1;

  function open(e: FlightEvent) {
    store.selectEvent(e.id, e.icao24);
    navigate({ tab: "trajectory" });
  }

  return (
    <div className="wrap">
      <h1>{STR.eventsPageTitle}</h1>
      <p className="muted">{STR.eventsPageIntro}</p>
      <div className="stats">
        <div className="card">
          <div className="muted">{STR.statCandidates}</div>
          <div className="big">{events.length}</div>
          <div className="muted cap">{STR.statCandidatesNote}</div>
        </div>
        <div className="card">
          <div className="muted">{STATE_LABEL.to_review}</div>
          <div className="big">{count("to_review")}</div>
          <div className="muted cap">{STR.statReviewNote}</div>
        </div>
        <div className="card">
          <div className="muted">{STATE_LABEL.confirmed}</div>
          <div className="big ok">{count("confirmed")}</div>
          <div className="muted cap">{STR.statConfirmedNote}</div>
        </div>
        <div className="card">
          <div className="muted">{STATE_LABEL.dismissed}</div>
          <div className="big">{count("dismissed")}</div>
          <div className="muted cap">{STR.statDismissedNote}</div>
        </div>
      </div>
      <div className="card evtable" style={{ padding: 0 }}>
        <div className="eventsbar">
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
        {shown.length === 0 ? (
          <p style={{ padding: 16 }}>{events.length === 0 ? STR.noEvents : STR.noMatches}</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>{STR.colEvent}</th>
                <th>{STR.colAircraft}</th>
                <th>{STR.colWindow}</th>
                <th>{STR.colRecords}</th>
                <th>{STR.colReview}</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((e) => {
                const s = stateOf(e.id);
                return (
                  <tr key={e.id} className={`click ${s}`} onClick={() => open(e)}>
                    <td>
                      <EventBadge type={e.type} />
                    </td>
                    <td>
                      <b>{e.callsign ?? STR.noCallsign}</b> <span className="mono icao">{e.icao24.toUpperCase()}</span>
                      {e.airport && <div className="muted">{e.airport}</div>}
                    </td>
                    <td className="mono" title={formatWindowTitle(e.start_ts, e.end_ts)}>
                      {formatWindow(e.start_ts, e.end_ts)}
                    </td>
                    <td className="mono">{e.raw_refs.length}</td>
                    <td className="revcell" onClick={(ev) => ev.stopPropagation()}>
                      <span className={`rstate ${s}`}>{s === "confirmed" ? "\u2713 " : ""}{STATE_LABEL[s]}</span>
                      {s === "to_review" ? (
                        <>
                          <button type="button" className="rbtn" onClick={() => store.setEventState(e.id, "confirmed")}>
                            {STR.confirm}
                          </button>{" "}
                          <button type="button" className="rbtn plain" onClick={() => store.setEventState(e.id, "dismissed")}>
                            {STR.dismiss}
                          </button>
                        </>
                      ) : (
                        <button type="button" className="rbtn plain" onClick={() => store.setEventState(e.id, "to_review")}>
                          {STR.backToReview}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
      <p className="muted" style={{ fontSize: 12.5 }}>{STR.eventsDisclaimerShort}</p>
    </div>
  );
}
