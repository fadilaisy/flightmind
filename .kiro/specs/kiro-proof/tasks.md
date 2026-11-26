# Tasks: kiro-proof (SCRUM-70)

Tick a box only when the check passes. After each ticked task, add a line to `KIRO.md`.

- [x] 0. Spec
  - Files: `.kiro/specs/kiro-proof/requirements.md`, `design.md`, `tasks.md`
  - Check: requirements are in EARS style and cite SCRUM-70.

- [x] 1. Trailer check
  - Files: `.githooks/commit-msg`, `scripts/install-hooks`, `.kiro/hooks/commit-trailer.kiro.hook`
  - Check: `git commit --allow-empty -m "test"` is refused after `scripts/install-hooks`.
  - Reqs: R1, R2, R3, R4

- [x] 2. Backfill and stats
  - Files: `KIRO.md` (Trailer corrections), `scripts/kiro-stats`
  - Check: `scripts/kiro-stats` prints `commits_unclassified=0`.
  - Reqs: R5

- [x] 3. Session logs
  - Files: `scripts/kiro-sessions-export`, `docs/kiro/sessions/cli/`, `docs/kiro/sessions/prompts/`
  - Check: second run changes no file; grep for `Pongo`, `@gmail`, `sk-`, `AKIA`, `ghp_`, `BEGIN` finds nothing.
  - Reqs: R6

- [x] 4. Timeline data
  - Files: `scripts/kiro-timeline.mjs`, `web/src/domain/kiroTimeline.ts`, `web/src/kiro/timeline.json`, `web/tests/kiroTimeline.test.ts`
  - Check: tests cover `spec web-ui/3`, `spec agent-mcp/10-21`, a `missing` correction and task counting.
  - Reqs: R7

- [ ] 5. Built with Kiro page
  - Files: `web/src/views/KiroView.tsx`, `web/src/strings.ts`, `web/src/views/Shell.tsx`, `web/src/App.tsx`, `web/tests/kiro.test.tsx`
  - Check: `npm test` and `npm run build` in `web/` pass; `?tab=kiro` renders without a recording.
  - Reqs: R8, R9

- [ ] 6. KIRO.md as the index
  - Files: `KIRO.md`, `docs/kiro/README.md`, `web/src/kiro/timeline.json`
  - Check: Evidence section links resolve; timeline regenerated; tests and build pass.
  - Reqs: R10
