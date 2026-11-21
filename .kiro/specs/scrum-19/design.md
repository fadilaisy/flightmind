# Design: SCRUM-19

## Files
| File | Trigger | Action |
| --- | --- | --- |
| `.kiro/hooks/log-ticked-task.kiro.hook` | file edited, `.kiro/specs/**/tasks.md` | ask agent: append one line to `KIRO.md` |
| `.kiro/hooks/regenerate-contract-types.kiro.hook` | file edited, `contracts/openapi.yaml` | run `npx --yes openapi-typescript@7 contracts/openapi.yaml -o contracts/types.ts` |
| `.kiro/hooks/pipeline-property-tests.kiro.hook` | file edited, `services/pipeline/**/*.py` | run pytest through a small `python -c` wrapper that treats exit code 5 (no tests collected) as success |
| `.kiro/hooks/raw-ref-guard.kiro.hook` | file edited, `services/**/*.py` | ask agent: check the saved file only |
| `.kiro/agents/data-quality-reviewer.json` | chosen by hand | read-only review |
| `scripts/crew-hooks/contract-types-guard.py` | Kiro Crew `Stop` event (set in the Crew dashboard) | print `{"decision": "block", "reason": ...}` once if `openapi.yaml` changed without regenerating `types.ts`; always exit 0 |

## Hook format
JSON with `name`, `description`, `version`, `when` (type and patterns) and `then` (type and prompt or command).

## Reviewer agent
- Tools: read, grep and glob only. No write tool, so it cannot edit code.
- Prompt: the four checks from `setup-prompts.md`, each reported as pass, fail or not applicable, with file and line.

## Log line format
`date | name | spec/task | what Kiro did | fixed by hand`, under the current week in `KIRO.md`. Role comes from `.github/CODEOWNERS` and is written as the person's name.

## Risks
| Risk | Plan |
| --- | --- |
| Crew Stop hook loops forever | Script remembers the last blocked contract state in the temp folder and blocks only once per state |
| Crew hook runs in an unknown folder | The repo path is passed as an argument; the script stays silent if it is not this repo |
| Log hook fires when a task is unticked | Prompt says: act only if a box changed from open to ticked |
| Types hook rewrites `contracts/types.ts` by hand edit | Command only; never an agent edit |
| `pytest` missing on a machine | The hook fails loudly; nothing else changes |
