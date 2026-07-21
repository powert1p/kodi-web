# State map — server journey внутри стабильного workspace

## Shell ownership

Server `next_step` остаётся единственным владельцем stage. Клиент не выводит stage из URL,
открытого sheet или локального mode. Локальное состояние ограничено draft, выбранным tab,
focus и presentation слоями.

```text
LearningWorkspace
├── SessionStrip        server context + save status
├── TaskAnchor          problem/topic/mode + learner attempt
├── ContextualLayer     processing | feedback | recovery | hint | tutor
└── ResponseDock        photo | typed | guided response + one primary action
```

## Server stage → workspace projection

| `next_step.type` | Task anchor | Contextual layer | Response dock | Geometry |
|---|---|---|---|---|
| `lesson_intro` | Topic goal, no problem yet | Why this topic | `Начать задачу` | Handoff shell; последний допустимый transition screen |
| `independent_task` | Full problem, mode `Самостоятельно` | Closed; optional `Помоги начать` | Photo default + typed alternative | Stable |
| `photo_processing` | Same problem + preserved attempt | Durable progress/status | Disabled submit; safe cancel only if contract permits | Stable |
| `photo_feedback` | Same problem + attempt | `correct` or `needs_revision` feedback | Next/retry; help secondary | Stable |
| `photo_recovery` | Same problem + preserved attempt | Local recovery, no math verdict | Rephoto/retype/retry provider | Stable |
| `guided_step` | Same problem, mode `Разбор`, solved context retained | Current hint/tutor thread | Text/options for one step | Stable |
| `transfer_task` | New problem, mode `Проверка самостоятельно` | Closed | Photo default + typed formative alternative | Stable; content changes, shell does not |
| `transfer_feedback` | Same transfer task + attempt | Verdict/mastery evidence | Retry/finish | Stable |
| `topic_result` | Topic + evidence summary | What was confirmed | Next topic / finish | May collapse workspace after cycle completes |

Pre-study `profile`, `exam_map`, `diagnostic_*`, `route_ready` remain a bounded sequential flow;
они не должны импортировать function dashboard в learning workspace.

## Local UI substates

```text
idle
├── photo_selecting → photo_ready → submitting
├── typed_editing → submitting
├── hint_open(rung 1..4)
└── tutor_open(thread scoped to problem + stage)

submitting
├── server_processing
├── correct
├── needs_revision
└── uncertain | offline | provider_error

typed_editing → typed_submitting → typed_feedback → independent

needs_revision
├── retry_same_mode
├── hint_open
└── guided_step

guided_step → guided_feedback → next_guided_step | transfer_task
```

Локальный `tutor_open` и `hint_open` не меняют server stage. Получение содержательного H1–H4 или
tutor response отправляет `support_used=true` на server и получает новую `revision`; простое
открытие/закрытие слоя eligibility не меняет.

## Resume contract

Server resume lookup identity: `student_id + journey_id`. The server resolves and returns the
current authoritative `problem_id`, `server_stage` and `revision`; those mutable values never form
the lookup key.

Сервер восстанавливает:

- task/topic/mode и current canonical stage;
- submission metadata и durable processing/result;
- prior verdict/evidence и mastery evidence;
- opened hint rung, guided step и tutor thread summary;
- idempotency record для повторной доставки.

Клиент восстанавливает только допустимый unsent draft и presentation preference. A local draft
may be compatibility-scoped by `journey_id + problem_id + revision`, but this is not server resume
identity. При mismatch identity/journey/problem или несовместимой revision локальный photo/typed
draft очищается fail-closed. Mutating requests send stage-specific identity and `revision` only as
optimistic-concurrency preconditions; a stale precondition returns the current authoritative
snapshot instead of making the old snapshot addressable.

Hint rung, `support_used` и tutor thread являются логической частью authoritative journey payload
с revision semantics. Конкретное хранение (`activity` JSONB или отдельная table) выбирается в
implementation Goal. Если thread повреждён/утерян, система сохраняет task/attempt, показывает
локальный recovery и не реконструирует выдуманную историю.

