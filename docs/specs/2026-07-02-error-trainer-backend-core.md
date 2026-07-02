# Тренажёр ошибок — ядро + ИИ-тьютор (backend-фундамент + PWA)

**Дата:** 2026-07-02 · **Ветка:** feat/error-trainer-mobile · **Репо:** kodi-web

## Цель
Тренажёр работает по кускам: closure сидит на моке, analytics-контракт рассинхронен FE↔BE, climb-down не экспонирован, а после диагноза ученик остаётся один на один с ошибкой — нет продолжения разговора. Довести флоу до конца: живой verification, «мои проблемные темы» в hub, multi-turn чат с ИИ-тьютором после диагноза — чтобы ученик закрывал ошибку с сопровождением, а не бросал.

## Scope
1. Дочинить ядро: verification API (closure с мока → живые данные), analytics-контракт, climb-down endpoint.
2. Агрегат «проблемные темы» через CC-таксономию + endpoint для hub.
3. Единый context-pack сервис (grounding для diagnose и чата).
4. Multi-turn чат-тьютор: 2 таблицы + endpoint + чат-панель в drill.
5. PWA: hub-блок «Мои проблемные темы», чат-панель после диагноза, closure на живом API.

## Out-of-scope (НЕ делать, не «улучшать» попутно)
kz-локализация; Flutter-фронт и граф-визуализация; remap micro_skill 372→337; стриминг чата; streak/points-геймификация; генерация контента (cabinet/engine); SPA deep-link 404 (известный баг — оставить как есть). НЕ удалять legacy `node.tag` / `micro_skills.domain`. НЕ трогать `POST /diagnose` core-логику (только вызывать новый context-pack).

## Продуктовые решения (из ответов пользователя)
- Полный флоу за один заход: бэк-фундамент + multi-turn чат с ИИ-тьютором после диагноза (endpoint + чат в drill-экране PWA).
- «Проблемные темы» ученик видит в hub тренажёра (PWA): тема → кол-во ошибок → прогресс закрытия. Flutter-граф не трогаем.

## Технические решения (обоснование в 1 строку)
1. **Каноническая таксономия = CC-слой** (strand→topic→node→micro_skill); агрегация тем идёт через `nodes.topic_id`→`topics.strand`. — единый источник группировки, `node.tag`/`micro_skills.domain` остаются legacy (пометить deprecated в docs/data-state.md).
2. **372→337 remap НЕ делаем**, `cc_topic_skill_tree.json` — архив. — remap затронул бы прод-данные recurring_errors ради нулевой ценности сейчас.
3. **«Проблемные темы» = агрегат, не новая графовая структура**: считаем из error_captures/recurring_errors/mastery, новых таблиц-графов нет. — память уже в существующих таблицах.
4. **Context-pack сервис** `core/agent_context.py:build_agent_context(session, student_id, problem_id, decomp_idx)` — единая сборка для diagnose-промпта и чата. — ИИ всегда получает максимум grounding из БД.
5. **Чат — в БД** (`tutor_sessions`/`tutor_messages`), не in-memory. — переживает рестарт; single-worker и так требование (ARCH-1).
6. **Чат без стриминга** (request/response), Gemini flash через `core/llm_openai.py`, сократический промпт, лимит истории 20 сообщений. — MVP; тот же провайдер, что diagnose.
7. **DDL идемпотентно в `run.py`** (`CREATE TABLE IF NOT EXISTS`), Alembic нет. — паттерн проекта (см. run.py:52-133).
8. **Analytics: FE → BE-контракт** `{my_top, global_top}` (BE — source of truth), убрать mock-fallback в `api.ts`. — сервер правильнее, FE-тип `error_types` мёртв.

## Файлы
**Backend (new)**
- `backend/core/agent_context.py` — `build_agent_context(...)`: задача (problems.text_ru/answer) + канонические шаги (problem_steps по decomp_idx) + fingerprints (problem_fingerprints) + прошлые диагнозы ученика (error_captures по student_id+node_id) + recurring_errors по релевантным micro_skills + mastery узла + topic-контекст (topics по nodes.topic_id). Возвращает dataclass/dict для system-промпта.
- `backend/core/tutor.py` — сборка сократического system-промпта из context-pack + вызов `llm_openai` chat-completions (без vision); helper на history-трим (последние 20).

