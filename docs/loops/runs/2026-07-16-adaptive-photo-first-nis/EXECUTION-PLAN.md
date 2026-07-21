# Execution plan — server-owned NIS journey

## Product state machine

Сервер возвращает один discriminated `next_step`; клиент ничего не выводит из URL или
локальных флагов.

```text
profile -> exam_map -> diagnostic_intro -> diagnostic_question*
        -> diagnostic_result -> route_ready -> lesson_intro
        -> independent_task -> photo_feedback
             | correct -----------------------> transfer_task
             | retry --------------------------> independent_task
             ` explicit_help -> guided_step* -> transfer_task
        -> transfer_feedback -> topic_result -> lesson_intro(next topic)
        -> route_complete
```

`processing` — client state вокруг одного idempotent request. Provider/offline, unreadable,
wrong-photo и unsure сохраняют текущий server step и photo-attempt evidence, но не меняют
mastery. Все mutating transitions блокируют journey row `FOR UPDATE` и проверяют `revision`.

## Durable schema

### `student_journeys`

- one row per student (`student_id UNIQUE`);
- `stage`, `revision`, profile/diagnostic/route/guided JSONB;
- `current_problem_id`, `current_decomp_idx`, `current_topic_id`;
- `created_at`, `updated_at`, `completed_at`.

### `journey_attempts`

- unique `(student_id, client_attempt_id)`;
- kind: `diagnostic`, `guided`, `independent_photo`, `transfer_photo`;
- stage/topic/problem/step binding and request hash;
- status/verdict/answer/photo ref/provider/model/confidence;
- `counts_for_mastery`, response snapshot and timestamps.

On existing DB the change is additive: `CREATE TABLE IF NOT EXISTS` + indexes only. No
destructive migration.

## Curriculum fixtures

Diagnostic anchors are real bank problems and branch to an easier same-domain probe after an
incorrect answer. Current question id and queue are persisted before response:

| Domain | Anchor | Easier branch |
|---|---:|---:|
| fractions | 127 (`FR05`) | 121 |
| percent change | 321 (`PC05`) | 320 |
| word equations | 876 (`EQ04`) | 448 |
| geometry relations | 1144 (`GE04`) | 544 |
| data/graphs | 1409 (`DA02`) | 804 |

Route order is evidence-based and has at least two real lessons:

- weak percentage evidence: `PC06` first, target 1765, transfer 331;
- weak word-equation evidence with stronger percentages: `EQ04` first, target 876,
  transfer 890;
- otherwise: harder exam-relevant `PC06`, then `EQ04`.

Only verified decompositions are admitted. Diagnostic seeds BKT conservatively; a correct new
independent transfer can cross the practice threshold `0.85`. Diagnostic/exam reporting keeps
its separate `0.7` semantics.

## API contract

- `GET /api/journey/current` — create/resume and return exactly one `next_step`.
- `POST /api/journey/profile` — persist profile goal and open official-format map.
- `POST /api/journey/continue` — named transition for map, intro, result, route and feedback.
- `POST /api/journey/diagnostic/answer` — idempotent typed answer bound to issued question.
- `POST /api/journey/help` — explicit switch of the same problem to guided mode.
- `POST /api/journey/guided/answer` — typed/choice step; never mastery evidence.
- `POST /api/journey/photo` — one whole-solution photo, attempt id, revision and problem id.
- Existing `/api/trainer/consent` remains the parent-photo consent authority.

Responses never include canonical answers or expected step values. Stale revision/problem
returns `409` with a fresh safe state. Duplicate client id with the same hash returns the stored
response; another payload returns `409`.

## Mandatory tests before implementation

1. New registration lands on profile, never on a lesson.
2. Relaunch/relogin resumes every durable stage.
3. Official map tells the truth: product covers Math + Quantitative Characteristics, not all NIS.
4. Diagnostic question is persisted/bound; easier branch changes route evidence.
5. Two result patterns produce two route orders; explicit start is required.
6. Independent task accepts one photo for the whole solution; duplicate request is idempotent.
7. Help keeps the same problem, steps are typed/choice and guided never changes mastery.
8. Transfer uses a new problem/photo; only confident independent evidence updates BKT.
9. Unreadable/unsure/wrong-photo/provider/offline preserve state and do not penalize.
10. Cross-student ids, stale revisions and mismatched problem ids cannot mutate state.

Browser journeys cover new student happy path, diagnostic branch/resume, independent success,
guided→transfer, unreadable recovery, offline retry, relogin resume and keyboard/mobile access.
