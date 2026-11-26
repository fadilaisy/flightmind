import { useState, type ReactElement } from "react";
import type { RawRecord } from "../api/types";
import { byteCount } from "../domain/hex";
import { recordItems, type RecordItem } from "../domain/recordItems";
import { STR } from "../strings";

export interface TreeNode {
  id: string;
  label: string;
  /** Item path when the node is a decoded item, so a click can select it. */
  itemPath?: string;
  children: TreeNode[];
}

/** Block > Record > Item > detail lines, like Wireshark's detail pane. One record per call. */
export function buildRecordTree(record: RawRecord): TreeNode {
  const items = recordItems(record);
  const detail = (it: RecordItem): TreeNode[] => [
    { id: `${it.path}:raw`, label: `Raw: ${STR.notInApi}`, children: [] },
    ...(it.lsb ? [{ id: `${it.path}:lsb`, label: `LSB ${it.lsb}`, children: [] }] : []),
    ...(it.datum ? [{ id: `${it.path}:datum`, label: `Datum ${it.datum}`, children: [] }] : []),
  ];
  const bytes = byteCount(record.hex);
  return {
    id: "block",
    label: `ASTERIX block · CAT 021 · recording ${record.recording_file_id}`,
    children: [
      {
        id: "record",
        label: `Record ${record.record_index} · ${bytes} bytes · SAC ${record.sac ?? "n/a"} / SIC ${record.sic ?? "n/a"} · ${items.length} items`,
        children: items.map((it) => ({
          id: it.path,
          itemPath: it.path,
          label: `${it.id} ${it.name}: ${it.value}`,
          children: detail(it),
        })),
      },
    ],
  };
}

interface Props {
  record: RawRecord;
  selectedPath: string | null;
  onSelectPath: (path: string) => void;
}

export function RecordTree({ record, selectedPath, onSelectPath }: Props) {
  const root = buildRecordTree(record);
  const [open, setOpen] = useState<Set<string>>(() => new Set(["block", "record"]));

  function toggle(id: string) {
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function row(node: TreeNode, depth: number): ReactElement {
    const has = node.children.length > 0;
    const expanded = open.has(node.id);
    const selected = node.itemPath !== undefined && node.itemPath === selectedPath;
    return (
      <div key={node.id} role="treeitem" aria-expanded={has ? expanded : undefined} aria-selected={selected}>
        <div
          className={`treerow${selected ? " sel" : ""}`}
          style={{ paddingLeft: 8 + depth * 16 }}
          onClick={() => {
            if (node.itemPath) onSelectPath(node.itemPath);
            if (has) toggle(node.id);
          }}
        >
          <span className="treearrow" aria-hidden="true">{has ? (expanded ? "▾" : "▸") : ""}</span>
          <span className={node.itemPath || depth > 1 ? "mono" : undefined}>{node.label}</span>
        </div>
        {has && expanded && <div role="group">{node.children.map((c) => row(c, depth + 1))}</div>}
      </div>
    );
  }

  return (
    <div className="tree" role="tree" aria-label={STR.decodeTree}>
      {row(root, 0)}
    </div>
  );
}
