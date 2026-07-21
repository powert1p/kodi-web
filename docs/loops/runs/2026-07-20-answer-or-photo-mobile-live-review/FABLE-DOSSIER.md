# Fable full-context planning dossier

## Verbatim owner intent

Authoritative source:
`/Users/esetseitkamal/kodi-web/docs/plan/2026-07-20-answer-or-photo-mobile-live-review-source.md`.
Он дословно фиксирует три owner decisions: correct typed answer должен работать как нормальная
сдача без обязательного фото; semantic verdict принадлежит AI; все mobile/flow недостатки должны
быть найдены живым review до отдачи результата.

## Whole-task synthesis

Kodi — единый learner journey для подготовки к NIS. Ранее workspace был спроектирован photo-first:
typed ответ считался formative, AI correct оставлял ту же task, а completion/mastery требовали
фото. Owner изменил продуктовый контракт: typed и photo теперь два полноценных способа сдачи.
Текущий backend уже использует grounded AI и CAS/idempotency, но после AI correct намеренно
сохраняет feedback на прежней task. Mobile fixed dock и сохранённый scroll offset превращают это
в визуальное «зависание». Задача включает contract freeze, backend/frontend implementation,
real responsive verification, blind review и deploy exact candidate с public CJM.

## Product outcome

Ребёнок решает текущую задачу в одном workspace, сдаёт ответ текстом или фото и после AI correct
видит подтверждение и следующую задачу. Ни один tap не исчезает, ошибки восстанавливаются без
потери draft, а 375 portrait/landscape остаются понятными и пригодными с экранной клавиатурой.

## Current system and evidence

- Live baseline: `LIVE-REPRODUCTION.md`. Реальный AI вернул typed `correct` за 1254 ms, HTTP 200,
  но `sameProblem=true`, `countsForMastery=false`; console/network clean.
- Existing state machine: `backend/api/routers/journey.py`, typed lease/idempotency и AI call уже
  production-shaped; `_apply_typed_result` сохраняет feedback и не меняет stage.
- Existing UI: `webapp/src/features/journey/LearningWorkspace.tsx` и `.css`; mobile response dock
  fixed, typed field находится внутри него, task не re-focus/scroll после state settlement.
- Existing AI contract: `docs/decisions/002-ai-owned-semantic-grading.md`; semantic ownership
  сохраняется, но прежний photo-only mastery/product clause отменён новым owner source.
- Previous workspace rationale:
  `docs/loops/runs/2026-07-17-unified-learning-workspace/BRIEF.md`; stable geometry и one-surface
  полезны, typed-formative clause является anti-reference после нового решения.

## Frozen decisions and constraints

- Correct typed answer, включая mathematically equivalent value, завершает task без фото.
- Photo остаётся полноценной альтернативой на том же surface.
- Semantic verdict только AI-owned; backend не вводит authoritative arithmetic/string checker.
- Backend остаётся server-authoritative для auth/state/revision/idempotency/schema/CAS.
- Новый submit получает полный grounded task/journey context; hidden answer не показывается детям.
- Нет destructive data operations и migration; live tests только на disposable learners.
- Действующий визуальный язык сохраняется как maintenance canon; это UX/state repair, не новый reskin.
- 375×844, 844×375, 932×430 и 1280×900 — обязательные render gates; short-landscape compact
  layout определяется orientation/height, а не только width breakpoint.

## Open decisions and assumptions

Product decisions закрыты. Evidence contract тоже frozen по photo parity: первый typed
`needs_revision` и первый typed `correct` для task/outcome учитываются один раз; `uncertain` и
provider/transport errors не учитываются; supported practice не создаёт mastery evidence.
Реализация helper и transient success может быть выбрана maker без новой persisted schema.

## Whole task graph and current slice

1. M1 reproduce live submit/mobile failures → freeze API/state/UX contract and acceptance matrix.
2. M2 after M1: implement AI context + atomic typed completion + stale/retry UI + responsive repair.
3. M2 gates: backend/frontend tests → 375/844/932-landscape/1280 renders → keyboard resize proxy →
   sync ADR/design/previous workspace contract → fresh Terra blind review.
4. M3 after accepted M2: build exact candidate → deploy without data/tunnel mutation → public typed,
   photo, 429/error-recovery and responsive CJM → real mobile keyboard evidence → record
   image/rollback receipt.

Current slice is the M1 contract boundary. Implementation must not start until this planning review
reconstructs the full graph and either accepts it or one allowed planning delta closes findings.

## Approaches considered

### A. Keep typed formative and only improve copy/loading

Минимальный diff, но прямо нарушает owner decision: correct снова требует photo и ребёнок не может
закончить task выбранным способом. Rejected.

### B. Let frontend advance optimistically after AI feedback

Визуально быстро, но создаёт вторую state machine, ломает replay/CAS/resume и может показывать
несуществующий progress. Rejected.

### C. Backend-atomic typed completion with existing lease/idempotency (proposed)

AI remains semantic owner; backend applies one terminal transition under lock, persists replay
payload, then UI renders server next task and adds only transient success/focus behavior. Lowest
consistency risk and no migration.

### D. Introduce a generic asynchronous Submission service/event pipeline

