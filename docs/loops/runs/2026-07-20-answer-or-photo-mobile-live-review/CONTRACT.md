# Frozen answer-or-photo contract

## Product invariant

На самостоятельной или transfer-задаче ребёнок выбирает один из двух полноценных способов
сдачи: typed answer или фото. AI-confirmed `correct` в любом из них завершает текущую задачу.
После correct typed submit фото этой же задачи не требуется.

## Typed state transition

`POST /api/journey/answer` остаётся server-authoritative и idempotent.

1. Backend под row lock валидирует auth, journey/revision/problem identity, stage, bounded input,
   client attempt id и отсутствие competing lease.
2. AI получает grounded context: journey/revision, topic/task identity, source stage, полное
   условие, canonical steps и accepted variants, hidden correct answer, typed submission,
   support state и релевантную историю попыток текущей задачи.
3. Backend принимает только schema-valid, echo-matching, evidence-verified result с достаточной
   confidence. Он может понизить ответ до `uncertain`, но не вычисляет semantic verdict скриптом.
4. `correct` и `correct + format` считаются успешной сдачей. В одной транзакции attempt получает
   terminal response, evidence учитывается не более одного раза, revision увеличивается один раз,
   а journey открывает следующую task: independent → первая transfer; transfer → следующая
   transfer либо topic result по server mastery policy.
5. `needs_revision` и `uncertain` сохраняют ту же task, draft и контекст. UI даёт повторить typed
   submit, выбрать фото или запросить помощь.

Typed submission использует ту же evidence policy, что фото: первый AI-confirmed `needs_revision`
и первый `correct` для task/outcome учитываются не более одного раза. Replay и повторный submit
того же outcome не создают дополнительного evidence. `uncertain`, provider/transport failure и
отменённый lease evidence не создают. Если task уже стала supported practice, её evidence не
считается mastery: correct всё равно завершает task, а независимое подтверждение назначается новой
transfer-задачей.

## Retry and concurrency

- Pending виден не позднее следующего animation frame; submit controls disabled до settlement.
- Повтор одного `client_attempt_id` возвращает persisted terminal response и не двигает прогресс
  второй раз.
- Другая payload с тем же id получает явный idempotency conflict.
- Stale revision применяет authoritative `error.state` к UI, показывает локальное объяснение и
  не теряет draft без подтверждённого success.
- Offline/timeout/provider error, включая HTTP 429/503, сохраняет draft и durable attempt id,
  показывает `Повторить` и оставляет фото доступной альтернативой.
- Поздний provider response после смены task блокируется CAS lease и не меняет новый экран.

## UX contract

- Task anchor, response controls и contextual feedback живут на одном route/surface.
- На correct: короткий success signal, новая задача, focus и scroll переводятся к новому task
  heading. На экране нет CTA «подтверди фото» для завершённой задачи.
- На incorrect/uncertain: условие остаётся доступным; focus переходит к feedback или полю retry,
  typed/photo switch не исчезает.
- 375×844: первый viewport показывает условие, одно primary action и переключение typed/photo;
  controls ≥44×44 px, page overflow ≤1 px.
- Compact response layout включается не только по ширине, но и при landscape/коротком visual
  viewport (`orientation: landscape` и/или height-rule, покрывающий 844×375 и 932×430). Typed form
  находится в document flow; fixed dock не перекрывает input/feedback и не занимает большую часть
  visual viewport.
- Открытая keyboard проверяется в M2 управляемым `visualViewport`/resize proxy, а перед release в
  M3 — на публичной сборке реальным iPhone Safari или эквивалентным mobile WebKit. Артефакт —
  screenshot либо screen recording с видимыми task, input, feedback и primary action.
- 1280×900: task остаётся доминирующей колонкой; feedback и response rail не сжимают математику.

## Compatibility and rollback

DB migration не требуется. Legacy stored attempts остаются читаемыми. Новый code path меняет
только новые typed attempts и additive UI behavior. Rollback образа возвращает прежнюю логику без
переписывания learner rows; тесты используют только disposable learners.
