---
inclusion: fileMatch
fileMatchPattern: ["web/**", ".kiro/specs/web-ui/**"]
---
# UI rules (FlightMind web)

- Audience: a data analyst who reads raw CAT021 and uses Wireshark. Plain, dense, no marketing tone.
- Default view is Map; 3D is a tab. Records is its own tab (Block > Record > Item, hex + ASCII, linked highlight).
- Wording: say what the data shows, never more. States are "To review / Confirmed by you / Dismissed by you". Use "flagged window" and "no on-ground flag (I021/040) was set", never "went around" or "no touchdown".
- Every claim cites a raw_ref (<recording_file_id>:<record_index>, per data-contracts.md). Item byte ranges come from the decoded record, never from raw_ref. Show the unit, LSB and datum (e.g. 1,250 ft, WGS-84).
- Time field is I021/071 everywhere. Sample numbers carry a "sample data" label.
- Style: sentence case, no trailing arrows, no all-caps labels, soft shadows, blue palette from the Figma file.
- Mock API only: use contracts/openapi.yaml and contracts/types.ts. No new endpoints.
