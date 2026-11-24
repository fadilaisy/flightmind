# Requirements: SCRUM-40 event feed and investigation panel

Jira: "Feed of detected events; panel shows the cited answer, and each citation opens `/api/raw/{raw_ref}` with decoded fields next to the hex." Owner: Fadil. Folder: `web/`. Rules: `.kiro/steering/ui.md`. API: `contracts/openapi.yaml` only; no new endpoints.

## Requirements
1. The feed lists events from `GET /api/events`: type, callsign, icao24, start and end time, airport, severity.
2. Each event shows a state: "To review", "Confirmed by you" or "Dismissed by you". Default "To review". The state is kept in the browser only.
3. Selecting an event opens the panel and loads `GET /api/events/{id}`.
4. The panel shows the flagged window (`start_ts` to `end_ts`) and the event's `raw_refs` as citation chips.
5. The panel has an "Ask about this event" box. It calls `POST /api/ask` and shows `answer_md` with its citations as chips. If `status` is `not_enough_evidence`, it shows "Not enough evidence" and no claim.
6. A citation chip of kind `cat021_record` opens the raw record viewer. A chip of kind `event` selects that event.
7. The raw record viewer calls `GET /api/raw/{raw_ref}`. It shows `raw_ref`, `sac`, `sic`, the decoded fields as a table, and the hex next to ASCII, in rows of 16 with offsets.
8. Selecting a decoded field highlights its bytes only when byte ranges are known. Otherwise the whole record is marked and the viewer says "Item byte ranges are not in the API response."
9. A 404 on `/api/raw/{raw_ref}` shows "Record not found: <raw_ref>".
10. Wording follows `ui.md`: "flagged window", never "went around"; sentence case; every number carries its unit.

## Not in scope
- Map, 3D, charts and scrubber (SCRUM-39 spec tasks 3 to 16).
- Compression size (SCRUM-41, blocked on the compression endpoint).
- Similar past events.

## Open items
1. The mock API's `decoded` object uses plain keys (`lat`, `baro_alt_ft`) and no I021 item numbers or byte ranges. The viewer shows keys as given; item numbers appear once the real decoder supplies them.
2. Event type labels are the detector's names: "Go-around flag", "Holding flag", "Squawk 7700 flag". Fadil confirms the wording.
