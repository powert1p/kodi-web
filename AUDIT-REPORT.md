# Аудит архитектуры — kodi-web
> Дата: 2026-06-22 · Аудитор: Claude (Workflow, 5 ридеров + adversarial verify)

## TL;DR

- **Проект жив и воскрешаем.** Backend бутается (`create_all` + idempotent ALTER + JSON-seed), frontend Flutter Web реально собирается прогоном настоящего тулчейна (`flutter build web --release` exit 0, `flutter analyze` 0 errors). Никаких архитектурных тупиков нет — это крепкий solo-проект эпохи обучения, а не руина.
- **Один настоящий P0-блокер деплоя:** `backend/fonts/DejaVuSerif.ttf` git-untracked, а `static/` в `.gitignore` → на свежем clone Docker build падает на `generate_images.py` (нет fallback'а). Это единственное, что жёстко ломает чистый redeploy.
- **Топ-риск безопасности (P1):** `JWT_SECRET` молча падает в `BOT_TOKEN`, а если и его нет — ключ подписи пустая строка `""`, что эмпирически подтверждено как тривиальная forgery-токена с полным имперсонированием любого `student_id`. Обязательно выставить перед первым бутом.
- **Две латентные 500-ки на живых эндпоинтах (P1):** сломанный `IN :seen` bind в exam/start (крэшит под asyncpg у вовлечённых юзеров) и невалидный Claude model id, из-за которого AI-автопочинка репортов мертва на 404 (фейлится тихо, не роняет приложение).
- **Сквозной долг (дедуплицировано):** тестов практически 0 во всём репозитории; миграций как ledger нет (только append-only ALTER в `run.py`); 1070-строчный монолит `routes.py`. Ничего из этого не блокирует запуск, но это первое, что чинить перед дальнейшей разработкой.
- **Ядро адаптивного движка (BKT, selector, diagnostic, exam, grading) — реально хорошее:** математика корректна и защищена от NaN/деления на ноль, state machine диагностики внутренне консистентен, grading-пайплайн необычно тщательный. Главный структурный мусор — `scorers/`+`classifiers/` (~40 модулей) полностью dead code в рантайме.
- **Для VPS-деплоя по образцу CDP** нужно: зафиксировать font в git, выставить env (`JWT_SECRET`, `CORS_ORIGINS`, `DATABASE_URL`), держать uvicorn в один worker, прокинуть `--proxy-headers` за nginx, и стартовать со свежей БД (тогда `create_all` строит полную схему и migration-gap не стреляет).

## Стек и общая картина

kodi-web — адаптивная платформа подготовки к НИШ по математике: backend на FastAPI поверх SQLAlchemy 2.0 async + asyncpg + Postgres (8 таблиц, ~11.4k LOC Python, единый монолитный роутер `routes.py` на 1070 строк), frontend на Flutter Web (kodi_web app + kodi_core package, ~8.6k LOC Dart, чистая BLoC-per-feature архитектура, полная kz/ru локализация). Сейчас задеплоен на Railway одним Docker-образом, где один сервис отдаёт и Flutter-статику, и FastAPI API (same-origin). Воскрешается под личную доработку с redeploy на собственный VPS через Docker Compose по образцу sibling-проекта CDP (свой Postgres, host nginx vhost, отдельные порты). Ядро — BKT-mastery движок со spaced-repetition, top-down диагностикой и двухфазным экзаменом; задачи и граф знаний сидятся из `data/*.json` (2525 задач, 118 узлов — не «10000+», как утверждает CLAUDE.md).

## Что хорошо (strengths)

**Core-алгоритмы:**
- BKT-математика корректна и защищена: `_posterior` + `bkt_update` (bkt.py:31-51) — стандартный Corbett-Anderson, `p_l` зажат в [0.001,0.999], есть guard `den==0` → NaN/деления на ноль невозможны.
- `is_mastered` (bkt.py:215-230) гейтит на `p_mastery>=0.85` AND `>=3 correct` AND `>=50% accuracy` — реально отсекает везунчиков, а не верит одной вероятности.
- Spaced-repetition (bkt.py:168-192) считает подряд правильные и маппит в интервалы [1,3,7,21,60] дней, корректно сбрасывая `next_review_at` при потере mastery.
- `get_or_create_mastery` использует `INSERT ... ON CONFLICT DO NOTHING` (bkt.py:95-99) против race на `(student_id,node_id)`.
- Selector cascade (selector.py) изощрён и корректен: targeting по близости `raw_score`, 4 fallback-тира, NIS-problems-first, рандом среди top-3 против циклов.
- State machine диагностики (`_reconstruct_levels`/`_next_sub_difficulty`/`_should_ask_again`) внутренне консистентен — самая хитрая логика в кодбазе.
- Grading-пайплайн: NFKC-нормализация, unicode-dash таблица, unit-conversion gate (`'3см'` ≠ `'3кг'`), парсинг дробей через `Fraction`, order-independent multi-value сравнение.
- `ExamState`/`DiagnosticState` имеют `to_dict`/`from_dict` для JSONB-персистентности → resume-after-restart.

**API/Auth/Security:**
- Telegram login hash реально верифицируется (routes.py:165-178): HMAC-SHA256 по sorted data_check, `hmac.compare_digest`, 24h freshness window — корректный алгоритм, не заглушка.
- PIN на bcrypt с per-hash salt + прозрачный upgrade legacy SHA256 → bcrypt при логине (routes.py:265-268).
- Весь DB-доступ параметризован: ORM `select()` + `text()` с `:sid/:limit`, ни одной f-string SQL-интерполяции.
- Pydantic v2 валидирует каждый body; query-параметры с constraints (`count ge=1 le=10`, `lang ^(ru|kz)$`).
- Каждый защищённый эндпоинт через `_get_current_student` с Bearer + JWT `algorithms=[HS256]` (alg=none атака заблокирована).
- Security headers middleware (HSTS, nosniff, X-Frame-Options DENY, no-store на /api/), slowapi rate-limit, контейнер от non-root `app`.

**DB/Данные/Миграции:**
- Современный async-стек: `create_async_engine` + `async_sessionmaker(expire_on_commit=False)`, тюнингованный пул (`pool_size=10, max_overflow=5, pool_recycle=1800`).
- Типизированные модели (`Mapped[...]`), продуманные FK ondelete: student CASCADE, node/problem RESTRICT (reference-данные не осиротеют).
- Осмысленные индексы под query-паттерны selector/stats (`ix_problems_node_id`, `ix_problems_raw_score`, `ix_attempts_student_node`).
- Идемпотентный seeding: short-circuit по row count + gate по `problems_version` ключу.
- Data-integrity чистая: все 118 node_id из задач существуют в графе, 0 FK-нарушений, 0 NULL в required-полях, все image-пути влезают в лимит.

**Frontend (Flutter):**
- Собирается и деплоится чисто: `flutter build web --release` с точными Dockerfile dart-defines exit 0 на Flutter 3.41.2 / Dart 3.11.0; monorepo path-dependency резолвится.
- Слоистая обработка ошибок: `NisApiClient` различает `NetworkException` vs `ApiException`, КАЖДЫЙ bloc ловит оба + generic fallback с локализованным ключом.
- Локализация полная: `app_ru.arb` и `app_kk.arb` — идентичные 200-ключевые сеты, 0 пустых значений.
- Никаких хардкод-секретов; единственный хардкод-URL — `localhost:8000` dev-default, перекрытый `--dart-define`.
- Чистый BLoC: один bloc на фичу, Equatable events/states, DI через провайдеры, JWT в SharedPreferences с load-on-boot.
- Хорошие UX-состояния: first-frame skeleton, CircularProgressIndicator, error-views с retry, empty-list guards, null-safe JSON-парсинг.

## Блокеры запуска (P0)

Эти пункты гейтят воскрешение. Только один настоящий hard-blocker сборки; остальное — обязательные pre-deploy действия, без которых деплой ломается предсказуемо.

1. **Docker build падает на свежем clone из-за git-untracked шрифта.**
   Где: `Dockerfile:32-33` (RUN `generate_images.py --lang ru && --lang kz`), `backend/scripts/generate_images.py:51` (FONT_PATH), `:750-751` (`ImageFont.truetype`).
   Почему блокер: `git ls-files backend/fonts/` возвращает 0 файлов (`?? backend/fonts/`), а `backend/static/` в `.gitignore` → fallback на готовые PNG невозможен. `generate_images.py` не имеет ни одного `try/except`; `ImageFont.truetype` на отсутствующем пути кидает `OSError`, RUN-шаг exit non-zero, build падает детерминированно. Это #1 вещь, ломающая чистый redeploy.
   Фикс: `git add backend/fonts/DejaVuSerif.ttf` и закоммитить (380KB, DejaVu свободно распространяемый), ИЛИ закоммитить готовые `static/` PNG и убрать generate-шаг. Проверить чистым `git clone` в tmp + `docker build` до деплоя. *(BUILD-1, P0 confirmed)*

2. **`JWT_SECRET` молча падает в `BOT_TOKEN`, при отсутствии обоих — пустой ключ подписи → forgery токенов.**
   Где: `backend/core/config.py:53` (`jwt_secret = os.getenv("JWT_SECRET") or os.getenv("BOT_TOKEN", "")`).
   Почему блокер деплоя: на VPS с phone-PIN-only `BOT_TOKEN` может легитимно отсутствовать → ключ становится `""`. Эмпирически подтверждено (PyJWT 2.12.1): `jwt.encode`/`decode` с пустым ключом проходят без исключения, форжённый токен с любым `sub` валидируется → `_get_current_student` загружает любого `student_id`. Startup hard-fail отсутствует.
   Фикс: выставить выделенный случайный `JWT_SECRET` (32+ байт, отличный от `BOT_TOKEN`) в env VPS ДО первого бута; добавить fail-fast при пустом секрете. Самое важное pre-deploy действие. *(SEC-1/AUTH-1, P1-high — гейтит безопасный запуск)*

3. **`exam/start` fallback 500-ит под asyncpg.**
   Где: `backend/api/routes.py:751` (`WHERE p.id NOT IN :seen` с tuple-bind).
   Почему блокер: SQLAlchemy `text()` не разворачивает tuple в IN-list без `bindparam(expanding=True)`; компилируется в `NOT IN $1` — невалидный Postgres, asyncpg кидает programming error, request 500. Путь триггерится у любого вовлечённого юзера (≥1 правильный ответ в достаточном числе тем, или `num_problems` > числа нетронутых тем) — детерминированная 500 на user-facing эндпоинте.
   Фикс: `bindparam('seen', expanding=True)` + list, либо `WHERE NOT (p.id = ANY(:seen))` (asyncpg-native array). Добавить тест на экзамен после решения большинства задач. *(API-1, P1-high confirmed)*

4. **Держать uvicorn в ОДИН worker.**
   Где: `backend/run.py:61` (уже single-worker), `backend/api/routes.py:786-787` (`_diagnostic_states` process-local).
   Почему блокер: `_diagnostic_states` + `asyncio.Lock` живут в памяти процесса. При `workers>1`/`gunicorn -w N` каждый worker имеет свой dict, `/diagnostic/answer` попадёт на worker, не видевший `/diagnostic/start`. JSONB-снапшот частично спасает, но Lock ничего не гарантирует между процессами.
   Фикс: зафиксировать single-worker в Dockerfile/compose, либо сделать DB JSONB единственным источником истины и выкинуть in-process cache+lock. *(ARCH-1, P2 — но критично для конфигурации деплоя)*

5. **За nginx — запускать uvicorn с `--proxy-headers` + trusted `forwarded-allow-ips`.**
   Где: `backend/api/routes.py:47` (`Limiter(key_func=get_remote_address)`).
   Почему блокер: за nginx peer всех запросов = `127.0.0.1` → slowapi схлопывает всех юзеров в один rate-limit bucket, auth-лимиты (5/min) залочат всю базу. Фикс: `proxy_headers=True` + `forwarded_allow_ips` на IP nginx, nginx ставит `X-Forwarded-For` (зеркалить CDP nginx config). *(OPS-1, P3 — но обязательно для рабочего деплоя за nginx)*

## Находки по подсистемам

### Core-алгоритмы

Ядро адаптивного движка реально хорошо построено; единственный correctness-дефект — мёртвый Claude-fallback. Главный структурный мусор — `scorers/`+`classifiers/` (~40 модулей, половина файлов под `core/`), которые никогда не импортируются в рантайме.

| ID | Severity | Категория | Где | Проблема | Рекомендация |
|---|---|---|---|---|---|
| CORE-1 | P1-high | correctness | core/grading.py:478 | Claude grading-fallback зовёт `model="claude-sonnet-4-5-20241022"` — невалидный id (фьюжн имени Sonnet-4.5 и даты retired Claude-3.5-Sonnet `20241022`; реальный id — `claude-sonnet-4-5-20250929`). API → 404, фича AI-автопочинки на 100% мертва в configured-состоянии; ловится broad `except` (routes.py:692), не роняет. Дубль API-2. | Сменить на валидный alias; по документированному intent (docstring + CLAUDE.md «Claude Haiku перепроверяет») — `claude-haiku-4-5`. Проверить `ANTHROPIC_API_KEY` в env VPS. Логировать 404 отдельно. |
| CORE-2 | P2-medium | tech-debt | core/scorers/__init__.py, core/classifiers/__init__.py | Весь subsystem `scorers/`+`classifiers/` (~40 модулей) — dead code: repo-wide grep `from core.scorers`/`core.classifiers` = 0 хитов вне самих пакетов. `raw_score`/`sub_difficulty` сидятся напрямую из JSON (seed.py:107-108,154), не этими scorers. Тысячи строк осиротевшего offline-тулинга в `core/`, маскирующегося под live. | Либо перенести в явный `tools/`/`scripts/` вне `core/`, либо удалить (данные уже запечены в `problems_v10.json`). Не держать молча в `core/`. |
| CORE-3 | P2-medium | correctness | core/bkt.py:24, core/web_graph.py:157,238, core/diagnostic.py:274 | Split порога mastery: 0.85 (practice) vs 0.7 (diagnostic/exam/graph). Студент с `p_mastery ∈ [0.7,0.85)` рисуется «mastered» (зелёный) в графе и считается в leaderboard, но selector держит узел как weakest-unmastered, `is_mastered()` = False. Один узел одновременно «mastered» (UI) и «not mastered» (engine) — реальная видимая юзеру нестыковка. | Продуктовое решение: задокументировать band и по-разному лейблить в UI, либо выровнять display-порог к `MASTERY_THRESHOLD`. Минимум — заменить голые литералы 0.7/0.85 на именованные константы из одного места. |
| CORE-6 | P3-low | correctness | core/bkt.py:136-139 | `record_attempt` при отсутствии node молча берёт default BKT-параметры (`p_t=0.3` и т.д.) и создаёт Mastery для несуществующего node_id — маскирует data-integrity проблему. | Оставить fallback, но логировать warning при `node is None`. One-time integrity check при seed. |
| CORE-5 | P3-low | correctness | core/diagnostic.py:976-983 | `_compute_additive_mastery` L3-retry overwrite жёстко связан с текущей формой `_reconstruct_levels`; нет assertion. При расширении state machine молча мис-кредитит. | Low priority. При добавлении тестов запинить additive-mastery для retry-пути. |

### API/Auth/Security

Backend — единый FastAPI поверх монолитного `routes.py` (1070 строк). Auth разумен для personal-проекта. Серьёзные проблемы — не классические web-дыры, а операционные/correctness баги, стреляющие на воскрешении: см. блокеры P0 (#2,#3,#4,#5). Ниже остальное.

| ID | Severity | Категория | Где | Проблема | Рекомендация |
|---|---|---|---|---|---|
| API-2 | P1-high | correctness | core/grading.py:478 | Дубль CORE-1: невалидный Claude model id → /api/practice/report AI-автопочинка всегда 404. | Валидный id (`claude-haiku-4-5`), проверить реальным вызовом после `ANTHROPIC_API_KEY`. |
| SEC-1 | P1-high | security | core/config.py:53 | Дубль AUTH-1: `JWT_SECRET` → `BOT_TOKEN` → `""`; пустой ключ = forgery токена с полным имперсонированием (эмпирически). Нет startup fail. См. P0 #2. | Требовать `JWT_SECRET` явно, raise при пустом. Выделенный 32+ байт секрет на VPS. |
| SEC-2 | P2-medium | ops | web.py:55-70 | CORS default allowlist указывает на мёртвый `kodi-web-production.up.railway.app` + localhost. На VPS реального origin нет в списке → cross-origin клиент блокируется молча. | Выставить `CORS_ORIGINS` на домен VPS. Убрать хардкод Railway-URL. |
| SEC-3 | P2-medium | security | web.py:49 | Swagger `/docs` + OpenAPI публично доступны без auth → энумерация всех эндпоинтов/схем. | Гейтить `/docs` за `settings.debug` или nginx basic-auth (зеркалить CDP). |
| ARCH-1 | P2-medium | architecture | api/routes.py:786-787 | `_diagnostic_states` + `asyncio.Lock` process-local — ломается под `workers>1`. См. P0 #4. | Single-worker (задокументировать), либо DB JSONB как единственный источник истины. |
| API-3 | P2-medium | architecture | api/routes.py:1 | 1070-строчный монолит: routing + JWT + hashing + Telegram verify + raw SQL + бизнес-логика в одном файле. Hand-rolled auth `(session, student)` + `try/finally` в каждом хендлере вместо `Depends()`. | Разбить на `routers/` (auth/practice/diagnostic/stats/graph) + `security.py` с `get_current_student` Depends(). JWT/PIN/Telegram → `core/auth.py`. |
| SEC-4 | P3-low | correctness | api/routes.py:696-699 | `_notify_report` через `asyncio.ensure_future` — fire-and-forget, не tracked; при быстром shutdown нотификация теряется. | `FastAPI BackgroundTasks` вместо bare `ensure_future`. |
| SEC-5 | P3-low | security | api/routes.py:226-227 | Registration требует только `len(pin)>=4`; login rate-limit 5/min/IP, без per-account lockout. 4-значный PIN = 10k комбинаций. Приемлемо для kids-app. | Acceptable для personal. При hardening — per-account failed-attempt counter. |
| OPS-1 | P3-low | ops | api/routes.py:47 | `get_remote_address` за nginx видит `127.0.0.1` → все юзеры в одном rate-limit bucket. См. P0 #5. | `proxy_headers=True` + `forwarded_allow_ips`. |
| OPS-2 | P3-low | ops | web.py:25 | `STATS_DIR=/tmp/nis_stats` хардкод; HTML stat-страницы эфемерны, возможно legacy (не используются Flutter-клиентом). | Проверить используется ли `/stats/{token}`; если нет — удалить. |

### DB/Данные/Миграции

DB-слой чистый и современный; слабое место — migration story (нет фреймворка) и build-pipeline (см. P0 #1). Data-integrity сама по себе чистая.

| ID | Severity | Категория | Где | Проблема | Рекомендация |
|---|---|---|---|---|---|
| BUILD-1 | P0-blocker | revival-blocker | Dockerfile:32-33, scripts/generate_images.py:51 | Font git-untracked + `static/` gitignored → Docker build падает детерминированно. См. P0 #1. | `git add backend/fonts/DejaVuSerif.ttf`. Проверить чистым clone + build. |
| MIG-1 | P1-high | revival-blocker | run.py:24-45, db/models.py:124-126 | Нет migration-фреймворка (нет Alembic). Схема через `create_all` (не альтерит existing) + hand-list ALTER, покрывающий только `students`/`problem_reports`. FSRS-колонки mastery (`fsrs_stability`, `fsrs_difficulty`, `next_review_at`) НЕ в ALTER-листе. При миграции старой Railway-БД без них → `UndefinedColumn` на основном practice-цикле. Условно: только при migrate-old-data; на свежей БД безопасно. | (a) Старт со свежей БД — `create_all` строит полную схему (проверить 3 FSRS-колонки), ИЛИ (b) при миграции prod — добавить 3 mastery ALTER...IF NOT EXISTS. Долгосрочно — Alembic/нумерованные миграции как в CDP. |
| SEED-1 | P2-medium | correctness | db/seed.py:128-209 | `_sync_problems` матчит DB↔JSON позиционно (`ORDER BY id`, zip) — при insert/delete в середине `problems_v10.json` хвост перезаписывается на чужие строки. **Downgrade с P1:** путь дормантный — зовётся только при пустой `nodes` (run.py:47); bump `PROBLEMS_VERSION` НЕ триггерит на обычном деплое. | Стабильный natural key (`slug`/`md5(text_ru)`) + `INSERT ... ON CONFLICT DO UPDATE`. Минимум — задокументировать: `problems_v10.json` только APPEND, никогда reorder/delete. |
| AUTH-2 | P2-medium | security | api/routes.py:154-160 | `_verify_pin` принимает legacy unsalted SHA-256 (любой 64-char hash). PIN = 4 цифры → тривиально brute/rainbow при утечке. Новые PIN на bcrypt (хорошо). | Upgrade-on-login: при успехе против 64-char hash перехешить bcrypt. Когда 64-char не останется — удалить legacy-ветку. |
| OPS-1(db) | P2-medium | ops | run.py:24-63, web.py:49 | Schema-bootstrap (`create_all`+ALTER+seed) только в `run.py:on_startup()`. У `web.py` нет lifespan/startup → запуск через `uvicorn web:app` (как в CDP-compose) НЕ создаёт таблицы и не сидит. | Перенести bootstrap в FastAPI lifespan на `web.app` → работает при любом запуске. `run.py` как тонкий wrapper. |
| DATA-1 | P3-low | tech-debt | data/problems_v10.json, CLAUDE.md | CLAUDE.md заявляет «10000+ задач» и «29 nodes», реально — 2525 задач, 118 узлов. Вводит в заблуждение при capacity-планировании. | Обновить CLAUDE.md (2525 задач, 118 узлов). Startup-assertion логирующий seeded-counts. |
| DATA-2 | P3-low | correctness | static/questions_kz/ (2522) vs questions/ (2525) | 3 KZ-картинки отсутствуют против 2525 RU. Все 2525 имеют непустой `text_kz`/`image_file_kz` → 3 KZ-карточки сломаны. Self-healing на чистом build. | Re-run `generate_images.py --lang kz` на чистой `questions_kz/`, spot-check 3 файла. |
| OPS-2(db) | P3-low | ops | kodi-web/ (нет .dockerignore) | Нет `.dockerignore` → `COPY` тянет весь tree (build-артефакты, `.dart_tool`, `__pycache__`, локальный `static/` ~5000 PNG). Раздувает context, риск stale-артефактов. | Добавить `.dockerignore`. |
| DX-1 | P3-low | dx | api/routes.py, db/models.py:21, run.py:12-15 | Импорты `from db.base import Base` предполагают `backend/` на sys.path → запуск из repo root ломается. bcrypt импортится лениво внутри функций. | Задокументировать `cd backend` в README/CLAUDE.md, или сделать пакет installable. |

### Frontend (Flutter)

Frontend СОБИРАЕТСЯ И ДЕПЛОИТСЯ сегодня (проверено реальным тулчейном: `pub get` чисто, `analyze` 0 errors, `build web --release` exit 0). Никаких revival-блокеров на build/deploy пути. Долг сконцентрирован в `dart:html` (блокирует WASM + ломает `flutter test`) и почти нулевом покрытии тестами.

| ID | Severity | Категория | Где | Проблема | Рекомендация |
|---|---|---|---|---|---|
| FE-1 | P2-medium | tech-debt | apps/kodi_web/.../login_page.dart:6 | `import 'dart:html'` → `flutter test` для app-пакета не компилируется (`Type 'html.WindowBase' not found`), весь test-run exit non-zero. Любой revival-CI на `flutter test` красный из коробки. | Мигрировать Telegram-popup на `package:web` + `dart:js_interop`. Фиксит и тест, и WASM (FE-2). |
| FE-3 | P2-medium | ops | apps/kodi_web/.../config.dart:3, Dockerfile:13 | `API_BASE_URL` — compile-time `String.fromEnvironment`, Dockerfile билдит пустым → same-origin relative `/api/...`. Работает только если nginx отдаёт Flutter-статику и проксирует `/api/` на тот же origin. При split origins — молча ломаются API-вызовы, менять надо ребилдом образа. | (a) Держать same-origin: host nginx проксирует `/api/` на backend под тем же hostname (проще), либо (b) runtime-config через `window.__API_BASE__` / `/config.json`. |
| FE-4 | P2-medium | tech-debt | apps/kodi_web/test/, packages/kodi_core/test/ | Near-zero coverage: 1 smoke-тест app (не компилится, FE-1) + 1 тривиальный kodi_core. Нет тестов на blocs, API error-mapping, `MathText` LaTeX-конверсию, JSON-парсинг. | После удаления `dart:html` — `bloc_test` для AuthBloc, Practice/Diagnostic/Exam blocs + unit на `MathText._convertToLatex` и `fromJson`. |
| FE-2 | P3-low | tech-debt | apps/kodi_web/.../login_page.dart:6 | `dart:html` блокирует WASM-билды. JS/CanvasKit билд (Dockerfile) не затронут — НЕ блокер. | Тот же фикс что FE-1. Low priority. |
| FE-5 | P3-low | security | apps/kodi_web/web/telegram_login.html:35 | Telegram OAuth popup шлёт `postMessage(..., '*')`; листенер принимает любой origin. Не auth-bypass (backend валидирует HMAC), но loose. | Явный target origin + проверять `event.origin`. |
| FE-6 | P3-low | correctness | practice_bloc.dart:138, diagnostic_bloc.dart:260, exam_bloc.dart:177 | Нет `EventTransformer` (нет `bloc_concurrency`); double-tap submit может enqueue два `submitAnswer` → дубль attempts. | `transformer: droppable()` на submit, или дизейблить кнопку in-flight. |
| FE-7 | P3-low | revival-blocker | apps/kodi_web/pubspec.yaml:31 | `assets/images/` объявлен но отсутствует в репо (`analyze` warning). Dockerfile компенсирует `mkdir -p`. Минорная friction, не hard-blocker. | `.gitkeep` в `assets/images/`. |
| FE-8 | P3-low | correctness | dashboard_page.dart:71 (+others) | 11 `use_build_context_synchronously`: BuildContext после `await` без `mounted`-check. На route, попнутом mid-await, кинет 'deactivated widget'. | `if (!context.mounted) return;` после await. Механический фикс. |

### Инфра/Деплой

Текущий деплой — Railway single-Docker (один сервис: Flutter-статика + FastAPI same-origin). Целевой — VPS Docker Compose по образцу CDP. Ключевые инфра-находки сведены в P0 (#1 font, #4 single-worker, #5 proxy-headers) и распределены по таблицам выше (SEC-2 CORS, OPS-1(db) lifespan, OPS-2(db) .dockerignore). Дополнительно: Dockerfile RUN `generate_images.py` на build-time требует graphviz + data-JSON в build-context.

> ⚠️ Reader `infra-deploy-revival` упал на rate-limit во время прогона; его scope покрыт остальными ридерами + синтезом и моей предварительной разведкой (Dockerfile/requirements/railway.toml/.env прочитаны вручную). Полностью независимый инфра-проход не делался — пробелы добьются на фазе 3 при реальном деплое.

| ID | Severity | Категория | Где | Проблема | Рекомендация |
|---|---|---|---|---|---|
| ARCH-2/MIG-1 | P1-high | tech-debt/ops | run.py:24-45 | (дедупл. с MIG-1) Миграции — append-only ALTER-лист на каждом старте, без ledger/down/version-tracking. `UPDATE students SET...` на каждом буте (table-scan с ростом данных). Источник будущих «works on fresh DB, breaks on existing». | Alembic / нумерованные `migrations/` как в CDP. Перед go-live — аудит что все читаемые колонки есть на целевой VPS-БД. |
| TEST-0 | P2-medium | tech-debt | backend/ (нет tests/), frontend (1 нерабочий) | (дедупл. CORE-4/ARCH-3/FE-4) Тестов практически 0 во всём репо; pytest нет в requirements. Самая logic-dense математика (BKT, diagnostic, grading) без покрытия. Два живых бага (API-1, API-2) были бы пойманы одним integration-тестом каждый. | pytest + pytest-asyncio; table-driven на `check_answer`, golden на `bkt_update`/`_reconstruct_levels`. Frontend — bloc_test после FE-1. |

## Приоритизированный backlog

**P0 — блокеры запуска/деплоя:**
- BUILD-1: `git add backend/fonts/DejaVuSerif.ttf` (иначе Docker build падает на свежем clone).
- SEC-1/AUTH-1: выставить выделенный `JWT_SECRET` на VPS до первого бута + fail-fast при пустом.
- API-1: починить `IN :seen` expanding bindparam (иначе 500 у вовлечённых юзеров на exam/start).
- ARCH-1: держать uvicorn single-worker (зафиксировать в Dockerfile/compose).
- OPS-1: за nginx — `--proxy-headers` + trusted `forwarded-allow-ips`.
- SEC-2: выставить `CORS_ORIGINS` на домен VPS (убрать мёртвый Railway-URL).
- MIG-1: стартовать со свежей БД (тогда `create_all` строит полную схему); при миграции prod — добавить 3 mastery FSRS ALTER.

**P1 — безопасность/корректность:**
- CORE-1/API-2: валидный Claude model id (`claude-haiku-4-5` по intent) + проверить `ANTHROPIC_API_KEY`.
- AUTH-2: upgrade-on-login legacy SHA-256 PIN → bcrypt.
- SEC-3: гейтить `/docs` за `settings.debug`.
- OPS-1(db): bootstrap в FastAPI lifespan (чтобы `uvicorn web:app` тоже создавал схему).

**P2 — долг для дальнейшей разработки:**
- TEST-0 (CORE-4/ARCH-3/FE-4): добавить pytest + bloc_test, начать с pure-функций (BKT, grading, diagnostic).
- ARCH-2/CORE-7: Alembic / нумерованные миграции как в CDP.
- API-3: разбить монолитный `routes.py` на `routers/` + `security.py` с `Depends()`.
- FE-1/FE-2: убрать `dart:html` → `package:web`+`js_interop` (фиксит тесты + WASM).
- CORE-2: вынести/удалить dead `scorers/`+`classifiers/`.
- CORE-3: выровнять или явно задокументировать mastery-band 0.7/0.85, заменить литералы константами.
- FE-3: решить same-origin vs runtime-config для `API_BASE_URL`.
- SEED-1: natural key для problems + ON CONFLICT, или задокументировать append-only.
- OPS-2(db): `.dockerignore`; SEC-4: `BackgroundTasks`; DATA-1: исправить counts в CLAUDE.md.
- Мелочи: CORE-5, CORE-6, FE-5, FE-6, FE-7, FE-8, SEC-5, OPS-2, DX-1, DATA-2.

## Что нужно, чтобы воскресить (revival checklist)

**A. Подготовка репо (до сборки):**
1. `git add backend/fonts/DejaVuSerif.ttf && git commit` — снять P0-блокер сборки (BUILD-1).
2. Добавить `.dockerignore` (frontend build outputs, `.dart_tool`, `__pycache__`, `.venv`, `backend/static`, `backend/web_static`, `.git`) — OPS-2(db).
3. Добавить `.gitkeep` в `frontend/apps/kodi_web/assets/images/` — FE-7.
4. Проверить чистым `git clone` в tmp → `docker build` проходит до конца (graphviz + `backend/data/*.json` в контексте).

**B. Локальный запуск:**
5. `cd backend && python run.py` (entrypoint предполагает `backend/` на sys.path — DX-1), либо `uvicorn web:app` ТОЛЬКО после переноса bootstrap в lifespan (OPS-1(db)).
6. Поднять локальный Postgres, выставить env: `DATABASE_URL` (конфиг авто-переписывает `postgresql://` → `postgresql+asyncpg://`), `JWT_SECRET` (выделенный случайный), опционально `BOT_TOKEN`, `ANTHROPIC_API_KEY`.
7. Первый бут на свежей БД → `create_all` строит полную схему. Проверить: таблица `mastery` имеет `fsrs_stability`, `fsrs_difficulty`, `next_review_at` (MIG-1); seed залил 118 узлов и 2525 задач.
8. Прогнать `flutter build web --release --dart-define=API_BASE_URL= --dart-define=TG_BOT_NAME=<bot>` — убедиться что собирается (он собирается).

**C. Деплой на VPS (по образцу CDP docker-compose):**
9. `docker-compose.yml` зеркалить sibling-CDP: сервис `app` (Docker-образ kodi-web) + сервис `postgres` (свой Postgres, отдельный volume), свежие порты (не пересекать с CDP: 8200/5434 заняты).
10. Env на VPS: `JWT_SECRET` (обязательно, P0), `CORS_ORIGINS=https://<vps-domain>` (P0), `DATABASE_URL`, `BOT_TOKEN`, `ANTHROPIC_API_KEY` (опционально — но без фикса CORE-1 AI-автопочинка мертва).
11. Держать uvicorn **single-worker** (`_diagnostic_states` process-local, ARCH-1); запускать с `proxy_headers=True` + `forwarded_allow_ips=<nginx-ip>` (OPS-1).
12. host nginx vhost: отдавать Flutter-статику и проксировать `/api/` на FastAPI под **тем же origin** (под текущий same-origin `API_BASE_URL=`, FE-3); ставить `X-Forwarded-For`; опционально basic-auth на `/docs` (SEC-3).
13. Стартовать со **свежей БД** (не мигрировать старую Railway-БД, чтобы обойти migration-gap MIG-1); если данные нужны — отдельно перелить, предварительно добавив 3 mastery FSRS ALTER.
14. Live-проверка после деплоя: регистрация по phone-PIN → диагностика → practice-ответ (триггерит `next_review_at` write) → exam/start после решения нескольких тем (триггерит fallback API-1 — должен быть пофикшен) → проверить что rate-limit не лочит всех (OPS-1).

## Метрики

| Метрика | Значение |
|---|---|
| Backend LOC (Python) | ~11.4k |
| Frontend LOC (Dart) | ~8.6k |
| `routes.py` | 1070 строк (монолит: routing+auth+SQL+бизнес-логика) |
| Backend тесты | ~0 (нет `tests/`, pytest не в requirements) |
| Frontend тесты | 2 (app smoke не компилится из-за `dart:html`; kodi_core тривиальный) |
| DB таблицы | 8 (typed `Mapped`, async SQLAlchemy 2.0 + asyncpg) |
| Задачи (problems_v10.json) | 2525 (CLAUDE.md ошибочно «10000+») |
| Узлы графа знаний | 118 (CLAUDE.md ошибочно «29»/«80+») |
| Dead code в `core/` | `scorers/`+`classifiers/` ~40 модулей, 0 рантайм-импортов |
| Локализация | ru/kz, 200/200 ключей, 0 пустых |
| Миграционный фреймворк | нет (append-only ALTER в `run.py`, без Alembic/ledger) |
| `flutter analyze` | 0 errors, 16 info/warnings |
| `flutter build web --release` | exit 0 (Flutter 3.41.2 / Dart 3.11.0) |
| Build-blocker'ы (P0) | 1 (git-untracked font) |
| Подтверждено P1 | 4 (CORE-1/API-2, API-1, SEC-1, MIG-1) |
| Downgrade adversarial-verify | SEED-1 (P1 → P2, дормантный за guard'ом) |
