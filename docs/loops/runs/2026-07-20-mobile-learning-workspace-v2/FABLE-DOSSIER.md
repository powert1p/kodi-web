# Fable full-context planning dossier

## Verbatim owner intent

`OWNER-SOURCE.md` — authoritative verbatim scope: непонятный guided input, бесполезный canned
tutor, запрет semantic grading скриптом, единый flow и требование не «пересобрать компоненты»,
а создать удобный mobile interface.

## Whole-task synthesis

AiPlus переводится из кликабельного MVP в рабочий продукт подготовки ребёнка к NIS. Ранее были
закрыты registration/adaptation/diagnostic/route и answer-or-photo: correct typed или photo может
завершить самостоятельную задачу, а AI владеет semantic verdict final submission. Текущий срез
выявил разрыв внутри supported practice: guided UI скрывает требуемое действие, deterministic
grader решает semantics, а tutor намеренно content-free и сводит любую реплику к canned prompt.
Крупная desktop-first композиция делает эти разрывы ещё тяжелее на телефоне. Нужна одна модель
учебной работы: task anchor → one current action → response → grounded feedback/help in place.

## Product outcome

После изменения новый ученик может на телефоне самостоятельно пройти independent task,
запросить разбор, понять каждый guided prompt, получить AI-проверку шага, задать помощнику
содержательный вопрос и перейти к transfer task без навигационного разрыва или обязательного фото.

## Current system and evidence

- Vision and pedagogy: `docs/VISION.md`.
- Current answer-or-photo invariant: `docs/loops/runs/2026-07-20-answer-or-photo-mobile-live-review/CONTRACT.md`.
- Design source/anti-reference: `webapp/DESIGN_SYSTEM.md`, `docs/loops/DESIGN-FLOW.md`.
- Current FE workspace: `webapp/src/features/journey/LearningWorkspace.tsx` and `.css`.
- Current guided projection and submit: `backend/api/routers/journey.py:956-979,1974-2073`.
- Current typed AI contract: `backend/core/llm_openai.py:807-850,1141-1168` and
  `backend/api/routers/journey.py:2318-2610`.
- Current tutor restriction: `backend/core/tutor.py:1240-1388`; endpoint
  `backend/api/routers/trainer.py:1442-1602`.
- API types: `webapp/src/lib/journeyApi.ts:180-187`, `webapp/src/lib/api.ts:389-395`.
- Tests: `backend/tests/test_journey_api.py`, `backend/tests/test_tutor_api.py`,
  `backend/tests/test_llm_openai.py`, `webapp/src/test/journeyPage.test.ts`.

## Frozen decisions and constraints

- Server journey remains source of truth; revision/idempotency/leases and mastery rules survive.
- AI owns semantic correctness for typed final and guided typed evidence; backend owns safety,
  schema/range/echo validation, concurrency and durable transition.
- Guided attempts never count as mastery; independent transfer confirms supported learning.
- No DB migration and no destructive data operation in this slice.
- Final correct typed answer never requires photo.
- Tutor is grounded and useful but must not leak hidden final/step answers by default.
- 375×844 is primary; 1280×900 is required; touch target ≥44px, visible focus, no page overflow.
- Old three-column workspace, giant cards/headings, forced full-screen tutor and canned moves are
  anti-reference. Brand palette may be refined, but mathematics must dominate orange/decor.
- One maker, mechanical gates, fresh blind implementation reviewer, at most one acceptance delta.

## Open decisions and assumptions

- AI guided evaluator can share the hardened typed-answer result contract if it receives only the
  current expected step as `correct_answer` plus full trusted problem/step context. Fable may
  challenge whether a separate schema is safer.
- Tutor may return free-form grounded text after strict output/schema/length validation and a
  protected-value leakage gate. Fable may challenge the exact defense-in-depth design.
- Step `input_prompt`, `format_hint` and unrelated example can be generated deterministically from
  answer shape; they must not expose `expected_value`. Fable may propose a more robust content path.

## Whole task graph and current slice

1. Registration/adaptation/diagnostic/route — existing and out of slice.
2. Independent answer-or-photo AI verdict — existing frozen invariant.
3. Guided content contract — add direct prompt/format metadata without answer leakage.
4. Guided AI evaluation — grounded semantic verdict, fail-closed state transition and retry.
5. Contextual tutor — grounded conversation, question-aware response, leakage defense and scope.
6. Mobile workspace — one continuous task/action surface consuming nodes 3–5.
7. Mechanical gates — backend/frontend tests, lint, typecheck, build.
8. Live acceptance — 375/1280, keyboard, focus, overflow, states, real AI.
9. Deploy exact accepted candidate and repeat public journey.

Current slice covers nodes 3–9. Nodes 3–5 freeze contracts before node 6; node 6 must exist before
meaningful live acceptance. Node 9 depends on all earlier evidence.

## Approaches considered

1. **Cosmetic responsive refactor only.** Preserve APIs/grading/tutor and shrink cards. Rejected:
   it cannot make an absent prompt or content-free tutor understandable.
