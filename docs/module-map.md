# Module Map

> **Источник истины — код; при расхождении доверяй коду. Актуализировано: 2026-07-03 (граф v02, чистка dead code, тренажёр+тьютор).** Числа `~Lines` — реальный `wc -l`; назначение — из docstring/классов/route-декораторов. Быстрая live-сверка: `wc -l backend/api/routes.py`, `ls backend/core/*.py`.

**Масштаб:** 13 core-модулей без __init__ (scorers/classifiers удалены 2026-07-03), `routes.py` ~1070 строк (монолит, 19 эндпоинтов) + `routers/trainer.py` (16 эндпоинтов тренажёра), 5 Flutter-фич + 5 PWA-фич (webapp/), 20 DB-таблиц, 2525 задач / **114 нод графа v02 / 36 тем CC**.

## Backend: Core (`backend/core/`)

| File | Назначение | Ключевое | ~Lines |
|------|-----------|----------|--------|
| diagnostic.py | Двухфазный адаптивный диагностический движок (Тест на пробелы → Тест НИШ); общий traversal для всех фаз | `DiagnosticState`, `PHASE1_ANCHORS`, аддитивный скоринг (L1=15/L2=25/L3=30/L4=30%), `DIAG_MASTERY_THRESHOLD=0.5`, `write_mastery_to_db` | 1335 |
| graph_viz.py | Рендер PNG карты знаний через graphviz (диагностический «туман войны» + полный/focused режим), цвета по mastery | `COLORS`, `CLUSTER_LABELS`, graphviz-render | 663 |
| exam.py | Режим экзамена для сильных учеников: Phase A (15 `EXAM_HEADS`) → Phase B (5 самых неопределённых подтем по BKT-uncertainty); переиспользует helpers из `diagnostic.py` | `EXAM_HEADS`, `PRIOR=0.30`, `SLIP`/`GUESS` по sub_difficulty, weighted-accuracy для подтем | 599 |
| grading.py | Проверка ответа: rule-based pipeline (8 правил — нормализация/exact/numeric/fraction/units/multi-value/text) + Claude LLM фолбэк при «неверно» | `check_answer`, `check_with_claude`, `_UNITS_RE`, `_DASHES` | 531 |
| selector.py | Выбор следующей задачи: блочное чередование (5 задач/тема), приоритет spaced-rep → weakest unmastered → review → challenge; внутри ноды — raw_score cascade (Tier 1-4) | `select_next_problem`, `_pick_problem_for_node`, `_REVIEW_STALE_DAYS=7` | 438 |
| web_graph.py | Сборка JSON графа+статистики для фронта и HTML stats-страницы. Слой тем: `build_topics_payload` (topics/strands, общий для route graph_me и HTML-экспорта), `_strand_meta` (имена разделов из data-файла) | `generate_graph_data`, `build_topics_payload`, UX-порог 0.7 (НЕ трогать) | 449 |
| bkt.py | Bayesian Knowledge Tracing: обновление `p_mastery` после каждого ответа (Corbett & Anderson) | `bkt_update`, `is_mastered`, `record_attempt`, `MASTERY_THRESHOLD=0.85`, `MASTERY_ALGO_VERSION` | 230 |
| graph.py | Операции с графом знаний (Knowledge Space Theory): outer/inner fringe, prerequisites, backward walk | `get_prerequisites`, `get_dependents`, `get_mastery_map`, `get_outer_fringe` | 157 |
| config.py | Настройки из `.env` (dataclass); фикс `postgres://`→`postgresql+asyncpg://` | `settings`, `Settings`, `is_privileged`, `_fix_database_url` | 69 |
> `scorers/` + `classifiers/` (~40 модулей, ~4180 строк offline-тулинга) **УДАЛЕНЫ 2026-07-03** (chore-чистка, commit 0049629; были dead code — 0 runtime-импортов). Значения `raw_score`/`sub_difficulty` берутся как есть из `problems_v10.json` (`seed.py`).

## Backend: API & App (`backend/api/`, `backend/web.py`, `backend/run.py`)

