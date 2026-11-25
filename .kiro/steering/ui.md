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
- Figma first: before you build or change a view, read its frame in Figma file RSgriaKxz59KrI9eWvrsr0 through the Figma MCP (`figma` server in `.kiro/settings/mcp.json`). Call `get_design_context` on the frame and `get_screenshot` to compare. Frames: 5 Trajectory map, 5b Trajectory 3D, 6 Event panel, 7 Raw record viewer, 7b Wireshark-style record, 9 Records. Take layout and spacing from Figma; take colours and type from `web/src/styles/tokens.css`. Where Figma conflicts with this file (caps labels, "went around", endpoints not in the contract), this file wins. Note what you read from Figma in the task's KIRO.md line.
- Visual reference: `docs/design/prototype-v2.html` (FlightMind prototype v2, light) together with the Figma file. Match its layout, colours and spacing. Only the wording rules above and the contract override it.
