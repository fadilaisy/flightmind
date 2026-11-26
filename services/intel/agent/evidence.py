"""The evidence rule, enforced in code (SCRUM-36).

The model may only cite ids that a tool result actually contained. Anything else is
dropped here, whatever the model was told. If no cited claim survives, the answer is the
fixed "not enough evidence" response.
"""
import logging
from typing import Any, Optional

from agent.tools import ToolResult

log = logging.getLogger("flightmind.agent")

NOT_ENOUGH_TEXT = "Not enough evidence in the loaded recording to answer that."
KIND_RECORD = "cat021_record"
KIND_EVENT = "event"


def not_enough(tool_calls: Optional[list] = None) -> dict:
    """The fixed response for every case where no cited claim can be shown."""
    return {
        "answer_md": NOT_ENOUGH_TEXT,
        "citations": [],
        "tool_calls": list(tool_calls or []),
        "status": "not_enough_evidence",
    }


class EvidenceSet:
    """Every raw_ref and event id that a tool result exposed during one question."""

    def __init__(self) -> None:
        self.raw_refs: set = set()
        self.events: dict = {}  # event id -> label

    def add(self, result: ToolResult) -> None:
        if result.is_error:
            return
        self.raw_refs.update(r for r in result.raw_refs if r)
        for event_id in result.event_ids:
            if event_id:
                self.events[event_id] = result.event_labels.get(event_id) or str(event_id)

    def label_for(self, kind: str, id: str) -> Optional[str]:
        """The citation label, or None when this (kind, id) was never returned by a tool."""
        if kind == KIND_RECORD and id in self.raw_refs:
            return id
        if kind == KIND_EVENT and id in self.events:
            return self.events[id]
        return None

    def render(self, final: Any, tool_calls: Optional[list] = None) -> dict:
        """Turn the model's structured answer into an AskResponse dict."""
        if not isinstance(final, dict) or final.get("status") != "ok":
            return not_enough(tool_calls)
        claims = final.get("claims")
        if not isinstance(claims, list):
            return not_enough(tool_calls)

        lines: list = []
        citations: list = []
        seen: set = set()
        for claim in claims:
            if not isinstance(claim, dict) or not isinstance(claim.get("text"), str):
                continue
            kept_labels: list = []
            pending: list = []
            for cite in claim.get("citations") or []:
                kind = cite.get("kind") if isinstance(cite, dict) else None
                cid = cite.get("id") if isinstance(cite, dict) else None
                label = self.label_for(kind, cid) if isinstance(kind, str) and isinstance(cid, str) else None
                if label is None:
                    log.warning("Dropped invalid citation kind=%s id=%s", kind, cid)
                    continue
                kept_labels.append(label)
                pending.append({"kind": kind, "id": cid, "label": label})
            text = " ".join(claim["text"].split())
            if not kept_labels or not text:
                log.warning("Dropped a claim with no valid citation (%d characters)", len(text))
                continue
            for item in pending:
                key = (item["kind"], item["id"])
                if key not in seen:
                    seen.add(key)
                    citations.append(item)
            unique_labels = list(dict.fromkeys(kept_labels))
            lines.append(text + " " + " ".join(f"[{lab}]" for lab in unique_labels))

        if not lines:
            return not_enough(tool_calls)
        return {
            "answer_md": "\n".join(lines),
            "citations": citations,
            "tool_calls": list(tool_calls or []),
            "status": "ok",
        }
