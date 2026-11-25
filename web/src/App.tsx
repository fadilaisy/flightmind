import { useEffect, useMemo, useState } from "react";
import { createApi, type Api } from "./api/client";
import { mockApi, type MockData } from "./api/mockClient";
import type { EventDetail, FlightEvent } from "./api/types";
import { EVENT_LABEL } from "./domain/eventLabels";
import { EventFeed } from "./components/EventFeed";
import { InvestigationPanel } from "./components/InvestigationPanel";
import { RawRecordViewer } from "./components/RawRecordViewer";
import { loadState, saveState, type EventState } from "./domain/eventState";
import { Shell } from "./views/Shell";
import { STR } from "./strings";
import mini from "../tests/fixtures/mini.json";

export function App() {
  // VITE_API_BASE set: real or SCRUM-33 mock API. Otherwise the sample fixture.
  const api: Api = useMemo(
    () => createApi(() => mockApi(mini as unknown as MockData)),
    [],
  );
  const usingSample = !import.meta.env.VITE_API_BASE;

  const [events, setEvents] = useState<FlightEvent[]>([]);
  const [states, setStates] = useState<Record<string, EventState>>({});
  const [selected, setSelected] = useState<EventDetail | null>(null);
  const [rawRef, setRawRef] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .events()
      .then((list) => {
        setEvents(list);
        setStates(Object.fromEntries(list.map((e) => [e.id, loadState(localStorage, e.id)])));
      })
      .catch((e: Error) => setError(e.message));
  }, [api]);

  function select(id: string) {
    setError(null);
    api.event(id).then(setSelected).catch((e: Error) => setError(e.message));
  }

  function setState(id: string, s: EventState) {
    saveState(localStorage, id, s);
    setStates((prev) => ({ ...prev, [id]: s }));
  }

  const trajectory = (
    <div className="three">
      <EventFeed events={events} states={states} selectedId={selected?.id ?? null} onSelect={select} />
      <div className="center">
        {error && <p role="alert">{error}</p>}
        <div className="titlebar">
          <h2>{selected ? (selected.callsign ?? selected.icao24) : STR.eventsTitle}</h2>
          {selected && (
            <span className="mono muted">
              {selected.icao24} · {EVENT_LABEL[selected.type]} · {selected.start_ts.slice(11, 19)}Z
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
        {rawRef && <RawRecordViewer api={api} rawRef={rawRef} onClose={() => setRawRef(null)} />}
      </div>
      <aside className="side r" aria-label="Investigation">
        <div className="slot" style={{ height: 318, flex: "none" }} aria-label="Compression card area" />
        {selected ? (
          <InvestigationPanel
            api={api}
            event={selected}
            state={states[selected.id] ?? "to_review"}
            onSetState={setState}
            onOpenRecord={setRawRef}
            onOpenEvent={select}
          />
        ) : (
          <p className="muted">{STR.selectEvent}</p>
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