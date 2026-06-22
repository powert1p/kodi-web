# kodi-web — Architecture

> Обновлено: 2026-06-22. Источник истины — код; при расхождении доверяй коду. Карта файлов: `docs/module-map.md`. Решения: `docs/decisions/`.
>
> **Правило файла:** стабильный каркас (слои, потоки, auth, инварианты алгоритмов) — держать ≤2 страниц. Новая фича ≠ новая секция здесь: фичи живут в `docs/module-map.md` + `docs/specs/`. Сюда — только то, что меняет слои/потоки/auth/алгоритмическую модель.

## Overview

Адаптивная платформа по математике для НИШ. Backend (FastAPI) отдаёт REST API и Flutter-статику одним сервисом (same-origin). Ядро — движок mastery на базе **BKT** (Bayesian Knowledge Tracing) со spaced-repetition, адаптивной диагностикой и двухфазным экзаменом. Контент (граф знаний + банк задач) сидится из `backend/data/*.json` в Postgres при первом старте.

## Слои (backend)

```
HTTP (FastAPI, web.py) ─► api/routes.py (монолит, 1070 строк: routing+auth+SQL+логика)
                           │
                           ├─► core/  (чистые алгоритмы: bkt, selector, diagnostic, exam, grading, graph)
                           └─► db/    (SQLAlchemy 2.0 async models + base session + seed)
                                  │
                                  └─► PostgreSQL (asyncpg)
```

- **web.py** — FastAPI app: CORS, security-headers middleware, slowapi rate-limit, SPA-фолбэк (отдаёт `web_static/` + index.html на не-API роуты).
- **api/routes.py** — ВСЕ эндпоинты в одном файле (auth, practice, diagnostic, exam, stats, graph, reports). Hand-rolled auth через `_get_current_student` + ручной `(session, student)` + `try/finally` в каждом хендлере (не `Depends()`). ⚠️ Цель рефакторинга — разбить на `routers/` + `security.py` (см. AUDIT API-3).
- **core/** — алгоритмы без знания об HTTP/ORM-сессии (принимают session как аргумент). `scorers/` + `classifiers/` (~40 модулей) — **dead code** в рантайме (offline-тулинг калибровки; данные уже запечены в JSON).
- **db/** — `models.py` (8 таблиц, typed `Mapped[...]`), `base.py` (async engine + sessionmaker + pool), `seed.py` (идемпотентный сид графа и задач).

## Поток ученика (CJM)

```
1. Регистрация: телефон+PIN (bcrypt) или Telegram OAuth (HMAC-verify) → JWT (HS256)
2. Диагностика (опц.): 3 фазы адаптивного теста → Mastery-записи по протестированным темам
3. Практика (основной цикл): блочное чередование (5 задач/тема → переключение на слабейшую);
   каждый ответ → BKT обновляет p_mastery; spaced repetition возвращает mastered-темы [1,3,7,21,60] дней
4. Экзамен: Phase A (15 EXAM_HEADS) + Phase B (5 неопределённых подтем) → обновление Mastery
5. Прогресс: граф знаний по статусам + статистика + лидерборд
```

## Auth-модель

- **JWT** (`PyJWT`, `HS256`), секрет из `JWT_SECRET`. ⚠️ Конфиг сейчас фолбэчит `JWT_SECRET → BOT_TOKEN → ""` — пустой секрет = forgery (AUDIT SEC-1). На VPS **обязательно** выставить выделенный `JWT_SECRET`.
- **Telegram OAuth** — hash реально верифицируется (HMAC-SHA256 по sorted data_check_string, `hmac.compare_digest`, 24h freshness). Не заглушка.
- **Phone+PIN** — bcrypt с per-hash salt; прозрачный upgrade legacy unsalted SHA-256 → bcrypt при логине.
- Каждый защищённый эндпоинт — через `_get_current_student` (Bearer + `algorithms=[HS256]`, alg=none заблокирован).

## Алгоритмы (инварианты — НЕ путать пороги)

- **BKT** (`core/bkt.py`): стандартный Corbett-Anderson. Параметры per node: P(T)=0.3, P(G)=0.05, P(S)=0.1, P(L0)=0.1. `p_l` зажат в [0.001,0.999], guard от деления на ноль.
- **MASTERY_THRESHOLD = 0.85** (практика, `bkt.py`) — алгоритмический порог. `is_mastered()` = `p_mastery≥0.85 AND correct≥3 AND accuracy≥50%`.
- **0.7** — отдельная логика диагностики/экзамена (`diagnostic.py`, `exam.py`) И UX-порог отображения графа (`web_graph.py`). ⚠️ Это РАЗНЫЕ пороги, не унифицировать бездумно. Известная нестыковка: узел с `p_mastery∈[0.7,0.85)` рисуется «mastered» в UI, но selector держит его как unmastered (AUDIT CORE-3).
- **Selector** (`core/selector.py`): блочное чередование, при переключении выбирает слабейшую из heads+fringe; внутри темы — raw_score cascade (4 тира) + NIS-problems-first + рандом среди top-3 (анти-циклы).
- **Diagnostic** (`core/diagnostic.py`): top-down state machine (`_reconstruct_levels`/`_next_sub_difficulty`/`_should_ask_again`); аддитивный скоринг L1=15%/L2=25%/L3=30%/L4=30%.
- **Grading** (`core/grading.py`): 8 правил (NFKC-нормализация → exact → numeric → fraction → compact → multi-value → text-number → symbols) + unit-conversion gate. Claude LLM фолбэк перепроверяет «неверно». ⚠️ Сейчас model id невалиден → фолбэк мёртв на 404 (AUDIT CORE-1).

## In-memory состояние

- `_diagnostic_states` (`routes.py`) — process-local dict + `asyncio.Lock` для активных сессий диагностики/экзамена. Бэкапится в `student.paused_diagnostic` (JSONB) для resume-after-restart.
- ⚠️ Ломается при `workers>1` (каждый worker — свой dict). **Держать uvicorn single-worker** (AUDIT ARCH-1).
- Практика состояния в памяти НЕ держит — всё в БД (`current_practice_node`, `practice_count`, `problems_on_current_node`).

## Схема БД (8 таблиц)

`nodes` (темы графа) · `edges` (пререквизиты) · `problems` (банк задач) · `students` · `mastery` (BKT per student×node + FSRS-поля) · `attempts` · `problem_reports` · `settings` (key-value). FK ondelete: student CASCADE, node/problem RESTRICT.

⚠️ **Миграций как фреймворка нет** (нет Alembic): схема через `create_all` (не альтерит existing) + hand-list `ALTER` в `run.py`. На свежей БД безопасно; при миграции старой БД — gap по FSRS-колонкам mastery (AUDIT MIG-1). Долгосрочно — нумерованные миграции как в CDP.

## Деплой

- **Сейчас:** Railway, один Docker-образ (multi-stage: Flutter build → Python serve), порт 8000, SPA same-origin.
- **Цель (revival):** self-hosted на свой VPS (тот же сервер, что CDP), Docker Compose (свой Postgres + app), host nginx vhost, отдельные порты (8200/5434 заняты CDP). Подробности и порядок cutover — `.claude/rules/deploy.md` и `docs/decisions/001-*`.
