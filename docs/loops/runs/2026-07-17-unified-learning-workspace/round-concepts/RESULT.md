# Result — concept benchmark

## Decision

**READY. Selected concept: C — `Нить решения`.**

Both blind judges independently selected C from the same immutable 30-render snapshot. No
acceptance delta was requested or applied after the snapshot was frozen.

## Frozen-bar result

| Gate | Required | Actual | Result |
|---|---:|---:|---|
| Render matrix | 30 | 30 | PASS |
| Console/page errors | 0 | 0 | PASS |
| Horizontal overflow | 0 px | 0 px | PASS |
| Targets below 44 px | 0 | 0 | PASS |
| Focus obstruction | 0 | 0 | PASS |
| Unnamed controls | 0 | 0 | PASS |
| Primary CTA per state | 1 | 1 | PASS |
| Each judge axis | ≥8.0 | min 8.4 | PASS |
| Each judge average | ≥8.5 | 8.70 / 8.98 | PASS |
| `math_focus` | ≥8.5 | 9.1 / 8.9 | PASS |
| `premium_distinctiveness` | ≥8.5 | 9.0 / 9.2 | PASS |
| Critical flags | 0 | 0 | PASS |
| Open P0/P1 | 0 | 0 | PASS |
| Blind verdicts | 2 × READY | 2 × READY | PASS |

## Scores for selected concept C

| Axis | Child-learning judge | Visual/accessibility judge | Mean |
|---|---:|---:|---:|
| Orientation | 8.6 | 9.1 | 8.85 |
| Continuity | 8.8 | 9.0 | 8.90 |
| Cognitive load | 8.4 | 8.8 | 8.60 |
| Math focus | 9.1 | 8.9 | 9.00 |
| Submission clarity | 8.6 | 8.8 | 8.70 |
| Pedagogical clarity | 8.7 | 9.1 | 8.90 |
| Responsive accessibility | 8.4 | 8.9 | 8.65 |
| Premium distinctiveness | 9.0 | 9.2 | 9.10 |
| **Average** | **8.70** | **8.98** | **8.84** |

## Why C won

- The problem, learner evidence, AI response and next action remain one continuous trace instead
  of becoming separate pages or a dashboard of cards.
- Desktop and mobile use different spatial compositions of the same model: a horizontal
  three-zone trace on desktop and a vertical proof-thread on mobile.
- `needs_revision` identifies the first divergence without revealing the final answer;
  `uncertain` visibly interrupts the evidence thread without recording a mathematical error.
- Photo remains the mastery-capable primary submission; typed response, hints and tutor remain
  close and available without competing with it.
- The dotted proof-thread is a recognisable Kodi signature without copying the old logo, mascot,
  Duolingo or a generic AI-chat visual language.

## Comparative disposition

- **A — `Поля мысли`: reserve.** Carry forward its strong editorial typography and semantic
  annotation discipline, but not its more conventional mobile worksheet stack.
- **B — `Точный верстак`: reject for the learner shell.** Keep its explicit zone naming as an
  information-architecture reference; do not carry its 48 px mobile rail or denser tutor state.
- **C — `Нить решения`: production direction.** Carry forward the thread, zone hierarchy,
  anchored help surface, subordinate mint context and orange action accents.

## Evidence

- Mechanical report: `MECHANICAL.md` and `MECHANICAL.json`.
- Root inspection: `OWN-EYES.md`.
- Blind verdicts: `JUDGE-LEARNING.md`, `JUDGE-VISUAL.md`.
- Immutable render snapshot: `evidence/SHA256SUMS`.
- Contact sheet: `evidence/contact-c.png`.

This is a design/contract readiness verdict. It is not a claim that production code, AI
evaluation, migration, deployment or learning outcomes are complete.
