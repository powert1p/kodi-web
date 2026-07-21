# AI feedback guard — frozen production benchmark

## Контракт

- Run type: `production`.
- Objective: ни чат-тьютор, ни `POST /api/trainer/diagnose` не раскрывают финальный или промежуточный ответ, при этом безопасные ссылки на номер шага не ломают учебный диалог.
- Scope: русский user-visible AI feedback, опубликованный каталог задач и декомпозиций, все реально используемые числовые формы ответов.
- Non-goals: доказательство эквивалентности произвольных символьных выражений; сокрытие текста, который сам ученик уже написал и который возвращается как `transcription`; языки кроме русского.
- Maker/integrator: root Codex. Reviewer: независимый read-only native subagent.

## Frozen inputs

| Input | SHA-256 |
|---|---|
| `backend/data/problems_v10.json` | `da3a8dbbcd394ce8b560bac07289cd9e5b3144f3edc4ff923c40a0315bd40fe2` |
| `backend/data/full_decomposition_v1.json` | `e8bfc2d5acabcef07e9e4f2c37857ee0c7cfadb56bfb0d85929e6e56128ac80a` |
| `BRIEF.md` | `96df3df648e4c8f2d60d73447a0256d93e3e4f0b47954042614985a445f990fd` |
| `CUSTOMER-JOURNEY-MAP.md` | `b9b3db300c2ef77af078e82af65bdf1c62737fd0173896947d6ab26af69e6cc0` |

Хэши и пороги этого run не меняются ради зелёного результата. Изменение каталога инвалидирует benchmark и требует нового snapshot.

## Frozen bar

`READY` разрешён только при одновременном выполнении всех условий:

1. `0` exact leaks на каждом уникальном `answer` и `expected_value` frozen-корпуса.
2. `0` semantic leaks в зафиксированных семействах: grouped integers, negative values, verbal fractions/decimals, sets/tuples, finite/infinite intervals, arbitrary ratios, clock time, percent, mixed numbers и конвертации всех единиц из verified final answers (`ч`, `с`, `га`, `дм²`, `π`).
3. `0` false blocks в frozen safe-cases: ordinal step/action references и безопасные неответные числа из unit tests.
4. `/diagnose` заменяет unsafe/blank/oversized `cause_text` до сохранения в БД и до HTTP-ответа; правильный ответ и каждый canonical `expected_value` защищены.
5. Полный backend suite, frontend Vitest, lint, design lint и production build зелёные.
6. Независимый reviewer возвращает явный `DEPLOY`; любой `NO_DEPLOY`, `NOT_RUN` или непроверенное семейство означает `NOT_READY`.

## Mechanical commands

```text
pytest backend/tests/test_tutor_api.py backend/tests/test_llm_openai.py backend/tests/test_trainer_api.py
pytest backend/tests/ -x -q
npx vitest run
npm run lint
npm run lint:design
npm run build
git diff --check
```

## Generator change after failed rounds

Первые два раунда латали отдельные написания ответа и оба пропустили новые опубликованные формы. Новый generator rule: сначала классифицировать семейство защищённого ответа и сравнивать его семантическую структуру/каноническую величину; неизвестный user-visible feedback обязан fail-close. Corpus sweep и semantic families становятся постоянными detectors, а не ручным review-чеклистом.

## Stop conditions

- `READY`: frozen bar полностью взят и reviewer явно разрешил deploy.
- `REPEAT`: найдено новое семейство, detector сначала добавлен красным тестом, затем меняется общий guard.
- `NOT_READY`: два следующих blind delta-раунда не улучшают результат либо остаётся неподдержанное опубликованное семейство.
- `STOPPED_BY_OWNER`: владелец явно остановил run.
