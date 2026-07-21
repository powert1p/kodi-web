# P2 — единый учебный экран

Статус: `FROZEN — TERRA READY`

## Цель

Собрать активную практику NIS в одном устойчивом learning workspace. Ученик не
переходит между отдельными полноэкранными страницами после каждого действия:
условие задачи, положение в теме и доступ к помощи остаются на месте, а внутри
экрана меняются только ответ, проверка, обратная связь или guided-шаг.

## Зафиксированные продуктовые решения

- Фото полного решения остаётся основным способом ответа и единственным новым
  evidence, которое может менять mastery.
- Рядом доступен текстовый ответ. Его проверяет AI по условию, каноническим шагам
  и правильному ответу; backend только fail-closed валидирует bounded JSON.
- Текстовый ответ является formative evidence: он сохраняется, но никогда не
  повышает и не понижает mastery. Даже после верного ответа экран предлагает
  подтвердить ход решения одним фото.
- «Не знаю, как решать» переводит эту же задачу в guided-шаги. Guided-ответы
  остаются текстовыми и не влияют на mastery; после разбора выдаётся новая
  transfer-задача.
- AI-наставник доступен контекстно в том же workspace, а не как отдельная
  навигационная страница. Он не раскрывает финальный ответ.
- При неуверенности AI, provider error или stale state введённый ответ не должен
  исчезать; система честно предлагает повторить проверку или отправить фото.
- Визуальный канон — `webapp/DESIGN_SYSTEM.md` v12: warm cream, forest, сдержанный
  orange, математика — главный визуальный объект, без mascot и card soup.

## Invariants

- Server-authoritative `journey.revision`, identity binding и idempotency остаются
  обязательными для каждого нового command.
- Нельзя использовать `/api/trainer/step-answer` или `/api/learning/answer`:
  у них другая state machine и persistence.
- AI binary verdict принимается только при schema-valid payload, finite confidence
  `>= 0.65` и вычисленном сервером `evidence_verified=true`; иначе результат
  `unsure`. Для typed-проверки `evidence_verified=true` означает, что bounded
  `answer_echo` после NFKC и схлопывания whitespace в точности совпал с
  нормализованным сервером ответом ученика, а bounded `check_summary` непустой и не
  содержит control characters. Это provider evidence: оба поля никогда не
  показываются ребёнку.
- Детский текст feedback строит backend по закрытому `error_focus` enum. Свободный
  текст модели ребёнку не показывается, поэтому AI не может выдать готовый ответ.
- Concurrent/stale typed-result не может изменить новый экран: после provider call
  backend повторно проверяет journey id, revision, stage и problem id.
- `counts_for_mastery=false` для всех typed attempts независимо от verdict.
- Existing photo/guided/retry/resume contracts и production DB schema не меняются.

## Предлагаемый контракт

### Backend

`POST /api/journey/answer`

```json
{
  "revision": 17,
  "problem_id": 42,
  "answer": "3/7",
  "client_attempt_id": "typed-uuid"
}
```

Endpoint разрешён только в `independent_task|transfer_task`. `answer` после trim
должен иметь длину `1..500`; endpoint защищён `limiter.limit("10/minute")` и
`ai_ip_limit`. Он создаёт
`JourneyAttempt(kind=independent_typed|transfer_typed, status=processing)`, вызывает
`evaluate_typed_answer`, затем сохраняет терминальный status
`accepted|provider_error|superseded`, `verdict`, `confidence`, `provider`, `model`,
всегда `counts_for_mastery=false`.

AI возвращает только:

```json
{
  "verdict": "correct | incorrect | unsure",
  "error_focus": "none | interpretation | calculation | units | format | unknown",
  "confidence": 0.0,
  "answer_echo": "3/7",
  "check_summary": "Ответ сопоставлен с условием и каноническими шагами"
}
```

`answer_echo` и `check_summary` имеют отдельные лимиты длины, строгие типы и
проверку control characters. `evidence_verified` не приходит от модели: backend
вычисляет его только после нормализации и полного schema check.

Жизненный цикл попытки:

1. Под `StudentJourney FOR UPDATE` выполняются `_ensure_not_processing`, guards по
   identity/revision/stage/problem и поиск другой typed-попытки `processing` для
   этого journey.
2. Fresh processing младше 45 секунд возвращает тот же authoritative state и
   conflict без второго provider call. Stale processing переводится в
   `provider_error`. Новая попытка создаётся и commit-ится **до** provider call;
   DB lock во время AI-запроса не удерживается.
3. После provider call backend заново берёт journey и attempt `FOR UPDATE`,
   проверяет attempt id, исходные revision/stage/problem и отсутствие активной
   photo-processing попытки.
