import {
  BufferGeometry,
  CanvasTexture,
  Color,
  Float32BufferAttribute,
  GridHelper,
  Line,
  LineBasicMaterial,
  LineDashedMaterial,
  LineSegments,
  PerspectiveCamera,
  Points,
  PointsMaterial,
  Scene,
  Vector2,
  Vector3,
  WebGLRenderer,
} from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { LineMaterial } from "three/examples/jsm/lines/LineMaterial.js";
import { LineSegments2 } from "three/examples/jsm/lines/LineSegments2.js";
import type { FeatureCollection } from "geojson";
import { useEffect, useRef, useState } from "react";
import type { FlightEvent, Track } from "../api/types";
import { StateBox } from "../components/StateBox";
import { formatPoint } from "../domain/format";
import { buildTrack3D, disposeTrack3D, fitDistance, formatAltTick, frameTrack, LINE_FLAGGED, LINE_KEPT, type Track3D } from "../domain/track3d";
import { styleColor } from "../domain/pointStyle";
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
const RUNWAY_ENDS: [number, number][] = runway.features.flatMap((f) =>
  f.geometry.type === "LineString" ? (f.geometry.coordinates as [number, number][]) : [],
);

interface Label {
  el: HTMLDivElement;
  at: Vector3;
}

interface Scene3D {
  setScrub: (ts: string | null) => void;
  dispose: () => void;
}

function dotTexture(fill: string, ring: string | null): CanvasTexture {
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const g = c.getContext("2d")!;
  g.beginPath();
  g.arc(32, 32, ring ? 26 : 28, 0, Math.PI * 2);
  g.fillStyle = fill;
  g.fill();
  if (ring) {
    g.lineWidth = 9;
    g.strokeStyle = ring;
    g.stroke();
  }
  const tex = new CanvasTexture(c);
  return tex;
}

