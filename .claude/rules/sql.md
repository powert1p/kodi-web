# kodi-web SQL — SQLAlchemy async + asyncpg

## Драйвер
- **SQLAlchemy 2.0 async + asyncpg** (НЕ psycopg3 как в CDP, НЕ sync). `DATABASE_URL` конфиг авто-переписывает `postgresql://` → `postgresql+asyncpg://`.
- Доступ к БД — через async session (`db/base.py`), `await session.execute(select(...))` / `await session.scalar(...)`.

## Безопасность
- ТОЛЬКО параметризованный SQL: ORM `select()` или `text("... :param")` с bind. **НИКОГДА** f-string/конкатенация.
- ⚠️ `text()` + `IN`-список: tuple НЕ разворачивается сам → `bindparam('x', expanding=True)` + list, либо `WHERE col = ANY(:arr)` (asyncpg native array). Иначе 500 (был баг exam/start, AUDIT API-1).

## Схема и миграции
- 8 таблиц (`db/models.py`, typed `Mapped[...]`): nodes, edges, problems, students, mastery, attempts, problem_reports, settings.
- ⚠️ **Нет Alembic.** Схема: `create_all` (НЕ альтерит existing) + hand-list `ALTER` в `run.py`. На свежей БД ок; existing-БД → gap (MIG-1).
- Долгосрочно — нумерованные миграции `migrations/NNN_name.sql` + ledger (как CDP). При вводе: идемпотентность (`IF NOT EXISTS`, `ON CONFLICT DO UPDATE`).
- Индексы: `idx_{table}_{column}` (уже есть `ix_problems_node_id`, `ix_problems_raw_score`, `ix_attempts_student_node`).

## Деструктив
- **DROP / DELETE / TRUNCATE — только с явного согласия владельца.** Никогда молча, в том числе внутри миграции.

## Комментарии — на русском.