4. Если экран уже изменился, проигравшая попытка получает `superseded`, сохраняет
   ответ и текущий authoritative payload, а клиент получает conflict с этим state.
5. Replay по `client_attempt_id` typed-специфичен: `accepted` возвращает сохранённый
   payload; fresh `processing` — conflict; stale/provider_error — retryable 503;
   `superseded` — conflict. Новый provider call на replay не запускается.

После принятия результат записывается в `journey.activity.typed_feedback` и
`journey.revision` увеличивается. Стадия и задача не меняются. `_render` добавляет
в `next_step.typed_feedback` серверный безопасный текст и выставляет
`response.typed_available=true` для task states.

`typed_feedback` очищается централизованно при назначении новой задачи, любом
переходе stage, старте photo processing и применении photo result. Отдельный
regression test покрывает `retry_task`, чтобы feedback старой задачи не протёк в
новую попытку.

### Frontend

- `JourneyPage` использует `hasJourneyWorkspace(state)` как границу active practice.
- Для active practice всегда монтируется один `LearningWorkspace`; legacy отдельные
  screen-компоненты больше не выбираются верхнеуровневым switch.
- Global scroll/focus reset применяется только к onboarding/result stages. В active
  practice фокус перемещается только на новый inline status/feedback через live region.
- Desktop: спокойная task column + узкая contextual rail. Mobile 375 px: одна колонка,
  компактный sticky response dock; tutor раскрывается inline/sheet и не конкурирует
  с основным действием.
- На task state видны: условие, одно основное фото-действие, компактные вторичные
  «Ввести ответ» и «Не знаю, как решать», contextual «Спросить AI».
- Processing/feedback/recovery/guided меняют внутреннюю панель, но сохраняют header,
  условие и rail. Компоненты не имеют viewport-sized `min-height`.
- Tutor availability matrix: доступен в `independent_task`; в guided — с текущим
  `stepN`; в `photo_feedback` — только при неверном решении и явном запросе помощи;
  скрыт в `photo_processing`, `photo_recovery`, `transfer_task` и
  `transfer_feedback`. Draft typed-ответа сохраняется при раскрытии/закрытии tutor
  и при inline смене состояния. Tutor chat не меняет `support.used`: этот флаг
  продолжает означать только явный вход в guided через «Не знаю, как решать».

## Task graph и зависимости

1. **AI typed grading contract**
   - files: `backend/core/llm_openai.py`, `backend/tests/test_llm_openai.py`;
   - DoD: strict schema, duplicate-key/type/range/control-char validation,
     NFKC-normalized `answer_echo`, bounded `check_summary`, серверный
     `evidence_verified`, provider fallback, malformed/low-confidence fail closed,
     prompt содержит полный trusted context.
2. **Journey command and persistence** — зависит от 1
   - files: `backend/api/routers/journey.py`, `backend/tests/test_journey_api.py`;
   - DoD: identity/state/revision/problem guards, commit-before-call, no DB lock
     during AI, single-flight и 45-second recovery, typed-specific idempotency,
     superseded/provider-error terminal states, safe feedback map, cleanup on every
     stage/problem/photo transition, no mastery mutation, `typed_available=true`.
3. **Frontend API/hook** — зависит от 2
   - files: `webapp/src/lib/journeyApi.ts`, `webapp/src/features/journey/useJourney.ts`,
     соответствующие tests;
   - DoD: durable attempt id, answer retained on failure, authoritative conflict state.
4. **Stable LearningWorkspace** — зависит от 3 и существующего workspace envelope
   - files: `JourneyPage.tsx`, `JourneyPage.css`, `journeyPage.test.ts`, при необходимости
     только локальная стилизация `TutorPanel`;
   - DoD: один mounted shell во всех 7 active states, photo/typed/guided/tutor
     доступны строго по matrix, typed/tutor drafts переживают inline transitions,
     без page scroll reset и competing primary CTA; tests фиксируют shell identity,
     draft retention, keyboard focus и отсутствие global scroll reset.
5. **Acceptance** — зависит от 1–4
   - backend/frontend tests, lint, typecheck, release build;
   - реальные renders 375×812 и 1280×900 для task, processing, typed feedback,
     guided, photo feedback/recovery; keyboard focus, console, overflow, loading/error;
   - fresh blind Terra review; максимум одна acceptance delta; exact image deploy и
     public smoke только после всех green gates.

## Out of scope

- Изменение BKT/mastery формулы, DB migration или новый тип mastery evidence.
- Перенос onboarding/diagnostic/route screens в workspace.
- Постоянный трёхпанельный dashboard, mascot, gamification и отдельная страница чата.
- Голос, live-планшет и выдача готового решения AI.
