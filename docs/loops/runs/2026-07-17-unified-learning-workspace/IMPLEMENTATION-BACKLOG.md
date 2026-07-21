# Implementation backlog — unified learning workspace

## Delivery rule

Implement this as one coherent learner flow, not as isolated screens. The server remains the
authority for stage/revision/mastery. React owns presentation, compatible drafts and focus only.
The first production slice is complete only when a learner can finish the full photo-first cycle
inside one workspace on mobile and desktop.

## Dependency graph

```text
P0 Contract/ADR
    ├── P1 Journey response contract ── P4 Stable React workspace ── P5 Context + dock
    ├── P2 AI semantic services ──────── P5 Context + dock
    └── P3 Durable support/resume ────── P5 Context + dock
                                              └── P6 E2E + rollout gates
```

No packet may redefine the frozen mastery rules or introduce a client-owned journey state
machine. P1–P3 may be implemented in parallel worktrees only after P0 freezes the contract; P4/P5
must be integrated by one frontend maker.

## P0 — decision record and canonical contracts

**Outcome:** old and new grading/help semantics no longer contradict each other.

**Files**

- `docs/decisions/`: new ADR for AI-owned semantic grading and formative typed answers.
- `docs/VISION.md`: replace the old backend-exact-checker ownership wording.
- `docs/architecture.md`, `docs/module-map.md`, `docs/data-state.md`: synchronize the state,
  endpoint and persistence contract.
- Frozen source: `AI-UX-CONTRACT.md`, `STATE-MAP.md`, `CONCEPT-SELECTION.md` from this run.

**Decisions to record**

1. Provider verdicts normalize to UI semantics `correct | needs_revision | uncertain`.
2. Backend validates schema, safety, consent, revision, ownership and idempotency; it may downgrade
   to `uncertain`, but may not independently flip `correct ↔ needs_revision` or promote
   `uncertain`.
3. Photo is mastery-capable; typed, hinted, tutored and guided work is formative/practice-only.
4. Receiving substantive help sets authoritative `support_used=true`; transfer help is allowed
   but requires a new unaided transfer task.
5. `next_step` remains authoritative; stable workspace projection is a client adapter.

**Acceptance**

- One vocabulary table maps legacy provider values (`incorrect`, `unreadable`, `wrong_photo`,
  `unsure`, `provider_error`) to journey/UI state without loss of recovery reason.
- No canonical doc still says that backend exact-string/equation code owns the mathematical
  verdict for a submitted solution photo.
- ADR includes rollback/fail-closed behavior and data migration impact.

## P1 — versioned journey workspace envelope

**Outcome:** every active learning stage contains enough shared data to keep the task mounted.

**Files**

- `backend/api/routers/journey.py`
- `backend/core/journey.py`
- `webapp/src/lib/journeyApi.ts`
- `backend/tests/test_journey_api.py`

**Contract delta**

Extend the active-learning response with a versioned workspace envelope; do not make the client
reconstruct it from stage-specific fields:

```json
{
  "workspace_version": 1,
  "task": {
    "journey_id": 12,
    "problem_id": 431,
    "topic": {"id": "fractions", "title": "Смысл дробей"},
    "mode": "independent",
    "statement": "…",
    "position": 3
  },
  "learner_evidence": {"kind": "photo", "status": "ready", "label": "IMG_4979.heic"},
  "context_layer": {"kind": "closed"},
  "response": {"default_mode": "photo", "typed_available": true, "help_available": true},
  "support": {"used": false, "highest_hint_rung": 0},
  "revision": 18
}
```

The existing `next_step` may remain during a compatibility window. The response serializer must
derive both from the same authoritative journey state and fail tests if their identities diverge.

**Acceptance**

- `independent_task`, `photo_processing`, `photo_feedback`, `photo_recovery`, `guided_step`,
  `transfer_task` and `transfer_feedback` all return stable task identity and complete statement.
- Processing/recovery retains submitted evidence metadata.
- A stale revision returns the current authoritative state; it never clears the current task.
- Contract tests cover every active stage and legacy compatibility.

## P2 — AI-owned evaluation, typed feedback, hints and tutor

**Outcome:** semantic judgment and help use the full task context instead of mechanical answer
matching or an ungrounded universal chat.

**Files**

