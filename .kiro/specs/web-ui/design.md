# Design: web-ui (SCRUM-39)

## Stack
TypeScript, React, Vite. Map: MapLibre GL. 3D: three.js. Charts: uPlot (small, fast on 5,000 points). Hex pane: own component. Each library that does real work is listed in the README.

Assumption: the repo has no web framework yet. Role 1 confirms the stack before task 1.

## Tokens (from Figma "Foundations", file RSgriaKxz59KrI9eWvrsr0)
Put in `web/src/styles/tokens.css`.

| Group | Token: value |
| --- | --- |
| Blue ramp | 100 #CAF0F8, 200 #ADE8F4, 300 #90E0EF, 400 #48CAE4, 500 #00B4D8, 600 #0096C7, 700 #0077B6, 800 #023E8A, 900 #03045E |
| bg | canvas #F3F3F3, surface #FFFFFF, raised #E4F8FF, overlay #FFFFFF, hover #CAF0F8 |
| border | subtle #ADE8F4, strong #0077B6 |
| text | primary #03045E, secondary #383838, muted #525252, inverse #FFFFFF |
| track | cyan #00B4D8, cyan-dim #0077B6, simplified #48CAE4 |
| event | amber #F2B13C, amber-bg #33270F |
| alert | red #F0524F, red-bg #3A1616 (squawk 7500, 7600, 7700 only) |
| ok | green #4CC38A, green-bg #0F2E20 |
| cite | text #023E8A, bg #E4F8FF, border #90E0EF |
| focus | ring #0077B6 |
| action | primary #0077B6, hover #023E8A, pressed #03045E |

Note: `event/amber-bg`, `alert/red-bg` and `ok/green-bg` are dark tints on a light theme. Check them in the frames before use.

Type: Inter for text, JetBrains Mono for all data.
| Style | Font, size/line |
| --- | --- |
| Display | Inter Semi Bold 28/36 |
| H1 | Inter Semi Bold 20/28 |
| H2 | Inter Semi Bold 15/22 |
| Body | Inter Regular 14/20 |
| Body strong | Inter Medium 14/20 |
| Body small | Inter Regular 12/16 |
| Label | Inter Medium 11/16, sentence case (Figma calls it Caps; `ui.md` forbids all caps) |
| Data | JetBrains Mono Regular 13/20 |
| Data small | JetBrains Mono Regular 11/16 |
| Data number | JetBrains Mono Medium 32/40 |
| Data hex | JetBrains Mono Regular 12/20 |

Colour rule from Figma: white cards on a gray canvas; cyan is the track; amber is an event; red only for squawk; always pair colour with a label.
Citation chip: the signature element. Every claim has one, and it opens the raw record.

Mapping to the three point styles: kept = track/cyan, event window = track/simplified, flagged = event/amber. Point colours for squawk events use alert/red.

## Folders (all under `web/`)
```
web/
  package.json, vite.config.ts, tsconfig.json
  src/
    api/        client.ts  mockClient.ts  types.ts (re-export of contracts/types.ts)
    state/      store.ts   (selected event, aircraft, scrubber time, selected raw_ref)
    domain/     pointStyle.ts  derive.ts  window.ts  itemMeta.ts
    views/      Shell.tsx  MapView.tsx  ThreeDView.tsx  RecordsView.tsx
    components/ Scrubber.tsx  Charts.tsx  EventList.tsx  Legend.tsx  HexPane.tsx  RecordTree.tsx
    geo/        wiii-runway.geojson
    styles/     tokens.css
  tests/
```
`web/src/api/types.ts` only re-exports from `contracts/types.ts`. Never hand-edit the contract file.

## Data flow
```
mock API (fixtures/) -> api/client -> store -> views
                                        ^         |
                                 Scrubber time <--+
```
One store holds: `eventId`, `icao24`, `scrubTs`, `rawRef`, `eventStates` (browser storage).
All three views read `scrubTs` and `rawRef`. Only the scrubber writes `scrubTs`.

## Point style (R3.3)
`pointStyle(point, event)` returns `flagged | eventWindow | kept`.
- `flagged`: `ts` inside the event's `start_ts` to `end_ts` and `raw_ref` in `event.raw_refs`.
- `eventWindow`: `ts` inside the window but `raw_ref` not in `raw_refs`, or `kept_for_event` true.
- `kept`: everything else.
Colours come from tokens in `tokens.css`, taken from the Figma file.

## Derived values (R4.2)
- Speed: ground distance between two points (haversine, WGS-84 mean radius) over the time step. Shown in kt.
- Vertical rate: change in `alt_ft` over the time step. Shown in ft/min.
- Null `alt_ft` gives null. A step under 0.5 s gives null.
- Each chart title: "computed from positions".

## Scrubber (R4)
- Range is first to last point `ts` of the track.
- `scrubTs` snaps to the nearest point at or before the cursor.
- Charts draw the cursor and the flagged window shading from `scrubTs` and the event.

## Map (R3)
- MapLibre with a plain raster or vector basemap. WIII runway as a GeoJSON line layer, drawn from `web/src/geo/wiii-runway.geojson`.
- Points are a GeoJSON source with a `style` property. Layer paint uses a `match` on that property.
- Marker for `scrubTs`. Tooltip text built by `formatPoint()`.

## 3D (R5)
- three.js scene. X = lon, Y = lat (both scaled to metres around the track centre), Z = altitude times an exaggeration factor. Factor is shown on screen.
- Same style colours. A sphere marks `scrubTs`.

## Records (R6)
- `/api/raw/{raw_ref}` returns `decoded` (object) and `hex`.
- `RecordTree` builds Block > Record > Item. With one record per call, Block is the recording file id and the record index.
- `itemMeta.ts` maps I021 item numbers to name, unit, LSB and datum (for example I021/071 time of applicability for position). It is a static table. Items not in the table show the raw value only.
- Hex and ASCII panes show bytes in rows of 16 with an offset column. Item to byte ranges come from `decoded` if it carries offsets; otherwise the link highlights the record as a whole.
- Open question: does `decoded` carry item byte offsets? See requirements, open item 3.

## Event state (R3.8)
`To review` default. User action sets `Confirmed by you` or `Dismissed by you`. Stored in `localStorage` under `flightmind.eventStates`. No API call.

## Wording
All user text lives in `src/strings.ts` so the wording rules can be checked in one file. A test fails on the banned phrases "went around" and "no touchdown".

## Testing
- Unit tests (Vitest): `pointStyle`, `derive`, `window`, `itemMeta`.
- Component tests: Scrubber keyboard, HexPane highlight link.
- One smoke test: load the mock API, open each tab, no console errors.

## Risks
| Risk | Plan |
| --- | --- |
| Fixtures not ready | Use the SCRUM-33 mock API; mini.json covers unit tests. |
| Contract lacks block and offsets | Show what exists; open an issue for Role 1 contract change |
| 5,000 points slow in 3D | Use one buffer geometry, not one mesh per point |
