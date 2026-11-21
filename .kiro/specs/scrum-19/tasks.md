# Tasks: SCRUM-19

- [x] 1. Log ticked task hook
  - Files: `.kiro/hooks/log-ticked-task.kiro.hook`
  - Check: valid JSON; trigger is `.kiro/specs/**/tasks.md`; prompt allows one `KIRO.md` line and no other change.

- [x] 2. Contract types and property test hooks
  - Files: `.kiro/hooks/regenerate-contract-types.kiro.hook`, `.kiro/hooks/pipeline-property-tests.kiro.hook`
  - Check: valid JSON; commands match `setup-prompts.md`; the types command writes only `contracts/types.ts`.

- [x] 3. raw_ref guard hook
  - Files: `.kiro/hooks/raw-ref-guard.kiro.hook`
  - Check: valid JSON; prompt says to check only the saved file and change nothing.

- [x] 4. data-quality-reviewer agent
  - Files: `.kiro/agents/data-quality-reviewer.json`
  - Check: valid JSON; no write tool listed; the four checks are in the prompt.

- [x] 5. Crew Stop hook script
  - Files: `scripts/crew-hooks/contract-types-guard.py`, `docs/kiro/setup-prompts.md`
  - Check: clean tree prints nothing; changed `openapi.yaml` without new `types.ts` prints one block; same state again prints nothing; always exits 0.

- [ ] 6. Create the Crew hook in the dashboard on a screen recording (person needed)
  - Files: `docs/kiro/clips.md`
  - Check: a row with the clip file name, date and "Crew Stop hook"; the clip shows the agent getting blocked once and running the generator.