2. **Minimal additive hints + keep canned tutor.** Safer diff, but still ignores real questions and
   violates owner decision that AI owns semantics. Rejected as incomplete.
3. **Unified workbook + grounded AI contracts.** Add step prompt metadata, AI guided evaluation,
   contextual tutor and rebuild workspace as one action stream. Chosen: smallest approach that
   actually closes causal gaps.
4. **Chat-first learning UI.** Put every event in conversation timeline. Rejected: task/math loses
   primacy and history becomes UI noise for 10–13-year-old learners.

## Proposed architecture

- Journey render adds additive guided fields: `prompt`, `format_hint`, `example`, `input_mode`.
  Expected value remains server-only. A small server formatter derives only answer-shape copy.
- Guided POST uses a new bounded AI completion built on the hardened typed result schema. Trusted
  context includes problem, all canonical steps, current step number/instruction/expected value,
  route/stage and submitted answer. Backend normalizes result to `correct|incorrect|unsure`, checks
  echo/confidence/evidence, and advances only on high-confidence correct.
- Guided AI completion is lease/idempotency-safe. Provider error/unsure persists a retryable local
  feedback state and never becomes incorrect/mastery evidence.
- Tutor prompt receives trusted task and active-step context plus bounded scoped history. Model
  returns structured `reply`, `intent`, optional `follow_up`; backend checks exact schema, length,
  control chars and protected answer values. Unsafe/malformed output becomes a contextual fallback,
  not a fake semantic response. Conversation is scoped at least by problem and active step.
- React workspace uses one DOM reading order: compact session header, task, current action region,
  response controls and inline feedback. Mobile composer is in document flow. Tutor is a modal
  bottom sheet/dialog with focus trap/restore and contextual header; desktop uses task + work rail.
- No persistence/schema change. Rollback of image restores legacy behavior; existing attempts stay
  readable because new response fields are additive.

## Definition of Done

- Guided prompt states the requested action and answer format without leaking expected value.
- AI, not `check_step_evidence`, decides guided semantic verdict; equivalent valid forms pass.
- Incorrect guided response stays on current step with concrete non-answer feedback; unsure/provider
  failure is retryable and not labeled incorrect.
- Tutor answers a contextual concept question, reacts differently to «не знаю» and «проверь мой
  ход», and never degenerates all inputs into canned next-step copy.
- At 375×844 first viewport communicates current goal/action; no overlap/overflow; keyboard path,
  focus/restore and touch sizes pass. At 1280×900 task dominates a two-zone composition.
- Correct final typed remains photo-free; all existing idempotency/mastery invariants pass.
- Full relevant backend/frontend gates are green; one fresh blind reviewer reports no P0/P1.
- Exact candidate is deployed and public smoke with real AI succeeds.

## Executable verification

- Backend targeted: `.venv/bin/pytest backend/tests/test_journey_api.py backend/tests/test_tutor_api.py backend/tests/test_llm_openai.py -q`.
- Backend full: `.venv/bin/pytest backend/tests/ -x -q`.
- Frontend: from `webapp/`: `npm run lint`, `npm run lint:design`, `npx tsc -b`,
  `npx vitest run`, `npm run build`.
- Browser render: 375×844, short landscape 844×375 and 1280×900; screenshot each key state;
  assert horizontal overflow ≤1px, controls ≥44px, console/page/request errors empty.
- Keyboard: tab order, visible focus, Enter submit, Escape closes tutor, focus returns to trigger;
  mobile virtual keyboard does not hide input/feedback/CTA.
- Real AI scenarios: equivalent guided expression accepted; wrong expression gives scoped feedback;
  tutor explains a term from current step; provider failure keeps draft and retry.
- Regression: correct final typed advances without photo; guided never increments mastery.

## Creative latitude

Fable may challenge evaluator reuse vs separate guided schema, tutor leakage guard, tutor persistence
scope, exact step-copy derivation, and mobile/desktop composition details. It may not challenge the
owner-frozen product rules: AI semantic ownership, useful contextual tutor, one continuous flow,
photo-free correct typed completion, mobile-first clarity, no mastery from guided practice.

## Context coverage

- `OWNER-SOURCE.md`: frozen owner decisions, current complaints, screenshots and acceptance intent;
  covers graph nodes 3–6 and product constraints.
- `BRIEF.md`: causal evidence, three concept alternatives, chosen direction, rules and acceptance;
  covers graph nodes 3–8.
- `docs/VISION.md`: audience, pedagogy and supported-practice/transfer outcome; covers nodes 1–6.
- prior `CONTRACT.md`: answer-or-photo, AI ownership, retry/concurrency and public mobile invariants;
  covers nodes 2, 4, 7–9.
- `docs/architecture.md`: existing server/state/AI boundaries; covers nodes 3–5 and rollback.
- `docs/loops/DESIGN-FLOW.md`: repository design workflow and render gates; covers nodes 6–8.
- `webapp/DESIGN_SYSTEM.md` is supplied only as anti-reference/current constraint history, not a
  visual canon. Broad audit history, legacy Flutter, mascot assets and unrelated routes are excluded.

