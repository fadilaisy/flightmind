# Tasks: SCRUM-35

- [x] 1. Story builder `embeddings/story.py` and its tests
- [x] 2. `Embedder` interface, `GeminiEmbedder` (REST, 1024 dimensions, key from `GOOGLE_API_KEY` or `GEMINI_API_KEY`), `FakeEmbedder`, L2 normalization
- [x] 3. `embed_missing(conn)` upserting into `event_embeddings`
- [x] 4. Call `embed_events` after a recording is ready in `real_api/uploads.py`; quiet skip without a key
- [x] 5. `search_similar` with pgvector `<=>` and type and time filters
- [x] 6. `GET /api/events/{id}/similar` in the real API and the mock API
- [x] 7. `contracts/openapi.yaml` 1.3.0 (path and `SimilarEvent`), `types.ts` regenerated
- [x] 8. Tests: story, normalization, Gemini request shape, mock endpoint, openapi path
- [ ] 9. Run the database tests (`embed_missing`, `search_similar`) against Postgres with pgvector; they skip without `FLIGHTMIND_TEST_DSN`
- [ ] 10. Follow-up: `find_similar_events` agent tool (see design.md)
- [ ] 11. Follow-up: run `embed_missing` once on a real recording with a real key and check three searches by eye
