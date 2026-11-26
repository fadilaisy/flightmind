import uPlot from "uplot";
import "uplot/dist/uPlot.min.css";
import { useEffect, useMemo, useRef, useState } from "react";
import type { FlightEvent, Track } from "../api/types";
import { derive } from "../domain/derive";
import { formatWindow, formatWindowTitle } from "../domain/format";
import { altitudeDatum } from "../domain/itemMeta";
import { AMBER_COLOR, windowColor } from "../domain/mapColors";
import { clockZ, signedInt, thousands } from "../domain/pointText";
import { STR } from "../strings";
import { snapIndex } from "./Scrubber";

type TrackPoint = Track["points"][number];

interface Props {
  points: TrackPoint[];
  event: FlightEvent;
  scrubTs: string | null;
  /** Called with the track time to jump to; the page moves the scrubber. */
  onGoTo: (ts: string) => void;
}

// Row geometry from Figma frame 5, in px inside the card.
const ALT_TOP = 11;
const ALT_H = 112;
const LANE_H = 49;
// Each lane has its own strip for the row label; the plot sits below it.
const LABEL_H = 16;
const PLOT_H = LANE_H - LABEL_H;
const SPEED_TOP = ALT_TOP + ALT_H;
const RATE_TOP = SPEED_TOP + LANE_H;
const AXIS_W = 56;
const PAD_R = 24;
const LINE = "#0aa3bf";

const sec = (iso: string) => Date.parse(iso) / 1000;

function axisLabel(v: number): string {
  if (v === 0) return "0";
  return v % 1000 === 0 ? `${v / 1000}k` : String(Math.round(v));
}

function finite(values: (number | null)[]): number[] {
  return values.filter((v): v is number => v !== null && Number.isFinite(v));
}

