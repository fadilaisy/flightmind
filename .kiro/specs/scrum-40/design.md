# Design: SCRUM-40

## Files (under `web/src/`)
| File | Job |
| --- | --- |
| `domain/eventState.ts` | state type, labels, load and save with an injectable storage |
| `domain/hex.ts` | split a hex string into rows of 16 bytes with offset and ASCII |
| `domain/citations.ts` | parse a raw_ref; label a citation |
| `domain/eventLabels.ts` | event type to display text |
| `components/EventFeed.tsx` | list, state buttons, selection |
| `components/CitationChip.tsx` | one chip; click opens record or event |
| `components/InvestigationPanel.tsx` | window, citations, ask box and answer |
| `components/RawRecordViewer.tsx` | decoded table and hex pane |
| `App.tsx` | wires the three pieces to the API |
| `api/client.ts` | add `ask()` (already in contract) |

## Data flow
```
feed select -> GET /api/events/{id} -> panel
chip click  -> GET /api/raw/{raw_ref} -> viewer
ask submit  -> POST /api/ask -> answer + chips
```

## Hex rows
Input `"0018130000C82F019E0B"` gives rows of `{offset, bytes[], ascii}`. Non-printable bytes show as `.`. Odd length or non-hex input returns an error row instead of throwing.

## State storage
Key `flightmind.eventStates`, value `{ [eventId]: "confirmed" | "dismissed" }`. Missing means "To review".

## Risks
| Risk | Plan |
| --- | --- |
| No DOM test setup | Test domain code with Vitest; check components by `tsc` and `vite build` |
| Mock has no byte ranges | Whole-record mark plus a one-line note (R8) |