| File | Назначение | Ключевое | ~Lines |
|------|-----------|----------|--------|
| api/routes.py | **Монолит, все 19 REST-эндпоинтов** (`prefix=/api`): auth (telegram/phone), stats/me, graph/me, **graph/public (БЕЗ auth — публичный граф)**, practice (next/answer/skip/report/exam/start), diagnostic (start/question/answer/finish/cancel/status). JWT inline, slowapi limiter | `router`, `_diagnostic_states` (process-local in-memory dict, бэкап в `student.paused_diagnostic`), `JWT_*` | 1070 |
| web.py | FastAPI app: middleware (security headers, CORS, rate-limit 60/min), `/health`, mount `/static`, отдача HTML-stats, SPA-фолбэк на `index.html` | `app`, `SecurityHeadersMiddleware`, `spa_fallback`, `save_html` | 125 |
| run.py | Точка входа: `Base.metadata.create_all` + `ALTER TABLE … IF NOT EXISTS` для отсутствующих колонок, сидинг при пустой БД, запуск uvicorn | `on_startup`, `main` | 67 |

> `_diagnostic_states` — **process-local in-memory** (`dict[int, object]`): при рестарте/мультиворкере теряется, восстанавливается из `student.paused_diagnostic` (JSONB). Практика состояние в памяти НЕ держит — всё в БД.

## Backend: DB (`backend/db/`)

| File | Назначение | Ключевое | ~Lines |
|------|-----------|----------|--------|
| seed.py | Загрузка графа (nodes+edges) и задач из JSON при пустой таблице; upsert по версии. **`seed_topics`** — идемпотентный upsert слоя тем, зовётся ВСЕГДА (не gated по nodes) | `seed_graph`, `seed_problems`, `seed_topics`, `PROBLEMS_VERSION="v10.1"` | 254 |
| models.py | SQLAlchemy-модели, **20 таблиц**: ядро (`Node`,`Edge`,`Problem`,`Student`,`Mastery`,`Attempt`,`ProblemReport`,`Setting`,`Topic`,`TopicEdge`) + тренажёр (`MicroSkill`,`DecompositionProblem`,`ProblemStep`,`ProblemFingerprint`,`ErrorCapture`,`RecurringError`,`TutorSession`,`TutorMessage`) + пилот (`Event`,`StepSubmission`) | `__tablename__` ×20 | ~385 |
| base.py | Async-движок (asyncpg), `async_session` factory, `Base` (DeclarativeBase), pool 10+5 | `engine`, `async_session`, `Base`, `get_session` | 24 |

## Backend: Scripts & Data

| File | Назначение | Ключевое | ~Lines |
|------|-----------|----------|--------|
| scripts/generate_images.py | Offline: рендер PNG-карточек для всех задач (стек-дроби, unicode-математика, адаптивная высота), запись в `static/questions[_kz]/` + поле `image_file` в JSON | `--lang ru/kz`, STIX/DejaVu fonts | 814 |
| scripts/patch_units.py | Offline: добавление подсказок единиц измерения («(Ответ в часах)») в условия задач RU+KZ | `UNIT_HINT_RU`, `--dry-run` | 388 |
| data/problems_v10.json | Банк задач — **2525 шт** (dict), привязаны к нодам; поля `raw_score`/`sub_difficulty`/`image_file` | — | ~2.4 MB |
| data/nis_knowledge_graph_v01.json | Граф знаний **v02 — 114 нод / 181 ребро** (чистка 2026-07-03, вердикт в specs); `name_ru`/`name_kz`, edges-пререквизиты | — | ~50 KB |

## Frontend: App (`frontend/apps/kodi_web/lib/`)

