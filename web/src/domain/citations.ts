import type { components } from "../../../contracts/types";

export type Citation = components["schemas"]["Citation"];

export interface ParsedRawRef {
  recordingFileId: string;
  recordIndex: number;
}

// raw_ref format: <recording_file_id>:<record_index> (data-contracts.md).
export function parseRawRef(rawRef: string): ParsedRawRef | null {
  const i = rawRef.lastIndexOf(":");
  if (i <= 0) return null;
  const index = Number(rawRef.slice(i + 1));
  if (!Number.isInteger(index) || index < 0) return null;
  return { recordingFileId: rawRef.slice(0, i), recordIndex: index };
}

export function rawRefCitation(rawRef: string): Citation {
  return { kind: "cat021_record", id: rawRef, label: rawRef };
}
