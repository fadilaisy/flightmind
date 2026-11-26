# Kiro prompt E: final fixes, states, wording, smoke, README. Hard stop at 12:40 local time.

Branch `claude/project-thread-6wj5yi`. Work only in `web/`, `.kiro/specs/web-ui/`, `.kiro/specs/scrum-40/`, `KIRO.md`, `docs/kiro/` and the web section of `README.md`. Do not touch `contracts/`, `services/`, `.kiro/agents/` (never `git add` its change or the `.bak` file) or `.kiro/settings/mcp.json`. Dev server already runs at http://127.0.0.1:5173. Wording rules in `.kiro/steering/ui.md` apply.

Time is short: Fadil needs this by 12:40 (check the clock with `Get-Date`). Do the steps in order, commit after each one (build and tests must pass; trailer line `Kiro: spec web-ui/<n>`; one KIRO.md line per commit). If it is 12:35 or later, commit what passes and stop. Skip screenshots except where a step asks for one.

1. Records tab fixes vs `docs/kiro/figma-check/ref/figma-9-records.png` (trailer web-ui/14):
   - Every card has double padding (an inner padded wrapper inside the card), so headers sit about 36 px in; Figma has 16 px. Use one level of padding.
   - Card borders are cyan; Figma uses the light grey border token.
   - Data items: I021/130 is split into two rows (lat, lon). Show one row with value "−6.12031, 106.65182" style (5 decimals, real minus sign). Same in the decode tree and item card.
   - Units show "deg": use "°" everywhere.
   - Card titles as Figma: bold label then a muted qualifier ("Records  in block 1", "Blocks  in recording rec01").
2. Trajectory fixes vs `figma-5-traj-map.png` (trailer web-ui/10):
   - Charts card: the row labels ("Ground speed, computed from positions, kt", "Vertical rate...") are drawn on top of the plot lines and the y-axis line. In Figma each row label sits in its own space above its row, left-aligned at 16 px, and the rows don't overlap. Hide the uPlot y-axis line; keep only the light grid like Figma.
   - Altitude y-axis ticks in Figma read "6k / 3k / 0"; use k-format.
3. Events tab vs `figma-4-events.png` (trailer web-ui/6): use the same dark badge with coloured dot (`EventBadge`) as the Trajectory list, ICAO24 upper-case mono everywhere (the list shows "8A0213", the Events table shows "8a0213"), and the review buttons and state pill styles from Figma. Match the table and stat card spacing to the PNG.
4. Loading, empty and error states (SCRUM-42; trailer web-ui/17): event list, Events table, map, charts, Records cards and the event drawer each show a loading line while fetching, an empty state ("No events in this recording", "Select an event to see its track", "Select a record to see its items"), and an error box with the message and a Retry button when the API fails, using `StateBox` styled like the cards in `figma-states.png` (light tokens). One test: a failing client renders the error box with Retry.
5. SCRUM-40 follow-ups (trailer `Kiro: spec scrum-40/<task>`): ask box sends the `askContext.ts` prefix and shows only what the user typed (test); flagged windows read `08:00:20 to 08:00:40 UTC (20 s)` with ISO in a `title` tooltip everywhere. Tick scrum-40 tasks 3 to 5 if the running app does this.
6. Task 16 (trailer web-ui/16): `tests/wording.test.ts` scans `src/strings.ts` and every `.tsx` under `src/` and fails on "went around", "no touchdown", all-caps labels, trailing arrows and mojibake (a capital A with circumflex or tilde before another symbol). Tick 16.
7. Task 17 (trailer web-ui/17): `tests/smoke.test.ts` renders each tab with the mock client in jsdom without throwing (stub WebGL and maplibre). List the remaining differences from the Figma PNGs in `docs/kiro/clips.md`. Leave the box unticked for Fadil.
8. Task 18 (trailer web-ui/18): README web section lists MapLibre GL (OSM tiles and attribution), three.js, uPlot, React, Vite, Inter and JetBrains Mono, and how to run against the mock and the SCRUM-33 mock API (`VITE_API_BASE=http://localhost:8000`). Tick 18.

Finish by printing what you committed and what you skipped.
