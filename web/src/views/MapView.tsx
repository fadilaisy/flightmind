import { Map as MapLibre, Popup, ScaleControl, setWorkerUrl, type GeoJSONSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
// Load the worker as its own file so it resolves in dev and in the build.
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import type { Feature, FeatureCollection, Point } from "geojson";
import { useEffect, useMemo, useRef, useState } from "react";
import type { FlightEvent, Track } from "../api/types";
import { CHIP_MARK } from "../components/CitationChip";
import { Legend } from "../components/Legend";
import { StateBox } from "../components/StateBox";
import { derive } from "../domain/derive";
import { KEPT_COLOR, SCRUB_RING, windowColor } from "../domain/mapColors";
import { clockZ, pointLine } from "../domain/pointText";
import { trackFitBounds, trackLine, trackPoints, windowBounds, windowLine } from "../domain/trackGeo";
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
// The first load shows the whole track; later events zoom to their flagged window. Module scope, because the map remounts while a track loads.
let fittedOnce = false;
setWorkerUrl(new URL(workerUrl, window.location.href).href);
const EMPTY: FeatureCollection<Point> = { type: "FeatureCollection", features: [] };

function NorthArrow() {
  return (
    <div className="north" aria-label={STR.northArrow}>
      <svg width="16" height="20" viewBox="0 0 16 20" aria-hidden="true">
        <path d="M8 0 L15 19 L8 14.5 L1 19 Z" fill="#03045e" />
      </svg>
      N
    </div>
  );
}

export function MapView({ points, event, scrubTs, onOpenRecord }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibre | null>(null);
  const pointsRef = useRef(points);
  const ratesRef = useRef<(number | null)[]>([]);
  const openRef = useRef(onOpenRecord);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  const rates = useMemo(() => derive(points).verticalRateFpm, [points]);
  pointsRef.current = points;
  ratesRef.current = rates;
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
        // The caption in the card carries the basemap credit, as in Figma.
        attributionControl: false,
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
          // Muted grey basemap, so the track is what stands out.
          layers: [
            {
              id: "osm",
              type: "raster",
              source: "osm",
              paint: { "raster-saturation": -1, "raster-contrast": -0.35, "raster-brightness-min": 0.6, "raster-brightness-max": 1 },
            },
          ],
        },
      });
    } catch (e) {
      setFailed((e as Error).message);
      return;
    }
    map.current = m;
    m.addControl(new ScaleControl({ maxWidth: 120, unit: "metric" }), "bottom-right");
    const popup = new Popup({ closeButton: false, closeOnClick: false, anchor: "top-left", offset: 12, className: "figtip", maxWidth: "none" });

    m.on("load", () => {
      m.addSource("runway", { type: "geojson", data: runway });
      m.addLayer({ id: "runway", type: "line", source: "runway", paint: { "line-color": "#8b94a3", "line-width": 5 } });
      m.addSource("line", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addSource("window", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addLayer({
        id: "halo",
        type: "line",
        source: "window",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": "#f2b13c", "line-width": 16, "line-opacity": 0.28, "line-blur": 4 },
      });
      m.addLayer({
        id: "line",
        type: "line",
        source: "line",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": KEPT_COLOR, "line-width": 2.5 },
      });
      m.addLayer({
        id: "windowline",
        type: "line",
        source: "window",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": "#f2b13c", "line-width": 3.5 },
      });
      m.addSource("points", { type: "geojson", data: EMPTY });
      m.addLayer({
        id: "points",
        type: "circle",
        source: "points",
        paint: {
          "circle-color": "#ffffff",
          "circle-radius": ["match", ["get", "style"], "flagged", 4.5, "eventWindow", 4, 3.5],
          "circle-stroke-color": KEPT_COLOR,
          "circle-stroke-width": 2,
        },
      });
      m.addSource("scrub", { type: "geojson", data: EMPTY });
      m.addLayer({
        id: "scrub",
        type: "circle",
        source: "scrub",
        paint: { "circle-color": "#ffffff", "circle-radius": 5, "circle-stroke-color": SCRUB_RING, "circle-stroke-width": 4 },
      });
      setReady(true);
    });

    m.on("mousemove", "points", (e) => {
      const f = e.features?.[0];
      if (!f) return;
      m.getCanvas().style.cursor = "pointer";
      const i = Number(f.properties?.index);
      const p = pointsRef.current[i];
      if (!p) return;
      const el = document.createElement("div");
      el.className = "maptip";
      const time = document.createElement("div");
      time.className = "t";
      time.textContent = clockZ(p.ts);
      const line = document.createElement("div");
      line.className = "p";
      line.textContent = pointLine(p, ratesRef.current[i]);
      const chip = document.createElement("div");
      chip.className = "chip static";
      chip.textContent = `${CHIP_MARK} rec ${p.raw_ref}`;
      el.append(time, line, chip);
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
    (m.getSource("window") as GeoJSONSource).setData(windowLine(points, event));
    const wc = windowColor(event.type);
    m.setPaintProperty("halo", "line-color", wc);
    m.setPaintProperty("windowline", "line-color", wc);
    m.setPaintProperty("points", "circle-stroke-color", ["match", ["get", "style"], "kept", KEPT_COLOR, wc]);
    const first = !fittedOnce;
    fittedOnce = true;
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
      <span className="maplabel l">{STR.mapCaption}</span>
      <span className="maplabel r">{STR.mapHintFigma}</span>
      <NorthArrow />
      <Legend eventType={event.type} />
    </div>
  );
}