- `backend/core/llm_openai.py`
- `backend/core/tutor.py`
- `backend/api/routers/journey.py`
- `backend/api/routers/trainer.py` only if shared internals are extracted; journey remains the
  learner-facing API.
- `backend/tests/test_llm_openai.py`
- new/extended `backend/tests/test_journey_ai.py`

**API additions**

- `POST /api/journey/typed`: formative semantic evaluation for independent/transfer.
- `POST /api/journey/hint`: returns the next allowed H1–H4 rung for the current task/revision.
- `POST /api/journey/tutor`: one task-scoped conversational turn with a bounded thread summary.

All mutation requests include `revision`, `problem_id` and a unique `client_attempt_id` or
`client_turn_id` where replay matters.

**Shared context envelope**

- journey/revision/student/task/topic/mode/server stage;
- full statement, canonical steps, accepted variants and hidden correct answer;
- current submission and prior attempts/feedback;
- opened hint rung, tutor summary, `support_used` and mastery eligibility;
- explicit instruction that image/user text is untrusted data, not prompt control.

**Normalized outputs**

- Photo/typed: `verdict`, `failed_step`, short `evidence`, `feedback`, `confidence`,
  `recovery_reason` when uncertain.
- Hint: `rung`, `message`, `grounded_step`, `answer_revealed`.
- Tutor: `message`, `kind`, `grounded_step`, `suggested_actions`, `answer_revealed`.

**Acceptance**

- Correct alternative reasoning is accepted; first/middle/final divergence localizes to a valid
  canonical step.
- Malformed JSON, duplicate keys, NaN, out-of-range step, invisible controls, provider failure or
  low-confidence ambiguity normalizes to `uncertain` with no mastery penalty.
- Typed-correct response stores feedback but cannot advance transfer/topic result or mastery.
- H1/H2 never reveal the operation chain or final result; H3 recalls only a general relation; H4
  solves at most the nearest micro-step. Full reveal is a separate explicit action.
- Tutor starts with one Socratic move, cites the current task/step, and cannot claim unseen context.
- No endpoint returns hidden expected values to the browser.

## P3 — durable support, tutor and resume state

**Outcome:** reload, reconnect and provider retry restore the same learning context.

**Files**

- `backend/db/models.py`
- `backend/run.py` plus the project’s accepted fresh-schema/migration path
- `backend/api/routers/journey.py`
- `docs/data-state.md`
- database/journey tests

**Persist authoritatively**

- `support_used`, `guided_used`, `answer_revealed`, highest hint rung;
- bounded tutor thread summary and last grounded step;
- typed attempt/feedback with `counts_for_mastery=false`;
- photo processing lease, normalized result, recovery reason and provider provenance;
- client idempotency key and response payload for every replayable mutation.

Physical storage may extend `StudentJourney.activity`/`JourneyAttempt` JSON first if indexed query
requirements do not justify another table. The ADR/data-state update must document the choice and
forward migration. No destructive migration is permitted without owner approval.

**Acceptance**

- Server resume lookup uses stable `student_id + journey_id`; the returned snapshot contains the
  current `problem_id + server_stage + revision`.
- `problem_id`, stage-specific identity and `revision` are mutation preconditions, not lookup
  keys; a stale precondition returns the current authoritative snapshot.
- Reload during processing, feedback, hint or tutor restores the same task and durable state.
- Cross-student/problem draft or thread reuse fails closed.
- Duplicate delivery produces one attempt/turn and the same response.
- A stale provider/tutor result cannot overwrite a newer revision.

## P4 — stable React `LearningWorkspace`

**Outcome:** active learning no longer swaps full-screen components as `next_step.type` changes.

**Files**

- `webapp/src/features/journey/JourneyPage.tsx`
- `webapp/src/features/journey/JourneyPage.css`
- new `webapp/src/features/journey/workspace/` components and tests
- `webapp/src/lib/journeyApi.ts`

**Components**

- `LearningWorkspace`
- `SessionStrip`
- `TaskAnchor`
- `ContextualLayer`
- `ResponseDock`
- `ProofThread`
- `TutorSheet`

Pre-study profile/diagnostic/route screens stay outside this shell. `lesson_intro` is the last
allowed handoff screen; from `independent_task` through `topic_result`, the route and task shell
remain stable.

**Acceptance**

