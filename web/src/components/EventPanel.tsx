import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { Api } from "../api/client";
import type { AskResponse, EventDetail, Track } from "../api/types";
import { buildAskQuestion } from "../domain/askContext";
import { rawRefCitation } from "../domain/citations";
import { derive } from "../domain/derive";
import { phrase } from "../domain/eventLabels";
import { STATE_LABEL, type EventState } from "../domain/eventState";
import { formatWindow, formatWindowTitle } from "../domain/format";
import { clockZ, signedInt, thousands } from "../domain/pointText";
import { inWindow } from "../domain/window";
import { STR } from "../strings";
import { CitationChip } from "./CitationChip";
import { EventBadge } from "./EventBadge";

type TrackPoint = Track["points"][number];

interface Props {
  api: Api;
  event: EventDetail;
  state: EventState;
  /** Track points of the aircraft, or null while they load. */
  points: TrackPoint[] | null;
  onSetState: (id: string, state: EventState) => void;
  onOpenRecord: (rawRef: string) => void;
  onOpenEvent: (eventId: string) => void;
  onClose: () => void;
}

const MIGHT_MEAN: Record<EventDetail["type"], string> = {
  go_around:
    "A go-around flag marks a climb after a low approach. That can be a missed approach, but the flag alone does not say why. Check the cited records and any ATC report.",
  holding:
    "A holding flag marks a track that stays in one area and keeps turning. That can be a published hold or a delay. The flag alone does not say which.",
  squawk_7500: "Code 7500 is the transponder code for unlawful interference. A wrong code can also be set by mistake, so check it across the records.",
  squawk_7600: "Code 7600 is the transponder code for radio failure. A wrong code can also be set by mistake, so check it across the records.",
  squawk_7700: "Code 7700 is the transponder code for a general emergency. A wrong code can also be set by mistake, so check it across the records.",
};

const FOOTER_TEXT: Record<EventState, string> = {
  to_review: "Candidate for your review",
  confirmed: "You confirmed this event",
  dismissed: "You dismissed this event",
};

function Chevron() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M6 3.5L10.5 8L6 12.5" stroke="#383838" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Fold({ title, children }: { title: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`dfold${open ? " open" : ""}`}>
      <button type="button" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        <span>{title}</span>
        <Chevron />
      </button>
      {open && <div className="foldbody">{children}</div>}
    </div>
  );
}

