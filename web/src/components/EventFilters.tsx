import type { FlightEvent } from "../api/types";
import type { TypeFilter } from "../domain/eventFilter";
import { EVENT_LABEL } from "../domain/eventLabels";
import { STR } from "../strings";

interface Props {
  types: FlightEvent["type"][];
  type: TypeFilter;
  onType: (t: TypeFilter) => void;
  query: string;
  onQuery: (q: string) => void;
}

export function EventFilters({ types, type, onType, query, onQuery }: Props) {
  return (
    <>
      <input
        className="search"
        type="search"
        aria-label={STR.searchLabel}
        placeholder={STR.searchLabel}
        value={query}
        onChange={(e) => onQuery(e.target.value)}
      />
      <div className="filters">
        <button type="button" className={type === "all" ? "on" : undefined} onClick={() => onType("all")}>
          {STR.filterAll}
        </button>
        {types.map((t) => (
          <button key={t} type="button" className={type === t ? "on" : undefined} onClick={() => onType(t)}>
            {EVENT_LABEL[t]}
          </button>
        ))}
      </div>
    </>
  );
}