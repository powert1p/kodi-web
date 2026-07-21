# Frozen rubric — unified learning workspace concept round

Этот run-specific rubric переопределяет legacy screenshot set `hub/drill/srez` из
`docs/loops/rubric-design.md`. Обязательный evidence set: `independent`, `needs_revision`,
`hint_h2`, `tutor_open`, `uncertain` × 375×844/1280×900 × A/B/C. Для concept round применяются
два независимых judge согласно `docs/loops/DESIGN-FLOW.md` §8.

## Scoring

Each axis receives `0..10` with screenshot-specific evidence.

- `0–4`: critical usability/semantic failure or generic/unfinished composition.
- `5–7`: usable direction but substantial ambiguity, old grammar or craft debt.
- `8`: production-worthy concept foundation; no major issue on this axis.
- `9`: unusually clear, coherent and product-specific.
- `10`: exceptional evidence with no meaningful improvement visible in scope.

`math_focus` anchor: 8 = condition and relevant reasoning remain primary in all five states; 9 =
feedback/help increase comprehension without visual competition; 10 = exceptional mathematical
orientation with no remaining craft gap. `premium_distinctiveness` anchor: 8 = coherent custom
spatial/signature system across viewports; 9 = unmistakably Kodi-specific and mature; 10 =
exceptional originality without usability tradeoff.

## Axes

1. **orientation** — within five seconds, task, mode and next action are unambiguous.
2. **continuity** — task/attempt stay visible and spatially anchored with feedback/help.
3. **cognitive_load** — one primary action, compact secondary actions, no competing function map.
4. **math_focus** — statement/reasoning outrank decoration, brand, progress and AI chrome.
5. **submission_clarity** — photo remains default; typed answer is visible and its formative role
   is clear without long explanation.
6. **pedagogical_clarity** — AI feedback is localized, safe and action-oriented without revealing
   the final answer.
7. **responsive_accessibility** — 375×844 and 1280×900 are intentional; Cyrillic/math, 44 px
   targets, focus, contrast, overflow and reduced-motion contract are credible.
8. **premium_distinctiveness** — deliberate Kodi-specific spatial/art system and one honest
   signature; no card soup, old station grammar, copied logo/mascot or generic AI aesthetic.

## Automatic caps / critical flags

- math text <18 px, target <44 px, unnamed control, hidden/obscured focus, page overflow or
  console error → `responsive_accessibility ≤4`, critical.
- wrong fixture math, answer leakage before explicit reveal, typed attempt shown as mastery, or
  `uncertain` shown as mathematical error → `pedagogical_clarity ≤4`, critical.
- task disappears when feedback/help is visible → `continuity ≤4`, critical.
- more than one primary CTA, generic feature navigation or mascot competing with problem →
  `cognitive_load ≤5`; repeated pattern is critical.
- token/radius reskin of the same DOM/spatial model → `premium_distinctiveness ≤4`.
- fake progress/points or decorative server claims → critical semantic flag.

## Frozen bar

- every axis `≥8.0`;
- average `≥8.5`;
- `math_focus ≥8.5` and `premium_distinctiveness ≥8.5`;
- `critical_flags = 0`;
- both independent judges explicitly return `READY` and no open P0/P1.

Mixed, missing or `UNCERTAIN/NOT_YET` verdict is not READY. Budget/plateau below the bar is
`NOT_READY/UNCERTAIN`, never a softened pass.

## Judge response format

```json
{
  "judge": "blind-id",
  "scores": {
    "orientation": 0,
    "continuity": 0,
    "cognitive_load": 0,
    "math_focus": 0,
    "submission_clarity": 0,
    "pedagogical_clarity": 0,
    "responsive_accessibility": 0,
    "premium_distinctiveness": 0
  },
  "average": 0,
  "critical_flags": [],
  "p0_p1": [],
  "winner": "A|B|C|none",
  "evidence": ["screenshot-specific finding"],
  "confidence": 0,
  "verdict": "READY|NOT_YET|UNCERTAIN"
}
```