/** The Figma event panel: a drawer over the right side with the event's numbers, evidence and review buttons. */
export function EventPanel({ api, event, state, points, onSetState, onOpenRecord, onOpenEvent, onClose }: Props) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const closeBtn = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeBtn.current?.focus();
  }, []);

  // The numbers come from the track points inside the flagged window.
  const facts = useMemo(() => {
    if (!points) return null;
    const rates = derive(points).verticalRateFpm;
    const inside = points.map((p, i) => ({ p, rate: rates[i] })).filter((x) => inWindow(x.p.ts, event));
    const alts = inside.map((x) => x.p.alt_ft).filter((v): v is number => v != null);
    const climbs = inside.map((x) => x.rate).filter((v): v is number => v != null);
    const lowest = alts.length > 0 ? Math.min(...alts) : null;
    const highest = alts.length > 0 ? Math.max(...alts) : null;
    return { lowest, highest, maxClimb: climbs.length > 0 ? Math.max(...climbs) : null };
  }, [points, event]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const typed = question.trim();
    if (!typed) return;
    setBusy(true);
    setError(null);
    try {
      // The API takes only `question`; the event goes in as a prefix the user never sees.
      setAnswer(await api.ask(buildAskQuestion(event, typed)));
    } catch (err) {
      setAnswer(null);
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const who = event.callsign ?? event.icao24.toUpperCase();
  const none = "\u2014";
  const why =
    `Flagged as a ${phrase(event.type)} over ${formatWindow(event.start_ts, event.end_ts)}, with ${event.raw_refs.length} ${STR.supportingRecords}.` +
    (facts && facts.lowest != null && facts.highest != null
      ? ` Altitude in the window ran from ${thousands(facts.lowest)} to ${thousands(facts.highest)} ft (barometric).`
      : "");
  const evidence = event.raw_refs.map((ref) => {
    const p = points?.find((x) => x.raw_ref === ref);
    if (!p) return { ref, text: `Record ${ref}` };
    const alt = p.alt_ft == null ? "altitude not reported" : `${thousands(p.alt_ft)} ft`;
    const low = facts?.lowest != null && p.alt_ft === facts.lowest ? ", lowest in the window" : "";
    return { ref, text: `${clockZ(p.ts)} · ${alt}${low}` };
  });

  return (
    <aside
      className="drawer"
      role="dialog"
      aria-label={STR.eventPanel}
      onKeyDown={(e) => {
        // The cited-record dialog closes itself on Escape; leave the drawer open then.
        if (e.key === "Escape" && !document.querySelector(".dlgback")) onClose();
      }}
    >
      <div className="dhead">
        <div className="dtags">
          <EventBadge type={event.type} />
          <span className="dpill">{STATE_LABEL[state]}</span>
          <div className="spacer" />
          <button type="button" ref={closeBtn} className="dclose" aria-label={STR.close} onClick={onClose}>
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <path d="M5 5L15 15M15 5L5 15" stroke="#03045E" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          </button>
        </div>
        <h2>
          {who} · {phrase(event.type)}
          {event.airport ? ` at ${event.airport}` : ""}
        </h2>
        <p className="dwindow" title={formatWindowTitle(event.start_ts, event.end_ts)}>
          {formatWindow(event.start_ts, event.end_ts)} · {event.raw_refs.length} {STR.supportingRecords}
        </p>
        <div className="dstats">
          <div className="dstat" title={`${STR.chartAltitudeLabel}, barometric`}>
            <span>{STR.statLowest}</span>
            <b>{facts?.lowest != null ? `${thousands(facts.lowest)} ft` : none}</b>
          </div>
          <div className="dstat">
            <span>{STR.statMaxClimb}</span>
            <b>{facts?.maxClimb != null ? `${signedInt(facts.maxClimb)} ft/min` : none}</b>
          </div>
          <div className="dstat">
            <span>{STR.statWindowEnd}</span>
            <b>{clockZ(event.end_ts)}</b>
          </div>
        </div>
      </div>

      <div className="dbody">
        <div className="dwhy">
          <b>{STR.whyFlagged}</b>
          <p>{why}</p>
        </div>

        <div className="dsechead">
          <h3>{STR.evidence}</h3>
          <span>{STR.evidenceHint}</span>
        </div>
        <div className="devlist">
          {evidence.map((r) => (
            <div className="devrow" key={r.ref}>
              <span>{r.text}</span>
              <CitationChip citation={rawRefCitation(r.ref)} onOpenRecord={onOpenRecord} onOpenEvent={onOpenEvent} />
            </div>
          ))}
        </div>

        <div className="dmore">
          <Fold title={STR.mightMean}>
            <p>{MIGHT_MEAN[event.type]}</p>
          </Fold>
          <Fold title={STR.cantTell}>
            <p>
              The records give time, position, altitude and the items decoded from CAT021. They do not give the reason, the pilot&apos;s intent, ATC
              instructions or the runway in use.
            </p>
            <p>Items the API does not return, such as the on-ground flag (I021/040), are not used here.</p>
          </Fold>
          <Fold title={`${STR.askAbout}`}>
            <form onSubmit={submit} style={{ display: "flex", gap: 6 }}>
              <input
                aria-label={STR.askAbout}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder={`Ask about ${who}`}
                style={{ flex: 1, minWidth: 0, padding: "6px 8px", border: "1px solid var(--line-ui)", borderRadius: 6, fontSize: 12 }}
              />
              <button type="submit" className="fbtn" disabled={busy}>
                {busy ? STR.asking : STR.ask}
              </button>
            </form>
            {error && <p role="alert">{error}</p>}
            {answer && answer.status === "not_enough_evidence" && <p>{STR.notEnoughEvidence}</p>}
            {answer && answer.status === "ok" && (
              <div style={{ marginTop: 8 }}>
                <div style={{ whiteSpace: "pre-wrap" }}>{answer.answer_md}</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 6 }}>
                  {answer.citations.map((c) => (
                    <CitationChip key={`${c.kind}:${c.id}`} citation={c} onOpenRecord={onOpenRecord} onOpenEvent={onOpenEvent} />
                  ))}
                </div>
              </div>
            )}
          </Fold>
        </div>
      </div>

      <div className="dfoot">
        <p>{FOOTER_TEXT[state]}</p>
        {state === "to_review" ? (
          <>
            <button type="button" className="fbtn lg solid" onClick={() => onSetState(event.id, "confirmed")}>
              {STR.confirm}
            </button>
            <button type="button" className="fbtn lg" onClick={() => onSetState(event.id, "dismissed")}>
              {STR.dismiss}
            </button>
          </>
        ) : (
          <button type="button" className="fbtn lg" onClick={() => onSetState(event.id, "to_review")}>
            {STR.undo}
          </button>
        )}
      </div>
    </aside>
  );
}
