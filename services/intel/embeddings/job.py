"""embed_missing: give every event without an event_embeddings row a story and a vector (SCRUM-35)."""
import logging
from typing import Optional

from .embedder import Embedder, from_env
from .story import build_story

log = logging.getLogger("flightmind.embeddings")

BATCH = 50
EVENT_SQL = (
    "SELECT e.id, e.type, e.icao24, e.callsign, e.start_ts, e.end_ts, e.airport, e.lat, e.lon, e.severity, e.details "
    "FROM events e LEFT JOIN event_embeddings m ON m.event_id = e.id WHERE m.event_id IS NULL "
    "ORDER BY e.start_ts, e.id"
)
UPSERT_SQL = (
    "INSERT INTO event_embeddings (event_id, story, model, embedding) VALUES (%s, %s, %s, %s::vector) "
    "ON CONFLICT (event_id) DO UPDATE SET story = EXCLUDED.story, model = EXCLUDED.model, "
    "embedding = EXCLUDED.embedding"
)


def vector_literal(vector: list) -> str:
    """pgvector text form, so no extra Python package is needed."""
    return "[" + ",".join(repr(float(x)) for x in vector) + "]"


def embed_missing(conn, embedder: Optional[Embedder] = None) -> int:
    """Embed every event that has no row yet and upsert it. Returns how many rows were written.

    `conn` is a psycopg connection with dict rows (as real_api.db.connect gives). Without an
    embedder argument the Gemini one is used when a key is set; with no key nothing happens.
    """
    embedder = embedder or from_env()
    if embedder is None:
        return 0
    rows = conn.execute(EVENT_SQL).fetchall()
    written = 0
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        stories = [build_story(r) for r in chunk]
        vectors = embedder.embed(stories)
        for row, story, vector in zip(chunk, stories, vectors):
            conn.execute(UPSERT_SQL, (row["id"], story, embedder.model, vector_literal(vector)))
            written += 1
    if written:
        log.info("embedded %d event(s) with %s", written, embedder.model)
    return written
