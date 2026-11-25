import { useEffect, useMemo, useState } from "react";
import { createApi, type Api } from "./api/client";
import { mockApi, type MockData } from "./api/mockClient";
import type { EventDetail, FlightEvent } from "./api/types";
import { EventFeed } from "./components/EventFeed";
import { InvestigationPanel } from "./components/InvestigationPanel";
import { RawRecordViewer } from "./components/RawRecordViewer";
import { EVENT_LABEL } from "./domain/eventLabels";
import { formatWindow, formatWindowTitle } from "./domain/format";
import { getStore, useStore } from "./state/store";
import { STR } from "./strings";
import { Shell } from "./views/Shell";
import mini from "../tests/fixtures/mini.json";

export function App() {
  // VITE_API_BASE set: real or SCRUM-33 mock API. Otherwise the sample fixture.
  const api: Api = useMemo(
    () => createApi(() => mockApi(mini as unknown as MockData)),
    [],
  );
  const usingSample = !import.meta.env.VITE_API_BASE;
  const store = getStore();

  const eventId = useStore((s) => s.eventId);
  const rawRef = useStore((s) => s.rawRef);
  const eventStates = useStore((s) => s.eventStates);

  const [events, setEvents] = useState<FlightEvent[]>([]);
  const [selected, setSelected] = useState<EventDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .events()
      .then(setEvents)
      .catch((e: Error) => setError(e.message));
  }, [api]);

  // The store holds which event is selected; this loads its detail.
  useEffect(() => {
    if (!eventId) {
      setSelected(null);
      return;
    }
    let current = true;
    api
      .event(eventId)
      .then((d) => current && setSelected(d))
      .catch((e: Error) => current && setError(e.message));
    return () => {
      current = false;
    };
  }, [api, eventId]);

  function select(id: string) {
    setError(null);
    const e = events.find((x) => x.id === id) ?? selected;
    store.selectEvent(id, e && e.id === id ? e.icao24 : null);
  }

  const trajectory = (
    <div className="three">
      <EventFeed events={events} states={eventStates} selectedId={eventId} onSelect={select} />
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
        {rawRef && <RawRecordViewer api={api} rawRef={rawRef} onClose={() => store.setRawRef(null)} />}
      </div>
      <aside className="side r" aria-label="Investigation">
        <div className="block slot" aria-label="Compression card area">
          <p className="muted" style={{ margin: 0, fontSize: 12.5 }}>{STR.compressionEmpty}</p>
        </div>
        {selected ? (
          <InvestigationPanel
            api={api}
            event={selected}
            state={eventStates[selected.id] ?? "to_review"}
            onSetState={store.setEventState}
            onOpenRecord={store.setRawRef}
            onOpenEvent={select}
          />
        ) : (
          <p className="muted block">{STR.selectEvent}</p>
        )}
      </aside>
    </div>
  );

  return (
    <Shell api={api} usingSample={usingSample}>
      {(tab) => (tab === "trajectory" ? trajectory : <p style={{ padding: 16 }}>{STR.tabPending}</p>)}
    </Shell>
  );
}