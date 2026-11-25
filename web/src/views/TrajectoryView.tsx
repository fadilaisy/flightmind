import { useEffect, useState } from "react";
import type { Api } from "../api/client";
import type { EventDetail, FlightEvent } from "../api/types";
import { EventFeed } from "../components/EventFeed";
import { InvestigationPanel } from "../components/InvestigationPanel";
import { EVENT_LABEL } from "../domain/eventLabels";
import type { EventState } from "../domain/eventState";
import { formatWindow, formatWindowTitle } from "../domain/format";
import { getStore } from "../state/store";
import { STR } from "../strings";
import { navigate } from "./nav";

interface Props {
  api: Api;
  events: FlightEvent[];
  eventId: string | null;
  states: Record<string, EventState>;
}

export function TrajectoryView({ api, events, eventId, states }: Props) {
  const store = getStore();
  const [selected, setSelected] = useState<EventDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  // The store holds which event is selected; this loads its detail.
  useEffect(() => {
    if (!eventId) {
      setSelected(null);
      return;
    }
    let current = true;
    setError(null);
    api
      .event(eventId)
      .then((d) => current && setSelected(d))
      .catch((e: Error) => current && setError(e.message));
    return () => {
      current = false;
    };
  }, [api, eventId]);

  function select(id: string) {
    const e = events.find((x) => x.id === id);
    store.selectEvent(id, e ? e.icao24 : null);
  }

  function openRecord(rawRef: string) {
    store.setRawRef(rawRef);
    navigate({ tab: "records" });
  }

  return (
    <div className="three">
      <EventFeed events={events} states={states} selectedId={eventId} onSelect={select} />
      <div className="center">
        {error && <p role="alert">{error}</p>}
        <div className="titlebar">
          <h2>{selected ? (selected.callsign ?? selected.icao24) : STR.eventsTitle}</h2>
          {selected && (
            <span className="mono muted" title={formatWindowTitle(selected.start_ts, selected.end_ts)}>
              {selected.icao24} · {EVENT_LABEL[selected.type]} · {formatWindow(selected.start_ts, selected.end_ts)}
            </span>
          )}
          <div className="spacer" />
          <div className="seg">
            <button className="on">{STR.viewMap}</button>
            <button disabled title={STR.notBuilt}>{STR.view3d}</button>
            <button disabled title={STR.notBuilt}>{STR.viewProfile}</button>
          </div>
        </div>
        <div className="viewport" aria-label="Map area" />
        <div className="chartbox" aria-label="Charts area" />
        <div className="scrub" aria-label="Scrubber area" />
      </div>
      <aside className="side r" aria-label="Investigation">
        <div className="block slot" aria-label="Compression card area">
          <p className="muted" style={{ margin: 0, fontSize: 12.5 }}>{STR.compressionEmpty}</p>
        </div>
        {selected ? (
          <InvestigationPanel
            api={api}
            event={selected}
            state={states[selected.id] ?? "to_review"}
            onSetState={store.setEventState}
            onOpenRecord={openRecord}
            onOpenEvent={select}
          />
        ) : (
          <p className="muted block">{STR.selectEvent}</p>
        )}
      </aside>
    </div>
  );
}