| File | Назначение | Ключевое | ~Lines |
|------|-----------|----------|--------|
| l10n/app_localizations.dart (+_ru/_kk) | Сгенерированные локализации (RU+KZ), по 651 строке на язык | — | 1334 / 651 / 651 |
| features/diagnostic/pages/diagnostic_page.dart | Экран диагностики: вопрос → ответ → результат, прогресс по фазам | использует problem_card/answer_input/result_card | 501 |
| features/diagnostic/bloc/diagnostic_bloc.dart | BLoC диагностики: check-session/resume/start(mode)/answer/finish | `DiagnosticCheckSession`, `DiagnosticResumeRequested` | 402 |
| features/exam/pages/exam_page.dart | Экран тайм-экзамена (N задач + таймер) | — | 375 |
| features/practice/pages/practice_page.dart | Основной цикл практики: задача → ответ → BKT-фидбек | — | 354 |
| features/dashboard/pages/dashboard_page.dart | Главный экран: hero, секции тем, статы, переходы в practice/diagnostic/graph/leaderboard | tabs, section cards | 347 |
| features/exam/bloc/exam_bloc.dart | BLoC экзамена: start(numProblems, timeMinutes) → таймер | `ExamStartRequested` | 319 |
| features/dashboard/pages/widgets/section_card.dart | Карточка темы (раскрываемая), статус mastery | `SectionCard` (Stateful) | 277 |
| features/practice/bloc/practice_bloc.dart | BLoC практики: started(tag/nodeId)/answer/skip | `PracticeStarted` | 265 |
| features/dashboard/pages/leaderboard_page.dart | Лидерборд: сортировка по количеству/точности/прогрессу | `LeaderboardSort`, `LeaderboardEntry` | 221 |
| features/auth/pages/phone_login_page.dart | Вход/регистрация по телефону+PIN | — | 219 |
| features/auth/pages/login_page.dart | Лендинг входа: Telegram OAuth (через `dart:html`) + переход на phone | использует `AppConfig.telegramBotName` | 187 |
| features/dashboard/pages/widgets/onboarding_view.dart | Онбординг для нового ученика (CTA на диагностику) | `OnboardingView` | 180 |
| features/dashboard/pages/graph_page.dart | Граф знаний: вложенная иерархия **Раздел→Тема→навык** (аккордеон, прогресс на уровнях, «Опирается на: …», fallback «Прочее»). CC-коды скрыты. **`PublicGraphPage`** (роут `/graph-public`, без auth) переиспользует `_GraphBody` | `GraphPage`, `PublicGraphPage`, `_StrandSection`, `_TopicSubCard`, `_NodeRow` | 676 |
| features/dashboard/pages/widgets/problem_section_card.dart | Карточка секции с задачами | `ProblemSectionCard` (Stateful) | 170 |
| features/auth/bloc/auth_bloc.dart | BLoC auth: check/telegram/phone-login, токен в SharedPreferences | `AuthCheckRequested`, `AuthAuthenticated`/`AuthUnauthenticated` | 128 |
| features/dashboard/pages/widgets/hero_card.dart | Hero-карточка дашборда (прогресс/CTA) | `HeroCard` | 128 |
| features/dashboard/bloc/dashboard_bloc.dart | BLoC дашборда: load (stats+graph+leaderboard) | `DashboardLoad`, `LeaderboardEntry` | 132 |
| shared/widgets/math_text.dart | LaTeX-рендеринг условий через flutter_math_fork | `MathText` | 108 |
| shared/widgets/answer_input.dart | Поле ввода ответа (числа/дроби/текст) | `AnswerInput` | 107 |
| shared/widgets/result_card.dart | Карточка результата (верно/неверно + правильный ответ) | `ResultCard` | 128 |
| features/dashboard/pages/widgets/stats_row.dart | Строка статистики (решено/точность/стрик) | `StatsRow` | 86 |
| main.dart | Entry point: `NisMathApp`, MultiBlocProvider (Locale/Auth/Dashboard), home-switch по AuthState | `NisMathApp`, smooth scroll | 81 |
| shared/widgets/problem_card.dart | Карточка задачи (условие + опц. картинка) | `ProblemCard` | 80 |
| shared/constants/tag_labels.dart | Единый маппинг тег→ярлык (RU) для dashboard+graph | `TagLabels` | 83 |
| app/router.dart | `onGenerateRoute`: dashboard/login/practice/graph/diagnostic/leaderboard/exam + 404 | `onGenerateRoute` | 64 |
| app/colors.dart | Централизованная палитра (заменяет 25+ scattered `Color(0xFF…)`) | `AppColors` (primary/success/error/warning) | 67 |
| shared/widgets/report_sheet.dart | Bottom-sheet жалобы на задачу | — | 51 |
| features/dashboard/pages/widgets/resume_banner.dart | Баннер «продолжить диагностику» | `ResumeBanner` | 52 |
| app/locale_bloc.dart | BLoC локали (RU/KK), персист в SharedPreferences | `LocaleLoaded`, `LocaleChanged` | 44 |
| app/theme.dart | Material 3 light-тема из `AppColors` | `AppTheme.light` | 40 |
| features/dashboard/pages/widgets/tab_chip.dart | Чип-таб (фильтр секций) | `TabChip` | 32 |
| shared/utils/responsive.dart | `rs()` — пропорциональный масштаб от 414px baseline | `rs`, `_designWidth=414` | 24 |
| features/dashboard/pages/widgets/section_data.dart | Модель данных секции (UI) | `SectionData` | 24 |
| features/dashboard/pages/widgets/error_view.dart | Виджет ошибки | `ErrorView` | 23 |
| app/error_l10n.dart | Маппинг BLoC error-кодов → локализованная строка | `localizeError` | 22 |
| app/config.dart | Конфиг из `--dart-define`: `apiBaseUrl`, `telegramBotName` | `AppConfig` | 12 |

