---
inclusion: always
---
# Structure

One folder per owner. Only the owner asks Kiro to write code in their folder; anyone else
opens an issue.

| Path | Owner |
| --- | --- |
| `.kiro/steering/`, `.kiro/hooks/`, `.kiro/agents/`, `web/`, `docs/`, `README.md`, `KIRO.md` | Role 1 |
| `services/pipeline/`, `fixtures/`, specs `ingest`, `compression`, `detectors`, `storage` | Role 2 |
| `services/intel/`, `infra/`, specs `embeddings`, `agent-mcp`, `api-deploy` | Role 3 |
| `contracts/` | Role 1 approves; producer and consumer review |

Rules
- Specs live in `.kiro/specs/<name>/` (requirements, design, tasks) and are generated in Kiro.
- `data/` holds full recordings and is gitignored. Never gitignore `.kiro/`.
- No new top-level folders without Role 1.
- Every commit ends with a `Kiro:` trailer (see `.gitmessage`).
