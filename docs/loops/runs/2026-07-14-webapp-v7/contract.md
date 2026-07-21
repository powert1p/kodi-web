# Contract — webapp v7 «Разбор по делу»

**Дата:** 2026-07-14  
**Objective:** заменить отвергнутый владельцем v6-интерфейс React PWA на цельный, взрослый и понятный ученику 10–13 лет UX уровня референса QARA по силе art direction, не копируя его фестивальный стиль.

## Scope

- Живая поверхность: только `webapp/` (`/app/`), путь `login → hub → srez → drill → closure → analytics`.
- Foundations: tokens, typography, page shell, responsive navigation, shared controls/states.
- UX: ясное различие «Разбор» и «Срез», честный progress rail, явный переход после feedback, согласие передаётся родителю, полноценные loading/error/empty/disabled states.
- Project routing: ближайшие инструкции должны однозначно вести `webapp/**` к webapp-канону, а `frontend/**` — к legacy Flutter.

## Non-goals

- Backend/API/DB, Flutter UI, деплой, production data, новые учебные механики.
- Копирование QARA-палитры, industrial/dark-регистра или festival-композиции.
- Новый icon pack, декоративные fake-данные, новая аналитика.

## Immutable inputs

- Product truth: `docs/VISION.md`.
- Реальные API contracts и текущая логика React PWA.
- Референс качества: Claude artifact `474e0a54-36df-4d30-b26a-ec2d544d82ea` (QARA/FEST), только как планка art direction.
- Design brief: `DESIGN-V7.md` этого run.
- Пользовательские изменения вне `webapp/` не затрагиваются.

## Frozen rubric

- `/Users/esetseitkamal/Documents/design-lab/AUDIT-RUBRIC.md` — SHA-256 `a79b5b296d3cdfb74dcd7e7c48f05040fed257ef200a2969d309b65f812c9ecc`.
- `docs/loops/rubric-design.md` — SHA-256 `9496afce8d1c5c280dacd32d08bccdeadbc7d053d657764290c3fd089baa7474`.
- v7 override: UX outcomes ниже имеют приоритет над v6 signature-требованием; v6 визуальные предписания superseded после реализации.

## UX outcomes

1. За 3 секунды ясно, что делать сейчас; один primary CTA на экран.
2. `/` называется «Разбор», `/srez` — «Срез», `/analytics` — «Прогресс»; активная позиция объявляется семантически.
3. На 375px и 1280px нет horizontal overflow, fixed navigation не закрывает форму/CTA, touch targets ≥48px.
4. Progress rail показывает только реальные шаги/задачи и не дублируется декоративно.
5. Условия читаются как текст: числа не превращаются в россыпь formula chips.
6. Srez feedback остаётся до явного «Следующий вопрос».
7. Loading/error/empty/disabled/success состояния дают status + recovery path; console без error.
8. Keyboard flow логичен, `focus-visible` заметен, reduced-motion не прячет контент.

## Mechanical gate

Из `webapp/`:

```bash
npm run lint
npx tsc -b
npm run lint:design
npx vitest run
npm run build
```

Visual gate: реальные renders 375×844 и 1280×900 для login/hub/srez/drill/closure/analytics; console errors = 0; `scrollWidth <= innerWidth`; keyboard/focus/touch/reduced-motion checks.

## READY threshold

- Mechanical + visual gates зелёные.
- Два независимых native reviewers получают один immutable diff/render snapshot и frozen rubric.
- У каждого reviewer все 8 осей ≥8, среднее панели ≥8.5, `punch ≥8`, critical findings = 0.
- Максимум 2 review-раунда. Если порог не взят, итог честно сообщает `NOT_YET` и точный residual gap.