## Frontend: Shared package (`frontend/packages/kodi_core/lib/`)

| File | Назначение | Ключевое | ~Lines |
|------|-----------|----------|--------|
| api/nis_api.dart | HTTP-клиент ко всем эндпоинтам: auth/stats/graph/practice/diagnostic; типизированные ошибки + локализованные сообщения | `NisApiClient`, `ApiException`, `NetworkException`, методы `getNextProblem`/`submitAnswer`/`startDiagnostic`/… | 222 |
| models/problem.dart | Модели `Problem` + `AnswerResult` (Equatable) | — | 70 |
| models/graph_node.dart | Модель `GraphNode` (нода графа + статус mastery + `topicId`) | — | 58 |
| models/graph_topic.dart | Модели `GraphTopic` (id/strand/grade/order/prereq/nodeIds) и `GraphStrand` слоя тем | — | 67 |
| models/student.dart | Модель `Student` (профиль, стрики, диагностика) | — | 45 |
| models/stats.dart | Модель `Stats` (решено/точность/освоенные) | — | 41 |
| kodi_core.dart | Barrel: реэкспорт models + nis_api | `library kodi_core` | 7 |

## Frontend: Кабинет «Работа над ошибками» (`cabinet/`) — НОВЫЙ, отдельно от Flutter

> Прото-фронт `cabinet/src/` УДАЛЁН 2026-07-03 (chore-чистка, commit 54ab122) — весь функционал перенесён в `webapp/` (useLadder/math.ts портированы). Остался только оффлайн-движок авторинга ниже (+ `cabinet/src/mock/srez.ts` как WIP-файл владельца).

### Движок авторинга лесенок (`cabinet/engine/`)
| Путь | Назначение |
|------|-----------|
| engine/author-prompt.md | Промпт агента-АВТОРА: «лесенка = шаги ЭТОГО решения» + **Definition of Done из 7 пунктов** (1 смысловой ход=1 ступень / каждая необходима / 1 вопрос / вопрос не содержит ответ / нет пересказов / последовательность / доводит). Канон для чтения/правки (обновлено 2026-06-24) |
| engine/critic-prompt.md | Промпт агента-КРИТИКА — судит против 7 пунктов DoD + явные примеры 3 частых нарушений (дробление / двойной вопрос «и» / формула-ответ в варианте) + «будь придирчив». На Sonnet ловит ~5/6 (Opus ловил 0/3). findings `{rung_index, issue, fix}` (обновлено 2026-06-24) |
| engine/ladder-engine.workflow.js | Оркестратор (Workflow): автор → критик → ≤1 правка. Вход `args.tasks[]` (grounding=эталонные steps[]); `args.model` (дефолт **'sonnet'** — плотнее/строже Opus, reversible). Критик **best-effort** (`.catch`): падение не теряет author-лесенку. Прогон 7 ≈ 1.5–3 мин |

