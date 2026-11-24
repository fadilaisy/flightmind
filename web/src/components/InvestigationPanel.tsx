import { useState } from "react";
import type { Api } from "../api/client";
import type { AskResponse, EventDetail } from "../api/types";
import { rawRefCitation } from "../domain/citations";
import { EVENT_LABEL } from "../domain/eventLabels";
import { CitationChip } from "./CitationChip";

interface Props {
  api: Api;
  event: EventDetail;
  onOpenRecord: (rawRef: string) => void;
  onOpenEvent: (eventId: string) => void;
}

export function InvestigationPanel({ api, event, onOpenRecord, onOpenEvent }: Props) {
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

  return (
    <section className="card" aria-label="Investigation panel">
      <h2 style={{ margin: 0, font: "600 15px/22px var(--font-text)" }}>
        {EVENT_LABEL[event.type]} · {event.callsign ?? event.icao24}
      </h2>
      <p className="data">
        Flagged window {event.start_ts} to {event.end_ts}
      </p>
      <p style={{ margin: "4px 0" }}>Records in the flagged window ({event.raw_refs.length}):</p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
        {event.raw_refs.map((r) => (
          <CitationChip key={r} citation={rawRefCitation(r)} onOpenRecord={onOpenRecord} onOpenEvent={onOpenEvent} />
        ))}
      </div>

      <form onSubmit={submit} style={{ marginTop: 12, display: "flex", gap: 6 }}>
        <input
          aria-label="Ask about this event"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={`Ask about ${event.callsign ?? event.icao24}`}
          style={{ flex: 1 }}
        />
        <button type="submit" disabled={busy}>
          {busy ? "Asking" : "Ask"}
        </button>
      </form>

      {error && <p role="alert">{error}</p>}
      {answer && answer.status === "not_enough_evidence" && <p>Not enough evidence.</p>}
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
  );
}
