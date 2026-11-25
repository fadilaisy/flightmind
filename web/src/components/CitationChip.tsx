import type { Citation } from "../domain/citations";

interface Props {
  citation: Citation;
  onOpenRecord: (rawRef: string) => void;
  onOpenEvent: (eventId: string) => void;
}

export function CitationChip({ citation, onOpenRecord, onOpenEvent }: Props) {
  const isRecord = citation.kind === "cat021_record";
  return (
    <button
      type="button"
      className="chip"
      title={isRecord ? `Open record ${citation.id}` : `Open event ${citation.id}`}
      onClick={() => (isRecord ? onOpenRecord(citation.id) : onOpenEvent(citation.id))}
    >
      {isRecord ? "rec " : "event "}
      {citation.label}
    </button>
  );
}
