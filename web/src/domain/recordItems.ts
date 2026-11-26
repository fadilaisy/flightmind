import type { RawRecord } from "../api/types";
import { describeDecoded, type DecodedRow } from "./itemMeta";
import type { ItemRange } from "./hex";

export interface RecordItem {
  /** Unique within the record, e.g. "I021/130.lat". */
  path: string;
  /** "I021/130" when known, otherwise the key the API used. */
  id: string;
  name: string;
  definition: string | null;
  lsb: string | null;
  datum: string | null;
  /** Value with its unit, e.g. "1,250 ft". */
  value: string;
  known: boolean;
}

function toItem(row: DecodedRow): RecordItem {
  // A unit goes only after a number, so a time string such as 08:00:30.00Z stays as it is.
  const numeric = row.unit && /^[-\u2212]?[\d.,]+$/.test(row.value);
  const value = numeric ? (row.unit === "°" ? `${row.value}°` : `${row.value} ${row.unit}`) : row.value;
  return {
    path: row.path,
    id: row.item?.id ?? row.key,
    name: row.item?.name ?? row.key,
    definition: row.item?.definition ?? null,
    lsb: row.item?.lsb ?? null,
    datum: row.item?.datum ?? null,
    value,
    known: Boolean(row.item),
  };
}

/** One row per decoded value, with name, unit, LSB and datum from itemMeta. */
export function recordItems(record: Pick<RawRecord, "decoded">): RecordItem[] {
  return describeDecoded(record.decoded).map(toItem);
}

/**
 * Byte ranges of the items. The API does not return them (item byte ranges are not in the
 * response), so this is empty. When the contract adds them, read them here and nowhere else.
 */
export function itemRanges(_record: Pick<RawRecord, "decoded" | "hex">): ItemRange[] {
  return [];
}
