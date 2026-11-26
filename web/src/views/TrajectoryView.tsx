import { useEffect, useState } from "react";
import type { Api } from "../api/client";
import type { EventDetail, FlightEvent } from "../api/types";
import { Charts } from "../components/Charts";
import { EventFeed } from "../components/EventFeed";
import { InvestigationPanel } from "../components/InvestigationPanel";
import { Scrubber } from "../components/Scrubber";
import { StateBox } from "../components/StateBox";
import { EVENT_LABEL } from "../domain/eventLabels";
import type { EventState } from "../domain/eventState";
import { formatWindow, formatWindowTitle } from "../domain/format";
import { getStore, useStore } from "../state/store";
import { useTrack } from "../state/useTrack";
import { STR } from "../strings";
import { MapView } from "./MapView";
import { navigate, useUrlParam } from "./nav";

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
  const view = useUrlParam("view") === "3d" ? "3d" : "map";
  const showCharts = useUrlParam("profile") !== "off";
  const { state: track, retry } = useTrack(api, selected?.icao24 ?? null);

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

  const scrubTs = useStore((s) => s.scrubTs);

  function select(id: string) {
    const e = events.find((x) => x.id === id);
    store.selectEvent(id, e ? e.icao24 : null);
  }

  function openRecord(rawRef: string) {
    store.setRawRef(rawRef);
    navigate({ tab: "records" });
  }

  function mainBox() {
    if (!selected) return <StateBox kind="empty" title={STR.selectEvent} />;
    if (track.status === "loading" || track.status === "idle") {
      return <StateBox kind="loading" title={STR.loadingTrack} />;
    }
    if (track.status === "error") {
      return (
        <StateBox kind="error" title={STR.trackError} text={track.message}>
          <button type="button" className="btn sm" onClick={retry}>{STR.retry}</button>
        </StateBox>
      );
    }
    if (track.track.points.length === 0) return <StateBox kind="empty" title={STR.noTrack} />;
    return <MapView points={track.track.points} event={selected} scrubTs={scrubTs} onOpenRecord={openRecord} />;
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
            <button className={view === "map" ? "on" : undefined} onClick={() => navigate({ view: "map" })}>
              {STR.viewMap}
            </button>
            <button disabled title={STR.notBuilt}>{STR.view3d}</button>
            <button
              className={showCharts ? "on" : undefined}
              aria-pressed={showCharts}
              onClick={() => navigate({ profile: showCharts ? "off" : null })}
            >
              {STR.viewProfile}
            </button>
          </div>
        </div>
        {mainBox()}
        {showCharts && (
          <div className="chartbox">
            {selected && track.status === "ready" && track.track.points.length > 0 ? (
              <Charts points={track.track.points} event={selected} scrubTs={scrubTs} />
            ) : null}
          </div>
        )}
        {selected && track.status === "ready" ? (
          <Scrubber points={track.track.points} event={selected} />
        ) : (
          <div className="scrub" aria-label={STR.scrubberLabel} />
        )}
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
