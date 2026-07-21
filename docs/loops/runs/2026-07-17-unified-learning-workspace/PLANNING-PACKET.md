# Planning packet — единый учебный workspace

> Статус до Fable review: `DRAFT`. Этот документ не является frozen contract.

## 1. Problem framing

Primary React PWA уже работает на одном route `/app/`, но после начала темы заменяет весь экран
на каждом server-stage. Для ребёнка это выглядит как постоянные переходы между страницами:
теряются условие, собственная попытка, предыдущий feedback и понимание следующего действия.
Одновременно самостоятельная задача принимает только фото, typed answer доступен лишь внутри
guided mode, контекстного AI-тьютора в primary journey нет, а подсказка фактически переводит
ученика в отдельный режим.

Нужен не новый набор экранов, а **один устойчивый учебный workspace**, в котором задача остаётся
пространственным якорем, а ответ, проверка, подсказки и разговор с AI меняют локальные слои.

## 2. Owner decisions

- После старта темы приложение не должно прыгать между полноэкранными состояниями.
- Основной способ доказать самостоятельное решение — одно фото всей страницы.
- Рядом должен быть видимый typed answer; это formative attempt, но не mastery evidence для
  многошаговой задачи.
- Семантический verdict по фото и typed/guided ответу принадлежит AI. Backend проверяет auth,
  consent, identity, idempotency, schema/enums/ranges, persistence и fail-closed recovery, но не
  заменяет AI verdict exact-string или локальным математическим checker.
- В AI всегда уходит контекст текущей задачи и пройденных этапов, чтобы проверка и разговор не
  были оторваны от решения.
- AI-assistant — контекстный слой текущей задачи, не отдельная страница и не generic chat.
- Подсказки идут по лестнице и не раскрывают ответ первым сообщением.
- Компоненты компактные; математика и следующая осмысленная action всегда важнее навигации,
  декоративного прогресса и brand.

## 3. Authority conflict to resolve explicitly

`docs/VISION.md` всё ещё говорит «правильность решает код». Более новое прямое решение владельца
для этого flow: AI владеет semantic verdict, backend — только contract validation и orchestration.
Для данного run owner decision выше старого текста. Следующий implementation Goal обязан
оформить ADR и синхронизировать `VISION.md`; этот design-freeze не меняет production architecture.

## 4. Invariants

1. Server journey, `revision` и idempotency остаются source of truth; refresh/relogin возвращает
   точную задачу, draft, выбранное фото, hint rung, verdict и tutor thread.
2. Parent consent проверяется до первого photo upload; фото не переносится между identity,
   journey или problem.
3. `unreadable`, `uncertain`, `wrong-photo`, provider/offline — recovery, а не математическая
   ошибка; draft и task context сохраняются.
4. Guided/typed help не повышает mastery. После разбора нужна новая independent transfer task и
   самостоятельное фото.
5. Условие задачи, режим (`independent / guided / transfer`) и доказанный progress не исчезают
   при открытии feedback, hint или tutor.
6. Один видимый primary action на текущем шаге; touch targets не меньше 44×44 px, учебный текст
   не меньше 18 px, видимый keyboard focus, `aria-live`, reduced motion, без page overflow.

## 5. Frozen product semantics proposed

### Submission

- `Фото решения` — default и mastery-capable submission.
- `Ввести ответ` — visible alternative. AI оценивает смысл, показывает formative feedback и
  предлагает подтвердить понимание самостоятельным решением. Даже при `typed correct` ученик
  остаётся в independent task, transfer не открывается, mastery не меняется, а primary action
  становится `Сфотографировать полное решение`.
- В guided steps ответ вводится текстом или выбирается из вариантов; фото каждого шага не нужно.

### Grading

- Verdict states: `correct`, `needs_revision`, `uncertain`.
- AI возвращает verdict, локализованный шаг, короткое evidence, понятное объяснение и next action.
- Backend отклоняет malformed/unsafe response и переводит её в recoverable `uncertain`, но не
  пересчитывает semantic verdict.

### Tutor and hints

- Tutor знает task, topic goal, mode, current stage/step, canonical reasoning, attempt, prior
  feedback, used hints и mastery evidence.