export function ThreeDView({ points, event, scrubTs, onOpenRecord }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const labelBox = useRef<HTMLDivElement>(null);
  const scene3d = useRef<Scene3D | null>(null);
  const scrubRef = useRef(scrubTs);
  const openRef = useRef(onOpenRecord);
  const pointsRef = useRef(points);
  const [failed, setFailed] = useState<string | null>(null);
  const [hover, setHover] = useState<{ index: number; x: number; y: number } | null>(null);
  const [factor, setFactor] = useState(1);
  const [altLabel, setAltLabel] = useState<{ x: number; y: number } | null>(null);
  scrubRef.current = scrubTs;
  openRef.current = onOpenRecord;
  pointsRef.current = points;

  useEffect(() => {
    const el = host.current;
    const labelsEl = labelBox.current;
    if (!el || !labelsEl) return;
    let renderer: WebGLRenderer;
    try {
      renderer = new WebGLRenderer({ antialias: true });
    } catch (e) {
      setFailed((e as Error).message);
      return;
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setClearColor(new Color("#ffffff"), 1);
    el.appendChild(renderer.domElement);
    renderer.domElement.style.display = "block";

    const t: Track3D = buildTrack3D(points, event, RUNWAY_ENDS);
    setFactor(t.exaggeration);
    const scene = new Scene();
    const FOV = 32;
    const camera = new PerspectiveCamera(FOV, 1, 10, t.half * 40);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.maxPolarAngle = Math.PI * 0.495;
    // Frame the track, its altitude axis and a nearby runway; refit only on the first real size.
    const frame = frameTrack(t, RUNWAY_ENDS.map(([lon, lat]) => t.toXZ(lon, lat)));
    let sized = false;
    function fitCamera(aspect: number) {
      camera.aspect = aspect;
      const dir = new Vector3(0.55, 0.42, 0.8).normalize();
      const c = new Vector3(...frame.center);
      let d = fitDistance(frame.radius, FOV, aspect);
      camera.far = Math.max(t.half * 40, d * 10);
      controls.target.copy(c);
      // Tighten with the real projection: every corner of the box inside 90 percent of the view.
      const corner = new Vector3();
      for (let pass = 0; pass < 5; pass++) {
        camera.position.copy(c).addScaledVector(dir, d);
        camera.lookAt(c);
        camera.updateProjectionMatrix();
        camera.updateMatrixWorld(true);
        let m = 0;
        for (const x of [frame.min[0], frame.max[0]])
          for (const y of [frame.min[1], frame.max[1]])
            for (const z of [frame.min[2], frame.max[2]]) {
              corner.set(x, y, z).project(camera);
              m = Math.max(m, Math.abs(corner.x), Math.abs(corner.y));
            }
        if (!(m > 0)) break;
        d *= m / 0.9;
      }
      camera.position.copy(c).addScaledVector(dir, d);
      camera.updateProjectionMatrix();
      controls.update();
    }
    fitCamera(1.6);

    const owned: { dispose(): void }[] = [];
    const own = <T extends { dispose(): void }>(o: T): T => {
      owned.push(o);
      return o;
    };

    // Ground grid.
    const divisions = Math.round((t.half * 2) / t.gridStep);
    const grid = new GridHelper(t.half * 2, divisions, "#90e0ef", "#bfeaf5");
    (grid.material as LineBasicMaterial).transparent = true;
    (grid.material as LineBasicMaterial).opacity = 0.9;
    own(grid.geometry);
    own(grid.material as LineBasicMaterial);
    scene.add(grid);

    // Runway on the grid.
    const rwyGeo = own(new BufferGeometry());
    const rwyPos: number[] = [];
    for (const f of runway.features) {
      if (f.geometry.type !== "LineString") continue;
      const c = f.geometry.coordinates;
      for (let i = 0; i + 1 < c.length; i++) {
        const [x1, z1] = t.toXZ(c[i][0], c[i][1]);
        const [x2, z2] = t.toXZ(c[i + 1][0], c[i + 1][1]);
        rwyPos.push(x1, 1, z1, x2, 1, z2);
      }
    }
    rwyGeo.setAttribute("position", new Float32BufferAttribute(rwyPos, 3));
    const rwyMat = own(new LineBasicMaterial({ color: "#9aa7b8" }));
    scene.add(new LineSegments(rwyGeo, rwyMat));

    // Altitude axis at the south-west corner, with ticks.
    const axisX = t.axisX;
    const axisZ = t.axisZ;
    const axisGeo = own(new BufferGeometry());
    const axisPos: number[] = [axisX, 0, axisZ, axisX, t.axisHeight, axisZ];
    const tickLen = t.half * 0.03;
    const ticks: number[] = [];
    for (let ft = 0; ft <= t.maxAltFt + 1; ft += t.tickStepFt) ticks.push(ft);
    const mPerFt = t.axisHeight / t.maxAltFt;
    for (const ft of ticks) axisPos.push(axisX, ft * mPerFt, axisZ, axisX - tickLen, ft * mPerFt, axisZ);
    axisGeo.setAttribute("position", new Float32BufferAttribute(axisPos, 3));
    scene.add(new LineSegments(axisGeo, own(new LineBasicMaterial({ color: "#525252" }))));

    // Drop lines, the line, its glow, points and the ground track.
    scene.add(new LineSegments(t.dropGeometry, own(new LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.45 }))));
    scene.add(
      new Line(
        t.groundGeometry,
        own(new LineDashedMaterial({ color: "#0077b6", dashSize: t.half * 0.02, gapSize: t.half * 0.016 })),
      ),
    );
    const ground = scene.children[scene.children.length - 1] as Line;
    ground.computeLineDistances();

    const glowMat = own(new LineMaterial({ color: LINE_FLAGGED, linewidth: 11, transparent: true, opacity: 0.22 }));
    const glow = new LineSegments2(t.glowGeometry, glowMat);
    const lineMat = own(new LineMaterial({ color: "#ffffff", vertexColors: true, linewidth: 2.5 }));
    const line = new LineSegments2(t.lineGeometry, lineMat);
    if (t.glowGeometry.attributes.instanceStart) scene.add(glow);
    if (t.lineGeometry.attributes.instanceStart) scene.add(line);

    const dot = own(dotTexture("#ffffff", null));
    const pointMat = own(
      new PointsMaterial({ size: 8, sizeAttenuation: false, vertexColors: true, map: dot, alphaTest: 0.5, transparent: true }),
    );
    scene.add(new Points(t.pointGeometry, pointMat));

    // Ring marker for scrubTs.
    const markerGeo = own(new BufferGeometry());
    markerGeo.setAttribute("position", new Float32BufferAttribute([0, 0, 0], 3));
    const ringTex = own(dotTexture("#ffffff", "#14213a"));
    const marker = new Points(
      markerGeo,
      own(new PointsMaterial({ size: 20, sizeAttenuation: false, map: ringTex, alphaTest: 0.4, transparent: true, depthTest: false })),
    );
    marker.visible = false;
    marker.renderOrder = 5;
    scene.add(marker);

    // HTML labels follow their 3D anchors.
    const labels: Label[] = [];
    const addLabel = (text: string, at: Vector3, cls: string) => {
      const d = document.createElement("div");
      d.className = `tdlabel ${cls}`;
      d.textContent = text;
      labelsEl.appendChild(d);
      labels.push({ el: d, at });
    };
    for (const ft of ticks) addLabel(formatAltTick(ft), new Vector3(axisX - tickLen * 1.6, ft * mPerFt, axisZ), "tick");
    addLabel(STR.threeAlt, new Vector3(axisX, t.axisHeight + t.half * 0.07, axisZ), "axis");
    addLabel(STR.threeLon, new Vector3(0, 0, t.half * 1.07), "axis");
    addLabel(STR.threeLat, new Vector3(t.half * 1.07, 0, 0), "axis");
    const rwy = runway.features[0];
    if (rwy && rwy.geometry.type === "LineString") {
      const c = rwy.geometry.coordinates;
      const [x1, z1] = t.toXZ(c[0][0], c[0][1]);
      const [x2, z2] = t.toXZ(c[c.length - 1][0], c[c.length - 1][1]);
      addLabel(`WIII ${STR.threeRunway} ${(rwy.properties?.name as string) ?? ""}`.trim(), new Vector3((x1 + x2) / 2, 0, (z1 + z2) / 2 + t.half * 0.06), "rwy");
    }
    const altAnchor = new Vector3(axisX, t.axisHeight, axisZ);

    const tmp = new Vector3();
    function placeLabels() {
      const w = el!.clientWidth;
      const h = el!.clientHeight;
      for (const l of labels) {
        tmp.copy(l.at).project(camera);
        l.el.style.transform = `translate(${((tmp.x + 1) / 2) * w}px, ${((1 - tmp.y) / 2) * h}px)`;
      }
      tmp.copy(altAnchor).project(camera);
      setAltLabel({ x: ((tmp.x + 1) / 2) * w, y: ((1 - tmp.y) / 2) * h });
    }

    let raf = 0;
    const size = new Vector2();
    function draw() {
      raf = 0;
      renderer.render(scene, camera);
      placeLabels();
    }
    function schedule() {
      if (!raf) raf = requestAnimationFrame(draw);
    }
    function resize() {
      const w = el!.clientWidth;
      const h = el!.clientHeight;
      if (w === 0 || h === 0) return;
      renderer.setSize(w, h, false);
      renderer.domElement.style.width = `${w}px`;
      renderer.domElement.style.height = `${h}px`;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      if (!sized) {
        sized = true;
        fitCamera(w / h);
      }
      size.set(w, h);
      lineMat.resolution.set(w, h);
      glowMat.resolution.set(w, h);
      schedule();
    }
    const ro = new ResizeObserver(resize);
    ro.observe(el);
    resize();
    controls.addEventListener("change", schedule);

    function setScrub(ts: string | null) {
      const i = ts ? pointsRef.current.findIndex((p) => p.ts === ts) : -1;
      if (i < 0 || !t.hasAlt[i]) {
        marker.visible = false;
      } else {
        marker.visible = true;
        const a = markerGeo.getAttribute("position");
        a.setXYZ(0, t.world[i * 3], t.world[i * 3 + 1], t.world[i * 3 + 2]);
        a.needsUpdate = true;
      }
      schedule();
    }
    setScrub(scrubRef.current);

    // Picking: nearest projected point within 9 px. Click without a drag cites it.
    function nearest(ev: PointerEvent): { index: number; x: number; y: number } | null {
      const rect = renderer.domElement.getBoundingClientRect();
      const mx = ev.clientX - rect.left;
      const my = ev.clientY - rect.top;
      let best = -1;
      let bestD = 81;
      for (let k = 0; k < t.pointIndex.length; k++) {
        const i = t.pointIndex[k];
        tmp.set(t.world[i * 3], t.world[i * 3 + 1], t.world[i * 3 + 2]).project(camera);
        if (tmp.z > 1) continue;
        const dx = ((tmp.x + 1) / 2) * rect.width - mx;
        const dy = ((1 - tmp.y) / 2) * rect.height - my;
        const d = dx * dx + dy * dy;
        if (d < bestD) {
          bestD = d;
          best = i;
        }
      }
      return best < 0 ? null : { index: best, x: mx, y: my };
    }
    let down: { x: number; y: number } | null = null;
    let dragging = false;
    let lastHover = -1;
    const onMove = (ev: PointerEvent) => {
      if (down && Math.hypot(ev.clientX - down.x, ev.clientY - down.y) > 4) dragging = true;
      if (dragging) {
        if (lastHover !== -1) {
          lastHover = -1;
          setHover(null);
        }
        return;
      }
      const hit = nearest(ev);
      renderer.domElement.style.cursor = hit ? "pointer" : "grab";
      const idx = hit ? hit.index : -1;
      if (idx !== lastHover || hit) {
        lastHover = idx;
        setHover(hit);
      }
    };
    const onDown = (ev: PointerEvent) => {
      down = { x: ev.clientX, y: ev.clientY };
      dragging = false;
    };
    const onUp = (ev: PointerEvent) => {
      if (down && !dragging) {
        const hit = nearest(ev);
        if (hit) openRef.current(pointsRef.current[hit.index].raw_ref);
      }
      down = null;
      dragging = false;
    };
    const onLeave = () => {
      lastHover = -1;
      setHover(null);
    };
    const dom = renderer.domElement;
    dom.addEventListener("pointermove", onMove);
    dom.addEventListener("pointerdown", onDown);
    dom.addEventListener("pointerup", onUp);
    dom.addEventListener("pointerleave", onLeave);

    scene3d.current = {
      setScrub,
      dispose() {
        if (raf) cancelAnimationFrame(raf);
        ro.disconnect();
        dom.removeEventListener("pointermove", onMove);
        dom.removeEventListener("pointerdown", onDown);
        dom.removeEventListener("pointerup", onUp);
        dom.removeEventListener("pointerleave", onLeave);
        controls.removeEventListener("change", schedule);
        controls.dispose();
        owned.forEach((o) => o.dispose());
        disposeTrack3D(t);
        renderer.dispose();
        renderer.forceContextLoss();
        dom.remove();
        labelsEl.replaceChildren();
      },
    };
    return () => {
      scene3d.current?.dispose();
      scene3d.current = null;
    };
  }, [points, event]);

  useEffect(() => {
    scene3d.current?.setScrub(scrubTs);
  }, [scrubTs]);

  if (failed) return <StateBox kind="error" title={STR.threeFailed} text={failed} />;

  const hp = hover ? points[hover.index] : null;
  const text = hp ? formatPoint(hp) : null;
  return (
    <div className="viewport tdview" aria-label={STR.threeArea}>
      <div ref={host} className="tdcanvas" />
      <div ref={labelBox} className="tdlabels" aria-hidden="true" />
      {altLabel && (
        <span className="tdfactor" style={{ left: altLabel.x + 44, top: altLabel.y - 20 }}>
          {STR.altitudeFactor}
          {factor}
        </span>
      )}
      <span className="maphint">{STR.threeHint}</span>
      <div className="legend tdlegend" aria-label={STR.legendLabel}>
        <span>
          <i style={{ background: LINE_KEPT }} />
          {STR.threeLegendKept}
        </span>
        <span>
          <i style={{ background: styleColor("flagged", event.type) }} />
          {STR.threeLegendWindow}
        </span>
        <span>
          <i className="dash" />
          {STR.threeLegendGround}
        </span>
      </div>
      {hover && text && (
        <div
          className="maptip tdtip"
          style={{ left: Math.min(hover.x + 14, (host.current?.clientWidth ?? 600) - 190), top: Math.max(hover.y - 90, 6) }}
        >
          <div className="mono">{text.time}</div>
          <div className="mono muted">{text.position}</div>
          <div className="mono">{text.altitude}</div>
          <div className="chip">{text.rawRef}</div>
        </div>
      )}
    </div>
  );
}
