# 002: AI владеет семантическим verdict в production journey

**Дата:** 2026-07-17  
**Статус:** accepted

## Контекст

Production journey проверяет не только финальное число, а полное решение ребёнка по фото и
короткий typed-ответ по server-owned эталону. Локальный `check_answer` надёжен для узких
exact/numeric контрактов, но не может определить математическую эквивалентность и корректность
альтернативного хода. Старые документы одновременно назначали владельцами verdict и backend
checker, и AI, из-за чего recovery мог ошибочно выглядеть математической ошибкой.

Канонический UX-контракт зафиксирован в
`docs/loops/runs/2026-07-17-unified-learning-workspace/AI-UX-CONTRACT.md`.

## Решение

1. В production journey AI является единственным владельцем semantic verdict для полного решения
   по фото и typed-ответа. Guided шаг валидируется отдельным server-owned контрактом и не выдаётся
   за независимое semantic evidence.
2. Backend проверяет auth, consent, ownership, task/revision, idempotency, transport и схему ответа.
   Он может только понизить недостоверный/невалидный результат до `uncertain`; он не меняет
   `correct ↔ needs_revision` и не повышает `uncertain` до математического verdict.
3. Канонический словарь UI/API: `correct | needs_revision | uncertain`. Legacy значения
   нормализуются без потери причины:

| Raw/legacy значение | Канонический verdict | `recovery_reason` |
|---|---|---|
| `correct` | `correct` | — |
| `incorrect` | `needs_revision` | — |
| `unreadable` | `uncertain` | `unreadable` |
| `wrong_photo` | `uncertain` | `wrong_photo` |
| `unsure` | `uncertain` | `unsure` |
| `provider_error` | `uncertain` | `provider_error` |
| неизвестное, malformed или несовместимое значение | `uncertain` | `unknown` |

4. AI-confirmed самостоятельное фото всей страницы и typed-ответ могут стать evidence. Для одной
   задачи учитывается максимум один `incorrect` и один `correct` outcome; повтор, provider/transport
   error, uncertain и superseded не меняют mastery. `Typed correct` атомарно завершает текущую
   задачу и открывает transfer (либо topic result), не требуя фото. После первой содержательной
   помощи authoritative `support_used=true` лишает текущую задачу mastery eligibility; понимание
   подтверждается новой самостоятельной transfer-задачей.
5. Контекст typed-проверки строит только backend: journey/revision, stage, topic/problem identity,
   условие, canonical steps/variants, hidden correct grounding и support state. Student answer и
   короткая history той же задачи передаются в отдельном fenced untrusted блоке; provider prose и
   hidden answer не попадают в UI.
6. `check_answer` остаётся допустимым в явно legacy exact-answer контрактах practice, diagnostic,
   exam и trainer closure. Он не является источником semantic verdict для submitted-photo journey.
7. `next_step` и root `revision` остаются server-authoritative. Versioned workspace envelope —
   additive projection того же состояния, а не вторая клиентская state machine.

## Совместимость, данные и rollback

- P0/P1 не меняют схему БД и не переписывают исторические строки. Legacy verdict нормализуется
  при render/read; исходная recovery-причина сохраняется.
- Fresh active journey responses получают `workspace_version=1`. Сохранённые до deploy
  `JourneyAttempt.response_payload` и старые 503 snapshots могут не иметь envelope; клиент обязан
  терпимо читать такие payload во время compatibility window.
- Неизвестные значения всегда fail-closed в `uncertain` и никогда не меняют mastery.
- Rollback приложения безопасен для данных: новых колонок и backfill нет. Старый код продолжит
  читать legacy `next_step`; additive envelope будет проигнорирован.
- Исторические агрегаты `Mastery.attempts_correct` сами по себе не доказывают происхождение от
  самостоятельного evidence. Eligibility новых попыток определяется `JourneyAttempt.kind`,
  `counts_for_mastery` и authoritative support state.

## Последствия

- P1 может стабилизировать API workspace без внедрения новых AI endpoints и без migration.
- P2 обязан реализовать hint/tutor services до включения соответствующих capability flags.
- Legacy exact-answer endpoints остаются рабочими, но их результат нельзя переиспользовать как
  semantic verdict production journey.
