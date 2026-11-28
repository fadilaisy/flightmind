"""Similar-event search over event_embeddings with pgvector cosine distance (SCRUM-35)."""
import uuid
from datetime import datetime
from typing import Optional

from .embedder import Embedder, from_env
from .job import vector_literal
from .story import build_story

COLUMNS = "e.id, e.type, e.icao24, e.callsign, e.start_ts, e.end_ts, e.airport, e.severity, e.raw_refs"
MAX_K = 50


class UnknownEvent(LookupError):
    """No events row has this id."""


def search_similar(
    conn,
    event_id: Optional[str] = None,
    text: Optional[str] = None,
    k: int = 5,
    type: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    embedder: Optional[Embedder] = None,
) -> list:
    """The k events whose stories are closest to an event or to free text, nearest first.

    Give exactly one of event_id and text. Each result is an events row plus `similarity`
    (1 minus the cosine distance, <=>). With event_id the event itself is left out. `type`
    filters on event type; `since` and `until` on start_ts (inclusive). An event that has no
    stored embedding is embedded on the fly when an embedder is available, else the result
    is empty. Raises UnknownEvent for an event_id that does not exist.
    """
    if (event_id is None) == (text is None):
        raise ValueError("Give exactly one of event_id and text.")
    k = max(1, min(int(k), MAX_K))
    if event_id is not None:
        try:
            uuid.UUID(str(event_id))
        except ValueError:
            raise UnknownEvent(event_id) from None
        row = conn.execute(
            "SELECT e.*, m.embedding::text AS vec FROM events e "
            "LEFT JOIN event_embeddings m ON m.event_id = e.id WHERE e.id = %s",
            (event_id,),
        ).fetchone()
        if row is None:
            raise UnknownEvent(event_id)
        query_vec = row["vec"]
        if query_vec is None:
            embedder = embedder or from_env()
            if embedder is None:
                return []
            query_vec = vector_literal(embedder.embed([build_story(row)])[0])
    else:
        embedder = embedder or from_env()
        if embedder is None:
            return []
        query_vec = vector_literal(embedder.embed([text])[0])

    where, args = [], [query_vec]
    if event_id is not None:
        where.append("e.id <> %s")
        args.append(event_id)
    if type:
        where.append("e.type = %s")
        args.append(type)
    if since is not None:
        where.append("e.start_ts >= %s")
        args.append(since)
    if until is not None:
        where.append("e.start_ts <= %s")
        args.append(until)
    sql = (
        f"SELECT {COLUMNS}, 1 - (m.embedding <=> %s::vector) AS similarity "
        "FROM event_embeddings m JOIN events e ON e.id = m.event_id "
        + ("WHERE " + " AND ".join(where) + " " if where else "")
        + "ORDER BY m.embedding <=> %s::vector, e.start_ts, e.id LIMIT %s"
    )
    return conn.execute(sql, [*args, query_vec, k]).fetchall()
