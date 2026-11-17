# services/intel

Role 3 (Zahran). Stories, embeddings, agent, MCP server, HTTP API.

## Mock API (SCRUM-33)

Serves every path in `contracts/openapi.yaml` from **synthetic** data in
`mock_api/data.py` (4 aircraft, 270 records, 4 events: 2 go-arounds, 1 holding, 1 squawk 7700).
The raw hex is shape-only, not valid ASTERIX. Every `raw_ref` in a track or event opens
through `/api/raw/{raw_ref}`.

```powershell
cd services/intel
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn mock_api.app:app --port 8000
```

Test (checks each response against `openapi.yaml`):

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Notes for the UI:

- CORS is open to any origin (mock only).
- `/api/stream` is a finite replay. The contract does not define its payload; the mock
  sends `event: position` and `event: event` records (see the docstring in `app.py`).
  Speed is set with `MOCK_STREAM_DELAY` seconds between items (default 0.05).
- `/api/ask` answers by keyword (7700 / go-around / hold) and otherwise returns
  `not_enough_evidence`. The real agent is SCRUM-36.
