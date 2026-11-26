# Kiro prompt A: finish map (tasks 7, 8), charts (10), scrubber (11)

You are on branch `claude/project-thread-6wj5yi` in the FlightMind repo. Work only in `web/`, `.kiro/specs/web-ui/`, `KIRO.md` and `docs/kiro/`. Do not touch `contracts/`, `services/`, `.kiro/agents/` (leave its uncommitted change and the `.bak` file alone, never `git add` them) or `.kiro/settings/mcp.json`.

Read first: `.kiro/specs/web-ui/requirements.md`, `design.md`, `tasks.md`, `.kiro/steering/ui.md`.

## Visual reference
- `docs/design/prototype-v2.html` is the layout to match (open it in a browser; the Trajectory screen is `go('traj')`). Reference screenshots at 1440 x 900 are in `docs/kiro/figma-check/ref/` (`proto-traj-map.png` etc.).
- If the Figma MCP (`figma` server, file `RSgriaKxz59KrI9eWvrsr0`, frame 5 `58:1847`) answers, use `get_screenshot` on the frame too. If it does not answer, do not stop: use the prototype and the screenshots in `docs/kiro/figma-check/` and say so in the KIRO.md line.
- Wording rules from `ui.md` win over the prototype (sentence case, "flagged window", never "went around", no invented numbers).

## State of the work
Task 7 (map with OSM basemap, WIII runway GeoJSON, legend) is written but uncommitted: `src/views/MapView.tsx`, `src/components/Legend.tsx`, `src/geo/`, `src/domain/trackGeo.ts`, `src/state/useTrack.ts`, `tests/trackGeo.test.ts`, plus edits in `format.ts`, `strings.ts`, `tokens.css`, `TrajectoryView.tsx`, `nav.ts`, `vite.config.ts`, `package.json`. Review it, keep it, fix it where needed.

## Do, in order. After each task: `npm run build` and `npm test` pass in `web/`, tick the box in tasks.md, add one KIRO.md line (format at the top of KIRO.md, role "Fadil"), commit only the files of that task with a message `web-ui/<n>: <what>` and a trailer line `Kiro: spec web-ui/<n>`.

1. Task 7. Check the map shows the runway layer and the legend names kept, event window and flagged with a label. On first load the map must fit the selected event's track (all points plus the runway) with padding, like the prototype, not a street-level zoom. Make sure the maplibre worker loads in dev and in build (an earlier run logged "Worker failed to load"). Commit.
2. Task 8. Points draw in the three styles from `pointStyle`; the track is also drawn as a line; hover shows a tooltip card like the prototype's (I021/071 time, lat and lon in degrees, altitude like "1,250 ft, barometric" from `itemMeta`, and the `raw_ref` as a chip); selecting an event zooms to its window; clicking a point sets `rawRef` in the store and opens the Records tab. Put formatting in `src/domain/format.ts` with tests. Commit.
3. Task 10. `src/components/Charts.tsx` with uPlot: altitude, ground speed and vertical rate over one shared time axis, in the box under the map (where the prototype shows "Altitude over time"). Null altitude shows a gap, never zero. The flagged window is shaded like the prototype (light amber band, label "flagged window 08:00:20 to 08:00:40 UTC"). Speed and vertical rate titles say "computed from positions". The Profile toggle shows or hides the charts. Units on every axis (ft, kt, ft/min). Commit.
4. Task 11. `src/components/Scrubber.tsx` and `tests/scrubber.test.tsx`, in the bar under the charts like the prototype: play button, current I021/071 time, a range slider, and the track's start and end time. Drag and arrow keys move one point, Shift+arrow ten; the scrubber is the only writer of `scrubTs`; the marker sits on the nearest point at or before the time, on the map (a dark dot) and as a vertical line on all charts. The flagged window is shaded on the slider. Commit.

## Visual check (required before you finish)
A dev server is already running at http://127.0.0.1:5173 with hot reload; do not start another and do not stop it. Open http://127.0.0.1:5173/?tab=trajectory at 1440 x 900 and compare with `docs/kiro/figma-check/ref/proto-traj-map.png`. Same regions, sizes and spacing: left event list 290 px, right column 310 px, map, chart box and scrubber bar stacked in the middle. Fix differences. Save your screenshot as `docs/kiro/figma-check/10-11-built.png` and list what still differs (real data values, mock has fewer points) in the task's KIRO.md line.

Finish with `npm run build` and `npm test` passing and print a short summary: tasks ticked, commits made, anything left.

