# Design: compression

## Algorithm
Douglas-Peucker with synchronized Euclidean distance (SED). It runs offline, per track, after detection. Pinned refs come from the detectors, so the event guarantee is structural.

## Constants (`flightmind_pipeline/compress.py`)
- `EPU_M = {11: 3.0, 10: 10.0, 9: 30.0, 8: 92.6}`. NACp 1 to 7 use 92.6 (approved cap). NACp 0 and None are always kept. These values are unverified (see requirements).
- `VERTICAL_TOL_FT = 25`
- `ERR_SLACK = 1e-6`, used only by the tests.

## Interface
```
@dataclass(frozen=True)
class TrackCompression:
    kept: list[Point]
    kept_reason: dict[str, str]       # raw_ref -> event|endpoint|attribute_change|nacp_unknown|shape
    max_h_err_m: float
    max_v_err_ft: float
    max_ratio: float                  # 0.0 when nothing is dropped
    dropped_by_nacp: Counter[int]
    dropped_no_position: int

def compress_track(track: Sequence[Point], pinned: AbstractSet[str]) -> TrackCompression
```

## Steps
1. Drop non-pinned points without lat or lon. Pinned points are kept even without a position. They take no part in interpolation.
2. Mark anchors among positioned points. When a point has several reasons, the first in this order is recorded: `event`, `endpoint`, `attribute_change`, `nacp_unknown`. Null attribute values are ignored when comparing.
3. Between consecutive anchors, run Douglas-Peucker with an explicit stack (no recursion). For each interior point:
   - **Horizontal error:** `h = distance_m(p, interp)`. Interpolation is linear in time between the segment ends. If both ends share a timestamp, interp = the start point.
   - **Vertical error:** `v` = max over {geo, baro} of |value − interpolated value|. If the value is missing on the point, that term is 0. If it is missing on either end, the term is infinite.
   - **Ratio:** `ratio = max(h / EPU, v / 25)`.
   - If the largest ratio is > 1, keep that point (reason `shape`) and split the segment there. Otherwise drop all interior points and record their ratio, h, v and NACp.
4. `kept` is returned in the track's `(ts, record_index)` order.

Docstring contract: lat, lon and altitude are interpolated linearly in time between kept neighbours. There is no antimeridian handling (WIII is far from it).

## Decided boundaries
- Empty track → 0 kept. One point → 1 kept.
- Equal timestamps: interp = the start point. No division by zero.
- All points pinned → all kept, `max_ratio = 0.0`.
- Very large track: the explicit stack avoids hitting Python's recursion limit.
- NACp is not written to telemetry (approved pick 7). It appears only through `dropped_by_nacp` in the report.

## Not bounded
Ground speed, track and vertical rate of dropped points are not bounded. MOPS v0 aircraft get no NUCp mapping: with no NACp, every point is kept.

## Rejected
- SQUISH-E (online opening window): this is batch work, and Douglas-Peucker with SED gives the same per-point guarantee with less code.

