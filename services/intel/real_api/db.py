"""Postgres access for the real API (SCRUM-37). The connection string is FLIGHTMIND_DSN."""
import os
from contextlib import contextmanager
from typing import Iterator

from fastapi import HTTPException


def dsn() -> str:
    value = os.environ.get("FLIGHTMIND_DSN", "").strip()
    if not value:
        raise HTTPException(status_code=503, detail="The database is not configured (FLIGHTMIND_DSN is not set).")
    return value


@contextmanager
def connect() -> Iterator["object"]:
    """One autocommit connection with dict rows. psycopg is imported here so the mock needs none."""
    target = dsn()  # first, so a missing DSN is a clear 503 even without psycopg installed
    import psycopg
    from psycopg.rows import dict_row

    try:
        conn = psycopg.connect(target, autocommit=True, row_factory=dict_row, connect_timeout=5)
    except psycopg.OperationalError:
        raise HTTPException(status_code=503, detail="The database is not reachable.") from None
    try:
        yield conn
    finally:
        conn.close()


def prefix_clause(column: str) -> str:
    """SQL that keeps rows of one recording: column starts with '<id>:'. Takes the id twice."""
    return f"left({column}, length(%s) + 1) = %s || ':'"
