import type { FlightEvent } from "../api/types";
import type { TypeFilter } from "../domain/eventFilter";
import { SHORT_LABEL } from "../domain/eventLabels";
import { STR } from "../strings";

interface Props {
  types: FlightEvent["type"][];
  counts: Record<string, number>;
  total: number;
  type: TypeFilter;
  onType: (t: TypeFilter) => void;
  query: string;
  onQuery: (q: string) => void;
  /** Second, muted line under the search box: time range, airport, status. */
  scope: string;
}

export function EventFilters({ types, counts, total, type, onType, query, onQuery, scope }: Props) {
  return (
    <>
      <label className="searchbox">
        <input
          type="search"
          aria-label={STR.searchLabel}
          placeholder={STR.searchLabel}
          value={query}
          onChange={(e) => onQuery(e.target.value)}
        />
        <small>{scope}</small>
      </label>
      <div className="filters">
        <button type="button" className={type === "all" ? "on" : undefined} onClick={() => onType("all")}>
          {STR.filterAll} {total}
        </button>
        {types.map((t) => (
          <button key={t} type="button" className={type === t ? "on" : undefined} onClick={() => onType(t)}>
            {SHORT_LABEL[t]} {counts[t] ?? 0}
          </button>
        ))}
      </div>
    </>
  );
}