## Submission state contract

| State | Primary action | Secondary actions | Mastery effect |
|---|---|---|---|
| Independent, empty | `Добавить фото` | `Ввести ответ`, `Помоги начать` | None |
| Photo ready | `Отправить решение` | Replace/remove, typed switch | Pending |
| Typed draft | `Проверить ответ` | Photo switch, clear | None, formative only |
| Typed feedback, correct | `Сфотографировать полное решение` | Edit typed answer, tutor | None; stays independent |
| Needs revision | `Исправить и проверить` | Hint/tutor, rephoto/retype | None until new independent evidence |
| Guided | `Проверить шаг` | Ask differently, exit to own attempt | Never |
| Transfer | `Отправить самостоятельное решение` | Typed formative only | AI-correct photo may add evidence |

## Feedback and recovery states

| State | Required content | Forbidden behavior |
|---|---|---|
| `correct` | Confirmed reasoning + next action | Confetti/points replacing evidence |
| `needs_revision` | Step location + evidence + why + retry | Binary «неверно» without diagnosis |
| `uncertain` | What could not be judged + recovery choices | Recording a math error |
| `wrong_photo` | Mismatch description + replace | Backend rejecting solvable handwriting semantically |
| `provider_error/offline` | Saved-state assurance + safe retry | Losing photo/draft or duplicating attempt |

## Mobile projection

- `TaskAnchor` is the page scroll container.
- `ResponseDock` is sticky at bottom with safe-area padding; it expands only for selected mode.
- `ContextualLayer` is a modal/non-modal bottom sheet depending on task obstruction; at least the
  task headline and relevant step stay visible.
- Opening tutor returns focus to its heading; closing returns focus to invoking control.
- Focused inputs are scrolled above dock/keyboard.

## Desktop projection

- Grid: `session strip` across top, `task anchor` dominant left/center, contextual rail right,
  response dock attached to work surface.
- Closed rail leaves breathing space, not placeholder cards.
- Tutor/feedback share the contextual rail but have different labels and state; AI chat never
  becomes global navigation.

## Transition invariants

1. `revision` may update content, never silently reset scroll/focus to page top during same task.
2. Problem change announces new task; layer change announces only local status.
3. Help/recovery never discards current attempt.
4. Guided → transfer is visually explicit: `Разбор закончен — теперь новая задача самостоятельно`.
5. `correct` on typed attempt cannot transition directly to mastery/topic result.
6. `uncertain` cannot decrement BKT or increment wrong-attempt telemetry.
7. Любой полученный H1–H4/tutor help ставит `support_used=true`; текущая task не может добавить
   mastery evidence, даже если следующее фото correct.
8. Help доступен в transfer; после использования текущая transfer task становится practice-only,
   а самостоятельность проверяет новая transfer task.

## Legacy API → workspace semantics

| Current server contract | Workspace semantic | Migration note |
|---|---|---|
| `photo_feedback.verdict=correct` | `correct` | Unchanged semantic; eligibility still checks submission type/support_used |
| `photo_feedback.verdict=incorrect` | `needs_revision` | Rename at view-model/API boundary |
| `photo_recovery.reason=unreadable` | `uncertain + recovery_reason=unreadable` | Keep precise rephoto action |
| `photo_recovery.reason=wrong_photo` | `uncertain + recovery_reason=wrong_photo` | Keep mismatch action |
| `photo_recovery.reason=unsure` | `uncertain + recovery_reason=unsure` | No mathematical verdict |
| `photo_recovery.reason=provider_error` | `uncertain + recovery_reason=provider_error` | Durable safe retry |
| no independent typed endpoint | `typed_submitting/typed_feedback` | New endpoint + persistence required |
| no tutor payload | contextual `tutor_open` | New authoritative thread summary required |
| `guided_step` | supported practice | Preserve; add AI semantic evaluation contract |

`uncertain` is a normalized verdict family whose UX consequence is the recovery layer. It is not a
terminal learning outcome and never changes mastery.
