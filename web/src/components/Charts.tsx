import uPlot from "uplot";
import "uplot/dist/uPlot.min.css";
import { useEffect, useMemo, useRef } from "react";
import type { FlightEvent, Track } from "../api/types";
import { derive } from "../domain/derive";
import { STR } from "../strings";

type TrackPoint = Track["points"][number];

interface Props {
  points: TrackPoint[];
  event: FlightEvent;
  scrubTs: string | null;
}

interface Panel {
  key: string;
  title: string;
  unit: string;
  color: string;
  values: (number | null)[];
}

const PANEL_H = 62;
const BAND = "rgba(242, 177, 60, 0.22)";

function utcClock(sec: number): string {
  return new Date(sec * 1000).toISOString().slice(11, 19);
}

/** Altitude, ground speed and vertical rate over one shared time axis (seconds since epoch, UTC). */
export function Charts({ points, event, scrubTs }: Props) {
  const rows = useRef<HTMLDivElement>(null);
  const plots = useRef<uPlot[]>([]);
  const live = useRef({ scrubTs, event });
  live.current = { scrubTs, event };

  const x = useMemo(() => points.map((p) => Date.parse(p.ts) / 1000), [points]);
  const panels = useMemo<Panel[]>(() => {
    const d = derive(points);
    return [
      { key: "alt", title: STR.chartAltitude, unit: "ft", color: "#0aa2c0", values: points.map((p) => p.alt_ft ?? null) },
      { key: "gs", title: STR.chartSpeed, unit: "kt", color: "#0077b6", values: d.speedKt },
      { key: "vr", title: STR.chartVerticalRate, unit: "ft/min", color: "#5b6b85", values: d.verticalRateFpm },
    ];
  }, [points]);

  useEffect(() => {
    const host = rows.current;
    if (!host || x.length === 0) return;
    const width = Math.max(200, host.clientWidth);
    const made = panels.map((panel, i) => {
      const last = i === panels.length - 1;
      const el = document.createElement("div");
      el.className = "chartrow";
      const title = document.createElement("div");
      title.className = "charttitle";
      title.textContent = `${panel.title} (${panel.unit})`;
      el.appendChild(title);
      host.appendChild(el);
      const u = new uPlot(
        {
          width,
          height: PANEL_H + (last ? 26 : 0),
          legend: { show: false },
          padding: [6, 18, 0, 0],
          cursor: { drag: { x: false, y: false }, sync: { key: "flightmind" } },
          scales: { x: { time: false, range: () => [x[0], x[x.length - 1] > x[0] ? x[x.length - 1] : x[0] + 1] } },
          axes: [
            {
              show: last,
              size: 26,
              space: 80,
              font: "11px JetBrains Mono, monospace",
              stroke: "#5b6b85",
              grid: { stroke: "#edf1f6", width: 1 },
              values: (_u, splits) => splits.map(utcClock),
            },
            {
              size: 56,
              space: 18,
              font: "11px JetBrains Mono, monospace",
              stroke: "#5b6b85",
              grid: { stroke: "#edf1f6", width: 1 },
              ticks: { show: false },
              gap: 4,
              values: (_u, splits) => splits.map((v) => Math.round(v).toLocaleString("en-US")),
            },
          ],
          series: [{}, { stroke: panel.color, width: 1.5, spanGaps: false, points: { show: false } }],
          hooks: {
            drawClear: [
              (self) => {
                const { start_ts, end_ts } = live.current.event;
                const a = self.valToPos(Date.parse(start_ts) / 1000, "x", true);
                const b = self.valToPos(Date.parse(end_ts) / 1000, "x", true);
                const { left, top, width: w, height } = self.bbox;
                const l = Math.max(left, Math.min(a, b));
                const r = Math.min(left + w, Math.max(a, b));
                if (r <= l) return;
                self.ctx.save();
                self.ctx.fillStyle = BAND;
                self.ctx.fillRect(l, top, r - l, height);
                if (i === 0) {
                  self.ctx.fillStyle = "#8a5600";
                  self.ctx.font = `${11 * devicePixelRatio}px Inter, sans-serif`;
                  self.ctx.textBaseline = "top";
                  self.ctx.fillText(
                    `${STR.flaggedWindowLower} ${start_ts.slice(11, 19)} to ${end_ts.slice(11, 19)} UTC`,
                    l + 4 * devicePixelRatio,
                    top + 2 * devicePixelRatio,
                  );
                }
                self.ctx.restore();
              },
            ],
            draw: [
              (self) => {
                const ts = live.current.scrubTs;
                if (!ts) return;
                const px = self.valToPos(Date.parse(ts) / 1000, "x", true);
                const { left, top, width: w, height } = self.bbox;
                if (px < left || px > left + w) return;
                self.ctx.save();
                self.ctx.strokeStyle = "#14213a";
                self.ctx.lineWidth = 1.5 * devicePixelRatio;
                self.ctx.beginPath();
                self.ctx.moveTo(px, top);
                self.ctx.lineTo(px, top + height);
                self.ctx.stroke();
                self.ctx.restore();
              },
            ],
          },
        },
        [x, panel.values] as uPlot.AlignedData,
        el,
      );
      return { u, el };
    });
    plots.current = made.map((m) => m.u);
    const ro = new ResizeObserver(() => {
      const w = Math.max(200, host.clientWidth);
      made.forEach(({ u }) => u.setSize({ width: w, height: u.height }));
    });
    ro.observe(host);
    return () => {
      ro.disconnect();
      made.forEach(({ u, el }) => {
        u.destroy();
        el.remove();
      });
      plots.current = [];
    };
  }, [x, panels, event]);

  useEffect(() => {
    plots.current.forEach((u) => u.redraw(false));
  }, [scrubTs]);

  return <div ref={rows} className="chartrows" aria-label={STR.chartsLabel} />;
}
