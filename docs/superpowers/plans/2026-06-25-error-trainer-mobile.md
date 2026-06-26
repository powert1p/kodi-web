# Error Trainer (mobile PWA, срез-driven) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the v1 vertical of a срез-driven "работа над ошибками" mobile PWA — student photographs a wrong handwritten solution, a cheap OpenAI vision model diagnoses *where* it broke (grounded in our canonical steps, never just revealing the answer), the student climbs a hint-ladder, reinforces with similar problems, and the system remembers recurring error types for targeting + owner analytics.

**Architecture:** Reuse the existing FastAPI + SQLAlchemy-async backend (2525-problem bank, BKT mastery, diagnostic="срез" wrong-attempts already recorded). Seed the standalone `docs/specs/full_decomposition_v1.json` (micro-skills, verified steps, error fingerprints) into DB tables so the wrong-task builder is a join, not a file-parse. Add three trainer endpoints (`/wrong-tasks`, `/diagnose`, `/analytics`) and a new OpenAI vision client. Build a **new** mobile-first React PWA in `webapp/` (porting the cabinet's pedagogy logic — `useLadder` escalation, answer-matching, hint contract — but with fresh "bold energetic" visuals), served same-origin at `/app/`. The legacy Flutter app and the `cabinet/` mock stay frozen.

**Tech Stack:** Backend — Python 3.11, FastAPI, SQLAlchemy 2.0 async + asyncpg, `openai` SDK, `pillow-heif`. Frontend — Vite + React 19 + TypeScript (strict) + Tailwind v4 + React Router 7 + TanStack Query + `vite-plugin-pwa` + KaTeX. Tests — pytest + pytest-asyncio (backend), vitest + tsc (frontend logic), Playwright MCP (visual).

## Global Constraints

- **Async only.** All handlers `async def`; DB via `await session.execute(...)` / `async_sessionmaker`. NEVER sync DB calls. (`backend/db/base.py`)
- **Parameterized SQL only.** ORM `select()` or `text()` with bind params. `text()` + `IN` → `bindparam(expanding=True)` or `= ANY(:arr)`. NEVER f-string/concat in SQL.
- **No Alembic.** New tables/columns via idempotent `CREATE TABLE IF NOT EXISTS` / `ALTER TABLE … ADD COLUMN IF NOT EXISTS` appended to the startup loop in `backend/run.py:29-48`. Timestamps `TIMESTAMPTZ DEFAULT now()`.
- **Secrets from env only.** `OPENAI_API_KEY` from env, default `""` → feature fails fast with a clear error, never hardcoded/logged. `JWT_SECRET` already required.
- **uvicorn single-worker** (process-local diagnostic state) — do not assume multi-worker.
- **Same-origin frontend.** API base is relative `/api/...`; new PWA served as static at `/app/`, no CORS additions.
- **Privacy.** Student photos → OpenAI **paid** API (NOT the data-sharing free tier). Store the file path/key in DB, never the blob. Photos under a server data dir, not in git.
- **Thresholds (do NOT unify):** `0.85` = BKT `MASTERY_THRESHOLD`; `0.7` = diagnostic/graph. Trainer level router uses its own constants defined in Task 6.
- **Comments in Russian; code identifiers English.** TypeScript strict, no `any`. Components < 150 lines, 1 component = 1 file. NEVER fonts Inter/Arial/Roboto.
- **Model id:** target `gpt-5.4-mini` (`gpt-4o-mini` is retiring). Provide a fallback chain `["gpt-5.4-mini", "gpt-5.4-nano", "gpt-4o-mini"]` and surface a clear error if none work / key missing. Verify the live id during Task 8.
- **ru+kz copy parity** for any user-facing strings that land in a shared dictionary (frontend i18n is v1-light: ru primary; keep strings in one `messages.ts` so kz can be added later).

---

## File Structure

**Backend (new/modified):**
- `backend/db/models.py` — MODIFY: add `MicroSkill`, `DecompositionProblem`, `ProblemStep`, `ProblemFingerprint`, `ErrorCapture`, `RecurringError` ORM models. **Decomp is a standalone bank** (idx-keyed; steps/fingerprints FK to `decomposition_problems.idx`, NOT to `problems.id`).
- `backend/run.py` — MODIFY: append idempotent `CREATE TABLE`/`ALTER` statements + a one-shot guarded seed call.
- `backend/db/seed_decomposition.py` — CREATE: parse `docs/specs/full_decomposition_v1.json`, upsert micro_skills + decomposition_problems (best-effort `problems_db_id` link via unique `(node_id,answer)`) + steps + fingerprints (idempotent). Created with the join-strategy docstring in Task 1.
- `backend/core/trainer.py` — CREATE: pure logic — `build_wrong_tasks`, `match_fingerprint`, `route_level`, `pick_easier_problem`, `pick_verification_problem`.
- `backend/core/llm_openai.py` — CREATE: lazy `AsyncOpenAI` client, `diagnose_photo(...)` grounded vision call with strict json_schema + fallback chain.
- `backend/api/routers/trainer.py` — CREATE: `GET /api/trainer/wrong-tasks`, `POST /api/trainer/diagnose`, `GET /api/trainer/analytics`. (New router module — do NOT grow the `routes.py` monolith.)
- `backend/web.py` — MODIFY: `include_router(trainer.router)`; mount `/app/` static; mount photo storage dir.
- `backend/core/config.py` — MODIFY: add `openai_api_key`, `openai_model_chain`, `owner_student_id`, `photo_dir`.
- `backend/requirements.txt` — MODIFY: add `openai`, `pillow-heif`.
- `backend/tests/` — CREATE: `conftest.py`, `test_trainer.py`, `test_seed_decomposition.py`, `test_llm_openai.py`, `test_trainer_api.py`.

**Frontend (new app `webapp/`):**
- `webapp/` — CREATE: Vite React-TS app. `package.json`, `vite.config.ts` (base `/app/`, vite-plugin-pwa), `tsconfig.json`, `index.html`, `tailwind` v4 via `@import`, `public/manifest.webmanifest` + icons.
- `webapp/src/lib/ladder.ts` — CREATE: ported `useLadder` escalation state machine (framework-agnostic core) + `answersMatch`/`normalizeAnswer` (from cabinet `lib/math.ts`).
- `webapp/src/lib/api.ts` — CREATE: typed fetch client (Bearer JWT, multipart for photo) + TanStack Query hooks.
- `webapp/src/lib/image.ts` — CREATE: client-side capture-compress (`createImageBitmap`→`OffscreenCanvas`→JPEG q0.8 ≤1568px).
- `webapp/src/lib/types.ts` — CREATE: `WrongTask`, `Step`, `Diagnosis`, etc. (mirror backend response shapes).
- `webapp/src/theme/` — CREATE: design tokens (CSS vars), fonts, motion primitives (ui-designer owns visuals).
- `webapp/src/features/auth/`, `features/hub/`, `features/drill/`, `features/closure/`, `features/analytics/` — CREATE: pages + components.
- `webapp/src/test/` — CREATE: vitest specs for `ladder.ts`, `image.ts`, `api.ts` parsing.

**Deploy (modified):**
- `Dockerfile` — MODIFY: add a `webapp` build stage; copy `webapp/dist` into the image; FastAPI serves it at `/app/`.
- `docker/nginx/kodi-web.conf` — MODIFY (if present): pass `/app/` and `/api/` to the app container.

---

## Phase 0 — Backend data foundation

### Task 1: Inspect `full_decomposition_v1.json` & confirm the DB-problem join key

**Files:**
- Read: `docs/specs/full_decomposition_v1.json`, `backend/db/models.py:56-78` (Problem), `backend/db/seed.py`

**Interfaces:**
- Produces: a confirmed join strategy from a decomposition `problems[]` entry → `problems.id` (documented at the top of `backend/db/seed_decomposition.py` as a module docstring). Candidates in priority order: explicit id/idx field; else `(node_id, normalized text)`; else `(node_id, answer)` positional.

- [ ] **Step 1: Dump the JSON shape** — Run:
```bash
cd /Users/esetseitkamal/kodi-web && python - <<'PY'
import json,collections
d=json.load(open("docs/specs/full_decomposition_v1.json"))
print("top keys:",list(d)[:10])
ps=d["problems"] if isinstance(d.get("problems"),list) else list(d["problems"].values())
print("n problems:",len(ps))
print("sample problem keys:",sorted(ps[0].keys()))
print("sample:",json.dumps(ps[0],ensure_ascii=False)[:800])
print("step keys:",sorted(ps[0]["steps"][0].keys()))
print("fingerprint sample:",json.dumps((ps[0].get("fingerprints") or [{}])[0],ensure_ascii=False))
print("catalog keys:",list(d.get("catalog",{}))[:5])
PY
```
Expected: prints the real field names (e.g. `idx`, `node_id`, `answer`, `primary_micro_skill`, `steps`, `fingerprints`) and confirms whether an explicit DB-problem id exists.

- [ ] **Step 2: Probe the join** — Run a script that, for 20 random decomposition entries, tries to find exactly one matching `problems` row by the candidate keys (compare `node_id` + `answer` and `node_id` + first 40 chars of text). Report match rate per strategy.

- [ ] **Step 3: Record the decision** — Write the chosen join strategy + match rate as the module docstring of a new empty `backend/db/seed_decomposition.py`. Commit:
```bash
git add backend/db/seed_decomposition.py && git commit -m "docs: confirm full_decomposition→DB problem join strategy"
```

### Task 2: New ORM models + idempotent schema

**Files:**
- Modify: `backend/db/models.py` (append after existing models)
- Modify: `backend/run.py:29-48` (extend ALTER/CREATE loop)
- Test: `backend/tests/test_schema.py`, `backend/tests/conftest.py`

**Interfaces:**
- Produces (ORM, English attrs / snake_case columns). **Decomp bank is keyed by `idx`** (the JSON's 0-based index), a standalone bank with best-effort DB linkage:
  - `MicroSkill(code: str PK, label_ru: str, domain: str|None, freq: int|None)`
  - `DecompositionProblem(idx: int PK, node_id: str FK→nodes.id RESTRICT, answer: str, primary_micro_skill: str|None, all_steps_verified: bool=False, needs_review: bool=False, problems_db_id: int|None FK→problems.id SET NULL)` — `problems_db_id` populated only where `(node_id, answer)` matches exactly one DB problem (~42%).
  - `ProblemStep(id PK, decomp_idx: int FK→decomposition_problems.idx CASCADE, n: int, instruction_ru: str, micro_skill: str, expected_value: str, verified: str|None)`
  - `ProblemFingerprint(id PK, decomp_idx: int FK→decomposition_problems.idx CASCADE, micro_skill: str, wrong_answer: str, mistake_ru: str)`
  - `ErrorCapture(id PK, student_id FK CASCADE, attempt_id: int|None FK SET NULL, problem_id FK RESTRICT, node_id, image_ref: str, transcription: str|None, failed_step: int|None, failed_micro_skill: str|None, cause_text: str|None, level: int|None, model: str|None, confidence: float|None, created_at)`
  - `RecurringError(student_id PK, micro_skill PK, node_id|None, error_count: int=0, last_seen_at|None, last_cause_text|None, resolved: bool=False, created_at)`
- Indexes: `idx_decomp_node` (node_id), `idx_decomp_dbid` (problems_db_id), `idx_problem_steps_decomp` (decomp_idx), `idx_problem_fingerprints_decomp` (decomp_idx), plus the error_captures/recurring_errors indexes below.

- [ ] **Step 1: Write the failing schema test**
```python
# backend/tests/test_schema.py
import pytest
from sqlalchemy import inspect
from db.base import engine

@pytest.mark.asyncio
async def test_new_tables_exist():
    async with engine.begin() as conn:
        names = await conn.run_sync(lambda c: inspect(c).get_table_names())
    for t in ("micro_skills","decomposition_problems","problem_steps","problem_fingerprints","error_captures","recurring_errors"):
        assert t in names, f"missing table {t}"
```

- [ ] **Step 2: Run it, expect FAIL** — `cd backend && .venv/bin/pytest tests/test_schema.py -x -q` → fails (tables missing). (If `conftest.py`/test DB is absent, create `backend/tests/conftest.py` first: an async fixture that builds the schema against a test Postgres URL from `TEST_DATABASE_URL` env, falling back to the dev DB — mirror `db/base.py` engine creation. Real Postgres, never mock.)

- [ ] **Step 3: Add the ORM models** to `backend/db/models.py` using `Mapped[...]` typing matching existing style (see `Attempt`/`Mastery` for FK + index patterns). Composite PK on `RecurringError` like `Mastery`. `DecompositionProblem.idx` is an explicit (non-autoincrement) integer PK. Add indexes `idx_decomp_node`, `idx_decomp_dbid`, `idx_problem_steps_decomp`, `idx_problem_fingerprints_decomp`, `idx_error_captures_student_node`, `idx_error_captures_created_at`, `idx_recurring_errors_micro_skill`.

- [ ] **Step 4: Add idempotent DDL to `run.py`** — append `CREATE TABLE IF NOT EXISTS …` for all six tables and any `ALTER … ADD COLUMN IF NOT EXISTS` to the existing migrations list / loop (`run.py:29-48`), so existing DBs get them too. Comments in Russian.

- [ ] **Step 5: Run the test, expect PASS** — `cd backend && python run.py` once (builds schema), then `.venv/bin/pytest tests/test_schema.py -x -q` → PASS.

- [ ] **Step 6: Commit** — `git add backend/db/models.py backend/run.py backend/tests/ && git commit -m "feat(db): trainer tables (micro_skills, steps, fingerprints, error_captures, recurring_errors)"`

### Task 3: Seed `full_decomposition_v1.json` into DB

**Files:**
- Create: `backend/db/seed_decomposition.py`
- Modify: `backend/run.py` (call seed once at startup, idempotent/guarded)
- Test: `backend/tests/test_seed_decomposition.py`

**Interfaces:**
- Produces: `async def seed_decomposition(session) -> dict` returning counts `{"micro_skills": int, "decomp_problems": int, "db_linked": int, "steps": int, "fingerprints": int}`. Per JSON entry: upsert `MicroSkill` rows from `catalog`; insert a `DecompositionProblem` keyed by `idx` with `problems_db_id` set ONLY when `(node_id, answer)` matches exactly one DB problem (else NULL — expect ~42% linked, this is normal, not an error); delete+reinsert that decomp's `ProblemStep`/`ProblemFingerprint` rows (clean re-run). Idempotent: skips if `decomposition_problems` already populated unless `FORCE_RESEED=1`. `db_linked` count logged via `logging`.

- [ ] **Step 1: Failing test** — seed against a small fixture JSON (commit `backend/tests/fixtures/decomp_sample.json` with 3 decomp entries: one whose `(node_id,answer)` uniquely matches a seeded DB test problem, one ambiguous/no-match) and assert: `decomp_problems==3`, `db_linked==1`, steps present, and a known fingerprint (`wrong_answer`,`mistake_ru`) is retrievable by `decomp_idx`.
- [ ] **Step 2: Run, expect FAIL** (`seed_decomposition` undefined).
- [ ] **Step 3: Implement** the parser using the `(node_id,answer)`-unique link strategy from Task 1 (the docstring already in this file); batch inserts; counts logged via `logging` (not print). Comments in Russian.
- [ ] **Step 4: Run, expect PASS.**
- [ ] **Step 5: Wire into `run.py`** guarded (only seeds when `decomposition_problems` empty or `FORCE_RESEED`); run `python run.py` against dev DB and confirm via SQL `select count(*) from problem_fingerprints` > 0 and that `db_linked`/`decomp_problems` ≈ 40-45% (log it).
- [ ] **Step 6: Commit** — `feat(db): idempotent seed of decomposition bank (micro-skills/steps/fingerprints, best-effort DB link)`.

---

## Phase 1 — Backend trainer core (pure logic)

### Task 4: `match_fingerprint` + answer normalization reuse

**Files:**
- Create: `backend/core/trainer.py`
- Test: `backend/tests/test_trainer.py`

**Interfaces:**
- Consumes: `core/grading.py` normalization helpers (reuse `_normalize`/numeric compare if exported; else add a thin `normalize_answer(s: str) -> str` in `trainer.py`). The `DecompositionProblem`/`ProblemFingerprint` bank from Tasks 2-3.
- Produces: `async def match_fingerprint(session, *, problem_id: int, answer_given: str) -> Fingerprint | None` where `Fingerprint` is a small dataclass `{micro_skill: str, mistake_ru: str, wrong_answer: str, decomp_idx: int}`. Resolves the candidate decomp entries for the DB problem: first any `DecompositionProblem` with `problems_db_id == problem_id` (the linked ~42%); else decomp entries sharing the DB problem's `(node_id, answer)` (the correct answer). Then returns the fingerprint among those whose `wrong_answer` matches `answer_given` (normalized, numeric-aware), else None. (93% of decomp entries carry fingerprints, so this yields a free cause hypothesis when the wrong answer is a known one.)

- [ ] **Step 1: Failing test** — seed a DB problem + a linked `DecompositionProblem` with fingerprints `{wrong_answer:"80", mistake_ru:"Перепутал знаки…", micro_skill:"int_add_sub"}`; assert `match_fingerprint(s, problem_id=pid, answer_given="80 ")` returns it (normalized match) and `answer_given="108"` (the correct) returns None; and that an unlinked problem still matches via `(node_id, answer)`.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** — resolve candidate decomp idx set, query `ProblemFingerprint` by `decomp_idx IN (...)` (`bindparam(expanding=True)` or `= ANY(:arr)`), compare normalized. Comments Russian.
- [ ] **Step 4: Run, expect PASS.**
- [ ] **Step 5: Commit** — `feat(trainer): fingerprint match (decomp bank) for free cause hypothesis`.

### Task 5: `build_wrong_tasks` (срез → trainer list)

**Files:**
- Modify: `backend/core/trainer.py`
- Test: `backend/tests/test_trainer.py`

**Interfaces:**
- Produces: `async def build_wrong_tasks(session, student_id: int, days: int = 14, limit: int = 30) -> list[WrongTask]`. `WrongTask` dataclass: `{id: str, problem_id: int, node_id: str, topic_label: str, statement: str, answer: str, primary_micro_skill: str|None, decomp_idx: int|None, steps: list[StepDTO], state: str, wrong_answer: str, mastery: float}`. `StepDTO`: `{n, instruction_ru, micro_skill, expected_value, kind: "compute", reveal: None}`. The `statement`/`answer`/`wrong_answer` come from the DB problem + attempt (always present). `steps`/`primary_micro_skill`/`decomp_idx` come from a resolved `DecompositionProblem`: prefer the linked one (`problems_db_id == problem_id`); else a same-`node_id` verified decomp entry (prefer one whose `answer` equals the DB answer, else any `all_steps_verified` entry on that node); else `steps=[]`, `decomp_idx=None` (single-step fallback handled by the ladder UI). One WrongTask per most-recent wrong attempt per problem (dedupe by problem_id, latest first). `state` from `route_state(mastery)` (Task 6).
- Helper produced here and reused by Task 6/diagnose: `async def resolve_decomp(session, *, problem_id, node_id, answer) -> DecompositionProblem | None` (the prefer-linked-else-same-node logic above).

- [ ] **Step 1: Failing test** — seed student + 2 wrong diagnostic attempts on 2 DB problems (one whose problem links to a decomp entry with steps, one on a node that has a same-node decomp but no exact link) + mastery rows; assert builder returns 2 tasks, correct `wrong_answer`/`statement`, `steps` populated from the linked decomp for #1 and from a same-node decomp for #2, dedupes a duplicate wrong attempt on the same problem.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** — SQL: `attempts` where `student_id`, `is_correct=false`, `source = ANY(:arr)` (`['diagnostic','exam','practice']`), `created_at >= now() - :days` (use `text()` with `bindparam`), join `problems`, `nodes` (topic label). Dedupe in Python by problem_id keeping latest `created_at`. For each, call `resolve_decomp` and map its `ProblemStep` rows → `StepDTO`. Use index `ix_attempts_student_source`. Comments Russian.
- [ ] **Step 4: Run, expect PASS.**
- [ ] **Step 5: Commit** — `feat(trainer): build wrong-task list from срез attempts (decomp-resolved steps)`.

### Task 6: `route_level` / `route_state` + `pick_easier_problem` + `pick_verification_problem`

**Files:**
- Modify: `backend/core/trainer.py`
- Test: `backend/tests/test_trainer.py`

**Interfaces:**
- Produces:
  - `route_level(mastery: float) -> int` — `1` if `mastery < 0.40` (не знаю тему), `2` if `0.40 <= mastery < 0.70` (забыл), `3` if `mastery >= 0.70` (описка). Constants `LEVEL1_MAX=0.40`, `LEVEL2_MAX=0.70` (distinct from BKT 0.85 / graph 0.7 — documented).
  - `route_state(mastery: float) -> str` — `"revisit"` (<0.40), `"almost"` (<0.70), `"got"` (>=0.70).
  - `async def pick_easier_decomp(session, *, micro_skill: str, exclude_idx: int|None) -> DecompositionProblem | None` — a same-`micro_skill` decomp entry with the FEWEST steps (prefer step-count 1, `all_steps_verified`), excluding `exclude_idx`; powers the ladder's climb-down rung.
  - `async def pick_verification_problem(session, node_id, exclude_problem_id) -> Problem | None` — a different same-node DB `problems` row (similar `sub_difficulty`) the student solves hint-free at closure (graded by existing `check_answer`).

- [ ] **Step 1: Failing tests** — table-driven for `route_level`/`route_state` (0.0→1/revisit, 0.5→2/almost, 0.9→3/got, boundaries 0.40 & 0.70); `pick_easier_decomp` returns a fewer-step same-micro_skill decomp entry; `pick_verification_problem` returns a different same-node DB problem.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** with the constants above; pure functions for routing, async DB for the pickers (`pick_easier_decomp` from the decomp bank, `pick_verification_problem` from DB `problems`).
- [ ] **Step 4: Run, expect PASS.**
- [ ] **Step 5: Commit** — `feat(trainer): level/state routing + easier & verification problem pickers`.

---

## Phase 2 — Backend OpenAI vision diagnosis

### Task 7: `core/llm_openai.py` — grounded photo diagnosis (mocked tests)

**Files:**
- Create: `backend/core/llm_openai.py`
- Modify: `backend/core/config.py` (add `openai_api_key`, `openai_model_chain: list[str]`, `photo_dir`, `owner_student_id`), `backend/requirements.txt` (`openai`, `pillow-heif`)
- Test: `backend/tests/test_llm_openai.py`

**Interfaces:**
- Produces:
  - `DiagnosisResult` dataclass `{transcription: str, failed_step: int|None, cause_text: str, level: int, micro_skill: str|None, confidence: float}`.
  - `async def diagnose_photo(*, image_bytes: bytes, content_type: str, statement: str, canonical_steps: list[dict], correct_answer: str, wrong_answer: str|None, fingerprint_hint: str|None) -> DiagnosisResult`.
  - Behavior: convert HEIC→JPEG via `pillow-heif`+Pillow if needed; base64 data-URL; call OpenAI **Responses/chat** with `detail:"high"` and **strict `json_schema`** (`{transcription, failed_step:int|null, cause_text, level:int(1..3), micro_skill:str|null, confidence:number}`, `additionalProperties:false`, all required with nullable unions). Prompt is **grounded**: includes canonical steps + correct answer + the student's wrong answer + optional fingerprint hint, and instructs the model to LOCATE where the student's work diverges and give a SHORT Socratic cause — never to reveal the final answer. Try `openai_model_chain` in order; raise `LlmUnavailable` if key missing or all models fail.

- [ ] **Step 1: Failing test** — monkeypatch the OpenAI client with a fake returning a known structured JSON; assert `diagnose_photo` parses it into `DiagnosisResult` and that the prompt sent includes the correct answer + steps (capture the call args). Add a test that with no key → raises `LlmUnavailable`. Add a HEIC-bytes test that conversion is attempted (monkeypatch Pillow open). Never call the real API in tests.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** — lazy `AsyncOpenAI` (mirror the lazy-init + `asyncio.wait_for` timeout pattern from `core/grading.py:_get_anthropic_client`), config-driven key/model chain, strict schema, fallback loop. Comments Russian. Add deps to `requirements.txt`.
- [ ] **Step 4: Run, expect PASS** (`.venv/bin/pytest tests/test_llm_openai.py -x -q`).
- [ ] **Step 5: Commit** — `feat(llm): OpenAI grounded vision diagnosis client (mocked)`.

### Task 8: Live smoke of the vision call (manual gate, real key)

**Files:** none (verification task)
- [ ] **Step 1:** Confirm `OPENAI_API_KEY` is set in the env. Run a tiny script that calls `diagnose_photo` on a committed sample photo `backend/tests/fixtures/sample_work.jpg` (a clear handwritten arithmetic error) with a real canonical problem. Print the `DiagnosisResult`.
- [ ] **Step 2:** Verify the live model id — if `gpt-5.4-mini` errors with "model not found", confirm the fallback chain catches it; record the actually-working id in `config.py` default and in `docs/data-state.md`.
- [ ] **Step 3:** If the diagnosis is plausible (locates the right step, doesn't dump the answer), proceed. If OCR misreads, note it in the spec's Risks and keep the "show transcription" receipt in the UI (Task 13). Commit any config id fix: `fix(llm): pin working OpenAI vision model id`.

---

## Phase 3 — Backend trainer API

### Task 9: `GET /api/trainer/wrong-tasks` + `GET /api/trainer/analytics`

**Files:**
- Create: `backend/api/routers/trainer.py`
- Modify: `backend/web.py` (`include_router`)
- Test: `backend/tests/test_trainer_api.py`

**Interfaces:**
- Consumes: `_get_current_student` auth dependency (reuse from `api/routes.py` — import or move to a shared `api/security.py` if not importable; do NOT duplicate JWT logic).
- Produces:
  - `GET /api/trainer/wrong-tasks?days=14&limit=30` → `{tasks: WrongTaskJSON[]}` (snake_case JSON of `build_wrong_tasks`).
  - `GET /api/trainer/analytics` → for current student `{my_top: [{micro_skill, label_ru, error_count, last_cause_text}], }`; if `student_id == settings.owner_student_id` also `{global_top: [...]}` aggregated across students.

- [ ] **Step 1: Failing test** — auth a test student, seed wrong attempts, `GET /api/trainer/wrong-tasks` returns 200 with the tasks; 401 without token; analytics returns `my_top` and (for owner) `global_top`.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** the router + Pydantic v2 response models; register in `web.py`. Early returns, ≤3 nesting. Comments Russian.
- [ ] **Step 4: Run, expect PASS.**
- [ ] **Step 5: Commit** — `feat(api): trainer wrong-tasks + analytics endpoints`.

### Task 10: `POST /api/trainer/diagnose` (photo → diagnosis → memory)

**Files:**
- Modify: `backend/api/routers/trainer.py`, `backend/web.py` (mount `settings.photo_dir` static if you serve thumbnails; else just store)
- Test: `backend/tests/test_trainer_api.py`

**Interfaces:**
- Produces: `POST /api/trainer/diagnose` (multipart): fields `problem_id: int`, `attempt_id: int|None`, file `photo`. Flow: validate problem; read+size-guard file (≤8MB); resolve `wrong_answer` from the attempt if `attempt_id` given else from latest wrong attempt; `match_fingerprint` for a hint; load `canonical_steps`/`answer`; call `diagnose_photo`; save the image to `settings.photo_dir/{student}/{uuid}.jpg` (`image_ref` = relative path); insert `ErrorCapture`; upsert `RecurringError` (`ON CONFLICT (student_id, micro_skill) DO UPDATE SET error_count=error_count+1, last_seen_at=now(), last_cause_text=excluded…`). Returns `DiagnosisJSON` (incl. `transcription`, `failed_step`, `cause_text`, `level`, `image_ref`). On `LlmUnavailable` → 503 with a clear message (frontend falls back to fingerprint hint / worked solution).

- [ ] **Step 1: Failing test** — monkeypatch `diagnose_photo` to return a fixed result; POST a tiny jpeg via `httpx` multipart; assert 200 + body shape; assert one `error_captures` row and one `recurring_errors` row (count incremented on a 2nd POST). Assert 503 when `diagnose_photo` raises `LlmUnavailable`.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.** `python-multipart` is already a dep. Idempotent recurring upsert via `text()` with binds. Comments Russian.
- [ ] **Step 4: Run, expect PASS.**
- [ ] **Step 5: Commit** — `feat(api): /trainer/diagnose photo→grounded diagnosis + error memory`.

---

## Phase 4 — Frontend foundation (new PWA `webapp/`)

> UI tasks specify the **component contract** (props/state/data) + **acceptance criteria** + **design direction**; the **ui-designer agent owns the visual implementation** (fresh "bold energetic" look) per the project's delegation rule — visual CSS/markup is intentionally not pixel-specified here, but every component's data contract and states ARE. Logic modules (`ladder.ts`, `image.ts`, `api.ts`) have concrete code + tests.

**Design direction (for ui-designer, all UI tasks):** Bold, energetic, mobile-first (390px primary). Oversized display headlines + high weight/size contrast; ONE dominant brand hue + 1-2 sharp accents via CSS variables; layered gradients/depth (never flat). Fonts (self-hosted, offline): **Space Grotesk** (display/numerals) + **Outfit** (body) — never Inter/Roboto. Motion: animate ONLY `transform`/`opacity`, staggered page-load reveal (150-300ms), wrap in `prefers-reduced-motion`. Every component: loading/error/empty/success. Touch targets ≥44px; inputs `font-size:16px` (no iOS zoom); safe-area insets; `min-h-dvh`. Tone: a mistake is "где растёт мозг" — never red "WRONG!", praise effort.

### Task 11: Scaffold `webapp/` + PWA shell + design tokens

**Files:** `webapp/package.json`, `vite.config.ts`, `tsconfig.json`, `index.html`, `src/main.tsx`, `src/App.tsx`, `public/manifest.webmanifest` + icons (192/512/512-maskable, apple-touch-icon 180), `src/theme/tokens.css`, `src/theme/fonts.css`, `src/index.css`

**Interfaces:**
- Produces: a running Vite app with `base: "/app/"`, `vite-plugin-pwa` (`registerType:'autoUpdate'`, shell-only precache, do NOT cache `/api/`), React Router 7 routes `/` (Hub), `/drill/:taskId`, `/closure/:taskId`, `/analytics`; TanStack Query provider; Tailwind v4 via `@import "tailwindcss"` + `@theme` tokens.

- [ ] **Step 1:** `npm create vite@latest webapp -- --template react-ts` (or hand-create); add deps: `react-router-dom@7`, `@tanstack/react-query`, `katex`, `vite-plugin-pwa`, `tailwindcss@4 @tailwindcss/vite`. `index.html`: `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">`, apple-touch-icon + `mobile-web-app-capable`. NO `maximum-scale`.
- [ ] **Step 2:** Configure `vite.config.ts` `base:'/app/'` + PWA manifest (standalone, portrait, theme/bg color, maskable icon). Tailwind v4 plugin.
- [ ] **Step 3:** ui-designer: tokens (`--color-*`, radii, fonts) in `theme/tokens.css`; self-host Space Grotesk + Outfit; base layout shell (safe-area, dvh, max-width mobile column) in `App.tsx`.
- [ ] **Step 4:** Verify `tsc --noEmit` clean and `npm run build` succeeds; `npm run dev` serves at `/app/`.
- [ ] **Step 5: Commit** — `feat(webapp): scaffold mobile PWA shell + design tokens`.

### Task 12: Logic libs — `ladder.ts`, `image.ts`, `api.ts`, `types.ts` (+ vitest)

**Files:** `webapp/src/lib/{ladder,image,api,types}.ts`, `webapp/src/test/{ladder,image,api}.test.ts`, `webapp/vitest.config.ts`

**Interfaces:**
- Produces:
  - `ladder.ts`: framework-agnostic port of cabinet `useLadder` — `createLadder(steps: Step[], easierRung?: EasierRung) ` returning `{rungs, submit(value): "correct"|"wrong"|"inserted", activeRung, attempts, hint}`. Same escalation: 1st wrong → hint; 2nd wrong on an `original` rung → splice ONE `easier` rung (climb-down), demote original; else fall through to reveal. Plus `normalizeAnswer`/`answersMatch` (fraction-aware) ported from cabinet `lib/math.ts`.
  - `image.ts`: `async compressForUpload(file: File): Promise<Blob>` — `createImageBitmap`→`OffscreenCanvas` long-edge ≤1568px→`convertToBlob({type:'image/jpeg',quality:0.8})`; normalizes EXIF/decodable-HEIC.
  - `api.ts`: typed client (Bearer from stored JWT) + TanStack hooks `useWrongTasks()`, `useDiagnose()` (multipart mutation), `useAnalytics()`; `types.ts` mirrors backend JSON.

- [ ] **Step 1: Failing vitest** for `ladder.ts` — golden sequences: correct advances; wrong shows hint; second wrong inserts exactly one easier rung; third path reveals; `answersMatch("1/2","0.5")` true, `answersMatch("3","4")` false.
- [ ] **Step 2: Run, expect FAIL** (`npx vitest run`).
- [ ] **Step 3: Implement** `ladder.ts` + `image.ts` (+ a small jsdom/`OffscreenCanvas` mock test asserting output is a jpeg Blob smaller dimensioned) + `api.ts` parse test.
- [ ] **Step 4: Run, expect PASS** + `tsc --noEmit` clean.
- [ ] **Step 5: Commit** — `feat(webapp): ported ladder logic, image compression, typed API client`.

### Task 13: Auth (minimal login)

**Files:** `webapp/src/features/auth/*`, `webapp/src/lib/auth.ts`
**Interfaces:** Produces a login that obtains a backend JWT and stores it; a route guard redirecting unauthenticated users to login. Reuse whatever the backend already accepts (inspect `api/routes.py` auth/login endpoints — likely Telegram OAuth and/or a dev login). v1: support the existing login mechanism; if only Telegram OAuth exists, add a dev "enter token"/test-login path guarded by `settings.debug` so the flow is testable, and note Telegram OAuth port as a follow-up.

- [ ] **Step 1:** Inspect backend auth endpoints; document what the webapp can call.
- [ ] **Step 2:** ui-designer + implementer: login page (contract: on success store JWT, redirect to Hub) with loading/error states.
- [ ] **Step 3:** Route guard; `tsc` clean; build passes.
- [ ] **Step 4: Commit** — `feat(webapp): minimal auth + route guard`.

---

## Phase 5 — Frontend feature screens

### Task 14: Hub — срез wrong-task list

**Files:** `webapp/src/features/hub/*`
**Interfaces:** Consumes `useWrongTasks()`. Renders a list of WrongTask cards (topic label, statement preview via KaTeX, traffic-light `state`), tap → `/drill/:taskId`. States: loading (skeleton), empty ("всё разобрано" celebratory), error (retry), success.
- [ ] **Step 1:** ui-designer: HubPage + TaskCard per design direction; KaTeX statement preview with `overflow-x` on a **wrapper** div, `throwOnError:false`.
- [ ] **Step 2:** Wire data via TanStack Query; handle all four states.
- [ ] **Step 3:** Playwright (390px): login→hub renders cards, no console errors. `tsc`/build clean.
- [ ] **Step 4: Commit** — `feat(webapp): срез hub with wrong-task cards`.

### Task 15: Drill — ladder + photo diagnosis (the headline)

**Files:** `webapp/src/features/drill/*`
**Interfaces:** Consumes a WrongTask + `ladder.ts` + `useDiagnose()` + `image.ts`. Flow: show the task; auto-`level` (from backend `state`/mastery) frames the intro copy (1 "разберём тему", 2 "вспомним метод", 3 "почти получилось — проверим где"); render the ladder (rungs, hint banner, easier-rung climb-down animation via transform/opacity); on level 3 OR a "Проверить моё решение 📸" action → camera input (`<input accept=image/* capture=environment>`) → `compressForUpload` → `useDiagnose` mutation → show **Diagnosis card**: the located failed step highlighted + Socratic `cause_text` (never the final answer) + a collapsible "что я увидел" showing `transcription` (receipts) with a "не так? поправить" affordance. On repeated failure, reveal worked step (not the final answer) as last resort.
- [ ] **Step 1:** ui-designer: DrillPage, Ladder/Rung/HintBanner, PhotoCapture button, DiagnosisCard (design direction; encouraging tone; transcription as receipts). Contract + states (idle/capturing/uploading/diagnosing/result/error-503-fallback).
- [ ] **Step 2:** implementer: wire `ladder.ts` state machine to the UI; photo capture→compress→diagnose; 503 fallback shows fingerprint hint / worked solution.
- [ ] **Step 3:** Playwright (390px): drive drill; simulate a wrong answer → hint → easier rung; trigger photo path with a stubbed/sample file → diagnosis card renders; no console errors.
- [ ] **Step 4: Commit** — `feat(webapp): drill — hint ladder + photo-diagnosis with receipts`.

### Task 16: Closure — verification reinforcement

**Files:** `webapp/src/features/closure/*`
**Interfaces:** After the ladder is solved, fetch a verification problem (same node, new numbers — backend `pick_verification_problem` exposed via a small `GET /api/trainer/verification?task=…` or embedded in the wrong-task payload) and require solving 1-2 WITHOUT hints to mark "closed"; celebratory reveal (transform/opacity). Updates local session "closed" set.
- [ ] **Step 1:** Add the verification source to the backend (extend `/wrong-tasks` payload with a `verification` field, or a tiny endpoint) + test.
- [ ] **Step 2:** ui-designer: ClosurePage + Celebration; implementer: gate "closed" on a no-hint correct solve.
- [ ] **Step 3:** Playwright: complete a task through closure; no console errors.
- [ ] **Step 4: Commit** — `feat(webapp): closure verification + celebration`.

### Task 17: Analytics view (owner + "your common mistakes")

**Files:** `webapp/src/features/analytics/*`
**Interfaces:** Consumes `useAnalytics()`. Renders the student's top recurring error types (micro-skill label + count + last cause); if owner, a global section. States: loading/empty/error/success.
- [ ] **Step 1:** ui-designer + implementer: AnalyticsPage per design direction.
- [ ] **Step 2:** Playwright: renders with seeded data; `tsc`/build clean.
- [ ] **Step 3: Commit** — `feat(webapp): error-type analytics (personal + owner)`.

---

## Phase 6 — Deploy

### Task 18: Docker build of `webapp/` + serve at `/app/`

**Files:** `Dockerfile`, `backend/web.py` (static mount of `/app/` → `webapp/dist`), `docker/nginx/kodi-web.conf` (if used), `.env` doc note for `OPENAI_API_KEY`, `OWNER_STUDENT_ID`, `PHOTO_DIR`.

- [ ] **Step 1:** Add a node build stage to `Dockerfile` (`npm ci && npm run build` in `webapp/`), copy `webapp/dist` into the image; FastAPI `StaticFiles` mount at `/app` (html=True) in `web.py`. Keep the existing Flutter serving untouched (frozen at root).
- [ ] **Step 2:** Local Docker build + `up`; `curl /health` → 200; open `http://127.0.0.1:8300/app/` → PWA loads.
- [ ] **Step 3:** Deploy: `rsync` changed files to `~/kodi-web` on `aiplus` → `ssh aiplus 'cd ~/kodi-web && docker compose up -d --build'`. Ensure `OPENAI_API_KEY` is in the server `.env`. Run the decomposition seed once on the server DB (`FORCE_RESEED=1 python run.py` inside the container, guarded). `/health` → 200.
- [ ] **Step 4: Live check** — via SSH tunnel, log in, open Hub, run one full drill incl. a real photo diagnosis, reach closure. Capture a screenshot. Record result.
- [ ] **Step 5: Commit + push** — `feat(deploy): build & serve trainer PWA at /app, OpenAI env`.

---

## Self-Review (run before execution)

- **Spec coverage:** срез hub (T14), photo→grounded diagnosis (T7/T10/T15), level routing 1/2/3 (T6/T15), hints-not-answer ladder (T12/T15), reinforcement/closure (T6/T16), error memory→targeting+analytics (T10/T17), seed decomposition (T3), new bold mobile PWA (T11-17), cheap OpenAI (T7/T8), deploy+live (T18). ✅ All spec scope mapped.
- **Out-of-scope honored:** no free-form photo, no chat-tutor (staged hints only), no theory-content generation, no other-screen migration, no Flutter deletion. ✅
- **Type consistency:** `WrongTask`/`Step`/`Diagnosis` shapes shared backend↔`types.ts`; `route_level` constants reused; `diagnose_photo` signature matches the `/diagnose` caller. ✅
- **Placeholder scan:** UI visual code is delegated to ui-designer by explicit project rule (contract + criteria given), not a placeholder; all logic steps carry concrete code/tests. ✅
- **Risk gates:** OCR misread → receipts (T15) + live validation (T8); model id drift → fallback chain + T8 pin; big seed → idempotent guard (T3).
