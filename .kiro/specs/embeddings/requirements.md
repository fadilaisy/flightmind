# Requirements: SCRUM-35 event stories, embeddings and similar-event search

Role 3. Contract C4 (`event_embeddings`, `contracts/schema.sql`) and one new C5 path.

1. **Story.** Each event row (type, aircraft, times, airport, severity, key numbers in `details`) becomes a short plain-English story. Built from the row only, deterministic, no LLM, no system time. A number the row lacks is left out.
2. **Embedding.** Stories are embedded with Google `gemini-embedding-001` at `output_dimensionality=1024`, L2-normalized, and stored in `event_embeddings(event_id, story, model, embedding vector(1024))`. The key comes from `GOOGLE_API_KEY` or `GEMINI_API_KEY`, is sent in a header, and is never logged or put in an error.
3. **Job.** `embed_missing(conn)` embeds every event without a row and upserts. It runs again after a recording becomes `ready` in the real API worker. With no key it skips quietly. A failure is logged and never fails the recording.
4. **Search.** `search_similar(conn, event_id | text, k=5, type, since, until)` ranks by pgvector cosine distance (`<=>`), filters on type and on `start_ts`, and never returns the query event.
5. **API.** `GET /api/events/{id}/similar?k&type&since&until` returns events nearest first, each with `similarity` (1 minus cosine distance). 404 for an unknown id; an empty list when the event has no stored embedding and no key is set. The mock API returns nearby events of the same type, without `similarity`. Contract version 1.3.0 (minor, additive).
6. **Tests.** Story text, normalization, `embed_missing` with a fake embedder, the mock endpoint and the openapi path. No test calls Gemini. Database tests skip without Postgres.

Out of scope: re-embedding when a story changes, an index on the vector column, cross-recording scoping.
