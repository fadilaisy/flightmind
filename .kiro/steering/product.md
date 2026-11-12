---
inclusion: always
---
# Product

FlightMind helps an air traffic data analyst work with **recorded** ASTERIX CAT021
(ADS-B) files, offline and in batch. It is not a live-traffic tool.

## The user
An analyst who receives raw CAT021 recordings. Today they fight data volume, and they
learn about unusual events from ATC reports instead of finding them in the data.

## What we ship (headline)
1. **4D trajectory view:** lat, lon, altitude and time for any aircraft, with a time scrubber.
   This is the first screen.
2. **Event-keeping compression:** store far fewer points than the raw file while keeping
   every point that belongs to a detected event. Always report the before/after size.
3. **Automatic detection:** go-around, holding, emergency squawk (7500, 7600, 7700).
4. **Cited summaries:** every claim in an AI answer links to the CAT021 record(s) behind it
   through `raw_ref`. If the data does not support an answer, say "not enough evidence".

## Side features (only after the headline works)
- Similar past events (vector search).
- Forkable replay: branch a recording and compare.

## Out of scope
- Live feeds as a requirement (replay is the only required mode).
- Weather (optional, on the cut list).
- More than five detectors.

## Tone of UI copy
Plain analyst language, aviation terms spelled the standard way (see the glossary).
