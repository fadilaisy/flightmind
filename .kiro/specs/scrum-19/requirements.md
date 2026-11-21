# Requirements: SCRUM-19 Kiro hooks and data-quality-reviewer agent

Source: Jira SCRUM-19 and `docs/kiro/setup-prompts.md`. Owner: Fadil. Folders: `.kiro/hooks/`, `.kiro/agents/`.

## Requirements
1. Four hooks exist in `.kiro/hooks/`, one file each, as in `setup-prompts.md`: log ticked task, regenerate contract types, pipeline property tests, raw_ref guard.
2. One custom agent `data-quality-reviewer` exists in `.kiro/agents/`. It reviews `services/pipeline` and `contracts`, and does not edit code.
3. The agent checks four things: no dropped `raw_ref` or `raw_refs`; compression keeps every point in an event's `raw_refs`; time comes from `clock.now()`; no new use of `weather_reports`.
4. Each hook changes only what its prompt allows. The log hook edits only `KIRO.md`.
5. Hooks do not touch `contracts/` except the types hook, which writes only `contracts/types.ts` by running the generator.
6. The first hook creation is screen-recorded and listed in `docs/kiro/clips.md`.
7. We build in Kiro Crew, which does not read `.kiro/hooks/`. A Crew `Stop` hook (`scripts/crew-hooks/contract-types-guard.py`) blocks the end of a turn once if `contracts/openapi.yaml` changed and `contracts/types.ts` was not regenerated. The four IDE hooks stay for teammates on the Kiro IDE.

## Not in scope
- Pipeline code, spec generation for other roles, any change to `contracts/openapi.yaml`.

## Open items
1. The ticket says to create the files inside Kiro so they are in Kiro's own format. These were written by hand in the documented format. Re-save them from the Agent Hooks panel if Kiro rewrites them.
2. The screen recording needs a person at the Kiro IDE (requirement 6).
3. The log hook uses names, not roles: Fadil, Koolkar, Zahran. The name comes from a spec-folder mapping inside the prompt, because `.github/CODEOWNERS` still has placeholder usernames for Role 2 and Role 3. Older `KIRO.md` rows keep `Role N`.
4. The log hook compares with `git diff` and skips a spec/task that already has a line.
5. The raw_ref guard also fires on test files. If that gets noisy, narrow its pattern.
