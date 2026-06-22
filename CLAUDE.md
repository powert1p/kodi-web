# kodi-web — Agent Instructions

Адаптивная платформа по математике для НИШ. **Flutter Web + FastAPI**, монорепо, один Docker-образ.
Воскрешается из learning-эпохи (последний коммит 2026-03-02) для личной дальнейшей разработки → деплой на свой VPS.

## Где что (живые доки — читай вместо раскопок)
- **PROJECT.md** — карта проекта, где что лежит, быстрый старт.
- **docs/architecture.md** — слои, потоки, auth, алгоритмы (BKT/diagnostic/exam), пороги, in-memory state.
- **docs/module-map.md** — какой файл за что отвечает (читай вместо exploring кодбазы).
- **docs/data-state.md** — состояние данных/схемы, известные проблемы.
- **AUDIT-REPORT.md** — аудит + backlog (P0/P1/P2). **DESIGN_SYSTEM.md** — токены (читать перед UI).
- **docs/plan/current.md** — текущий план. **docs/decisions/** — ADR. **.claude/rules/** — правила по слоям.

## Стек (НЕ путать с CDP)
- Backend: Python 3.11 + FastAPI + **SQLAlchemy 2.0 async + asyncpg** (НЕ psycopg3, НЕ sync). Драйвер — `backend/db/base.py`.
- Frontend: **Flutter Web + BLoC** (НЕ React), Material 3, LaTeX через flutter_math_fork.
- 8 таблиц, 118 узлов графа, 2525 задач. Backend ~11.4k LOC, frontend ~8.6k LOC.

## Пороги — НЕ ПУТАТЬ
- **0.85** — `MASTERY_THRESHOLD` практики (`core/bkt.py`), алгоритмический.
- **0.7** — отдельная логика диагностики/экзамена (`diagnostic.py`/`exam.py`) И UX-порог графа (`web_graph.py`). РАЗНЫЕ пороги.

## Критично для запуска/деплоя (из аудита)
- `backend/fonts/DejaVuSerif.ttf` ДОЛЖЕН быть в git (иначе Docker build падает).
- `JWT_SECRET` — выделенный, не пустой, не фолбэк на BOT_TOKEN (иначе forgery токенов).
- uvicorn **single-worker** (`_diagnostic_states` process-local); за nginx — `proxy_headers`.
- Старт со **свежей БД** (migration-gap по FSRS-колонкам на existing-БД).
- Деструктив данных (DROP/DELETE/TRUNCATE) — ТОЛЬКО с явного согласия владельца.

## Запуск тестов
- Backend: `.venv/bin/pytest backend/tests/ -x -q` (тестов пока ~0 — главный долг).
- Frontend: `flutter analyze` + `flutter build web --release`.
- Бутстрап схемы/сида — `cd backend && python run.py` (импорты предполагают `backend/` на sys.path).

## Коммиты
- Один коммит = одно логическое изменение. Формат: `type: description` (feat/fix/docs/refactor/test/ci).

## Конец содержательной сессии → /wrap
Если в сессии реально что-то делалось (код/данные/деплой/решения) — вызови Skill `wrap` сам, не жди команды. Для тривиальных Q&A не нужен.
