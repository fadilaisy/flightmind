# Design: SCRUM-35

Package `services/intel/embeddings/`:

| Module | Content |
| --- | --- |
| `story.py` | `build_story(event: dict) -> str`. One branch per type (go_around, holding, squawk_*), a generic fallback, one trailing "Severity N." |
| `embedder.py` | `Embedder` protocol (`model`, `embed(texts)`), `GeminiEmbedder` (REST `batchEmbedContents`, 100 texts per call, `taskType` SEMANTIC_SIMILARITY, `outputDimensionality` 1024, key in `x-goog-api-key`), `FakeEmbedder` (hashed bag of words, unit length), `l2_normalize`, `from_env()` (None without a key) |
| `job.py` | `embed_missing(conn, embedder=None)`: `events LEFT JOIN event_embeddings`, batches of 50, upsert with `%s::vector` text literal (no `pgvector` Python package needed) |
| `search.py` | `search_similar(...)`: `ORDER BY embedding <=> query`, `similarity = 1 - distance`, filters on `type` and `start_ts`; event_id path reads the stored vector, or embeds the story on the fly when an embedder exists |

Wiring:
- `real_api/uploads.py`: `embed_events(recording_id)` after `_set_ready`; never raises.
- `real_api/app.py`: `GET /api/events/{id}/similar` (k 1 to 50).
- `mock_api/app.py`: same path, same type, nearest `start_ts`; imports nothing from `embeddings`, so the Docker image is unchanged.
- `contracts/openapi.yaml` 1.3.0: the path and `SimilarEvent` (Event plus optional `similarity`); `types.ts` regenerated.

Decisions
- Same model for stories and queries, so one task type. Normalizing in Python keeps vectors unit length at 1024 dimensions.
- No ANN index yet: the table holds one row per event, so an exact scan is fast enough.
- `similarity` is optional so the mock can stay honest about having no embeddings.

Follow-up (not done): a `find_similar_events` agent tool. The four-tool list is pinned by tests in `test_agent_tools.py`, `test_agent_loop.py`, `test_agent_mcp.py` and `test_mcp_server.py`, and the agent's citation rule needs a decision on how similar events count as evidence. Do it as its own ticket.
