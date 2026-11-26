import type { Citation } from "../domain/citations";

interface Props {
  citation: Citation;
  onOpenRecord: (rawRef: string) => void;
  onOpenEvent: (eventId: string) => void;
}

/** The record mark in the Figma chip. */
export const CHIP_MARK = "\u2317";

export function CitationChip({ citation, onOpenRecord, onOpenEvent }: Props) {
  const isRecord = citation.kind === "cat021_record";
  return (
    <button
      type="button"
      className="chip"
      title={isRecord ? `Open record ${citation.id}` : `Open event ${citation.id}`}
      onClick={() => (isRecord ? onOpenRecord(citation.id) : onOpenEvent(citation.id))}
    >
      <span aria-hidden="true">{CHIP_MARK}</span>
      {isRecord ? "rec " : "event "}
      {citation.label}
    </button>
  );
}

/** A chip that only shows a record id, for places that already sit on a clickable target. */
export function StaticChip({ rawRef }: { rawRef: string }) {
  return (
    <span className="chip static">
      <span aria-hidden="true">{CHIP_MARK}</span>
      rec {rawRef}
    </span>
  );
}
