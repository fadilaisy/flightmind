import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, createApi, type Api } from "./api/client";
import { mockApi, type MockData } from "./api/mockClient";
import type { FlightEvent } from "./api/types";
import type { Recording } from "./api/uploadTypes";
import { StateBox } from "./components/StateBox";
import { getStore, useStore } from "./state/store";
import { STR } from "./strings";
import { EventsView } from "./views/EventsView";
import { KiroView } from "./views/KiroView";
import { CleanView } from "./views/CleanView";
import { ExportView } from "./views/ExportView";
import { LoadView, type StartUpload } from "./views/LoadView";
import { PreviewView } from "./views/PreviewView";
import { StreamsView } from "./views/StreamsView";
import { isProcessing, rawStreamId } from "./domain/upload";
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
  /** Scanned or being processed: the Load, Preview and Clean tabs work, the data tabs wait. */
  | { kind: "pending"; recording: Recording }
  | { kind: "error"; message: string };

/** Tabs that show the mock's sample dataset. The others show the recording itself. */
const SAMPLE_TABS = ["events", "trajectory", "records"];

export function App() {
  // VITE_API_BASE set: real or SCRUM-33 mock API. Otherwise the sample fixture.
  const api: Api = useMemo(
    () =>
      createApi(() => {
        let storage: Storage | undefined;
        try {
          storage = localStorage;
        } catch {
          storage = undefined; // blocked storage: the mock keeps its data in memory
        }
        return mockApi(mini as unknown as MockData, { storage });
      }),
    [],
  );
  const usingSample = !import.meta.env.VITE_API_BASE;

  const eventId = useStore((s) => s.eventId);
  const eventStates = useStore((s) => s.eventStates);
  const recordingId = useUrlParam("recording");
  const streamParam = useUrlParam("stream");
  const tabParam = useUrlParam("tab");

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
        .then((r) =>
          set(
            r.status === "ready"
              ? { kind: "ready", recording: r }
              : r.status === "scanned" || isProcessing(r.status)
                ? { kind: "pending", recording: r }
                : { kind: "load", follow: recordingId },
          ),
        )
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

  const refreshGate = () => setGateAttempt((n) => n + 1);

  function loadView(follow: string | null) {
    return (
      <LoadView
        key={`${loadMode?.key ?? 0}:${follow ?? ""}`}
        api={api}
        follow={follow}
        start={loadMode?.start ?? null}
        onReady={(id) => {
          setLoadMode(null);
          navigate({ recording: id, tab: "events" });
          refreshGate();
        }}
        onScanned={(r) => {
          setLoadMode(null);
          const raw = rawStreamId(r);
          navigate({ recording: r.id, tab: raw ? "preview" : "load", stream: raw });
          refreshGate();
        }}
        onReset={() => {
          setLoadMode((m) => ({ start: null, key: (m?.key ?? 0) + 1 }));
          navigate({ recording: null }, "replace");
        }}
      />
    );
  }

  function anotherFile() {
    setLoadMode((m) => ({ start: null, key: (m?.key ?? 0) + 1 }));
    navigate({ recording: null, stream: null, tab: "load" }, "replace");
  }

  function notice(text: string, label: string, tab: string) {
    return (
      <div className="wrap">
        <StateBox kind="empty" title={text}>
          <button type="button" className="fbtn" onClick={() => navigate({ tab })}>
            {label}
          </button>
        </StateBox>
      </div>
    );
  }

  /** The Load, Preview, Clean and Export tabs of a selected recording. Null when the tab is not one of them. */
  function recordingTab(tab: string, rec: Recording | null) {
    if (tab !== "load" && tab !== "preview" && tab !== "clean" && tab !== "export") return null;
    if (!rec) return tab === "load" ? loadView(null) : notice(STR.noStreamChosen, STR.goToLoad, "load");
    const streamId = streamParam ?? rawStreamId(rec) ?? rec.streams.find((s) => s.supported)?.id ?? null;
    if (tab === "load") {
      return (
        <StreamsView
          recording={rec}
          onUse={(id) => navigate({ tab: "preview", stream: id })}
          onAnotherFile={anotherFile}
        />
      );
    }
    if (tab === "preview") {
      if (!streamId) return notice(STR.noStreamChosen, STR.goToLoad, "load");
      return (
        <PreviewView
          key={`${rec.id}:${streamId}`}
          api={api}
          recording={rec}
          streamId={streamId}
          onContinue={() => navigate({ tab: "clean", stream: streamId })}
          onAnotherFile={anotherFile}
        />
      );
    }
    if (tab === "clean") {
      return (
        <CleanView
          key={rec.id}
          api={api}
          recording={rec}
          streamId={streamId}
          onReady={() => {
            navigate({ tab: "events" });
            refreshGate();
          }}
          onReviewEvents={() => navigate({ tab: "events" })}
        />
      );
    }
    return <ExportView api={api} recording={rec} />;
  }

  function body(tab: string) {
    // The Built with Kiro page reads only its generated JSON, so it needs neither a recording nor the API.
    if (tab === "kiro") return <KiroView />;
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
    if (gate.kind === "load") return loadView(gate.follow);
    const own = recordingTab(tab, gate.recording);
    if (own) return own;
    if (gate.kind === "pending") return notice(STR.applyFirst, STR.goToClean, "clean");
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
    gate.kind === "ready" ? (gate.recording ? gate.recording.filename : undefined) : gate.kind === "pending" ? gate.recording.filename : null;

  return (
    <Shell
      api={api}
      usingSample={usingSample && gate.kind === "ready" && SAMPLE_TABS.includes(tabParam ?? "trajectory")}
      hasRecording={recordingId !== null}
      activeTab={gate.kind === "load" && tabParam !== "kiro" ? "load" : null}
      recordingName={recordingName}
      selectedId={recordingId}
      onSelectRecording={chooseRecording}
      onPickFile={startUpload}
    >
      {body}
    </Shell>
  );
}

