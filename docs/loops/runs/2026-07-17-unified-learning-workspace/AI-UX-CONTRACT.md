# AI + UX contract — проверка, тьютор и подсказки

## Contract boundary

AI владеет semantic judgment и педагогическим ответом. Backend владеет безопасной доставкой,
доступом, целостностью и сохранением состояния. UI владеет честным представлением verdict и не
превращает AI uncertainty в ошибку ребёнка.

## 1. Evaluation context envelope

Один envelope используется для photo, typed и guided evaluation; поля, которых нет для режима,
передаются как `null`, а не угадываются моделью.

```json
{
  "contract_version": "learning-evaluation.v1",
  "journey": {
    "journey_id": "server-id",
    "revision": 17,
    "student_id": "server-scoped-id",
    "locale": "ru-KZ"
  },
  "task": {
    "problem_id": 328,
    "topic_id": "fractions-part-of-remainder",
    "topic_goal": "Находить долю от оставшейся части",
    "mode": "independent",
    "stage": "independent_task",
    "statement": "…",
    "canonical_steps": [
      {"n": 1, "intent": "Найти оставшуюся долю", "expected": "5/8"},
      {"n": 2, "intent": "Взять 2/5 от остатка", "expected": "1/4"}
    ],
    "accepted_variants": [],
    "correct_answer": "1/4"
  },
  "attempt": {
    "attempt_id": "idempotent-server-id",
    "submission_type": "photo",
    "typed_text": null,
    "photo_ref": "opaque-private-ref",
    "prior_verdicts": [],
    "opened_hint_rungs": []
  },
  "learning": {
    "guided_used": false,
    "mastery_evidence": {"independent_correct": 1, "required_correct": 3}
  }
}
```

`correct_answer`, expected values and hidden rubric are model grounding, never direct UI content.
Raw personally identifying fields and public photo URLs are not part of the prompt envelope.

## 2. Evaluation response

```json
{
  "contract_version": "learning-evaluation.v1",
  "verdict": "needs_revision",
  "confidence": 0.91,
  "failed_step": 1,
  "evidence": "Ученик сразу взял 2/5 от целого и не вычел 3/8.",
  "child_message": "Сначала найди, какая часть книг осталась после 3/8.",
  "next_action": "retry_step",
  "confirmed_steps": [],
  "safety": {"answer_revealed": false}
}
```

Allowed values:

- `verdict`: `correct | needs_revision | uncertain`;
- `next_action`: `continue | retry_step | rephoto | retype | open_hint | transfer`;
- `failed_step`: integer within canonical step range or `null`;
- `confidence`: finite number `[0, 1]`.

Malformed JSON, duplicate keys, invalid enum/range, invisible-control evidence или missing
required fields fail closed to server-owned recoverable `uncertain`; backend не исправляет
semantic verdict на `correct/needs_revision` своим checker.

Backend может применить versioned confidence safety policy только как downgrade
`correct|needs_revision → uncertain` при confidence ниже frozen threshold. Это fail-closed
contract validation, а не самостоятельный semantic verdict. Backend никогда не меняет
`correct ↔ needs_revision` и не повышает `uncertain` до математического verdict.

## 2.1 Legacy verdict mapping

| Durable v0 value | v1 normalized response | UX consequence |
|---|---|---|
| `correct` | `correct` | Continue or eligible mastery evidence |
| `incorrect` | `needs_revision` | Localized feedback + retry/help |
| `unreadable` | `uncertain`, reason `unreadable` | Rephoto/retype |
| `wrong_photo` | `uncertain`, reason `wrong_photo` | Replace photo |
| `unsure` | `uncertain`, reason `unsure` | Rephoto/retype/select fragment |
| `provider_error` | `uncertain`, reason `provider_error` | Safe provider retry |

Действующий server stage `photo_recovery` может сохраниться в первой implementation delta; UI
adapter проецирует его в `uncertain` contextual layer. Причина не схлопывается в generic error.

## 3. Submission semantics

| Mode | Input | AI behavior | Mastery |
|---|---|---|---|
| Independent | Whole-page photo | Evaluate reasoning against full task context | `correct` may add evidence |
| Independent | Typed answer/explanation | Formative semantic feedback | Never adds evidence |
| Guided | Text/options for current step | Evaluate current step with prior context | Never adds evidence |
| Transfer | Whole-page photo | Evaluate independent application | `correct` may add evidence |
| Transfer | Typed answer | Formative only; ask to prove on paper | Never adds evidence |

Backend image preflight may validate file type/size, decoding, ownership and transport. Он не
должен отвергать читаемое математическое решение потому, что локальный OCR/checker его не понял.

