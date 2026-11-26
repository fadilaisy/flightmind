import { useEffect, useState } from "react";
import type { Api } from "../api/client";
import type { EventDetail, FlightEvent } from "../api/types";
import { CompressionBadge } from "../components/CompressionBadge";
import { Charts } from "../components/Charts";
import { EventFeed } from "../components/EventFeed";
import { EventPanel } from "../components/EventPanel";
import { PointCard } from "../components/PointCard";
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
  const [detailAttempt, setDetailAttempt] = useState(0);
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
  }, [api, eventId, detailAttempt]);

  const firstRef = selected?.raw_refs[0] ?? events[0]?.raw_refs[0] ?? null;
  const recordingId = firstRef ? firstRef.split(":")[0] : null;
  const scrubTs = useStore((s) => s.scrubTs);
  const [cited, setCited] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);

  function select(id: string) {
    const e = events.find((x) => x.id === id);
    store.selectEvent(id, e ? e.icao24 : null);
    setPanelOpen(true);
  }

  /** A citation chip opens the cited-record dialog over the view; the map opens the Records tab. */
  function openCited(rawRef: string) {
    store.setRawRef(rawRef);
    setCited(rawRef);
  }

  /** Moves the scrubber to the first point at or after ts (or the last point). */
  function goTo(points: { ts: string }[], ts: string) {
    const t = Date.parse(ts);
    const p = points.find((x) => Date.parse(x.ts) >= t) ?? points[points.length - 1];
    if (p) store.setScrubTs(p.ts);
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
    if (!selected && eventId && !error) return <StateBox kind="loading" title={STR.loadingEventDetail} />;
    if (!selected) return <StateBox kind="empty" title={STR.selectEventTrack} />;
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
        {error && (
          <StateBox kind="error" title={STR.eventError} text={error}>
            <button type="button" className="btn sm" onClick={() => setDetailAttempt((n) => n + 1)}>{STR.retry}</button>
          </StateBox>
        )}
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
        {showCharts &&
          (selected && track.status === "ready" && track.track.points.length > 0 ? (
            <Charts points={track.track.points} event={selected} scrubTs={scrubTs} onGoTo={(ts) => goTo(track.track.points, ts)} />
          ) : (
            <div className="chartbox" aria-label={STR.chartsLabel}>
              <p className="listmsg">{!selected ? STR.chartsEmpty : track.status === "error" ? STR.trackError : STR.loadingCharts}</p>
            </div>
          ))}
        {selected && track.status === "ready" ? (
          <Scrubber points={track.track.points} event={selected} events={events.filter((e) => e.icao24 === selected.icao24)} />
        ) : (
          <div className="scrub" aria-label={STR.scrubberLabel} />
        )}
      </div>
      <aside className="side r" aria-label="Investigation">
        <CompressionBadge api={api} recordingId={recordingId} />
        {selected && track.status === "ready" && track.track.points.length > 0 ? (
          <PointCard points={track.track.points} scrubTs={scrubTs} onOpenRecord={openCited} />
        ) : (
          <section className="rcard point" aria-label={STR.selectedPoint}>
            <div className="rhead">
              <span>{STR.selectedPoint}</span>
              <span className="mono">I021</span>
            </div>
            <p className="empty">{selected ? STR.loadingTrack : STR.selectEvent}</p>
          </section>
        )}
      </aside>
      {selected && panelOpen && (
        <EventPanel
          api={api}
          event={selected}
          state={states[selected.id] ?? "to_review"}
          points={track.status === "ready" ? track.track.points : null}
          onSetState={store.setEventState}
          onOpenRecord={openCited}
          onOpenEvent={select}
          onClose={() => setPanelOpen(false)}
        />
      )}
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


