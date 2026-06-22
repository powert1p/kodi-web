# kodi-web Backend — Python + FastAPI

## Стек (НЕ путать с CDP — там psycopg3)
- Python 3.11 (прод-паритет через Docker; локально может быть новее — гонять в Docker при сомнениях)
- FastAPI + **SQLAlchemy 2.0 async** + **asyncpg** (НЕ psycopg, НЕ sync). Драйвер — `db/base.py`.
- Pydantic v2 для request/response. `PyJWT` (HS256), `bcrypt`, `slowapi`, `anthropic`, `Pillow`+`graphviz`.

## Слои
- handler (`api/routes.py`) → core-алгоритм (`core/*.py`) → ORM (`db/`). Core не знает об HTTP, принимает session аргументом.
- ⚠️ `routes.py` — монолит 1070 строк (auth+SQL+логика в хендлерах). Новый код по возможности — отдельными модулями; долгосрочная цель — `routers/` + `security.py` с `Depends()` (AUDIT API-3). Не раздувать монолит дальше без нужды.

## Async — ВСЕГДА
- `async def` хендлеры; `await session.execute(...)`; `async_sessionmaker`. НИКОГДА sync DB-вызовов.
- Пул в `db/base.py` (`pool_size`, `max_overflow`, `pool_recycle`) — руками соединения не трогать.

## SQL — безопасность
- ТОЛЬКО параметризованный SQL. ORM `select()` или `text()` с bind-параметрами (`:sid`, `:limit`).
- **ЗАПРЕЩЕНО** f-string/конкатенация в SQL.
- ⚠️ `text()` НЕ разворачивает tuple в `IN`-список — нужен `bindparam('x', expanding=True)` + list, либо `= ANY(:arr)` (asyncpg-native). Был баг 500 в exam/start (AUDIT API-1).

## Auth & секреты
- JWT проверяется на каждом защищённом эндпоинте (`_get_current_student`). Никаких TODO/заглушек в auth.
- Секреты — ТОЛЬКО из env. **`JWT_SECRET` обязателен и выделенный** (не фолбэк на BOT_TOKEN, не пустой — fail-fast). Никогда в коде/логах/комментах.
- В проде не отдавать stack-trace. `/docs` гейтить за `settings.debug` или nginx basic-auth.

## Конфиг деплоя (критично)
- **uvicorn single-worker** (`_diagnostic_states` process-local, AUDIT ARCH-1).
- За nginx — `proxy_headers=True` + `forwarded_allow_ips=<nginx-ip>` (иначе slowapi лочит всех в один bucket, AUDIT OPS-1).
- `CORS_ORIGINS` = реальный домен VPS (убрать мёртвый Railway-URL).

## Стиль
- Early return над вложенностью (макс 3 уровня). Комментарии на русском.
- Искать существующие утилиты перед написанием новых.
