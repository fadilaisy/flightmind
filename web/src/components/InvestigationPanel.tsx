import { useState } from "react";
import type { Api } from "../api/client";
import type { AskResponse, EventDetail } from "../api/types";
import { rawRefCitation } from "../domain/citations";
import { EVENT_LABEL } from "../domain/eventLabels";
import { STATE_LABEL, type EventState } from "../domain/eventState";
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
    if (!question.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setAnswer(await api.ask(question.trim()));
    } catch (err) {
      setAnswer(null);
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const who = event.callsign ?? event.icao24;
  const stateBadge = state === "confirmed" ? "b-ok" : "b-grey";

  return (
    <>
      <section className="card" aria-label="Investigation panel">
        <span className={`badge ${stateBadge}`}>{STATE_LABEL[state]}</span>
        <h2 style={{ marginTop: 8 }}>
          {who} · {EVENT_LABEL[event.type]}
        </h2>
        <h3 style={{ marginTop: 12 }}>{STR.whyFlagged}</h3>
        <p className="mono" style={{ margin: "0 0 12px" }}>
          {event.start_ts} to {event.end_ts}
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
      </section>

      <section className="card" aria-label={STR.recordsInWindow}>
        <h3>
          {STR.recordsInWindow} ({event.raw_refs.length})
        </h3>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
          {event.raw_refs.map((r) => (
            <CitationChip key={r} citation={rawRefCitation(r)} onOpenRecord={onOpenRecord} onOpenEvent={onOpenEvent} />
          ))}
        </div>
      </section>

      <section className="card">
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
      </section>
    </>
  );
}