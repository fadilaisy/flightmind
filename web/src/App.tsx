import { useEffect, useMemo, useState } from "react";
import { createApi, type Api } from "./api/client";
import { mockApi, type MockData } from "./api/mockClient";
import type { EventDetail, FlightEvent } from "./api/types";
import { EventFeed } from "./components/EventFeed";
import { InvestigationPanel } from "./components/InvestigationPanel";
import { RawRecordViewer } from "./components/RawRecordViewer";
import { loadState, saveState, type EventState } from "./domain/eventState";
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

  return (
    <main style={{ display: "grid", gridTemplateColumns: "360px 1fr", gap: 16, padding: 16 }}>
      <div>
        <h1 style={{ font: "600 20px/28px var(--font-text)", margin: "0 0 8px" }}>
          Events{usingSample ? " (sample data)" : ""}
        </h1>
        {error && <p role="alert">{error}</p>}
        <EventFeed
          events={events}
          states={states}
          selectedId={selected?.id ?? null}
          onSelect={select}
          onSetState={setState}
        />
      </div>
      <div style={{ display: "grid", gap: 16, alignContent: "start" }}>
        {selected ? (
          <InvestigationPanel api={api} event={selected} onOpenRecord={setRawRef} onOpenEvent={select} />
        ) : (
          <p>Select an event to open the investigation panel.</p>
        )}
        {rawRef && <RawRecordViewer api={api} rawRef={rawRef} onClose={() => setRawRef(null)} />}
      </div>
    </main>
  );
}