/** Altitude, ground speed and vertical rate over one shared time axis (seconds since epoch, UTC). */
export function Charts({ points, event, scrubTs, onGoTo }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const altEl = useRef<HTMLDivElement>(null);
  const speedEl = useRef<HTMLDivElement>(null);
  const rateEl = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(768);
  const [zoomed, setZoomed] = useState(false);

  const x = useMemo(() => points.map((p) => sec(p.ts)), [points]);
  const d = useMemo(() => derive(points), [points]);
  const ws = sec(event.start_ts);
  const we = sec(event.end_ts);
  const full: [number, number] = [x[0], x[x.length - 1] > x[0] ? x[x.length - 1] : x[0] + 1];
  const pad = Math.max(5, (we - ws) * 0.5);
  const [v0, v1]: [number, number] = zoomed ? [Math.max(full[0], ws - pad), Math.min(full[1], we + pad)] : full;
  const color = windowColor(event.type);

  const live = useRef({ scrubTs, v0, v1 });
  live.current = { scrubTs, v0, v1 };

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setWidth(Math.max(300, el.clientWidth)));
    ro.observe(el);
    setWidth(Math.max(300, el.clientWidth));
    return () => ro.disconnect();
  }, []);

  const plots = useRef<uPlot[]>([]);
  useEffect(() => {
    if (!altEl.current || !speedEl.current || !rateEl.current || x.length === 0) return;
    const altVals = points.map((p) => p.alt_ft ?? null);
    const inWin = x.map((t) => t >= ws && t <= we);
    const altWin = altVals.map((v, i) => (inWin[i] ? v : null));
    const altMax = Math.max(1000, ...finite(altVals));
    const altTop = Math.ceil(altMax / 1000) * 1000;
    const speedMax = Math.max(50, ...finite(d.speedKt)) * 1.15;
    const rateAbs = Math.max(500, ...finite(d.verticalRateFpm).map(Math.abs)) * 1.2;

    const common = (height: number, showAxis: boolean): uPlot.Options => ({
      width,
      height,
      legend: { show: false },
      cursor: { show: false },
      select: { show: false, left: 0, top: 0, width: 0, height: 0 },
      padding: [showAxis ? 18 : 4, PAD_R, showAxis ? 8 : 4, showAxis ? 0 : AXIS_W],
      scales: { x: { time: false, range: () => [live.current.v0, live.current.v1] } },
      series: [],
    });
    const band = (fill: string) => (self: uPlot): void => {
        const a = self.valToPos(ws, "x", true);
        const b = self.valToPos(we, "x", true);
        const { left, width: w } = self.bbox;
        const l = Math.max(left, Math.min(a, b));
        const r = Math.min(left + w, Math.max(a, b));
        if (r <= l) return;
        self.ctx.save();
        self.ctx.fillStyle = fill;
        self.ctx.fillRect(l, 0, r - l, self.height * devicePixelRatio);
        self.ctx.restore();
    };

    const alt = new uPlot(
      {
        ...common(ALT_H, true),
        scales: {
          x: { time: false, range: () => [live.current.v0, live.current.v1] },
          y: { range: () => [0, altTop] },
        },
        axes: [
          { show: false },
          {
            size: AXIS_W,
            space: 34,
            font: "12px Inter, sans-serif",
            stroke: "#525252",
            grid: { stroke: "#edf2f7", width: 1 },
            ticks: { show: false },
            border: { show: false },
            gap: 8,
            incrs: [1000, 2000, 3000, 5000, 10000],
            values: (_u, splits) => splits.map(axisLabel),
          },
        ],
        series: [
          {},
          { stroke: LINE, width: 1.5, spanGaps: false, points: { show: false } },
          { stroke: color, width: 2, spanGaps: false, points: { show: false } },
        ],
        hooks: {
          drawClear: [band("#fdf6e6")],
          draw: [
            (self) => {
              const ts = live.current.scrubTs;
              if (!ts) return;
              const i = snapIndex(points, ts);
              const v = altVals[i];
              if (v === null || v === undefined) return;
              const px = self.valToPos(sec(points[i].ts), "x", true);
              const py = self.valToPos(v, "y", true);
              const { left, width: w } = self.bbox;
              if (px < left || px > left + w) return;
              self.ctx.save();
              self.ctx.fillStyle = "#14213b";
              self.ctx.strokeStyle = "#ffffff";
              self.ctx.lineWidth = 1.5 * devicePixelRatio;
              self.ctx.beginPath();
              self.ctx.arc(px, py, 4 * devicePixelRatio, 0, Math.PI * 2);
              self.ctx.fill();
              self.ctx.stroke();
              self.ctx.restore();
            },
          ],
        },
      },
      [x, altVals, altWin] as uPlot.AlignedData,
      altEl.current,
    );

    const speed = new uPlot(
      {
        ...common(PLOT_H, false),
        scales: { x: { time: false, range: () => [live.current.v0, live.current.v1] }, y: { range: () => [0, speedMax] } },
        axes: [{ show: false }, { show: false }],
        series: [{}, { stroke: LINE, width: 1.5, spanGaps: false, points: { show: false } }],
        hooks: { drawClear: [band("#fcf2db")] },
      },
      [x, d.speedKt] as uPlot.AlignedData,
      speedEl.current,
    );

    const rate = new uPlot(
      {
        ...common(PLOT_H, false),
        scales: { x: { time: false, range: () => [live.current.v0, live.current.v1] }, y: { range: () => [-rateAbs, rateAbs] } },
        axes: [{ show: false }, { show: false }],
        series: [{}, { stroke: LINE, width: 1.5, spanGaps: false, points: { show: false } }],
        hooks: {
          drawClear: [band("#fcf2db")],
          draw: [
            (self) => {
              // Zero line and its label.
              const y = self.valToPos(0, "y", true);
              const { left, width: w } = self.bbox;
              self.ctx.save();
              self.ctx.strokeStyle = "#edf2f7";
              self.ctx.lineWidth = devicePixelRatio;
              self.ctx.beginPath();
              self.ctx.moveTo(left, y);
              self.ctx.lineTo(left + w, y);
              self.ctx.stroke();
              self.ctx.fillStyle = "#8a99ad";
              self.ctx.font = `${10 * devicePixelRatio}px Inter, sans-serif`;
              self.ctx.textBaseline = "middle";
              self.ctx.fillText("0", 40 * devicePixelRatio, y);
              self.ctx.restore();
            },
          ],
        },
      },
      [x, d.verticalRateFpm] as uPlot.AlignedData,
      rateEl.current,
    );

    plots.current = [alt, speed, rate];
    return () => {
      plots.current = [];
      alt.destroy();
      speed.destroy();
      rate.destroy();
    };
  }, [x, points, d, event, width, v0, v1, color, ws, we]);

  useEffect(() => {
    plots.current.forEach((u) => u.redraw(false));
  }, [scrubTs]);

  const plotW = width - AXIS_W - PAD_R;
  const xAt = (t: number) => AXIS_W + ((t - v0) / (v1 - v0)) * plotW;
  const idx = snapIndex(points, scrubTs);
  const cursorX = scrubTs ? xAt(sec(points[idx].ts)) : null;
  const cursorShown = cursorX !== null && cursorX >= AXIS_W && cursorX <= AXIS_W + plotW;
  const speedNow = d.speedKt[idx];
  const rateNow = d.verticalRateFpm[idx];
  // Keep the label clear of the two buttons at the top right.
  const flagLeft = Math.max(210, Math.min(xAt(Math.max(ws, v0)) - 4, width - 15 - 300 - 215));

  return (
    <div className="chartbox" aria-label={STR.chartsLabel}>
      <div className="chartnav">
        <button type="button" className="go" onClick={() => onGoTo(event.start_ts)}>
          {STR.goTo} {clockZ(event.start_ts)}
        </button>
        <button type="button" className="zoom" aria-pressed={zoomed} onClick={() => setZoomed((z) => !z)}>
          {zoomed ? STR.showFullTrack : STR.zoomToWindow}
        </button>
      </div>
      <div className="chartclip" ref={host}>
        <div className="chartrows">
          <div className="chartrow" style={{ top: ALT_TOP, height: ALT_H }} ref={altEl} />
          <div className="chartrow" style={{ top: SPEED_TOP + LABEL_H, height: PLOT_H }} ref={speedEl} />
          <div className="chartrow" style={{ top: RATE_TOP + LABEL_H, height: PLOT_H }} ref={rateEl} />
          <span className="charttitle">
            {STR.chartAltitudeLabel} ({altitudeDatum()}), ft
          </span>
          <span className="chartflag" title={formatWindowTitle(event.start_ts, event.end_ts)} style={{ left: flagLeft, color: color === AMBER_COLOR ? AMBER_COLOR : color }}>
            {STR.flaggedWindowCap} {formatWindow(event.start_ts, event.end_ts)}
          </span>
          <span className="laneLabel" style={{ top: SPEED_TOP + 1 }}>{STR.chartSpeedLabel}</span>
          <span className="laneLabel" style={{ top: RATE_TOP + 1 }}>{STR.chartRateLabel}</span>
          {cursorShown && (
            <>
              <div className="chartcursor" style={{ left: cursorX }} />
              <span className="chartval" style={{ left: cursorX, top: SPEED_TOP + LABEL_H }}>
                {speedNow === null || speedNow === undefined ? "\u2014" : `${thousands(speedNow)} kt`}
              </span>
              <span className="chartval" style={{ left: cursorX, top: RATE_TOP + LABEL_H }}>
                {rateNow === null || rateNow === undefined ? "\u2014" : `${signedInt(rateNow)} ft/min`}
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
