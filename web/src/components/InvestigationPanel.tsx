import { useState } from "react";
import type { Api } from "../api/client";
import type { AskResponse, EventDetail } from "../api/types";
import { buildAskQuestion } from "../domain/askContext";
import { rawRefCitation } from "../domain/citations";
import { EVENT_LABEL } from "../domain/eventLabels";
import { STATE_BADGE, STATE_LABEL, type EventState } from "../domain/eventState";
import { formatWindow, formatWindowTitle } from "../domain/format";
import { STR } from "../strings";
import { CitationChip } from "./CitationChip";

interface Props {
  api: Api;
  event: EventDetail;
  state: EventState;
  onSetState: (id: string, state: EventState) => void;
  onOpenRecord: (rawRef: string) => void;
  onOpenEvent: (eventId: string) => void;
}

export function InvestigationPanel({ api, event, state, onSetState, onOpenRecord, onOpenEvent }: Props) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

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

  const who = event.callsign ?? event.icao24;

  return (
    <section aria-label="Investigation panel">
      <div className="block">
        <span className={`badge ${STATE_BADGE[state]}`}>{STATE_LABEL[state]}</span>
        <h2 style={{ marginTop: 8 }}>
          {who} · {EVENT_LABEL[event.type]}
        </h2>
        <h3>{STR.flaggedWindow}</h3>
        <p className="mono" style={{ margin: "0 0 12px" }} title={formatWindowTitle(event.start_ts, event.end_ts)}>
          {formatWindow(event.start_ts, event.end_ts)}
        </p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {state === "to_review" ? (
            <>
              <button type="button" className="btn primary sm" onClick={() => onSetState(event.id, "confirmed")}>
                {STR.confirm}
              </button>
              <button type="button" className="btn sm" onClick={() => onSetState(event.id, "dismissed")}>
                {STR.dismiss}
              </button>
            </>
          ) : (
            <button type="button" className="btn ghost sm" onClick={() => onSetState(event.id, "to_review")}>
              {STR.backToReview}
            </button>
          )}
        </div>
      </div>

      <div className="block">
        <h3>
          {STR.recordsInWindow} ({event.raw_refs.length})
        </h3>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
          {event.raw_refs.map((r) => (
            <CitationChip key={r} citation={rawRefCitation(r)} onOpenRecord={onOpenRecord} onOpenEvent={onOpenEvent} />
          ))}
        </div>
      </div>

      <div className="block">
        <form onSubmit={submit} style={{ display: "flex", gap: 6 }}>
          <input
            aria-label="Ask about this event"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={`Ask about ${who}`}
            style={{ flex: 1, minWidth: 0, padding: "4px 8px", border: "1px solid var(--line)", borderRadius: 6 }}
          />
          <button type="submit" className="btn sm" disabled={busy}>
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
      </div>
    </section>
  );
}