`typed_feedback` — отдельный formative sub-state внутри текущей independent/transfer task. Даже
если AI отвечает `correct`, endpoint сохраняет attempt/feedback, не открывает transfer/topic
result, не пишет mastery, а возвращает primary action `Сфотографировать полное решение`.

## 4. Contextual tutor contract

Tutor thread scoped to:

`student + journey + problem + server stage + canonical step context`.

Каждый turn получает:

- full task statement and topic goal;
- current mode/stage and visible feedback;
- learner attempt/evidence and prior turns;
- canonical reasoning as hidden grounding;
- opened hint rung and whether answer reveal is allowed;
- mastery rule and required next independent evidence.

Tutor never claims to have seen data outside the envelope. На открытие `Мне нужна помощь` он
отвечает одним question/orienting move, а не длинной лекцией.

### Tutor response shape

```json
{
  "message": "В условии есть слова «из оставшихся». Что нужно найти до того, как брать 2/5?",
  "kind": "socratic_question",
  "grounded_step": 1,
  "suggested_actions": ["answer_tutor", "open_next_hint", "return_to_solution"],
  "answer_revealed": false
}
```

UI показывает task/step provenance (`По этой задаче · шаг 1`), чтобы assistant не выглядел
универсальным чатом.

## 5. Hint ladder policy

| Rung | Purpose | Allowed | Forbidden |
|---|---|---|---|
| H1 | Orient attention | Point to phrase/quantity/diagram | Formula with substituted numbers |
| H2 | Elicit strategy | One Socratic question | Naming the final operation chain completely |
| H3 | Recall relation | General rule/model + analogous symbols | Computed task answer |
| H4 | Work one micro-step | Demonstrate only nearest step after learner attempt | Full worked solution or final answer |

Full solution is a separate explicit action after an attempt and acknowledgement: `Показать полный
разбор`. It sets `guided_used=true`, records `answer_revealed=true` and schedules a fresh transfer
task. Rapid hint-click telemetry is captured for product evaluation, not punishment.

Простое открытие слоя не меняет mastery. Первый полученный H1–H4 или содержательный tutor response
ставит authoritative `support_used=true`; current task становится practice-only. Это же правило
действует в transfer: помощь доступна, но после неё требуется новая transfer task.

## 6. UI presentation

- Verdict headline ≤1 line; evidence ≤3 short lines; one primary recovery/continue action.
- `needs_revision` avoids punitive red as page material; icon + label + location carry meaning.
- `uncertain` literally says that AI did not issue a mathematical verdict.
- Long explanation is progressive disclosure through tutor; task remains visible.
- Photo/typed/tutor controls expose accessible names and current mode.
- New AI message/status uses `aria-live="polite"`; blocking recovery uses assertive alert only when
  action cannot continue.

## 7. Backend responsibilities

- authenticate and authorize learner/task;
- verify consent before photo transport;
- enforce attempt idempotency and revision ordering;
- persist upload, processing lease, raw provider response, normalized safe response and telemetry;
- persist authoritative `support_used`, highest hint rung and tutor thread summary under journey
  revision semantics; physical storage is an implementation decision;
- validate response schema, enum, finite confidence, failed-step range and text safety;
- return recoverable uncertainty for provider/schema/safety failure;
- update mastery only from eligible independent photo evidence;
- prevent stale tutor/evaluation response from overwriting newer revision.

## 8. UI responsibilities

- never infer verdict from color, confidence or text fragments;
- render only normalized server response;
- preserve task, attempt and local draft across layer changes;
- distinguish `AI проверяет` from `Ответ сохранён` and from final verdict;
- do not show hidden expected values/correct answer from context payload;
- return focus correctly when sheets/rails open and close;
- label formative typed result as not-yet mastery evidence.

## 9. Required evaluation tests for the next Goal

1. Correct alternative reasoning path → AI `correct`, backend preserves verdict.
2. Wrong first/middle/final step → localized `needs_revision` within valid range.
3. Ambiguous handwriting/partial crop → `uncertain`, no BKT penalty.
4. Typed semantically equivalent answer → formative correct, no mastery change.
5. Guided answer → feedback, no mastery change.
6. Malformed JSON/duplicate keys/NaN/out-of-range step/invisible controls → safe `uncertain`.
7. Duplicate attempt/reload/provider retry → one durable attempt and same result.
8. Stale response after stage change → rejected without overwriting new state.
9. Tutor H1–H4 → no early final-answer leakage; reveal marks guided and creates transfer.
10. Cross-account/problem draft or thread reuse → fail closed.
