# Benchmark contract — unified learning workspace

> Frozen before concept generation. The bounded Terra closure check returned `READY`; canonical
> inputs, evidence matrix and rubric are immutable for this benchmark round.

## Run

- **Objective:** freeze an implementation-ready continuous learning workspace that removes
  full-screen stage hopping after a topic starts.
- **Type:** concept/design-freeze generator benchmark, not production readiness.
- **Scope:** BRIEF/CJM/state/AI contracts, three concepts, five-state responsive evidence,
  selection and implementation backlog.
- **Non-goals:** React/backend implementation, AI endpoints, DB migration, deploy, DS promotion,
  learning-gain claim.
- **Register:** `собранный`; no card soup, state replacement or mascot/display-first UI.
- **Authority:** owner decision overrides old AI-grading wording in `docs/VISION.md` for this run;
  implementation remains gated by an ADR and doc synchronization.

## Frozen evidence matrix

- Concepts: `A Поля мысли`, `B Точный верстак`, `C Нить решения`.
- States: `independent`, `needs_revision`, `hint_h2`, `tutor_open`, `uncertain`.
- Viewports: `375×844`, `1280×900`.
- Expected screenshots: `3 × 5 × 2 = 30`.
- Shared deterministic fixture: `STATE-MATRIX.json`.

## Frozen quality bar

- each of eight axes ≥8.0;
- average ≥8.5;
- `math_focus` and `premium_distinctiveness` ≥8.5;
- critical flags = 0;
- both blind concept judges explicitly `READY`, no open P0/P1.

Mixed/missing verdict, failed mechanics or unchanged frozen hashes means not READY. Budget or
plateau below the bar is `NOT_READY/UNCERTAIN`.

## Roles

- Root Codex: sole concept maker/integrator and own-eyes reviewer.
- Fable: one read-only planning review; verdict `REVISE`, one bounded delta applied.
- Fresh Terra: planning-delta closure verifier before freeze.
- Two fresh Terra reviewers: blind concept judges after immutable snapshot.

## Frozen inputs and hashes

Canonical manifest: `FROZEN-SHA256SUMS`; rubric shortcut: `RUBRIC.sha256`.

Every render metadata record must include:

```json
{
  "rubric_sha256": "49d6de2eee2ad24ed2b07bbd95a84c78bae63897282dd2496b9723976555fa9d",
  "state_matrix_sha256": "5cc8a4b47d48bc7b8b05e7f0e8a3392ff1d21fcba253914c491596a6da5fe0b8"
}
```

If either digest differs at render or judging time, the snapshot is invalid.

## Mechanical commands

```bash
.venv/bin/python -m json.tool docs/loops/runs/2026-07-17-unified-learning-workspace/STATE-MATRIX.json
shasum -a 256 -c docs/loops/runs/2026-07-17-unified-learning-workspace/FROZEN-SHA256SUMS
.venv/bin/python docs/loops/runs/2026-07-17-unified-learning-workspace/render_gate.py
git diff --check -- docs/loops/runs/2026-07-17-unified-learning-workspace
```

`render_gate.py` must render all 30 files with real Chromium and fail on console/page errors,
horizontal overflow, unnamed interactives, targets <44 px, focus obstruction, missing fonts,
wrong matrix counts or digest mismatch. It also runs the deterministic fraction truth assertion.

## Evidence order

`mechanics → root own-eyes → immutable screenshot snapshot → two blind judges → selection/backlog`.

Judges receive the same `contract.md`, `RUBRIC.md`, `STATE-MATRIX.json`, 30 screenshots,
mechanical report and own-eyes report. They do not receive each other’s verdict.

## Stop semantics

- `READY`: every frozen gate and both judge verdicts pass.
- `REPEAT`: a structural/craft delta has a changed generator hypothesis and new snapshot.
- `NOT_READY/UNCERTAIN`: budget/plateau below bar or unresolved evidence.
- `STOPPED_BY_OWNER`: explicit owner stop.

Current planning gate: `READY`.
