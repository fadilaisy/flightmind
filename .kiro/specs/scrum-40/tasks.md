# Tasks: SCRUM-40

- [x] 1. Domain helpers
  - Files: `web/src/domain/eventState.ts`, `hex.ts`, `citations.ts`, `eventLabels.ts`, `web/tests/domain.test.ts`
  - Check: tests pass for state default and save, hex rows with offset and ASCII, bad hex, raw_ref parse.
  - Reqs: R2, R7, R10

- [x] 2. API ask call
  - Files: `web/src/api/client.ts`, `web/src/api/mockClient.ts`, `web/tests/api.test.ts`
  - Check: `ask(question)` returns `AskResponse`; mock returns `not_enough_evidence` for an unknown question.
  - Reqs: R5

- [ ] 3. Event feed
  - Files: `web/src/components/EventFeed.tsx`
  - Check: lists events with the three states; clicking a state changes it and it survives a reload; build passes.
  - Reqs: R1, R2

- [ ] 4. Citation chip and raw record viewer
  - Files: `web/src/components/CitationChip.tsx`, `RawRecordViewer.tsx`
  - Check: viewer shows raw_ref, sac, sic, decoded table, hex rows with ASCII; 404 shows "Record not found: <raw_ref>"; build passes.
  - Reqs: R6, R7, R8, R9

- [ ] 5. Investigation panel and app wiring
  - Files: `web/src/components/InvestigationPanel.tsx`, `web/src/App.tsx`, `web/src/main.tsx`
  - Check: selecting an event shows its window and chips; ask shows answer and chips or "Not enough evidence"; against the SCRUM-33 mock API, a chip opens the record.
  - Reqs: R3, R4, R5, R6, R10

- [x] 6. Wording check
  - Files: `web/tests/wording.test.ts`
  - Check: no "went around", "no touchdown" or all-caps labels in `web/src`.
  - Reqs: R10
