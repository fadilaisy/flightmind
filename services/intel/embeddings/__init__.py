"""Event stories, embeddings and similar-event search (SCRUM-35, contract C4)."""
from .embedder import DIMENSIONS, Embedder, EmbeddingError, FakeEmbedder, GeminiEmbedder, from_env, l2_normalize
from .job import embed_missing
from .search import UnknownEvent, search_similar
from .story import build_story

__all__ = [
    "DIMENSIONS", "Embedder", "EmbeddingError", "FakeEmbedder", "GeminiEmbedder", "UnknownEvent",
    "build_story", "embed_missing", "from_env", "l2_normalize", "search_similar",
]
