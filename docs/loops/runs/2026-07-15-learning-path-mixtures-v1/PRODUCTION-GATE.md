# Production gate — final

## Frozen inputs

- Product brief: `BRIEF.md`
- Rubric: `RUBRIC.md`
- Browser harness: `production_e2e.py`
- Frozen evidence: `PRODUCTION-PATH-SNAPSHOT.sha256` — 19/19 files verified

## Mechanical evidence

- Backend: `176 passed` against the test PostgreSQL database.
- Final content-identity regression after the startup-log fix: `6 passed`.
- Frontend ESLint: pass; three pre-existing warnings only (`AuthContext`, `ConsentCard`, `useRoutePath`).
- Design lint: `109 files`, pass.
- TypeScript: pass.
- Vitest: `15 files`, `89 passed`.
- Production build: pass and copied into `backend/webapp_dist/`.
- Production browser E2E: `18 screenshots`; console, page, request and API error arrays are empty.
- Browser matrix: 375×844 and 1280×900, keyboard focus, touch targets ≥44 px, reduced motion and no horizontal overflow.
- Independent code re-review after manifest and explicit lesson-ID fixes: `CLEAN/READY`.

## Correctness gates

- Answer mutations carry `activity_id` and `activity_index`; stale tabs receive an authoritative `409` state under row lock.
- Async UI state is scoped by identity and lesson; late `/start` responses cannot roll back a newer answer or advance.
- Draft answer and idempotency key survive ambiguous network failure and reload until the server accepts the attempt.
- Existing databases receive stable `content_idx` identities and safe canonical problem synchronization on startup.
- Decomposition fallback fails closed unless the relationship is canonical or an explicitly validated legacy link.
- Root API returns a cumulative path with explicit course, current block, block-scoped progress and one current lesson.
- The UI renders the semantic lesson phase from `current_role`, not a raw six-activity counter.

## Own-eyes gate

- «Мой путь» makes the course → current block → next lesson hierarchy explicit and contains no daily queue or error-closure framing.
- The first mobile viewport has one primary action and no photo/chat/theory/mascot competition.
- Worked, guided, independent, transfer and result states are visually and pedagogically distinct.
- Wrong-answer support appears only after an attempt and does not reveal the answer.
- Reload restores the exact step and answer; a failed request preserves the typed value with honest copy.
- Error, empty, loading and completed states use the same material and typography.
- The desktop result evidence was re-captured after a 500 ms compositor-settle gate; no transient unpainted background remains.
- Returning from the result re-renders the cumulative path at `1 из 1`, marks the lesson as completed and exposes the persisted result action on both viewports.

## Blind panel after owner correction

- Judge A: `9.60`, `READY`, `working_product=true`.
- Judge B: `9.40`, `READY`, `working_product=true`.
- Judge C: `9.36`, `READY`, `working_product=true`.
- Panel average: `9.45`; minimum individual axis: `9.1`; every key axis for every judge is above `8.5`.
- No final high or medium delta. The only medium evidence gap — persisted return to the cumulative path — is closed by the frozen `path-completed-*` renders.

**Final verdict:** `READY` — all mechanical, correctness, own-eyes and blind-panel thresholds pass.
