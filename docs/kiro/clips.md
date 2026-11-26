# Clip log

Add a row only after the clip exists in the shared Drive folder.
Mark `video` = yes for the two best clips each week.

| Date | File | Role | Kiro feature | What it shows | Video |
| --- | --- | --- | --- | --- | --- |
| 2026-11-25 | 2026-11-25_role3_mcp-get_track.mp4 | Role 3 | MCP server via kiro-cli chat (SCRUM-34) | kiro-cli chat calls get_track from the workspace mcp.json, driven by Claude Code: 8A0F21 returns 60 points with raw_ref, ZZZZZZ returns the unknown-aircraft error, API stopped returns the unreachable error | no |
| 2026-11-26 | 2026-11-26_role3_mcp-get_track-ide.mp4 | Role 3 | MCP server in IDE chat (SCRUM-34) | A person asks Kiro chat for get_track: 8A0F21 returns 60 points with raw_ref, ZZZZZZ returns the unknown-aircraft error, API stopped returns the unreachable error (played at 1.75x) | no |

## Web UI: remaining differences from the Figma PNGs (task 17, 2026-11-26)

Compared `docs/kiro/figma-check/ref/figma-*.png` with the running app (headless Edge, sample data and the SCRUM-33 mock API). Task 17 stays unticked for a person to do the final pass.

Header (all frames)
- Figma tabs: Clean, Events, Trajectory, Records, Export. App tabs: Events, Trajectory, Records (Clean and Export are not built).
- Figma shows the file name, record count and SAC/SIC chip on Records. The app shows the recording id only, because `/api/meta` has no record count.

Trajectory, map (frame 5)
- Reduction card: no Mean position error, Max altitude error or "Change cleaning and error bound" (the compression endpoint has none of these).
- Selected point card: Figma shows Geometric height (WGS-84), Pressure alt. and Mode 3/A values and a ground speed. The app labels altitude "barometric" (the API does not say the datum is geometric), shows "not in the API response" for pressure altitude and Mode 3/A, and computes ground speed and vertical rate from positions (a dash for the first point).
- Map: no coverage-gap annotation, no runway polygon fill or runway designator labels (07L/25R), no "Flagged window - climb-out" caption on the map; basemap is plain OSM, not the blue-water style.
- Charts: altitude axis ticks follow the data (0, 5k), Figma shows 0, 3k, 6k; row title is "Altitude (barometric), ft", Figma "Geometric height (WGS-84), ft".
- Events list: Figma has 7 events with a confirmed one; the mock API has 4 and sample data 1.

Trajectory, 3D (frame 5b)
- Altitude tick step is 1k ft on the sample track, Figma uses 2k ft.
- No in-scene "Go-around - climb-out" label; the point tooltip shows on hover, Figma shows it pinned.
- Figma view toggle reads 3D / Top-down / Profile; the app has Map / 3D / Profile (spec decision).

Event panel (frame 6)
- No "Lowest geometric height / Max climb / Back on approach" stat tiles and no "Back on approach" evidence line: the contract has no such fields. "What it might mean" and "What the data can't tell us" are not accordions.

Records (frames 9 and 7b)
- Frames table, block offsets and lengths, record offsets, item offsets/Len/FRN, item bit view and the decoder name are "n/a" or "not in the API response" (the raw endpoint returns only hex, decoded items, sac and sic).
- Export slice (.pcap) and Export record (.atx) are disabled; Apply is disabled.
- Hex pane shows one record, not the whole frame; no colour legend for Ethernet/UDP, block header and FSPEC.
- Records card scrolls inside 200 px; Figma shows 3 rows without scroll.
