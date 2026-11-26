import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, createApi, type Api } from "./api/client";
import { mockApi, type MockData } from "./api/mockClient";
import type { FlightEvent } from "./api/types";
import type { Recording } from "./api/uploadTypes";
import { StateBox } from "./components/StateBox";
import { getStore, useStore } from "./state/store";
import { STR } from "./strings";
import { EventsView } from "./views/EventsView";
import { LoadView, type StartUpload } from "./views/LoadView";
import { RecordsView } from "./views/RecordsView";
import { Shell } from "./views/Shell";
import { TrajectoryView } from "./views/TrajectoryView";
import { navigate, useUrlParam } from "./views/nav";
import mini from "../tests/fixtures/mini.json";

/** What the app shows before the recording's data: a check, the Load screen, or the data itself. */
type Gate =
  | { kind: "checking" }
  | { kind: "load"; follow: string | null }
  | { kind: "ready"; recording: Recording | null }
  | { kind: "error"; message: string };

export function App() {
  // VITE_API_BASE set: real or SCRUM-33 mock API. Otherwise the sample fixture.
  const api: Api = useMemo(
    () => createApi(() => mockApi(mini as unknown as MockData, { storage: localStorage })),
    [],
  );
  const usingSample = !import.meta.env.VITE_API_BASE;

  const eventId = useStore((s) => s.eventId);
  const eventStates = useStore((s) => s.eventStates);
  const recordingId = useUrlParam("recording");

  // The analyst asked to load a file (header panel or "Try another file"), so the Load screen stays up.
  const [loadMode, setLoadMode] = useState<{ start: StartUpload | null; key: number } | null>(null);
  const [gate, setGate] = useState<Gate>({ kind: "checking" });
  const [gateAttempt, setGateAttempt] = useState(0);

  useEffect(() => {
    if (loadMode) {
      setGate({ kind: "load", follow: null });
      return;
    }
    let current = true;
    const set = (g: Gate) => current && setGate(g);
    setGate({ kind: "checking" });
    if (recordingId) {
      api
        .getRecording(recordingId)
        .then((r) => set(r.status === "ready" ? { kind: "ready", recording: r } : { kind: "load", follow: recordingId }))
        .catch(() => set({ kind: "load", follow: recordingId }));
    } else {
      api
        .listRecordings()
        .then((list) => {
          const ready = list.find((r) => r.status === "ready");
          if (ready) navigate({ recording: ready.id }, "replace");
          else set({ kind: "load", follow: null });
        })
        .catch((e: Error) => {
          // A server without the recordings API still serves one fixed recording.
          if (e instanceof ApiError && (e.status === 404 || e.status === 405)) set({ kind: "ready", recording: null });
          else set({ kind: "error", message: e.message });
        });
    }
    return () => {
      current = false;
    };
  }, [api, recordingId, loadMode, gateAttempt]);

  const [events, setEvents] = useState<FlightEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const shownRecording = useRef<string | null>(null);
  const ready = gate.kind === "ready";

  const load = useCallback(() => {
    if (!ready) return;
    setError(null);
    setEvents(null);
    if (shownRecording.current !== recordingId) {
      shownRecording.current = recordingId;
      getStore().selectEvent(null, null);
    }
    (recordingId ? api.events(recordingId) : api.events())
      .then((list) => {
        setEvents(list);
        // Open the first event on load, unless one is already selected.
        if (list.length > 0 && getStore().getState().eventId === null) {
          getStore().selectEvent(list[0].id, list[0].icao24);
        }
      })
      .catch((e: Error) => setError(e.message));
  }, [api, ready, recordingId]);

  useEffect(load, [load]);

  function chooseRecording(id: string) {
    setLoadMode(null);
    navigate({ recording: id });
  }

  function startUpload(file: File) {
    setLoadMode((m) => ({ start: { file }, key: (m?.key ?? 0) + 1 }));
    navigate({ recording: null }, "replace");
  }

  function body(tab: string) {
    if (gate.kind === "checking") {
      return (
        <div className="wrap">
          <StateBox kind="loading" title={STR.loadingRecording} />
        </div>
      );
    }
    if (gate.kind === "error") {
      return (
        <div className="wrap">
          <StateBox kind="error" title={STR.apiUnreachable} text={gate.message}>
            <button type="button" className="btn sm" onClick={() => setGateAttempt((n) => n + 1)}>{STR.retry}</button>
          </StateBox>
        </div>
      );
    }
    if (gate.kind === "load") {
      return (
        <LoadView
          key={`${loadMode?.key ?? 0}:${gate.follow ?? ""}`}
          api={api}
          follow={gate.follow}
          start={loadMode?.start ?? null}
          onReady={(id) => {
            setLoadMode(null);
            navigate({ recording: id, tab: "events" });
          }}
          onReset={() => {
            setLoadMode((m) => ({ start: null, key: (m?.key ?? 0) + 1 }));
            navigate({ recording: null }, "replace");
          }}
        />
      );
    }
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
    return <RecordsView api={api} events={events} eventId={eventId} />;
  }

  const recordingName =
    gate.kind === "ready" ? (gate.recording ? gate.recording.filename : undefined) : null;

  return (
    <Shell
      api={api}
      usingSample={usingSample}
      recordingName={recordingName}
      selectedId={recordingId}
      onSelectRecording={chooseRecording}
      onPickFile={startUpload}
    >
      {body}
    </Shell>
  );
}
