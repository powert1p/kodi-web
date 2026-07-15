"""Общий конфиг тестов.

Интеграционные тесты идут ТОЛЬКО против отдельной *_test базы (env TEST_DATABASE_URL).
Если переменная не задана — db-фикстуры пропускаются (data-тесты работают без БД).
Безопасность: drop_all выполняется только если имя БД содержит 'test'.
"""

import os

# env ДО любого импорта core.config — иначе fail-fast по пустому JWT_SECRET.
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-with-at-least-32-chars")

_TEST_URL = os.getenv("TEST_DATABASE_URL")

import pytest
import pytest_asyncio
from sqlalchemy import text


@pytest_asyncio.fixture
async def db_session():
    """Свежая схема в *_test БД + AsyncSession. Движок изолирован от db.base."""
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан — пропуск интеграционных тестов БД")

    dbname = _TEST_URL.rsplit("/", 1)[-1]
    assert "test" in dbname, f"интеграционные тесты только на *_test БД, получено '{dbname}'"

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from db.base import Base
    import db.models  # noqa: F401 — регистрация таблиц в metadata

    engine = create_async_engine(_TEST_URL)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def seeded_student(db_session):
    """Минимальный зарегистрированный студент (id=1) для тестов API графа."""
    await db_session.execute(
        text(
            "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
            "VALUES (1, true, 'ru', NOW(), false) "
            "ON CONFLICT (id) DO NOTHING"
        )
    )
    await db_session.commit()
    return 1
