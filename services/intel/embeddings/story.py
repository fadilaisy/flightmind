"""Event story builder (SCRUM-35): one event row in, one short plain-English story out.

The story is what gets embedded (contract C4, event_embeddings.story), so it is built only
from the row: type, aircraft, times, airport, severity and the key numbers in `details`. It
is deterministic and uses no LLM and no system time. A number the row does not have is left
out, never guessed.
"""
from datetime import datetime, timezone
from typing import Any, Optional

SQUAWK_MEANING = {
    "7500": "unlawful interference",
    "7600": "radio failure",
    "7700": "general emergency",
}


def _dt(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def _num(value: Any) -> Optional[float]:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _ft(value: Any) -> Optional[str]:
    n = _num(value)
    return None if n is None else f"{round(n):,} ft"


def _duration(seconds: float) -> str:
    seconds = max(0, round(seconds))
    if seconds < 90:
        return f"{seconds} s"
    minutes = seconds / 60
    return f"{round(minutes)} min" if minutes >= 10 else f"{minutes:.1f} min"


def _who(event: dict) -> str:
    callsign = (event.get("callsign") or "").strip()
    icao = (event.get("icao24") or "").strip().upper()
    if callsign and icao:
        return f"{callsign} (icao24 {icao})"
    return callsign or (f"aircraft {icao}" if icao else "an aircraft")


def _when(event: dict) -> tuple:
    start, end = _dt(event.get("start_ts")), _dt(event.get("end_ts"))
    text = f"on {start:%Y-%m-%d} at {start:%H:%M} UTC" if start else ""
    seconds = (end - start).total_seconds() if start and end else None
    return text, seconds


def build_story(event: dict) -> str:
    """A short plain-English story for one events row (a dict with the events columns)."""
    kind = str(event.get("type") or "event")
    details = event.get("details") or {}
    if not isinstance(details, dict):
        details = {}
    who = _who(event)
    when, seconds = _when(event)
    airport = (event.get("airport") or "").strip()
    near = f" near {airport}" if airport else ""
    sentences: list = []

    if kind == "go_around":
        runway = details.get("runway")
        head = f"Go-around{' at ' + airport if airport else ''}: {who} broke off its approach"
        head += f" to runway {runway}" if runway else ""
        sentences.append(" ".join(p for p in (head, when) if p) + ".")
        low = _num(details.get("min_hat_ft"))
        if low is not None:
            text = f"It came down to {round(low):,} ft above the runway"
            rebound = _num(details.get("rebound_ft"))
            text += f" and then climbed {round(rebound):,} ft" if rebound is not None else ""
            sentences.append(text + ".")
        vrate = _num(details.get("max_vrate_fpm"))
        if vrate is not None:
            sentences.append(f"Its best climb rate was {round(vrate):,} ft/min.")
    elif kind == "holding":
        head = f"Holding pattern{near}: {who} flew racetrack turns"
        sentences.append(" ".join(p for p in (head, when) if p) + ".")
        parts = []
        circuits = details.get("circuits")
        if isinstance(circuits, int):
            parts.append(f"{circuits} circuit{'s' if circuits != 1 else ''}")
        if details.get("direction") in ("left", "right"):
            parts.append(f"{details['direction']}-hand turns")
        span = _num(details.get("duration_s"))
        span = span if span is not None else seconds
        if span is not None:
            parts.append(f"{_duration(span)} in the pattern")
        low, high = _ft(details.get("min_alt_ft")), _ft(details.get("max_alt_ft"))
        if low and high:
            parts.append(f"between {low} and {high}")
        if parts:
            sentences.append("It made " + ", ".join(parts) + ".")
    elif kind.startswith("squawk_"):
        code = str(details.get("code") or kind.split("_", 1)[1])
        meaning = SQUAWK_MEANING.get(code)
        head = f"Emergency squawk {code}{' (' + meaning + ')' if meaning else ''}{near}: {who} transmitted {code}"
        sentences.append(" ".join(p for p in (head, when) if p) + ".")
        parts = []
        if seconds is not None:
            parts.append(f"for {_duration(seconds)}")
        alt = _ft(details.get("alt_ft"))
        if alt:
            kind_word = {"pressure": "pressure ", "geometric": "geometric "}.get(details.get("alt_kind"), "")
            parts.append(f"at {alt} {kind_word}altitude")
        records = details.get("records_with_code")
        if isinstance(records, int):
            parts.append(f"in {records} record{'s' if records != 1 else ''}")
        if parts:
            sentences.append("The code was seen " + ", ".join(parts) + ".")
    else:
        head = f"{kind.replace('_', ' ').capitalize()}{near}: {who}"
        sentences.append(" ".join(p for p in (head, when) if p) + ".")

    severity = event.get("severity")
    if isinstance(severity, int) and not isinstance(severity, bool):
        sentences.append(f"Severity {severity}.")
    return " ".join(sentences)
