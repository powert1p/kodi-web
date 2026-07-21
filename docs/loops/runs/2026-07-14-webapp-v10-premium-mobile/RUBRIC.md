# Frozen visual/product rubric — v10

Каждый judge независимо смотрит одинаковые 375×844 и 1280×900 renders, читает `BRIEF.md`, проверяет relevant code/interaction evidence и даёт конкретные deltas.

## Оси 0–10

| Ось | 9–10 | 5–7 = провал |
|---|---|---|
| **math_focus** | Один математический объект командует экраном; следующий action очевиден | UI chrome/cards/mascot спорят с задачей |
| **composition** | Авторская mobile композиция, сильный rhythm, meaningful break/overlap | Ровный stack одинаковых cards или ужатый desktop |
| **typography** | Distinctive Cyrillic display + чистый body + выверенная math scale | Generic system/Inter feel, все одного веса/масштаба |
| **brand_mascot** | Реальный AiPlus узнаваем; mascot встроен редко и режиссированно | Чужой logo, generic fox, avatar/bubble spam |
| **color_atmosphere** | Warm mineral field + disciplined orange event + depth/material | Candy, чрезмерный orange, flat beige, SaaS blue |
| **ux_states_craft** | Состояния coherent, controls/content связаны, details pixel-tight | Happy-path mockup, непоследовательные controls, fake data |
| **motion_interaction** | Purposeful state/motion signature; touch/focus/reduced motion | Fade-up everywhere, bounce, motion ради motion или none |
| **premium_distinctiveness** | Хочется смотреть; не MVP, не template, не выглядит AI-generated | Аккуратно, но можно заменить logo и продать любому EdTech |

## Mechanical gate — всё обязательно

- `lint`, design lint, typecheck, tests, production build — green.
- 375/1280: console clean, no request failures outside intentional fixtures, no horizontal overflow.
- Touch targets ≥44 px, input text ≥16 px, visible focus.
- loading/error/empty/success минимум для Hub; focus-flow error/success для Drill/Closure; reduced motion.
- Real AiPlus logo and approved mascot assets load without distortion.
- Behavioral/product constraints из `BRIEF.md` не нарушены.

## READY threshold

- Mechanical gate полностью green.
- У **каждого** judge каждая ось ≥8.0.
- Средний score панели ≥8.5.
- `premium_distinctiveness` и `math_focus` ≥8.5 у каждого judge.
- Минимум 2/3 judges ставят `wow: true` и прямо подтверждают: «не MVP / не generic AI UI».
- Нет consensus-delta (одна и та же проблема у ≥2 judges) severity high.

Если threshold не пройден, фиксируется новый round с immutable renders и только затем меняется implementation.

## Judge JSON

```json
{
  "scores": {
    "math_focus": 0,
    "composition": 0,
    "typography": 0,
    "brand_mascot": 0,
    "color_atmosphere": 0,
    "ux_states_craft": 0,
    "motion_interaction": 0,
    "premium_distinctiveness": 0
  },
  "avg": 0,
  "wow": false,
  "evidence": [],
  "top_deltas": [],
  "verdict": "READY | NOT_YET"
}
```
