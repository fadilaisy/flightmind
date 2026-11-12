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
