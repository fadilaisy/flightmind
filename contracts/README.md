# Contracts

- `schema.sql`: C1 to C4 (tables).
- `openapi.yaml`: C5 (HTTP API).
- `types.ts`: generated, never edited by hand:
  `npx openapi-typescript contracts/openapi.yaml -o contracts/types.ts`
  (a Kiro hook runs this whenever `openapi.yaml` is saved).
- C6 (the clock) is a code interface in `services/`, described in
  `.kiro/steering/data-contracts.md`.
