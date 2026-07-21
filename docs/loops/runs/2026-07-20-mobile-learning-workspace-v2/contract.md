# Frozen benchmark contract — mobile learning workspace v2

## Objective

Пересобрать production learning workspace как удобный непрерывный учебный сценарий: ребёнок
понимает условие и одно текущее действие, сдаёт полный ответ или разбирает шаг, задаёт AI любой
контекстный вопрос и не теряет задачу, draft, focus или scroll.

## Run

- **Type:** production generator benchmark.
- **Scope:** guided content contract, AI verdict guided steps, contextual tutor, responsive
  workspace, automated and public live journey.
- **Non-goals:** DB/schema migration, новый curriculum, mastery-policy rewrite, mascot/logo copy,
  глобальный redesign остальных страниц.
- **Direction:** A «Рабочая тетрадь» из `BRIEF.md`.
- **Register:** спокойный умный наставник; editorial workbook, не admin dashboard и не card soup.
- **Anti-reference:** старый трёхколоночный workspace, giant cards, fixed mobile dock, canned tutor,
  decorative circles and old typography hierarchy.

## Frozen product invariants

- Самостоятельная задача принимает AI-confirmed typed answer или фото; correct typed answer не
  требует фото.
- Разбор по шагам начинается только по выбору ребёнка; внутри шага фото не нужно.
- AI владеет semantic verdict. Backend валидирует contract, leakage, idempotency и state changes,
  но deterministic script не выносит математический verdict.
- Задача, текущее действие, feedback и composer живут на одном route/surface.
- Tutor отвечает на фактический вопрос, grounded в активном шаге, не выдавая hidden answer.
- Guided practice не повышает mastery; новая independent transfer task подтверждает навык.
- Persisted schema и learner rows не мигрируют.

## Target journeys

1. **Independent typed:** condition → typed correct → task completes without photo.
2. **Independent photo:** condition → photo → AI result on same surface.
3. **Needs help:** condition → «Не знаю, как начать» → guided step with explicit expected action.
4. **Guided retry:** equivalent correct form accepted by AI; wrong form receives scoped, non-leaky
   feedback; unsure/provider failure preserves draft and retry.
5. **Tutor:** child asks concept, term, or «почему» question; response addresses that question,
   retains task context and refuses requests for ready answer.
6. **Return:** close tutor → exact task/step, draft, scroll and focus restored.

## Evidence matrix

- Viewports: `375×844`, `390×844`, `844×375`, `1280×900`.
- States: `independent`, `typed_pending`, `needs_revision`, `guided`, `guided_feedback`,
  `tutor_open`, `provider_error`, `success`.
- Automated journey: Chromium desktop/mobile and WebKit mobile.
- Public journey: exact deployed candidate with real AI and keyboard artifact.

## Mechanical gates

```bash
.venv/bin/pytest backend/tests/ -x -q
cd webapp && npm run lint
cd webapp && npm run lint:design
cd webapp && npm run test -- --run
cd webapp && npm run build
git diff --check
```

Live gate additionally fails on console/page errors, horizontal overflow >1 px, unnamed controls,
touch targets <44 px, obscured focus, lost draft, broken Escape/focus restore or missing Cyrillic
glyphs. `NOT_RUN`, timeout or blocked browser evidence is not PASS.

## Roles and evidence order

- Root Codex: sole maker/integrator and own-eyes reviewer.
- Fable: pre-freeze architecture/planning review.
- Fresh Terra: verifies the single Fable planning delta.
- Three fresh blind judges: score the same immutable production snapshot.

Order: `contracts → backend/AI mechanics → frontend mechanics → own-eyes live journey → immutable
snapshot → three blind judges → acceptance delta at most once → public deploy/smoke`.

## Stop rule

- `READY`: all mechanics PASS, own-eyes PASS, every rubric threshold met, all three judges
  explicitly READY, no open P0/P1, public real-AI journey PASS.
- `REPEAT`: one structural generator delta is specified and evidence is regenerated.
- `NOT_READY/UNCERTAIN`: budget or two blind delta rounds plateau below bar.
- `STOPPED_BY_OWNER`: explicit owner stop.

