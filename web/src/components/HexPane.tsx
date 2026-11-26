import { useMemo } from "react";
import { rangeAt, toHexRows, type ItemRange } from "../domain/hex";
import { STR } from "../strings";

interface Props {
  hex: string;
  /** Byte range per item. Empty when the API gives none. */
  ranges: ItemRange[];
  selectedPath: string | null;
  onSelectPath: (path: string) => void;
  selectedByte?: number | null;
  onSelectByte?: (index: number) => void;
}

/**
 * Hex and ASCII in rows of 16 with an offset column. An item selected by `selectedPath` marks
 * its bytes in both panes. Without ranges, a selected item marks the whole record and the pane
 * says so. A click on a byte selects the item whose range holds it.
 */
export function HexPane({ hex, ranges, selectedPath, onSelectPath, selectedByte = null, onSelectByte }: Props) {
  const result = useMemo(() => toHexRows(hex), [hex]);
  if (!result.ok) return <p role="alert">{result.error}</p>;

  const active = selectedPath ? ranges.find((r) => r.path === selectedPath) : undefined;
  const wholeRecord = Boolean(selectedPath) && ranges.length === 0;
  const marked = (i: number) => wholeRecord || (active !== undefined && i >= active.start && i < active.end);

  function pick(i: number) {
    onSelectByte?.(i);
    const r = rangeAt(ranges, i);
    if (r) onSelectPath(r.path);
  }

  function cls(i: number): string {
    return ["hb", marked(i) ? "sel" : "", selectedByte === i ? "pick" : ""].filter(Boolean).join(" ");
  }

  return (
    <div className="hexpane">
      <div className="hexrows" role="group" aria-label={STR.hexBytesLabel}>
        {result.rows.map((row) => (
          <div className="hexrow" key={row.offset}>
            <span className="hexoff">{row.offset.toString(16).padStart(4, "0")}</span>
            <span className="hexbytes">
              {row.bytes.map((b, j) => {
                const i = row.offset + j;
                return (
                  <span key={i} data-hex={i} className={cls(i)} onClick={() => pick(i)}>
                    {b}
                  </span>
                );
              })}
            </span>
            <span className="hexascii">
              {[...row.ascii].map((ch, j) => {
                const i = row.offset + j;
                return (
                  <span key={i} data-ascii={i} className={cls(i)} onClick={() => pick(i)}>
                    {ch}
                  </span>
                );
              })}
            </span>
          </div>
        ))}
      </div>
      {wholeRecord && <p className="muted hexnote">{STR.noItemRanges}</p>}
    </div>
  );
}