- H1 ориентирует, H2 задаёт вопрос о стратегии, H3 напоминает правило/связь, H4 разбирает один
  микро-шаг. Каждый следующий rung открывается явным действием.
- Полный worked solution доступен лишь после попытки и явного подтверждения; это guided evidence,
  после него система назначает новую transfer task.
- Открытие панели помощи само по себе ничего не меняет. Получение любого содержательного H1–H4
  или tutor response ставит `support_used=true`: текущая задача становится practice-only и не
  может дать mastery evidence.
- Hint/tutor доступны и в transfer, чтобы ребёнок не попадал в тупик, но первое содержательное
  использование переводит текущую transfer-задачу в supported practice; затем выдаётся новая
  transfer-задача для самостоятельного доказательства.

## 6. Stable workspace state model

После `lesson_start` shell не меняется:

`task_anchor + session_strip + response_dock + contextual_layer`

- `task_anchor`: topic, mode, full statement, learner work/attempt.
- `session_strip`: честный progress и сохранённость, не меню функций.
- `response_dock`: photo default, typed alternative, одна submit action.
- `contextual_layer`: inline feedback либо mobile sheet/desktop rail для hint/tutor; task остаётся
  видимой и доступной.

State transitions меняют содержимое локального слоя:

`independent → photo_submitting → correct | needs_revision | uncertain → retry | guided → transfer → topic_result`

`independent → typed_submitting → typed_feedback → independent`, где `typed_feedback` всегда
formative и не открывает transfer/mastery.

`uncertain` — нормализованная UX-семантика без математического verdict. Действующие server
reasons `unreadable | wrong_photo | unsure | provider_error` сохраняются как `recovery_reason`,
а существующий `photo_recovery` проецируется в contextual recovery layer без смены workspace.

## 7. Task graph

1. Зафиксировать BRIEF, CJM, state map и AI/UX contracts.
2. До build зафиксировать register, forbidden tendencies, rubric и три структурно разные
   seven-line concept packets.
3. Собрать три статичных, но интерактивно правдоподобных concept artifacts с одинаковой задачей
   и frozen matrix из пяти состояний на 375×844 и 1280×900: `independent`, `needs_revision`,
   `hint_h2`, `tutor_open`, `uncertain`.
4. Выполнить semantic truth gate, browser mechanics, own-eyes review и immutable snapshot.
5. Два blind reviewer оценивают один snapshot; победитель проходит frozen thresholds либо run
   получает честный `NOT_READY/UNCERTAIN`.
6. Привязать implementation backlog к выбранным workspace states и API contracts.

## 8. Design-freeze scope

В scope: UX architecture, visual directions, responsive renders, selection, contracts, backlog.

Не в scope: production React/backend implementation, новый AI endpoint, DB migration, deploy,
реальные child usability claims, изменение `VISION.md` или действующего `DESIGN_SYSTEM.md`.

## 9. Verification and DoD

- Три направления отличаются spatial model, typography, atmosphere/material и signature.
- Для каждого есть 10 полных renders: пять frozen states × 375×844 и 1280×900.
- На каждом render за 5 секунд понятны: задача, текущий режим и следующее действие.
- Task остаётся видимой при feedback/help; photo и typed answer доступны в одном workspace.
- Console errors, page overflow, unnamed controls, targets <44 px и focus obstruction = 0.
- Math fixture проходит отдельный deterministic truth check.
- Два независимых concept judge возвращают `READY`, без P0/P1; каждая rubric axis ≥8.0,
  average ≥8.5, `math_focus` и `premium_distinctiveness` ≥8.5, `critical_flags=0`.
- Backlog содержит state/API/test mapping и не смешивает typed/guided activity с mastery.

## 10. Risks and explicit non-claims

- Четыре hint rung — initial contract, а не доказанный оптимум; его валидируют с детьми.
- Static concepts доказывают композицию, но не production readiness и не learning gain.
- Полная AI ownership требует отдельной safety/evaluation architecture; design contract не
  подменяет eval на реальных детских решениях.
- Persistent workspace не означает persistent open chat: assistant открывается по намерению и
  всегда привязан к текущему task/step.
