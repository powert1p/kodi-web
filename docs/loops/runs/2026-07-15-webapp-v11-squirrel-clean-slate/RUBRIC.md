# Frozen visual/product rubric — webapp v11

Каждый judge смотрит одинаковые 375×844 и 1280×900 renders, читает `BRIEF.md`, проверяет relevant code/interaction evidence и даёт конкретные deltas. Нельзя повышать score за текстовое описание, если качество не видно в render.

## Оси 0–10

| Ось | 9–10 | 5–7 = провал |
|---|---|---|
| **math_focus** | Математический объект и текущая операция командуют экраном; следующий action понятен за 2 секунды | Headline, chrome, mascot или decoration спорят с задачей |
| **composition** | Авторская mobile-first система с сильным rhythm и осмысленной трансформацией на desktop | Ровный stack одинаковых cards, bento или ужатый desktop |
| **typography** | Выразительная Cyrillic/Kazakh-capable пара, точная scale и ясная math typography | Generic system/Inter feel, тяжёлый editorial serif или всё одного веса |
| **source_transformation** | AiPlus узнаваем по характеру и orange discipline, но mark — самостоятельная адаптация; реальные белки встроены режиссированно | Exact logo lockup, чужой/костюмный mascot, logo/mascot spam или произвольный ребрендинг |
| **color_atmosphere** | Тёплая, живая, неофициальная среда; orange — событие, остальные цвета поддерживают focus | Candy, orange wall, flat beige, SaaS blue или тёмный luxury-stage |
| **ux_states_craft** | Состояния coherent, controls/content связаны, recovery ясен, детали pixel-tight | Happy-path mockup, fake data, непоследовательные controls или потеря input |
| **motion_interaction** | Одна purposeful signature объясняет изменение шага; focus/touch/reduced-motion выверены | Fade-up/bounce everywhere, motion ради motion или отсутствие state feedback |
| **premium_distinctiveness** | Хочется смотреть и пользоваться; не MVP, не template, не generic AI UI и при этом подходит ребёнку 10–13 | Аккуратно, но без характера; официальный brochure UI; детский mobile game; AI-generated template |

## Concept gate

- Три направления визуально и пространственно различаются на Hub/Drill/Srez.
- 375×844 и 1280×900 renders без overflow и asset errors.
- Минимум два независимых judge.
- Победитель имеет лучший минимальный score по осям, `math_focus ≥ 8`, `source_transformation ≥ 8`, `premium_distinctiveness ≥ 8` и не имеет consensus high delta.
- Если ни одно направление не проходит — macro-direction пересобирается до production implementation.

## Mechanical production gate — всё обязательно

- `npm run lint`, design lint, `npx tsc -b`, relevant Vitest suite и production build — green.
- 375/1280: console clean, no unexpected request failures, no horizontal viewport overflow.
- Touch targets ≥44 px; input text ≥16 px; visible keyboard focus.
- Hub loading/error/empty/success; Drill/Closure/Srez focus error+success; Analytics empty/success.
- Reduced-motion сохраняет всю информацию и state change.
- Real squirrel assets load without distortion; exact old logo and costume fox отсутствуют.
- Behavioral/product constraints из `BRIEF.md` не нарушены.

## READY threshold

- Mechanical gate полностью green.
- У каждого production judge каждая ось ≥8.0.
- Средний score панели ≥8.5.
- `premium_distinctiveness` и `math_focus` ≥8.5 у каждого judge.
- Минимум 2/3 judges ставят `wow: true` и прямо подтверждают: «не MVP / не generic AI UI».
- Нет consensus-delta severity high.

Если threshold не пройден, фиксируется новый immutable round, исправляются consensus deltas и проводится новый review.

## Judge JSON

```json
{
  "scores": {
    "math_focus": 0,
    "composition": 0,
    "typography": 0,
    "source_transformation": 0,
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
