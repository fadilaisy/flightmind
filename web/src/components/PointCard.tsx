import type { Track } from "../api/types";
import { derive } from "../domain/derive";
import { altitudeDatum } from "../domain/itemMeta";
import { clockZ, signedDeg, signedInt, thousands } from "../domain/pointText";
import { snapIndex } from "./Scrubber";
import { rawRefCitation } from "../domain/citations";
import { CitationChip } from "./CitationChip";
import { STR } from "../strings";

type TrackPoint = Track["points"][number];

interface Props {
  points: TrackPoint[];
  scrubTs: string | null;
  onOpenRecord: (rawRef: string) => void;
}

/** The right-hand "Selected point" card: the I021 values for the point under the scrubber. */
export function PointCard({ points, scrubTs, onOpenRecord }: Props) {
  const i = snapIndex(points, scrubTs);
  const p = points[i];
  const d = derive(points);
  const speed = d.speedKt[i];
  const rate = d.verticalRateFpm[i];
  const none = "\u2014";
  const na = STR.notInApi;

  const rows: { label: string; value: string; kind?: "na" | "mono"; title?: string }[] = p
    ? [
        { label: STR.timeOfApplicability, value: clockZ(p.ts), title: STR.timeItem },
        { label: STR.latitude, value: signedDeg(p.lat) },
        { label: STR.longitude, value: signedDeg(p.lon) },
        { label: `${STR.chartAltitudeLabel} (${altitudeDatum()})`, value: p.alt_ft == null ? "not reported" : `${thousands(p.alt_ft)} ft` },
        { label: STR.pressureAlt, value: na, kind: "na" },
        { label: STR.groundSpeedComputed, value: speed == null ? none : `${thousands(speed)} kt` },
        { label: STR.verticalRateComputed, value: rate == null ? none : `${signedInt(rate)} ft/min` },
        { label: STR.mode3a, value: na, kind: "na" },
      ]
    : [];

  return (
    <section className="rcard point" aria-label={STR.selectedPoint}>
      <div className="rhead">
        <span>{STR.selectedPoint}</span>
        <span className="mono">I021</span>
      </div>
      <dl>
        {rows.map((r) => (
          <div className="pkv" key={r.label}>
            <dt>{r.label}</dt>
            <dd className={r.kind === "na" ? "na" : undefined} title={r.title}>
              {r.value}
            </dd>
          </div>
        ))}
        {p && (
          <div className="pkv src">
            <dt>{STR.sourceRecord}</dt>
            <dd>
              <CitationChip citation={rawRefCitation(p.raw_ref)} onOpenRecord={onOpenRecord} onOpenEvent={() => {}} />
            </dd>
          </div>
        )}
      </dl>
      {!p && <p className="empty">{STR.selectEvent}</p>}
    </section>
  );
}
