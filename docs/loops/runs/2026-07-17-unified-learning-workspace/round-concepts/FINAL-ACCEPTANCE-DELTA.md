# Final acceptance delta

## Trigger

The fresh final artifact reviewer returned one P1: the state map incorrectly defined mutable
`problem_id + server_stage + revision` as part of the server resume lookup key. That would make a
stale tab unable to resolve the current journey after a hint, tutor turn or verdict increments the
revision.

## Bounded correction

- Server resume lookup identity is now stable: `student_id + journey_id`.
- The server returns current `problem_id`, `server_stage` and `revision` in the authoritative
  snapshot.
- Mutable identity/revision fields remain request preconditions for optimistic concurrency; a
  stale request receives the current snapshot instead of addressing historical state.
- A compatible local unsent draft may still be scoped more narrowly and is cleared fail-closed on
  mismatch.

Changed canonical artifacts:

- `STATE-MAP.md`, resume contract only;
- `IMPLEMENTATION-BACKLOG.md`, P3 acceptance only.

## Evidence impact

No rendered state, copy, layout, task fixture, rubric, state matrix or prototype source changed.
The 30-render immutable screenshot snapshot and both visual/pedagogical judge verdicts therefore
remain applicable. `FROZEN-SHA256SUMS` was refreshed only for the corrected `STATE-MAP.md`; all
other frozen digests remain byte-identical. The same final reviewer must verify closure before the
run can be marked READY.
