# Prompts to set up Kiro (run these inside Kiro)

Create each hook from Kiro's Agent Hooks panel and each spec from the Specs panel, so the
files Kiro writes in `.kiro/hooks/` and `.kiro/specs/<name>/` are in Kiro's own format.
Commit them as they are.

## Hooks (Role 1)

1. **Log ticked task.** Trigger: file saved, pattern `.kiro/specs/**/tasks.md`.
   Prompt: "A spec task was just ticked in this tasks.md. Append exactly one line to
   KIRO.md under the current week, in the format
   `date | role | spec/task | what Kiro did | fixed by hand`. Take the role from
   .github/CODEOWNERS. If you cannot tell what was fixed by hand, write `TODO`. Change no
   other file."
2. **Regenerate contract types.** Trigger: file saved, pattern `contracts/openapi.yaml`.
   Action: run command `npx openapi-typescript contracts/openapi.yaml -o contracts/types.ts`
   if this Kiro version offers a command action; otherwise ask the agent to run it and change
   nothing else.
3. **Pipeline property tests.** Trigger: file saved, pattern `services/pipeline/**/*.py`.
   Action: run `pytest services/pipeline -q` (command action if available).
4. **raw_ref guard.** Trigger: file saved, pattern `services/**/*.py`.
   Prompt: "Check only the saved file. If any function that returns telemetry points,
   events or citations can drop `raw_ref` / `raw_refs`, say where in one line. Otherwise
   say nothing and change nothing."

## Custom agent: data-quality reviewer (Role 1)

"Create a custom agent called data-quality-reviewer. Its job: review changes under
services/pipeline and contracts. It must (1) reject any change that can drop raw_ref or
raw_refs, (2) check that compression keeps every point listed in an event's raw_refs,
(3) check that time comes from clock.now(), (4) flag any new dependency on
weather_reports. It reviews and comments; it does not edit code."

## Specs (each owner, one generation, then edit by hand)

| Spec | Owner | First prompt |
| --- | --- | --- |
| ingest | Role 2 | "Read and index ASTERIX CAT021 recording files into the telemetry table (contract C1), with raw_ref and raw_offset on every row, and a replay Source on the shared clock. Include a property test that decode then encode round-trips." |
| compression | Role 2 | "Reduce stored telemetry points per track while keeping every point that belongs to an event, with a bounded position error. Report raw bytes versus stored bytes per recording." |
| detectors | Role 2 | "Detect go-around, holding and emergency squawk 7500/7600/7700 from telemetry, writing to events (C3) with raw_refs for every record used." |
| storage | Role 2 | "Schema, migrations and retention for contracts/schema.sql on Timescale." |
| web-ui | Role 1 | "A 4D trajectory view (lat, lon, altitude, time scrubber) as the first screen, then the event feed and an investigation panel where every citation opens /api/raw/{raw_ref}." |
| embeddings | Role 3 | "Write an event story per event and embed it into event_embeddings (C4); vector search with type and time filters." |
| agent-mcp | Role 3 | "An agent with four tools (query_tracks, search_events, get_track, get_raw) that answers with citations of kind cat021_record or event, or status not_enough_evidence; expose the same tools as an MCP server." |
| api-deploy | Role 3 | "Serve contracts/openapi.yaml with a mock from fixtures first, then the real implementation; Docker Compose and the public replay URL." |