**Backend (edit)**
- `backend/db/models.py` — добавить `TutorSession`(id, student_id FK, problem_id FK, node_id, created_at) и `TutorMessage`(id, session_id FK CASCADE, role['user'/'assistant'], content, created_at); индекс `idx_tutor_messages_session`.
- `backend/run.py` — после строки 133: `CREATE TABLE IF NOT EXISTS tutor_sessions/tutor_messages` + индекс (идемпотентно).
- `backend/api/routers/trainer.py` — добавить endpoints:
  - `GET /api/trainer/problem-topics` → per-topic: `topic_id, strand, name_ru, error_count, top_micro_skills[], nodes_mastery_avg, closure_progress`. Агрегат: error_captures→problems.node_id→nodes.topic_id→topics. **Fallback:** если у attempt/capture нет decomp-линка — group через `problems.node_id` (не только decomposition_problems). Считать по ВСЕМ темам ученика, не только первой.
  - `POST /api/trainer/verification/start` (body: task/problem_id) → `pick_verification_problem(node_id, exclude_problem_id)` → problem для closure.
  - `POST /api/trainer/verification/answer` (body: problem_id, answer) → сверка через `core.grading.check_answer` → correct + при correct UPDATE `recurring_errors.resolved=true` по micro_skill.
  - `GET /api/trainer/easier?decomp_idx=&micro_skill=` → `pick_easier_decomp(...)` → EasierDecompRow-shape (climb-down).
  - `POST /api/trainer/tutor/chat` (body: problem_id, decomp_idx?, message) → auto-create/reuse session по (student, problem_id), history из БД, context-pack в system, ответ ассистента; persist обе реплики. `@limiter.limit("15/minute")` (паттерн routes.py:186).
  - Слить diagnose-промпт на `build_agent_context` (context-pack единый), не менять response-схему `DiagnosisOut`.

**Frontend (webapp/, edit)**
- `src/lib/types.ts` — `AnalyticsData` → `{ my_top: RecurringErrorOut[], global_top?: GlobalErrorOut[] }` (зеркало BE); добавить `ProblemTopic`, `TutorMessage`, `VerificationProblem` (from BE).
- `src/lib/api.ts` — `fetchAnalytics` читать `my_top` (убрать `error_types` + mock-fallback); добавить `fetchProblemTopics`, `startVerification`/`answerVerification`, `sendTutorMessage`, `fetchEasier` + хуки.
- `src/features/hub/HubPage.tsx` (+ new компонент) — блок «Мои проблемные темы» из `problem-topics`: тема → error_count → closure_progress. AiPlus (ApCard/ApTag, orange #FF8C00, DM Sans).
- `src/features/drill/DrillPage.tsx` + new чат-панель — после диагноза multi-turn чат (`tutor/chat`), loading/error/empty states.
- `src/features/closure/ClosurePage.tsx` + `useClosure.ts` — с `MOCK_VERIFICATION` на `verification/start` + `verification/answer` (живой API).
- `src/features/analytics/AnalyticsPage.tsx` — рендер `my_top` без mock-fallback.

## Критерии успеха (проверяемые)
- `.venv/bin/pytest backend/tests/ -x -q` зелёный с `TEST_DATABASE_URL` (реальный Postgres): новые тесты на `agent_context`, `problem-topics`, `tutor/chat` (happy + 401 + empty), `verification/start|answer`, `easier`.
- SQL-инвариант: `problem-topics.error_count` по каждой теме == raw `SELECT count(*) FROM error_captures ec JOIN problems p ON p.id=ec.problem_id JOIN nodes n ON n.id=p.node_id WHERE n.topic_id=:tid AND ec.student_id=:sid` (сходится по ВСЕМ темам).
- `tsc` + `vite build` webapp чистые (0 errors).
- Playwright (same-origin, JWT в localStorage `kodi.jwt`): hub показывает проблемные темы; drill → фото → диагноз → чат отвечает; closure решается на живом API; analytics рендерит `my_top` без mock.
- Деплой VPS (rsync + `docker compose up -d --build`, .claude/rules/deploy.md) → `/health` 200 + один живой запрос `tutor/chat` возвращает ответ.

## Риски
- Латентность/качество Gemini flash в диалоге → митигируем grounding-пакетом + существующей fallback-цепочкой моделей.
- 7 из 43 тем пустые; `attempts.source=practice` может не иметь decomp-линка → агрегат ОБЯЗАН иметь fallback через `problems.node_id` (иначе темы «пропадут»); заметим SQL-инвариантом.
- Чат = новые LLM-затраты → `@limiter.limit("15/minute")` на chat-endpoint; заметим по логам rate-limit.