Potentially unifies photo/typed long-term, but adds subsystem, queue semantics and migration-sized
surface beyond the reported defect. Deferred unless Fable identifies a concrete blocker in C.

## Proposed architecture

- Extend typed AI request with bounded `TrustedTypedContext` assembled server-side: journey id,
  revision, stage, topic/problem identity, statement, canonical steps/variants, hidden answer,
  support flags and relevant same-problem attempts. Student text remains explicitly untrusted.
- Preserve strict provider schema, confidence/evidence/echo fail-closed gate.
- Generalize mastery recording away from photo-named helper or add a typed-specific equivalent;
  record first correct and first needs-revision once per task/outcome, and respect support eligibility.
- In `_apply_typed_result`, after lease validation: incorrect/uncertain keep task + feedback;
  correct records eligible evidence, selects next transfer/topic state using existing server policy,
  increments revision once, renders, persists attempt response and commits once.
- Frontend hook applies authoritative state on stale 409 while surfacing an issue; durable attempt
  id survives transport/provider retry and is removed only after terminal accepted response.
- Workspace awaits typed submit result. Correct task identity change clears draft, scrolls/focuses
  new task heading and shows a short aria-live success. Incorrect/errors keep typed mode/draft.
- Portrait retains a compact reachable response dock. Typed mode and short visual viewport move
  dock into document flow; an orientation/height rule covers both 844×375 and 932×430 so
  landscape/keyboard never lets controls cover task or feedback.
- M2 amends `docs/decisions/002-ai-owned-semantic-grading.md`, the superseded typed-formative
  contract in `docs/loops/runs/2026-07-17-unified-learning-workspace/BRIEF.md`, and relevant
  `webapp/DESIGN_SYSTEM.md` §§6–8 so maintenance docs cannot restore mandatory photo.
- Rollback is the previous application image; no data rewrite is needed.

## Definition of Done

- AI exact/equivalent correct completes current task exactly once and opens server-selected next
  task/topic result; no photo CTA for completed task.
- Needs-revision/uncertain/provider/offline/stale paths preserve state and offer explicit recovery.
- Photo submit/recovery/guided/tutor flows remain functional.
- Acceptance matrix is green at backend/frontend, 375×844, 844×375, 932×430 and 1280×900;
  HTTP 429/503, stale, offline and replay recovery preserve the draft and do not duplicate evidence.
- M2 produces a keyboard `visualViewport`/resize-proxy artifact. M3 owner is the root release runner:
  it records public iPhone Safari or equivalent mobile WebKit evidence with task, input, feedback and
  primary action visible while the OS keyboard is open.
- ADR 002, the prior workspace BRIEF and DESIGN_SYSTEM §§6–8 explicitly reflect typed/photo parity.
- Live public run observes real AI requests for typed and photo, clean console/network and correct
  server/UI state; fresh blind reviewer finds no P0/P1.
- Deployed image fingerprint and rollback target are recorded; no owner learner data is touched.

## Executable verification

- Backend targeted pytest: correct/equivalent atomic advance, attempt replay, double submit/CAS,
  stale revision, incorrect/uncertain/provider error, grounded prompt contents and no local verdict.
- Backend full relevant suite: `.venv/bin/pytest backend/tests/ -x -q`.
- Frontend: deferred-promise pending test, correct next-task render/focus, stale state apply,
  offline retry/idempotency, photo regression; then `npm run lint`, `npm run lint:design`,
  `npx tsc -b`, `npx vitest run`, `npm run build`.
- Playwright: 375×844, 844×375, 932×430 and 1280×900; overflow, target size, active element,
  `visualViewport`/resize keyboard proxy, loading/error/success, 429/503, console/request failures
  and reduced motion. Artifacts live under this run's `evidence-local/` directory.
- Public disposable learner: full registration→route→typed correct→new task, typed recovery and
  real photo/Gemini path; record real mobile keyboard artifact under `evidence-public/`; compare
  image asset fingerprint and server logs.

## Creative latitude

Fable may challenge helper boundaries, mastery accounting details, success presentation, AI context
serialization, responsive CSS strategy, rollback packaging and test topology. It may propose a
smaller robust architecture. It may not restore mandatory photo after typed correct, add a local
semantic checker, mutate learner data, or weaken live responsive/recovery acceptance.

## Context coverage

- Owner source → frozen correct/no-photo, AI ownership and live mobile acceptance; graph M1–M3.
- `answer-or-photo-mobile-live-review-chain.md` → lossless requirement registry, milestones, bans
  and artifacts.
- `LIVE-REPRODUCTION.md` → current runtime evidence and causal diagnosis.
- `CONTRACT.md` + `ACCEPTANCE-MATRIX.md` → proposed state/API/UX boundary and executable gates.
- `docs/decisions/002-ai-owned-semantic-grading.md` → preserved AI/backend trust boundary and
  explicitly superseded photo-only clause.
- Prior workspace BRIEF → stable geometry, responsive/accessibility rationale and superseded
  typed-formative clause.
- `docs/VISION.md` → startup scope, learning outcome and architecture constraints.
- `webapp/DESIGN_SYSTEM.md` → accepted maintenance visual tokens; no redesign authority.

Excluded deliberately: credentials, JWTs, learner identifiers, raw server logs, unrelated Flutter,
cabinet and historical design runs. They do not change this answer-or-photo contract.
