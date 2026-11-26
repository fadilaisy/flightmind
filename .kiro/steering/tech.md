---
inclusion: always
---
# Tech

- **Pipeline and intel services:** Python 3.12, type hints, `pytest` + Hypothesis for property tests.
- **Database:** one Postgres with TimescaleDB (time series) and pgvector (embeddings).
- **Web:** TypeScript. Types for API calls come only from `contracts/types.ts`, which is
  generated from `contracts/openapi.yaml`; never hand-edit it.
- **Time:** every service calls `clock.now()` (contract C6). Never read system time directly.
- **Evidence:** any row, event or answer that comes from data carries `raw_ref`
  (`<recording_file_id>:<record_index>`). Never drop it in a transform.
- **Raw bytes stay in the recording file.** The database stores the file id, record index
  and byte offset; `/api/raw/{raw_ref}` reads the bytes from the file on demand. This is what
  lets compression shrink storage without losing citations.
- Disclose every third-party library or API that does real work (ASTERIX decoder, LLM,
  embeddings) in the README.

## Third-party model APIs (Role 3, SCRUM-32)

- **LLM:** Anthropic Claude API, model `claude-haiku-5-5` (Claude Haiku 5.5), called with the
  official `anthropic` Python SDK, not an OpenAI-compatible shim. Key via `ANTHROPIC_API_KEY`
  (never committed; on the deployed site it is a server-side env var, never in the web
  bundle). The model id is read from `FLIGHTMIND_LLM_MODEL` (default `claude-haiku-5-5`) so it
  can change without a code change. Set effort per route: `low` for event stories,
  `medium` for cited agent answers. Keep prompts under 100K tokens (Haiku 5.5 costs more
  above that). Changed on 2026-11-26 from `gemini-3-8-flash` through the Coarena gateway;
  no LLM code existed yet.
- **Budget:** the API credit is a fixed $100 that will not be refilled. Log `usage` (input,
  output and cache tokens) for every call so real cost per answer is measured, not guessed.
  Before recording the video, run the same hard questions on `claude-opus-5-5` and switch
  `FLIGHTMIND_LLM_MODEL` only if the answers are clearly better and the measured cost fits.
- **Public demo guard:** `/api/ask` on the public URL must be rate-limited (SCRUM-36), and the
  Claude Console keeps a spend limit with auto-reload off, so visitors cannot drain the
  $100 API credit.
- **Embeddings:** Google `gemini-embedding-001`, called with `output_dimensionality=1024`
  so vectors fit the existing `event_embeddings.embedding = vector(1024)` without changing
  the contract. Key via `GEMINI_API_KEY`. Embeddings are L2-normalized before storage,
  because Gemini only returns unit-length vectors at the native 3072 dims.
- Both must appear in the README third-party disclosure list, noting that
  `output_dimensionality=1024` applies to the embedding model.
