import { Map as MapLibre, Popup, setWorkerUrl, type GeoJSONSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
// Load the worker as its own file so it resolves in dev and in the build.
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import type { Feature, FeatureCollection, Point } from "geojson";
import { useEffect, useRef, useState } from "react";
import type { FlightEvent, Track } from "../api/types";
import { Legend } from "../components/Legend";
import { StateBox } from "../components/StateBox";
import { formatPoint } from "../domain/format";
import { trackFitBounds, trackLine, trackPoints, windowBounds } from "../domain/trackGeo";
import runwayText from "../geo/wiii-runway.geojson?raw";
import { STR } from "../strings";

type TrackPoint = Track["points"][number];

interface Props {
  points: TrackPoint[];
  event: FlightEvent;
  scrubTs: string | null;
  onOpenRecord: (rawRef: string) => void;
}

const runway = JSON.parse(runwayText) as FeatureCollection;
setWorkerUrl(new URL(workerUrl, window.location.href).href);
const EMPTY: FeatureCollection<Point> = { type: "FeatureCollection", features: [] };

export function MapView({ points, event, scrubTs, onOpenRecord }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibre | null>(null);
  const pointsRef = useRef(points);
  const openRef = useRef(onOpenRecord);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  const fitted = useRef(false);
  pointsRef.current = points;
  openRef.current = onOpenRecord;

  // Create the map once.
  useEffect(() => {
    if (!box.current) return;
    let m: MapLibre;
    try {
      m = new MapLibre({
        container: box.current,
        center: [106.65, -6.13],
        zoom: 11,
        attributionControl: { compact: false },
        style: {
          version: 8,
          sources: {
            osm: {
              type: "raster",
              tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
              tileSize: 256,
              maxzoom: 19,
              attribution: "© OpenStreetMap contributors",
            },
          },
          layers: [{ id: "osm", type: "raster", source: "osm" }],
        },
      });
    } catch (e) {
      setFailed((e as Error).message);
      return;
    }
    map.current = m;
    const popup = new Popup({ closeButton: false, closeOnClick: false, offset: 10 });

    m.on("load", () => {
      m.addSource("runway", { type: "geojson", data: runway });
      m.addLayer({ id: "runway", type: "line", source: "runway", paint: { "line-color": "#7d8a9b", "line-width": 5 } });
      m.addSource("line", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addLayer({ id: "line", type: "line", source: "line", paint: { "line-color": "#0aa2c0", "line-width": 1.5, "line-opacity": 0.7 } });
      m.addSource("points", { type: "geojson", data: EMPTY });
      m.addLayer({
        id: "points",
        type: "circle",
        source: "points",
        paint: {
          "circle-color": ["get", "color"],
          "circle-radius": ["match", ["get", "style"], "flagged", 5, "eventWindow", 4, 3],
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1,
        },
      });
      m.addSource("scrub", { type: "geojson", data: EMPTY });
      m.addLayer({
        id: "scrub",
        type: "circle",
        source: "scrub",
        paint: { "circle-color": "#14213a", "circle-radius": 6, "circle-stroke-color": "#ffffff", "circle-stroke-width": 2 },
      });
      setReady(true);
    });

    m.on("mousemove", "points", (e) => {
      const f = e.features?.[0];
      if (!f) return;
      m.getCanvas().style.cursor = "pointer";
      const p = pointsRef.current[Number(f.properties?.index)];
      if (!p) return;
      const t = formatPoint(p);
      const el = document.createElement("div");
      el.className = "maptip";
      for (const [cls, text] of [["mono", t.time], ["mono muted", t.position], ["mono", t.altitude], ["chip", t.rawRef]]) {
        const line = document.createElement("div");
        line.className = cls;
        line.textContent = text;
        el.appendChild(line);
      }
      popup.setLngLat((f.geometry as Point).coordinates as [number, number]).setDOMContent(el).addTo(m);
    });
    m.on("mouseleave", "points", () => {
      m.getCanvas().style.cursor = "";
      popup.remove();
    });
    m.on("click", "points", (e) => {
      const ref = e.features?.[0]?.properties?.raw_ref;
      if (typeof ref === "string") openRef.current(ref);
    });

    return () => {
      popup.remove();
      m.remove();
      map.current = null;
      setReady(false);
    };
  }, []);

  // Draw the track and zoom to the flagged window when the event changes.
  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    (m.getSource("points") as GeoJSONSource).setData(trackPoints(points, event));
    (m.getSource("line") as GeoJSONSource).setData(trackLine(points));
    const first = !fitted.current;
    fitted.current = true;
    // First load shows the whole track and the runway; selecting another event zooms to its window.
    const b = first ? trackFitBounds(points, runway) : windowBounds(points, event);
    m.resize();
    if (b) m.fitBounds(b, { padding: 50, maxZoom: 14, duration: 0 });
  }, [ready, points, event]);

  // The marker follows scrubTs.
  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    const p = scrubTs ? points.find((x) => x.ts === scrubTs) : undefined;
    const data: FeatureCollection<Point> = p
      ? {
          type: "FeatureCollection",
          features: [{ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [p.lon, p.lat] } } as Feature<Point>],
        }
      : EMPTY;
    (m.getSource("scrub") as GeoJSONSource).setData(data);
  }, [ready, points, scrubTs]);

  if (failed) {
    return <StateBox kind="error" title={STR.mapFailed} text={failed} />;
  }
  return (
    <div className="viewport" aria-label={STR.mapArea}>
      <div ref={box} className="mapbox" />
      <Legend eventType={event.type} />
      <span className="maphint">{STR.mapHint}</span>
    </div>
  );
}
