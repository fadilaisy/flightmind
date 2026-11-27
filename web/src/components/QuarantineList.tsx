import { useEffect, useState } from "react";
import type { Api } from "../api/client";
import type { QuarantinePage, RecipeStep } from "../api/uploadTypes";
import { STR } from "../strings";
import { CitationChip } from "./CitationChip";
import { RawRecordViewer } from "./RawRecordViewer";
import { StateBox } from "./StateBox";
import { navigate } from "../views/nav";

export const QUARANTINE_PAGE = 20;
const nf = (n: number) => n.toLocaleString("en-US");

/** The page of rows shown, 1-based: "1 to 20 of 1,860". */
export function pageLine(offset: number, count: number, total: number): string {
  if (total === 0 || count === 0) return `0 of ${nf(total)}`;
  return `${nf(offset + 1)} to ${nf(offset + count)} of ${nf(total)}`;
}

interface Props {
  api: Api;
  recordingId: string;
  steps: RecipeStep[];
  onClose: () => void;
}

/** Records the cleaning set aside, paged (Figma frame 8b). Each raw_ref chip opens the raw record dialog. */
export function QuarantineList({ api, recordingId, steps, onClose }: Props) {
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<QuarantinePage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rawRef, setRawRef] = useState<string | null>(null);
  const label = (code: string) => steps.find((s) => s.code === code)?.label ?? code;

  useEffect(() => {
    let live = true;
    setPage(null);
    setError(null);
    api
      .recordingQuarantine(recordingId, offset, QUARANTINE_PAGE)
      .then((p) => live && setPage(p))
      .catch((e: Error) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [api, recordingId, offset]);

  return (
    <div className="card evtable quarantine" style={{ padding: 0 }}>
      <div className="cardtitle qhead">
        <h2>
          {STR.quarantineTitle} {page && <span className="muted small">{nf(page.total)} {STR.quarantineTotal}</span>}
        </h2>
        <button type="button" className="fbtn" onClick={onClose}>
          {STR.quarantineBack}
        </button>
      </div>
      {error ? (
        <StateBox kind="error" title={STR.quarantineError} text={error} />
      ) : !page ? (
        <StateBox kind="loading" title={STR.quarantineLoading} />
      ) : (
        <>
          <table>
            <thead>
              <tr>
                <th>{STR.colRawRef}</th>
                <th>{STR.colRule}</th>
                <th>{STR.colReason}</th>
              </tr>
            </thead>
            <tbody>
              {page.items.map((q, i) => (
                <tr key={`${q.raw_ref}:${offset + i}`}>
                  <td>
                    <CitationChip
                      citation={{ kind: "cat021_record", id: q.raw_ref, label: q.raw_ref.replace(/^rec/, "") }}
                      onOpenRecord={setRawRef}
                      onOpenEvent={() => {}}
                    />
                  </td>
                  <td>{label(q.step_code)}</td>
                  <td>{q.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="pager">
            <span className="muted">
              {STR.recordsShown} {pageLine(offset, page.items.length, page.total)}
            </span>
            <span className="rowbtns">
              <button type="button" className="fbtn" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - QUARANTINE_PAGE))}>
                {STR.pagePrev}
              </button>
              <button
                type="button"
                className="fbtn"
                disabled={offset + QUARANTINE_PAGE >= page.total}
                onClick={() => setOffset(offset + QUARANTINE_PAGE)}
              >
                {STR.pageNext}
              </button>
            </span>
          </div>
        </>
      )}
      {rawRef && (
        <RawRecordViewer
          api={api}
          rawRef={rawRef}
          onClose={() => setRawRef(null)}
          onOpenInRecords={() => {
            setRawRef(null);
            navigate({ tab: "records" });
          }}
        />
      )}
    </div>
  );
}

