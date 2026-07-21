# Mechanical gate — concept round

## Result

`PASS`

- Chromium renders: **30 / 30** (`3 concepts × 5 states × 2 viewports`).
- Screenshot dimensions: frozen `375×844` and `1280×900` viewports.
- Deterministic fixture: `1 − 3/8 = 5/8`; `5/8 × 2/5 = 1/4`.
- Horizontal overflow: **0 px** maximum.
- Targets below 44 px: **0**.
- Focus obstruction/out-of-viewport failures: **0**.
- Unnamed visible controls: **0**.
- Console/page errors: **0**.
- Primary CTA count: **exactly 1** in every render.
- Learning-text minimum: **18 px**.
- Required Cyrillic fonts loaded: **30 / 30**.
- Visible interactives per state: **5–7**, including the skip-link and stable shell controls.
- Reduced-motion offenders: **0**.

## Command

```bash
.venv/bin/python docs/loops/runs/2026-07-17-unified-learning-workspace/render_gate.py
```

Observed output:

```text
PASS: 30 renders; truth=1/4; critical_failures=0
```

Machine-readable evidence lives in `MECHANICAL.json` and `evidence/metadata.json`; every render
record carries the frozen rubric and state-matrix digests.
