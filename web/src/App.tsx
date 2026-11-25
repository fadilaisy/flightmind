import { useCallback, useEffect, useMemo, useState } from "react";
import { createApi, type Api } from "./api/client";
import { mockApi, type MockData } from "./api/mockClient";
import type { FlightEvent } from "./api/types";
import { StateBox } from "./components/StateBox";
import { getStore, useStore } from "./state/store";
import { STR } from "./strings";
import { EventsView } from "./views/EventsView";
import { Shell } from "./views/Shell";
import { TrajectoryView } from "./views/TrajectoryView";
import mini from "../tests/fixtures/mini.json";

export function App() {
  // VITE_API_BASE set: real or SCRUM-33 mock API. Otherwise the sample fixture.
  const api: Api = useMemo(
    () => createApi(() => mockApi(mini as unknown as MockData)),
    [],
  );
  const usingSample = !import.meta.env.VITE_API_BASE;

  const eventId = useStore((s) => s.eventId);
  const eventStates = useStore((s) => s.eventStates);

  const [events, setEvents] = useState<FlightEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    setEvents(null);
    api
      .events()
      .then((list) => {
        setEvents(list);
        // Open the first event on load, unless one is already selected.
        if (list.length > 0 && getStore().getState().eventId === null) {
          getStore().selectEvent(list[0].id, list[0].icao24);
        }
      })
      .catch((e: Error) => setError(e.message));
  }, [api]);

  useEffect(load, [load]);

  function body(tab: string) {
    if (error) {
      return (
        <div className="wrap">
          <StateBox kind="error" title={STR.apiUnreachable} text={error}>
            <button type="button" className="btn sm" onClick={load}>{STR.retry}</button>
          </StateBox>
        </div>
      );
    }
    if (events === null) {
      return (
        <div className="wrap">
          <StateBox kind="loading" title={STR.loadingEvents} />
        </div>
      );
    }
    if (tab === "events") return <EventsView events={events} states={eventStates} />;
    if (tab === "trajectory") {
      return <TrajectoryView api={api} events={events} eventId={eventId} states={eventStates} />;
    }
    return <p style={{ padding: 16 }}>{STR.tabPending}</p>;
  }

  return (
    <Shell api={api} usingSample={usingSample}>
      {body}
    </Shell>
  );
}