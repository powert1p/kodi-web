# Planning addendum — mobile learning workspace v2

Этот addendum закрывает обязательные изменения Fable-review до production-кода. Решения ниже
заморожены для текущего run; схема БД и persisted learner data не меняются.

## Режим design-приёмки

Run идёт как **production generator benchmark**, потому что владелец явно запросил loop/live
review и отверг предыдущий workspace, хотя тот прошёл облегчённую приёмку.

- До implementation замораживаются `contract.md` и `RUBRIC.md` с SHA-256.
- Старый workspace и `webapp/DESIGN_SYSTEM.md` — evidence/anti-reference, не визуальный канон.
- Три направления уже разведены в `BRIEF.md` по spatial model; production-кандидат строится по
  направлению A «Рабочая тетрадь».
- После mechanics и own-eyes один immutable production snapshot получают три blind judges.
- READY возможен только при выполнении frozen thresholds каждым judge; budget/plateau ниже bar
  означает `NOT_READY/UNCERTAIN`.

## Tutor scoping без изменения schema

Persistence остаётся `(student_id, problem_id)`. Обещания storage-scoping по шагу нет.

- В prompt всегда передаётся новый trusted-блок активного шага: условие задачи, номер шага,
  безопасная инструкция текущего шага и уже пройденные шаги.
- `final_answer`, expected value текущего шага и будущие шаги модель не получает.
- Untrusted history ограничена последними 6 сообщениями; при смене `step_n` backend не использует
  старую историю как instructional context. UI начинает новый видимый раздел разговора.
- `step_n` — часть request/prompt context, но не storage key.

DoD: tutor grounded в active step, bounded и безопасен; storage остаётся problem-scoped.

## Единая защита от утечки ответа

Tutor и guided feedback используют один принцип:

1. trusted context и untrusted learner text разделены fenced-блоками;
2. модель видит только минимально нужный контекст;
3. структурный ответ ограничен по длине и допустимым verdict/intent;
4. normalized protected-values gate проверяет ответ до persistence/render;
5. unsafe/malformed output заменяется контекстным fallback без ответа.

Tutor получает `reply`, `intent`, `follow_up`; `reply` отвечает на фактический вопрос ребёнка, а
не выбирает canned-фразу. Guided evaluator получает `verdict`, `confidence`, `evidence_verified`,
`answer_echo`, `feedback`. Feedback не может содержать hidden expected value.

Read-path policy: новые tutor replies сохраняются только после validation; render больше не
прогоняет их через legacy allowlist. Старые canned replies остаются читаемыми. Невалидная legacy
строка заменяется нейтральным scoped fallback.

## Guided AI evaluation и processing state

- `POST /guided/answer` получает тот же двухфазный lease/CAS принцип, что typed answer, но свой
  step-scoped evaluator contract.
- Новый projection `guided_processing` сразу возвращается UI; provider call не держит row lock.
- Confidence threshold: `0.65`, как у typed evaluation. Ниже порога или при
  `evidence_verified=false` verdict становится `unsure`.
- `correct` продвигает шаг; `incorrect` остаётся на шаге; `unsure`/provider error сохраняет draft
  и даёт retry. Только AI решает математику; deterministic checker остаётся shadow telemetry и
  никогда не меняет learner state.
- Replay того же attempt id возвращает persisted terminal response; stale/late response
  блокируется lease/revision check. Guided evidence всегда `counts_for_mastery=false`.
- Typed two-phase helpers parameterize stage/lease/result application instead of duplicating a
  second race-prone pipeline. `guided_processing` is an explicit frontend projection: input and
  primary action stay visible, become pending-safe, duplicate submit is blocked, and retry keeps
  the draft in the same workspace.
- Mirror tests cover guided stale-lease recovery, provider-error retry with preserved draft,
  idempotent replay of the same attempt id, rejection of a late result after revision change, and
  the frontend `guided_processing` consumer (pending, restored focus and retry).
- Endpoint получает `@limiter.limit("20/minute")` и `@ai_ip_limit`: лимит допускает нормальный
  четырёхшаговый разбор с повторными попытками, но ограничивает provider abuse.

## Guided copy formatter

Formatter классифицирует только форму ожидаемого ввода, не проверяет ответ:

- integer/decimal;
- fraction or mixed number;
- equation/expression;
- value with unit;
- short text/choice;
- generic fallback «Запиши один следующий переход».

Поля `prompt`, `format_hint`, `example`, `input_mode` additive. Example опционален и не содержит
normalized expected value. Bank-wide property test обходит каждый шаг каждого файла
`backend/data/*.json`, включая неизвестную или неполную форму через generic fallback: copy
непустая и bounded, classifier не падает, expected value не утекает, а неизвестная форма всегда
получает безопасный generic contract.

## Mobile keyboard и public acceptance

До READY обязательны:

- automated `visualViewport`/resize proxy и mobile WebKit journey на `375×844` и `844×375`;
- на публичной сборке — реальный iPhone Safari либо эквивалентный mobile WebKit;
- screenshot/recording с одновременно доступными task anchor, input, feedback и primary action;
- отсутствие fixed response dock, горизонтального overflow и focus loss при открытии tutor.
