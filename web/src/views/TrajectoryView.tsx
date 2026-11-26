import { useEffect, useState } from "react";
import type { Api } from "../api/client";
import type { EventDetail, FlightEvent } from "../api/types";
import { Charts } from "../components/Charts";
import { EventFeed } from "../components/EventFeed";
import { InvestigationPanel } from "../components/InvestigationPanel";
import { RawRecordViewer } from "../components/RawRecordViewer";
import { Scrubber } from "../components/Scrubber";
import { StateBox } from "../components/StateBox";
import { phrase } from "../domain/eventLabels";
import type { EventState } from "../domain/eventState";
import { formatWindowTitle } from "../domain/format";
import { getStore, useStore } from "../state/store";
import { useTrack } from "../state/useTrack";
import { STR } from "../strings";
import { MapView } from "./MapView";
import { ThreeDView } from "./ThreeDView";
import { navigate, useUrlParam } from "./nav";

/** "8A0213 · go-around flag at WIII · 08:00–08:01Z", all from the event and its track. */
export function headerLine(event: EventDetail, points: { ts: string }[]): string {
  const parts = [event.icao24.toUpperCase(), event.airport ? `${phrase(event.type)} at ${event.airport}` : phrase(event.type)];
  if (points.length > 0) {
    const hm = (iso: string) => iso.slice(11, 16);
    parts.push(`${hm(points[0].ts)}–${hm(points[points.length - 1].ts)}Z`);
  }
  return parts.join(" · ");
}

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
  const [cited, setCited] = useState<string | null>(null);

  function select(id: string) {
    const e = events.find((x) => x.id === id);
    store.selectEvent(id, e ? e.icao24 : null);
  }

  /** A citation chip opens the cited-record dialog over the view; the map opens the Records tab. */
  function openCited(rawRef: string) {
    store.setRawRef(rawRef);
    setCited(rawRef);
  }

  /** Opens the Records tab at the first record the event cites. */
  function showRawPoints() {
    if (selected?.raw_refs[0]) store.setRawRef(selected.raw_refs[0]);
    navigate({ tab: "records" });
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
    if (view === "3d") {
      return <ThreeDView points={track.track.points} event={selected} scrubTs={scrubTs} onOpenRecord={openRecord} />;
    }
    return <MapView points={track.track.points} event={selected} scrubTs={scrubTs} onOpenRecord={openRecord} />;
  }

  return (
    <div className="three">
      <EventFeed events={events} states={states} selectedId={eventId} onSelect={select} />
      <div className="center">
        {error && <p role="alert">{error}</p>}
        <div className="trackhead">
          <h2>{selected ? (selected.callsign ?? selected.icao24.toUpperCase()) : STR.eventsTitle}</h2>
          {selected && (
            <span className="sub" title={formatWindowTitle(selected.start_ts, selected.end_ts)}>
              {headerLine(selected, track.status === "ready" ? track.track.points : [])}
            </span>
          )}
          <div className="spacer" />
          <div className="seg" role="group" aria-label={STR.threeArea}>
            <button className={view === "map" ? "on" : undefined} aria-pressed={view === "map"} onClick={() => navigate({ view: "map" })}>
              {STR.viewMap}
            </button>
            <button className={view === "3d" ? "on" : undefined} aria-pressed={view === "3d"} onClick={() => navigate({ view: "3d" })}>
              {STR.view3d}
            </button>
            <button
              className={showCharts ? "profile on" : "profile"}
              aria-pressed={showCharts}
              onClick={() => navigate({ profile: showCharts ? "off" : null })}
            >
              {STR.viewProfile}
            </button>
          </div>
          <button type="button" className="fbtn" disabled={!selected} title={STR.showRawPointsTitle} onClick={showRawPoints}>
            {STR.showRawPoints}
          </button>
        </div>        {mainBox()}
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
            onOpenRecord={openCited}
            onOpenEvent={select}
          />
        ) : (
          <p className="muted block">{STR.selectEvent}</p>
        )}
      </aside>
      {cited && (
        <RawRecordViewer
          api={api}
          rawRef={cited}
          event={selected}
          onClose={() => setCited(null)}
          onOpenInRecords={(r) => {
            store.setRawRef(r);
            setCited(null);
            navigate({ tab: "records" });
          }}
        />
      )}
    </div>
  );
}