## Тренажёр ошибок + новый фронт (Обновлено: 2026-06-26)
**Backend (новое):**
- `core/trainer.py` — match_fingerprint, build_wrong_tasks (срез→список ошибок), route_level/route_state (1/2/3 по mastery: <0.40 / <0.70 / ≥0.70 — отдельные пороги, НЕ путать с BKT 0.85), resolve_decomp, pick_easier_decomp, pick_verification_problem.
- `core/llm_openai.py` — vision-диагноз; `vision_provider` (default **gemini** через OpenAI-compat base_url, OpenAI-фолбэк); grounded-промпт (канон. ответ+шаги+wrong_answer) + «диагноз с транскрипцией»; strict json_schema; lazy-клиент + timeout + sanitized-логи (без утечки ключа).
- `api/routers/trainer.py` (НЕ растит routes.py) — GET /api/trainer/wrong-tasks, POST /api/trainer/diagnose (multipart фото, ≤8МБ, content-type allowlist, фото пишется ПОСЛЕ commit), GET /api/trainer/analytics (my_top + global_top для владельца).
- `db/seed_decomposition.py` — сид банка. `run.py:on_startup` создаёт все 6 таблиц + сидит.
**Frontend (новое, заменяет Flutter):** `webapp/` — mobile-PWA (React19+Vite+Tailwind v4+RR7+TanStack Query+vite-plugin-pwa+KaTeX), base `/app/`, served same-origin из backend (StaticFiles, Dockerfile node-stage). Дизайн-система `webapp/DESIGN_SYSTEM.md` (v3 Duolingo-style оранжевый). lib/{ladder,image,api,auth,types}.ts; features/{auth,hub,drill,closure,analytics}; components/{Button3D,Mascot,...}. Auth: phone+PIN (бэкенд /api/auth/phone/*), токен localStorage `kodi.jwt`. Старый Flutter `frontend/` + мок `cabinet/` — заморожены.

## Тренажёр: context-pack + чат-тьютор + закрытие ошибки (Обновлено: 2026-07-02)
**Backend:**
- `core/agent_context.py` — `build_agent_context(session, *, student_id, problem_id, decomp_idx=None)` → AgentContext (задача+канон. шаги+fingerprints+прошлые диагнозы+recurring_errors+mastery+тема). ЕДИНАЯ точка grounding: её потребляют и `/diagnose`, и чат.
- `core/tutor.py` — `build_system_prompt` (сократический, correct_answer только «для тебя, НЕ называй ученику») + `generate_tutor_reply` (history-трим 20); `llm_openai.chat_reply(messages)` — текстовый chat-completions без vision.
- `core/trainer.py` (+) — `build_problem_topics` (агрегат тем через nodes.topic_id, fallback через problems.node_id); WrongTask.id = **attempts.id** (стабильный, НЕ UUID — deep-link closure зависит от этого).
- `api/routers/trainer.py` (+5 endpoints) — GET `/problem-topics`; POST `/verification/start|answer` (check_answer решает правильность, resolved по node_id); GET `/easier` (climb-down, pick_easier_decomp); POST `/tutor/chat` (rate-limit 15/min, session auto-create ON CONFLICT, 503 при LlmUnavailable).
**Frontend (webapp/):** hub/`ProblemTopicsCard` (темы+closure_progress); drill/`TutorPanel` (multi-turn чат после диагноза, greeting локально без LLM); closure на живом API (`useClosure` → verification/*, инвалидация wrong-tasks+problem-topics после correct); analytics рендерит `my_top` (контракт BE, mock-fallback удалён).