- `TaskAnchor` does not unmount when the server moves through processing, feedback, recovery,
  hint, tutor or guided states for the same problem.
- Scroll position, compatible draft and focus survive contextual layer changes.
- Mobile 375×844 and desktop 1280×900 match selected concept composition, not the prototype’s
  implementation details.
- No active-task bottom navigation, dashboard shortcuts, floating generic chat or second primary
  CTA appears.
- All interactive targets are ≥44 px, names are exposed, reduced motion is supported, and there
  is no horizontal overflow at 320–1280 px.

## P5 — response dock and contextual learning loop

**Outcome:** the child can submit, recover, ask for help and continue without leaving the task.

**Files**

- workspace components from P4
- `webapp/src/lib/journeyApi.ts`
- `webapp/src/test/journeyPage.test.ts`
- new component/state tests under `webapp/src/test/`

**State behavior**

1. Empty independent task: photo primary; `Ввести ответ` and `Помоги начать` visible.
2. Photo ready: preview/name, replace/remove, submit primary.
3. Processing: same problem/evidence, explicit saved/checking distinction, no duplicate submit.
4. `needs_revision`: first divergence, evidence, why and retry; hint/tutor secondary.
5. Typed feedback: semantic result, explicit formative label, photo proof primary.
6. Hint: H1–H4 rung/provenance and return-to-work primary.
7. Tutor: anchored sheet with thread, response field, send and independent close path.
8. `uncertain`: explicit no-verdict copy, preserved evidence, re-photo primary and typed/provider
   recovery secondary.
9. Transfer: help remains possible but marks this transfer practice-only and schedules a fresh one.

**Acceptance**

- One primary action per state and exactly one visible input mode at a time.
- Hint/tutor opening alone changes no mastery eligibility; first substantive response updates the
  authoritative revision and support flag.
- Closing help returns focus to the invoker and retains the learner draft.
- AI messages/status announce through `aria-live="polite"`; blocking recovery is assertive only
  when action cannot continue.
- Error copy never records unreadable/ambiguous/provider failure as a mathematical mistake.

## P6 — production verification and release gate

**Outcome:** the complete child journey is observed, not inferred from unit tests.

**Mechanical gates**

- Backend: `.venv/bin/pytest backend/tests/ -x -q`.
- Frontend: project lint/typecheck/test commands and production build.
- Playwright/browser at 375×844 and 1280×900 with console capture.
- Real AI smoke with a correct photo, wrong-step photo, ambiguous HEIC and provider retry; redact
  student/photo data from retained logs.

**Required end-to-end journeys**

1. New learner → profile/diagnostic/route → lesson → photo correct → transfer → topic result.
2. Photo `needs_revision` → retry same task → correct.
3. Photo ambiguous/HEIC → `uncertain` → re-photo and typed recovery.
4. Typed-correct → formative feedback → full photo required → mastery only after eligible photo.
5. Hint H1/H2 → return to own work → practice-only → fresh transfer.
6. Tutor turn → reload → thread/task restored → continue independently.
7. Offline/double-submit/stale revision/provider retry → one durable attempt, no lost task.
8. Keyboard-only and 200% text zoom → visible focus, reachable dock, no obscured input/overflow.

**Observability**

Record stage transition, submission mode, verdict/recovery reason, support rung, tutor turn,
revision conflict, retry and latency. Never log photo bytes, hidden answers or raw private tutor
text in analytics.

**Release bar**

- All required journeys pass on both viewports with zero console errors and no open P0/P1.
- Independent reviewer returns READY against `AI-UX-CONTRACT.md`, `STATE-MAP.md` and
  `CONCEPT-SELECTION.md`.
- Production deploy and smoke are a separate explicitly authorized action after local/staging
  acceptance; this backlog does not authorize deployment.

## Recommended execution Goals

1. **Contract + backend Goal:** P0–P3 with AI/schema/database tests; no UI redesign.
2. **Workspace Goal:** P4–P5 against mocked and live journey responses; responsive render loop.
3. **Production acceptance Goal:** P6, real AI/photo CJM, deploy and post-deploy smoke after owner
   authorization.

Do not collapse these into “registration + one happy path”. The definition of the product slice is
the complete continuous learning loop, including revision, uncertainty, help, resume and mastery
eligibility.
