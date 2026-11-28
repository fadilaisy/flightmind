"""Embedders (SCRUM-35, contract C4): Google gemini-embedding-001 at 1024 dimensions, L2-normalized.

`Embedder` is the interface; `GeminiEmbedder` calls the Gemini REST API, `FakeEmbedder` is a
deterministic stand-in for tests that needs no key and no network. The key is read from
GOOGLE_API_KEY, else GEMINI_API_KEY, and goes only in a request header: it is never logged
and never put in an error message.
"""
import hashlib
import math
import os
import re
from typing import Optional, Protocol

import httpx

DIMENSIONS = 1024
GEMINI_MODEL = "gemini-embedding-001"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:batchEmbedContents"
BATCH_SIZE = 100  # the API accepts at most 100 texts per batch call
TIMEOUT_SECONDS = 30.0


class EmbeddingError(Exception):
    """An embedding call failed. The message is safe to log."""


class Embedder(Protocol):
    model: str

    def embed(self, texts: list) -> list:
        """One L2-normalized vector of DIMENSIONS floats per text, in order."""
        ...


def l2_normalize(vector: list) -> list:
    """Scale to unit length. Gemini returns unit vectors only at its native 3072 dimensions."""
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0 or not math.isfinite(norm):
        raise EmbeddingError("The embedding has zero length and cannot be normalized.")
    return [x / norm for x in vector]


def api_key() -> Optional[str]:
    for name in ("GOOGLE_API_KEY", "GEMINI_API_KEY"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


class GeminiEmbedder:
    model = GEMINI_MODEL

    def __init__(self, key: str, *, transport: Optional[httpx.BaseTransport] = None, url: str = GEMINI_URL) -> None:
        self._key = key
        self._transport = transport
        self._url = url

    def embed(self, texts: list) -> list:
        out: list = []
        for i in range(0, len(texts), BATCH_SIZE):
            out.extend(self._batch(texts[i:i + BATCH_SIZE]))
        return out

    def _batch(self, texts: list) -> list:
        body = {
            "requests": [
                {
                    "model": f"models/{GEMINI_MODEL}",
                    "content": {"parts": [{"text": t}]},
                    "taskType": "SEMANTIC_SIMILARITY",
                    "outputDimensionality": DIMENSIONS,
                }
                for t in texts
            ]
        }
        try:
            with httpx.Client(timeout=TIMEOUT_SECONDS, transport=self._transport) as client:
                response = client.post(self._url, json=body, headers={"x-goog-api-key": self._key})
        except httpx.HTTPError as exc:
            raise EmbeddingError(f"The Gemini embedding call failed ({type(exc).__name__}).") from None
        if response.status_code != 200:
            raise EmbeddingError(f"The Gemini embedding call answered {response.status_code}.")
        try:
            vectors = [e["values"] for e in response.json()["embeddings"]]
        except (ValueError, KeyError, TypeError):
            raise EmbeddingError("The Gemini embedding response was not in the expected shape.") from None
        if len(vectors) != len(texts) or any(len(v) != DIMENSIONS for v in vectors):
            raise EmbeddingError(f"Expected {len(texts)} vectors of {DIMENSIONS} numbers from Gemini.")
        return [l2_normalize([float(x) for x in v]) for v in vectors]


class FakeEmbedder:
    """Deterministic bag-of-words vectors: texts that share words get a high cosine similarity."""

    model = "fake-embedder"

    def embed(self, texts: list) -> list:
        return [self._one(t) for t in texts]

    @staticmethod
    def _one(text: str) -> list:
        vector = [0.0] * DIMENSIONS
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            vector[int.from_bytes(digest[:4], "big") % DIMENSIONS] += 1.0 if digest[4] & 1 else -1.0
        if not any(vector):
            vector[0] = 1.0  # an empty text still gets a valid unit vector
        return l2_normalize(vector)


def from_env() -> Optional[Embedder]:
    """The Gemini embedder when a key is set, else None (callers skip quietly)."""
    key = api_key()
    return GeminiEmbedder(key) if key else None
