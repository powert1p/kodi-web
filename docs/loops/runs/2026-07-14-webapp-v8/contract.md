# Contract — webapp v8 clean-slate redesign

**Дата:** 2026-07-14  
**Objective:** заново спроектировать React PWA тренажёра как цельный, выразительный и
понятный ученику 10–13 лет продукт, не наследуя визуальную систему v6/v7 и не меняя
учебную механику или backend contracts.

## Scope

- `webapp/` на `/app/`: login → hub → srez → drill → closure → analytics.
- Foundations: typography, tokens, atmosphere, navigation, responsive spatial model,
  shared controls, feedback и states.
- Один собственный signature, который объясняет путь решения и использует реальные данные.
- Новый project design canon только после выбора clean-slate concept.
- Native Codex design-flow: correct routing, skills, real renders, independent judges.

## Non-goals

- Backend/API/DB, Flutter UI, production data, deploy и новые учебные механики.
- Копирование QARA industrial/neon-композиции или любой старой kodi palette/component grammar.
- Gamification, фейковые metrics, новый mascot или новый icon pack.
- Переписывание data hooks и API adapters без доказанной UX-причины.

## Immutable inputs

- Product truth: `docs/VISION.md`, SHA-256
  `96cac33b8134b15d765f8888e2edb947f70f17210fe7c181733e4361aa318309`.
- Существующие API contracts, auth, telemetry и учебная логика React PWA.
- Кёди остаётся существующим SVG-персонажем; визуальная роль может стать тише.
- Чужая dirty-работа в `cabinet/**` и root `AGENTS.md` не затрагивается.
- V6/V7 screenshots, components и design docs — anti-reference и behavioral evidence,
  не визуальный вход нового решения.

## Frozen rubric

- `/Users/esetseitkamal/Documents/design-lab/AUDIT-RUBRIC.md` — SHA-256
  `a79b5b296d3cdfb74dcd7e7c48f05040fed257ef200a2969d309b65f812c9ecc`.
- `docs/loops/rubric-design.md` — SHA-256
  `c337c704998cb40655e73d4c192206c439d8d617976687f5096ac11b00f8cf03`.
- Внутри run rubric и threshold не ослабляются.

## UX success criteria

1. За 3 секунды понятны текущая задача, следующий шаг и единственное primary action.
2. Hub показывает приоритет разбора; drill — где именно сбилось решение; srez — независимую
   проверку без подсказки правильного ответа.
3. Feedback мягкий, конкретный и всегда даёт recovery path; network submit видим и защищён
   от дубля.
4. Login, loading, error, empty, feedback, success и disabled выглядят частью одной системы.
5. 375×844 и 1280×900 — самостоятельные композиции без horizontal overflow и закрытых CTA.
6. Keyboard focus заметен, touch targets ≥44px, reduced-motion сохраняет весь content.
7. Новый вид нельзя описать как «сменили font/colors/radius у v6».

## Mechanical gate

Из `webapp/`:

```bash
npm run lint
npm run lint:design
npx tsc -b
npx vitest run
npm run build
```

Дополнительно: syntax/selftest global design hook; font coverage для кириллицы и `Ң`;
Playwright render login/hub/srez/drill/closure/analytics на 375×844 и 1280×900;
console errors = 0; `scrollWidth <= innerWidth`; keyboard + reduced-motion checks.

## Benchmark loop

- Round 0: три rendered clean-slate concepts на hub/drill/srez; blind comparison.
- Round 1: победитель перенесён в React и проверен полным visual gate.
- Round 2–3: только consensus fixes по frozen rubric.
- Максимум три React review-раунда.

## READY

- Все mechanical/visual gates зелёные.
- Минимум два независимых reviewers оценивают один immutable render/diff snapshot.
- У каждого все 8 осей ≥8; panel average ≥8.5; punch ≥8; critical findings = 0.
- Минимум два reviewer независимо ставят `wow=true`.

