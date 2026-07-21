# Round 2 mechanical evidence

## Frozen rubric

Command: `LC_ALL=C shasum -a 256 -c RUBRIC.sha256`

Result: `RUBRIC.md: OK`

## Previous v10 immutability

Command: `LC_ALL=C shasum -a 256 -c SNAPSHOT.sha256` in the v10 run.

Result: all 7 frozen inputs `OK` (`RESEARCH`, `BRIEF`, `RUBRIC`, `contract`, logo and two mascot
assets).

## Structure and routing

Read-only validator checked 10 runtime/project files and 16 invariants: known-shape route,
rejected redesign, explicit quality bar, two-fail escalation, hard stop, generator repair,
three directions, root-only maker, explicit judge READY, three project judges, frozen external
rubric, active run, target sizes, imagegen/glyphs, blind delta and old-DS anti-reference.

Result: `flow contract: OK (10 files, 16 invariant checks)`.

## Hygiene

- `git diff --check` on tracked project flow files: PASS.
- trailing whitespace scan on every touched runtime/project file: PASS.
- skill relative links resolve: PASS.
- stale/Claude-only runtime strings (`codex-worker`, `loop-verify`, `gen-image.sh`, old BOLD
  prompt) absent: PASS.
