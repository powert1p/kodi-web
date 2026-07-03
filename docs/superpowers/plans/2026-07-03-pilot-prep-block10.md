# Plan: Блок 1.0 — Пилот-подготовка (мини-срез · consent · телеметрия)

**Spec:** `docs/specs/2026-07-03-pilot-prep-block10.md`

## Goal
Свежий ученик проходит быстрый мини-срез (12 задач) → у него появляются задачи в тренажёре;
сбор детских фото юридически закрыт consent'ом до первой фотографии; сырые события UX пишутся в БД
для послепилотного анализа. Всё — не трогая diagnostic/exam FSM, mastery, граф.

## Architecture
- Backend: новые эндпоинты живут в модульном `backend/api/routers/trainer.py` (prefix `/api/trainer`),
  используют `_get_current_student(request)` и `limiter` из `api.routes` — паттерн существующих эндпоинтов.
  Схема расширяется через `Base.metadata.create_all` + идемпотентные ALTER/CREATE в `backend/run.py` (Alembic нет).
- Frontend: React PWA (`webapp/`), react-router-dom, TanStack Query поверх raw-fetch в `src/lib/api.ts`,
  JWT в `localStorage['kodi.jwt']`, дизайн — закрытые компоненты `Ap*` + `Mascot` (DESIGN_SYSTEM v5).

## Tech Stack
- Backend: Python 3.11, FastAPI, SQLAlchemy 2.0 async + asyncpg, Pydantic v2, slowapi, pytest + pytest-asyncio + httpx.
- Frontend: React + TypeScript strict + Tailwind v4, TanStack Query, Vitest.

## Global Constraints
- SQL: ТОЛЬКО параметризованный (`text()` + bind или ORM). `text()` + `IN` → `= ANY(:arr)` (asyncpg native). Никаких f-string.
- Async везде; `session, student = await _get_current_student(request)` → работа в `try` → `finally: await session.close()`.
- Комментарии/тексты — на русском, термины английские. Без новых зависимостей.
- Новый backend-код НЕ раздувает `api/routes.py` — идёт в `api/routers/trainer.py`.
- НЕ трогать: `core/trainer.py::build_wrong_tasks`, diagnostic/exam FSM, mastery/BKT, граф.
- НЕ реализовывать ничего сверх задач ниже (полировка соседнего кода запрещена).
- UI-задачи: перед кодом прочитать `webapp/DESIGN_SYSTEM.md`, использовать ТОЛЬКО токены/`Ap*`-компоненты.
- Гейты перед «done» задачи: backend — `.venv/bin/pytest backend/tests/ -x -q`; frontend — `npx tsc --noEmit` + `npm run lint:design` + `npm run build` + `npx vitest run` (в `webapp/`).
- ⚠️ Backend integration-тесты требуют `TEST_DATABASE_URL` (иначе db-фикстуры skip). Рабочий URL: `postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/kodi_test`.

---

## Task 1 — Миграция + модели: таблица `events`, колонки consent

**Files:**
- `backend/db/models.py` (edit): модель `Event`; 2 поля в `Student`.
- `backend/run.py` (edit): 2 ALTER в список students, CREATE TABLE events + индекс в список CREATE.
- `backend/tests/test_pilot_schema.py` (new): проверка, что схема создаётся и колонки/таблица есть.

**Steps:**

1. Напиши failing-тест `backend/tests/test_pilot_schema.py`:
```python
"""Схема Блока 1.0: колонки consent + таблица events создаются метадатой."""
from __future__ import annotations

import os
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_students_have_consent_columns(db_session):
    cols = (await db_session.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'students'"
    ))).scalars().all()
    assert "photo_consent" in cols
    assert "photo_consent_at" in cols


@pytest.mark.asyncio
async def test_events_table_exists_and_inserts(db_session):
    await db_session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (1, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ))
    await db_session.execute(text(
        "INSERT INTO events (student_id, event_type, payload) "
        "VALUES (1, 'hub_opened', '{\"k\": 1}'::jsonb)"
    ))
    await db_session.commit()
    n = (await db_session.execute(text("SELECT count(*) FROM events"))).scalar()
    assert n == 1
```
2. Запусти `TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/kodi_test .venv/bin/pytest backend/tests/test_pilot_schema.py -x -q` → падает (нет таблицы/колонок).
3. В `backend/db/models.py` в класс `Student` (после `paused_diagnostic`, строка ~109) добавь:
```python
    # Согласие родителя на использование фото работ ребёнка (Блок 1.0).
    # NULL = не спрашивали (мягкая карточка на hub); true/false = ответ дан.
    photo_consent: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    photo_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```
4. В `backend/db/models.py` в конец файла добавь модель `Event` (JSON/JSONB импорты уже есть):
```python
class Event(Base):
    """Сырое событие телеметрии UX (Блок 1.0, пилот-аналитика)."""

    __tablename__ = "events"
    __table_args__ = (
        Index("idx_events_student_created", "student_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)  # произвольная строка, не enum
    payload: Mapped[dict | None] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False
    )
```
5. В `backend/run.py` в список ALTER (после строки `ALTER TABLE students ... paused_diagnostic`, ~стр.36) добавь:
```python
            # ── consent на фото (Блок 1.0) ──
            "ALTER TABLE students ADD COLUMN IF NOT EXISTS photo_consent BOOLEAN",
            "ALTER TABLE students ADD COLUMN IF NOT EXISTS photo_consent_at TIMESTAMPTZ",
```
6. В `backend/run.py` в список CREATE (после индекса `idx_tutor_messages_session`, ~стр.156, ПЕРЕД закрывающей `]`) добавь:
```python
            # ── телеметрия UX (Блок 1.0) ──
            """
            CREATE TABLE IF NOT EXISTS events (
                id          BIGINT      PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                student_id  BIGINT      NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                event_type  TEXT        NOT NULL,
                payload     JSONB,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_events_student_created ON events (student_id, created_at)",
```
7. Запусти тест из шага 2 → зелёный. Прогони весь `.venv/bin/pytest backend/tests/ -x -q` (с TEST_DATABASE_URL) → зелёный.
8. Commit: `feat(pilot): схема Блока 1.0 — таблица events + колонки consent`.

---

## Task 2 — Backend consent: эндпоинт + 403 в diagnose + поле в auth/me + регистрация

**Files:**
- `backend/api/routers/trainer.py` (edit): `POST /consent`; 403-гейт в начале `post_diagnose`.
- `backend/api/routes.py` (edit): `PhoneRegisterBody.photo_consent`; запись при регистрации; `photo_consent` в `/auth/me`.
- `backend/tests/test_consent_api.py` (new).

**Steps:**

1. Напиши failing-тест `backend/tests/test_consent_api.py` (паттерн `test_verification_api.py` — подмена `async_session` в `db.base` и `api.routes`):
```python
"""Consent API: 403 на diagnose без согласия, проставление через /consent."""
from __future__ import annotations

import os
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

_TEST_URL = os.getenv("TEST_DATABASE_URL")


@pytest_asyncio.fixture
async def cclient(db_session):
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан")
    SID = 9500
    await db_session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (:sid, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ), {"sid": SID})
    await db_session.execute(text(
        "INSERT INTO nodes (id, name_ru, name_kz, bkt_p_t, bkt_p_g, bkt_p_s) "
        "VALUES ('CN01', 'Узел', 'Узел', 0.3, 0.05, 0.1) ON CONFLICT (id) DO NOTHING"
    ))
    pid = (await db_session.execute(text(
        "INSERT INTO problems (node_id, text_ru, answer, answer_type) "
        "VALUES ('CN01', 'задача', '5', 'number') RETURNING id"
    ))).scalar_one()
    await db_session.commit()

    from api.routes import _create_token
    token = _create_token(SID)

    import api.routes as routes_module
    import db.base as db_base
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    eng = create_async_engine(_TEST_URL)
    fac = async_sessionmaker(eng, expire_on_commit=False)
    o1, o2 = db_base.async_session, routes_module.async_session
    db_base.async_session = fac
    routes_module.async_session = fac
    from web import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac, token, pid, SID
    db_base.async_session = o1
    routes_module.async_session = o2
    await eng.dispose()


@pytest.mark.asyncio
async def test_diagnose_requires_consent(cclient):
    ac, token, pid, _sid = cclient
    files = {"photo": ("x.jpg", b"\xff\xd8\xff", "image/jpeg")}
    data = {"problem_id": str(pid)}
    r = await ac.post("/api/trainer/diagnose", headers={"Authorization": f"Bearer {token}"},
                      data=data, files=files)
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "consent_required"


@pytest.mark.asyncio
async def test_consent_endpoint_sets_flag(cclient, db_session):
    ac, token, _pid, sid = cclient
    r = await ac.post("/api/trainer/consent", headers={"Authorization": f"Bearer {token}"},
                      json={"photo_consent": True})
    assert r.status_code == 200
    row = (await db_session.execute(text(
        "SELECT photo_consent, photo_consent_at FROM students WHERE id = :sid"
    ), {"sid": sid})).fetchone()
    assert row.photo_consent is True
    assert row.photo_consent_at is not None
```
2. Запусти `.venv/bin/pytest backend/tests/test_consent_api.py -x -q` (с TEST_DATABASE_URL) → падает.
3. В `backend/api/routers/trainer.py` добавь схему и эндпоинт (рядом с другими Pydantic-схемами / эндпоинтами):
```python
class ConsentIn(BaseModel):
    photo_consent: bool


@router.post("/consent")
async def post_consent(request: Request, payload: ConsentIn) -> dict:
    """Проставляет согласие родителя на использование фото + timestamp."""
    session, student = await _get_current_student(request)
    try:
        await session.execute(
            text(
                "UPDATE students SET photo_consent = :c, "
                "photo_consent_at = CASE WHEN :c THEN NOW() ELSE photo_consent_at END "
                "WHERE id = :sid"
            ),
            {"c": payload.photo_consent, "sid": student.id},
        )
        await session.commit()
    finally:
        await session.close()
    return {"photo_consent": payload.photo_consent}
```
4. В `backend/api/routers/trainer.py` в `post_diagnose` — в самом начале тела `try` (после `session, student = await _get_current_student(request)`, ПЕРЕД загрузкой задачи, ~стр.322-324) вставь гейт:
```python
        # Сбор фото гейтится согласием родителя (Блок 1.0). Проверяем ДО любой работы.
        if student.photo_consent is not True:
            raise HTTPException(
                status_code=403,
                detail={"code": "consent_required",
                        "message": "Нужно согласие родителя на использование фото."},
            )
```
5. В `backend/api/routes.py`:
   - в `PhoneRegisterBody` (стр.77-80) добавь поле: `photo_consent: bool = False`.
   - в `auth_phone_register` при создании `Student(...)` (стр.236-244) добавь аргументы:
     `photo_consent=body.photo_consent, photo_consent_at=(func.now() if body.photo_consent else None),`
     (⚠️ проверь, что `func` импортирован в routes.py; если нет — используй `datetime.now(timezone.utc)` с уже существующими импортами, либо просто `photo_consent=body.photo_consent` и timestamp не ставь при регистрации — согласовано: при регистрации timestamp опционален, но если ставишь — только при True).
   - в `auth_me` (стр.278-288) в возвращаемый dict добавь: `"photo_consent": student.photo_consent,`.
6. Запусти тест из шага 2 → зелёный. Прогони весь backend pytest → зелёный.
7. Commit: `feat(pilot): consent — эндпоинт, 403 в diagnose, поле в auth/me и регистрации`.

---

## Task 3 — Backend мини-срез: `/srez/start` + `/srez/answer`

**Files:**
- `backend/core/srez.py` (new): чистая функция выбора 12 задач `pick_srez_problems`.
- `backend/api/routers/trainer.py` (edit): эндпоинты `POST /srez/start`, `POST /srez/answer`.
- `backend/tests/test_srez.py` (new): юнит выбора + integration start/answer.

**Steps:**

1. Напиши failing-тест `backend/tests/test_srez.py`:
```python
"""Мини-срез: выбор задач (разброс тем, difficulty ASC, исключение решённых) + API."""
from __future__ import annotations

import os
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

_TEST_URL = os.getenv("TEST_DATABASE_URL")


async def _seed_graph(db_session):
    # 3 темы, по 2 узла, по 2 задачи — хватит проверить разброс и исключение решённых.
    for tid in ("T1", "T2", "T3"):
        await db_session.execute(text(
            "INSERT INTO topics (id, strand, name_ru, name_kz, order_idx) "
            "VALUES (:t, 'RP', :t, :t, 0) ON CONFLICT (id) DO NOTHING"
        ), {"t": tid})
    diff = {"N1": 1, "N2": 2, "N3": 3}
    topic = {"N1": "T1", "N2": "T2", "N3": "T3"}
    for nid in ("N1", "N2", "N3"):
        await db_session.execute(text(
            "INSERT INTO nodes (id, name_ru, name_kz, difficulty, topic_id, bkt_p_t, bkt_p_g, bkt_p_s) "
            "VALUES (:n, :n, :n, :d, :t, 0.3, 0.05, 0.1) ON CONFLICT (id) DO NOTHING"
        ), {"n": nid, "d": diff[nid], "t": topic[nid]})
    ids = {}
    for nid in ("N1", "N2", "N3"):
        pid = (await db_session.execute(text(
            "INSERT INTO problems (node_id, text_ru, answer, answer_type) "
            "VALUES (:n, 'задача '||:n, '5', 'number') RETURNING id"
        ), {"n": nid})).scalar_one()
        ids[nid] = pid
    await db_session.commit()
    return ids


@pytest.mark.asyncio
async def test_pick_srez_distinct_topics_and_difficulty(db_session):
    from core.srez import pick_srez_problems
    await _seed_graph(db_session)
    rows = await pick_srez_problems(db_session, student_id=1, count=12)
    # Разброс: не более одной задачи на topic
    topics = [r.topic_key for r in rows]
    assert len(topics) == len(set(topics))
    # difficulty ASC
    diffs = [r.node_difficulty for r in rows]
    assert diffs == sorted(diffs)


@pytest.mark.asyncio
async def test_pick_srez_excludes_attempted(db_session):
    from core.srez import pick_srez_problems
    ids = await _seed_graph(db_session)
    await db_session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (7, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ))
    await db_session.execute(text(
        "INSERT INTO attempts (student_id, problem_id, node_id, answer_given, is_correct, source, created_at) "
        "VALUES (7, :pid, 'N1', '5', true, 'diagnostic', NOW())"
    ), {"pid": ids["N1"]})
    await db_session.commit()
    rows = await pick_srez_problems(db_session, student_id=7, count=12)
    assert ids["N1"] not in [r.id for r in rows]


@pytest_asyncio.fixture
async def sclient(db_session):
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан")
    ids = await _seed_graph(db_session)
    SID = 9600
    await db_session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (:sid, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ), {"sid": SID})
    await db_session.commit()
    from api.routes import _create_token
    token = _create_token(SID)
    import api.routes as routes_module
    import db.base as db_base
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    eng = create_async_engine(_TEST_URL)
    fac = async_sessionmaker(eng, expire_on_commit=False)
    o1, o2 = db_base.async_session, routes_module.async_session
    db_base.async_session = fac
    routes_module.async_session = fac
    from web import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac, token, ids, SID
    db_base.async_session = o1
    routes_module.async_session = o2
    await eng.dispose()


@pytest.mark.asyncio
async def test_srez_start_and_answer_flow(sclient, db_session):
    ac, token, ids, sid = sclient
    h = {"Authorization": f"Bearer {token}"}
    r = await ac.post("/api/trainer/srez/start", headers=h, json={})
    assert r.status_code == 200
    tasks = r.json()["tasks"]
    assert len(tasks) >= 1
    assert "answer" not in tasks[0]        # НЕ палим правильный ответ
    assert "solution" not in tasks[0]
    first = tasks[0]
    # Отвечаем неверно
    a = await ac.post("/api/trainer/srez/answer", headers=h,
                      json={"problem_id": first["problem_id"], "answer": "-999", "elapsed_ms": 1000})
    assert a.status_code == 200
    assert a.json()["is_correct"] is False
    # attempt записан как diagnostic → build_wrong_tasks его увидит
    n = (await db_session.execute(text(
        "SELECT count(*) FROM attempts WHERE student_id = :sid AND source = 'diagnostic' AND is_correct = false"
    ), {"sid": sid})).scalar()
    assert n == 1
```
2. Запусти `.venv/bin/pytest backend/tests/test_srez.py -x -q` (с TEST_DATABASE_URL) → падает (нет `core/srez.py`).
3. Создай `backend/core/srez.py`:
```python
"""Мини-срез (Блок 1.0): stateless-выбор задач для быстрого онбординга.

НЕ переиспользует diagnostic/exam FSM. Задачи выбираются один раз на /srez/start,
стейт держит клиент; ответы пишутся как attempts(source="diagnostic").
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# answer_type, набираемые с клавиатуры (choice/text исключены — их не ввести полем).
_TYPEABLE = ("number", "integer", "fraction", "decimal", "float")


async def pick_srez_problems(session: AsyncSession, student_id: int, count: int = 12):
    """Возвращает до `count` задач: разброс по темам, difficulty ASC, decomp мягко предпочтён,
    исключая задачи, по которым у ученика уже есть attempts.

    Каждая строка: .id .statement .answer_type .node_id .node_title .node_difficulty .topic_key
    """
    result = await session.execute(
        text(
            "SELECT id, statement, answer_type, node_id, node_title, node_difficulty, topic_key "
            "FROM ( "
            "  SELECT DISTINCT ON (COALESCE(n.topic_id, n.id)) "
            "    p.id, p.text_ru AS statement, p.answer_type, p.node_id, "
            "    n.name_ru AS node_title, n.difficulty AS node_difficulty, "
            "    COALESCE(n.topic_id, n.id) AS topic_key, "
            "    (dp.problems_db_id IS NOT NULL) AS has_decomp "
            "  FROM problems p "
            "  JOIN nodes n ON n.id = p.node_id "
            "  LEFT JOIN decomposition_problems dp ON dp.problems_db_id = p.id "
            "  WHERE (p.answer_type IS NULL OR p.answer_type = ANY(:types)) "
            "    AND NOT EXISTS ( "
            "      SELECT 1 FROM attempts a "
            "      WHERE a.student_id = :sid AND a.problem_id = p.id "
            "    ) "
            "  ORDER BY COALESCE(n.topic_id, n.id), has_decomp DESC, "
            "           n.difficulty ASC NULLS LAST, p.id "
            ") per_topic "
            "ORDER BY node_difficulty ASC NULLS LAST, id "
            "LIMIT :lim"
        ),
        {"types": list(_TYPEABLE), "sid": student_id, "lim": count},
    )
    return result.fetchall()
```
4. В `backend/api/routers/trainer.py` добавь импорт `from core.srez import pick_srez_problems` и эндпоинты:
```python
class SrezTaskOut(BaseModel):
    problem_id: int
    statement: str
    answer_type: str | None
    node_title: str
    position: int
    total: int


class SrezStartOut(BaseModel):
    tasks: list[SrezTaskOut]


class SrezAnswerIn(BaseModel):
    problem_id: int
    answer: str
    elapsed_ms: int | None = None


class SrezAnswerOut(BaseModel):
    is_correct: bool


@router.post("/srez/start", response_model=SrezStartOut)
async def post_srez_start(request: Request) -> SrezStartOut:
    """Мини-срез: сервер выбирает 12 задач (разброс тем, лёгкие первыми). Стейт держит клиент.
    Ответ НЕ содержит правильных ответов/решений."""
    session, student = await _get_current_student(request)
    try:
        rows = await pick_srez_problems(session, student_id=student.id, count=12)
    finally:
        await session.close()
    total = len(rows)
    tasks = [
        SrezTaskOut(
            problem_id=r.id, statement=r.statement, answer_type=r.answer_type,
            node_title=r.node_title, position=i + 1, total=total,
        )
        for i, r in enumerate(rows)
    ]
    return SrezStartOut(tasks=tasks)


@router.post("/srez/answer", response_model=SrezAnswerOut)
async def post_srez_answer(request: Request, payload: SrezAnswerIn) -> SrezAnswerOut:
    """Проверяет ответ задачи среза и пишет attempt(source='diagnostic').
    НЕ возвращает correct_answer/solution (задачи потом попадут в drill)."""
    session, student = await _get_current_student(request)
    try:
        prob = (await session.execute(
            text("SELECT node_id, answer, answer_type FROM problems WHERE id = :pid"),
            {"pid": payload.problem_id},
        )).fetchone()
        if prob is None:
            raise HTTPException(status_code=404, detail=f"Задача {payload.problem_id} не найдена")
        is_correct = check_answer(payload.answer, prob.answer, prob.answer_type)
        await session.execute(
            text(
                "INSERT INTO attempts "
                "(student_id, problem_id, node_id, answer_given, is_correct, response_time_ms, source, created_at) "
                "VALUES (:sid, :pid, :nid, :ans, :ok, :ms, 'diagnostic', NOW())"
            ),
            {"sid": student.id, "pid": payload.problem_id, "nid": prob.node_id,
             "ans": payload.answer, "ok": is_correct, "ms": payload.elapsed_ms},
        )
        await session.commit()
    finally:
        await session.close()
    return SrezAnswerOut(is_correct=is_correct)
```
5. Запусти тест из шага 2 → зелёный. Прогони весь backend pytest → зелёный.
6. Commit: `feat(pilot): мини-срез — /srez/start + /srez/answer (stateless, source=diagnostic)`.

---

## Task 4 — Backend телеметрия: `/events` (batch) + `/events/export` (owner CSV)

**Files:**
- `backend/api/routers/trainer.py` (edit): `POST /events`, `GET /events/export`.
- `backend/tests/test_events_api.py` (new).

**Steps:**

1. Напиши failing-тест `backend/tests/test_events_api.py` (фикстура-клиент как в Task 2, `SID = 9700`; для owner-теста ставь `settings.owner_student_id`):
```python
"""Телеметрия: batch insert событий + owner-only CSV-экспорт."""
from __future__ import annotations

import os
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

_TEST_URL = os.getenv("TEST_DATABASE_URL")


@pytest_asyncio.fixture
async def eclient(db_session):
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан")
    SID = 9700
    await db_session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (:sid, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ), {"sid": SID})
    await db_session.commit()
    from api.routes import _create_token
    token = _create_token(SID)
    import api.routes as routes_module
    import db.base as db_base
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    eng = create_async_engine(_TEST_URL)
    fac = async_sessionmaker(eng, expire_on_commit=False)
    o1, o2 = db_base.async_session, routes_module.async_session
    db_base.async_session = fac
    routes_module.async_session = fac
    from web import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac, token, SID
    db_base.async_session = o1
    routes_module.async_session = o2
    await eng.dispose()


@pytest.mark.asyncio
async def test_events_batch_insert(eclient, db_session):
    ac, token, sid = eclient
    h = {"Authorization": f"Bearer {token}"}
    r = await ac.post("/api/trainer/events", headers=h, json={"events": [
        {"event_type": "hub_opened"},
        {"event_type": "srez_answered", "payload": {"problem_id": 3, "is_correct": False}},
    ]})
    assert r.status_code == 200
    assert r.json()["inserted"] == 2
    n = (await db_session.execute(text(
        "SELECT count(*) FROM events WHERE student_id = :sid"), {"sid": sid})).scalar()
    assert n == 2


@pytest.mark.asyncio
async def test_events_export_owner_only(eclient):
    ac, token, sid = eclient
    from core.config import settings
    # Не владелец → 403
    old = settings.owner_student_id
    settings.owner_student_id = sid + 1
    r = await ac.get("/api/trainer/events/export?format=csv", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    # Владелец → 200 CSV
    settings.owner_student_id = sid
    r2 = await ac.get("/api/trainer/events/export?format=csv", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert "text/csv" in r2.headers["content-type"]
    assert "event_type" in r2.text
    settings.owner_student_id = old
```
2. Запусти `.venv/bin/pytest backend/tests/test_events_api.py -x -q` → падает.
3. В `backend/api/routers/trainer.py` добавь импорты вверху: `import csv`, `import io`, `import json`, `from fastapi.responses import Response`. Добавь схемы и эндпоинты:
```python
class EventIn(BaseModel):
    event_type: str
    payload: dict | None = None


class EventsBatchIn(BaseModel):
    events: list[EventIn]


class EventsBatchOut(BaseModel):
    inserted: int


@router.post("/events", response_model=EventsBatchOut)
@limiter.limit("60/minute")
async def post_events(request: Request, payload: EventsBatchIn) -> EventsBatchOut:
    """Пишет batch событий телеметрии (≤20). Неизвестные event_type НЕ отклоняем."""
    session, student = await _get_current_student(request)
    try:
        events = payload.events[:20]  # cap 20 за запрос
        for ev in events:
            await session.execute(
                text(
                    "INSERT INTO events (student_id, event_type, payload, created_at) "
                    "VALUES (:sid, :et, CAST(:pl AS JSONB), NOW())"
                ),
                {"sid": student.id, "et": ev.event_type,
                 "pl": json.dumps(ev.payload) if ev.payload is not None else None},
            )
        await session.commit()
    finally:
        await session.close()
    return EventsBatchOut(inserted=len(events))


@router.get("/events/export")
async def get_events_export(request: Request, format: str = Query("csv")) -> Response:
    """CSV-выгрузка всех событий. Только владелец (settings.owner_student_id), иначе 403."""
    session, student = await _get_current_student(request)
    try:
        is_owner = settings.owner_student_id != 0 and student.id == settings.owner_student_id
        if not is_owner:
            raise HTTPException(status_code=403, detail="Только для владельца")
        rows = (await session.execute(
            text("SELECT id, student_id, event_type, payload, created_at "
                 "FROM events ORDER BY created_at")
        )).fetchall()
    finally:
        await session.close()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "student_id", "event_type", "payload", "created_at"])
    for r in rows:
        payload = r.payload if isinstance(r.payload, str) else json.dumps(r.payload) if r.payload else ""
        writer.writerow([r.id, r.student_id, r.event_type, payload, r.created_at])
    return Response(content=buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=events.csv"})
```
4. Запусти тест из шага 2 → зелёный. Прогони весь backend pytest → зелёный.
5. Commit: `feat(pilot): телеметрия — /events batch + owner-only CSV-экспорт`.

---

## Task 5 — Frontend: api-клиент, типы, auth-проброс consent, телеметрия-хелпер

**Files:**
- `webapp/src/lib/types.ts` (edit): типы `SrezTask`.
- `webapp/src/lib/api.ts` (edit): `startSrez`, `answerSrez`, `postConsent`, хук `useSrezStart`.
- `webapp/src/lib/auth.ts` (edit): `registerWithPin(..., photoConsent)`; `StudentProfile.photo_consent`.
- `webapp/src/features/auth/AuthContext.tsx` (edit): `register(phone,name,pin,photoConsent)`.
- `webapp/src/lib/telemetry.ts` (new): `track(eventType, payload?)` fire-and-forget.
- `webapp/src/test/pilot-api.test.ts` (new): vitest на srez-парсинг + track-глушение ошибок.

**Steps:**

1. Напиши failing-тест `webapp/src/test/pilot-api.test.ts` (паттерн `src/test/api.test.ts`, `vi.stubGlobal('fetch', ...)`):
```typescript
import { describe, it, expect, vi, afterEach } from 'vitest'
import { startSrez, answerSrez } from '../lib/api'
import { track } from '../lib/telemetry'

afterEach(() => vi.restoreAllMocks())

function okJson(body: unknown) {
  return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) } as Response)
}

describe('srez api', () => {
  it('startSrez возвращает список задач', async () => {
    vi.stubGlobal('fetch', vi.fn(() => okJson({ tasks: [{ problem_id: 1, statement: 'x', answer_type: 'number', node_title: 'T', position: 1, total: 12 }] })))
    const tasks = await startSrez()
    expect(tasks).toHaveLength(1)
    expect(tasks[0].problem_id).toBe(1)
  })

  it('answerSrez возвращает is_correct', async () => {
    vi.stubGlobal('fetch', vi.fn(() => okJson({ is_correct: false })))
    const res = await answerSrez(1, '5', 1000)
    expect(res.is_correct).toBe(false)
  })
})

describe('telemetry', () => {
  it('track глотает сетевую ошибку (fire-and-forget)', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('offline'))))
    await expect(track('hub_opened')).resolves.toBeUndefined()
  })
})
```
2. Запусти `cd webapp && npx vitest run src/test/pilot-api.test.ts` → падает.
3. В `webapp/src/lib/types.ts` добавь:
```typescript
/** Одна задача мини-среза (Блок 1.0). Правильный ответ на клиент НЕ приходит. */
export interface SrezTask {
  problem_id: number
  statement: string
  answer_type: string | null
  node_title: string
  position: number
  total: number
}
```
4. В `webapp/src/lib/api.ts` добавь (после verification-секции):
```typescript
import type { SrezTask } from './types'

// ── Мини-срез (Блок 1.0) ──
export async function startSrez(): Promise<SrezTask[]> {
  const res = await apiFetch(`${API_BASE}/trainer/srez/start`, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  const data = (await res.json()) as { tasks?: SrezTask[] }
  return data.tasks ?? []
}

export async function answerSrez(problemId: number, answer: string, elapsedMs?: number): Promise<{ is_correct: boolean }> {
  const res = await apiFetch(`${API_BASE}/trainer/srez/answer`, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ problem_id: problemId, answer, elapsed_ms: elapsedMs ?? null }),
  })
  return res.json() as Promise<{ is_correct: boolean }>
}

// ── Consent (Блок 1.0) ──
export async function postConsent(photoConsent: boolean): Promise<void> {
  await apiFetch(`${API_BASE}/trainer/consent`, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ photo_consent: photoConsent }),
  })
}
```
   ⚠️ `SrezTask` импортируй в существующий `import type { ... } from './types'` (не дублируй строку импорта).
5. Создай `webapp/src/lib/telemetry.ts`:
```typescript
// Телеметрия UX (Блок 1.0): fire-and-forget POST /api/trainer/events.
// НИКОГДА не блокирует UX и не бросает — все ошибки глотаются.

const STORAGE_KEY = 'kodi.jwt'

/** Отправляет одно событие. Ошибки глотаются (fire-and-forget). */
export async function track(eventType: string, payload?: Record<string, unknown>): Promise<void> {
  try {
    let token: string | null = null
    try {
      token = typeof localStorage !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null
    } catch { /* localStorage недоступен */ }
    if (!token) return
    await fetch('/api/trainer/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ events: [{ event_type: eventType, payload: payload ?? null }] }),
    })
  } catch {
    // fire-and-forget: телеметрия не должна ронять UX
  }
}
```
6. В `webapp/src/lib/auth.ts`: в `StudentProfile` добавь `photo_consent: boolean | null`; в `registerWithPin` добавь параметр и поле body:
```typescript
export async function registerWithPin(phone: string, name: string, pin: string, photoConsent: boolean): Promise<void> {
  const res = await fetch(`${AUTH_BASE}/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone, name, pin, photo_consent: photoConsent }),
  })
  // ... (остальное без изменений)
```
7. В `webapp/src/features/auth/AuthContext.tsx`: измени тип и реализацию `register`:
```typescript
  register: (phone: string, name: string, pin: string, photoConsent: boolean) => Promise<void>
  // ...
  const register = useCallback(async (phone: string, name: string, pin: string, photoConsent: boolean) => {
    await registerWithPin(phone, name, pin, photoConsent)
    // ... (остальное как было)
  }, [/* deps как были */])
```
8. Запусти тест из шага 2 → зелёный. Прогони `npx tsc --noEmit` (в webapp) → должен показать ошибку в LoginPage (register теперь требует 4 аргумента) — это ОК, чинится в Task 7. Пока проверь, что vitest зелёный.
9. Commit: `feat(pilot-web): api-клиент срез/consent + телеметрия-хелпер`.

---

## Task 6 — UI: экран мини-среза `/srez` + CTA HubEmpty

> **v5-протокол (обязателен).** Прочти `webapp/DESIGN_SYSTEM.md` целиком. Компоненты-эталоны:
> `ApTextField` → `features/closure/RungActive`, `ApLinearProgress` → `features/hub/ProblemTopicsCard`,
> `Mascot` §5, `ApButton` → `ClosurePage`. Реши ТОЛЬКО из токенов + `Ap*`. Реплики Кёди голосом §5.

**Целевой макет (390×844):**
```
┌───────────────────────────────┐
│  Мини-срез          3 из 12    │  ← ApLinearProgress value=3/12, tone brand
│  ▓▓▓░░░░░░░░░░░░░               │
│                                │
│  ┌──────── ApCard ─────────┐   │
│  │  Тема: Дроби            │   │  ← node_title (muted caption)
│  │  <условие задачи 18px+> │   │  ← statement, MathText
│  │                         │   │
│  │  [ ApTextField ответ ]  │   │  ← фокус, inputMode подходящий
│  └─────────────────────────┘   │
│                                │
│  [   Проверить (ApButton)  ]   │  ← единственный primary-CTA
└───────────────────────────────┘
  фидбек: Mascot oops/hi + строка «Верно!»/«Разберём это потом» → авто-переход
```
**Финал:**
```
   Mascot celebrate
   «Нашли N тем для прокачки»
   [ К разбору ]  → navigate('/'), invalidate ['wrong-tasks']
```

**Files:**
- `webapp/src/features/srez/SrezPage.tsx` (new), при необходимости мелкие саб-компоненты в той же папке.
- `webapp/src/App.tsx` (edit): добавить `<Route path="/srez" element={<SrezPage />} />` внутри вложенных Routes (RequireAuth+AppShell).
- `webapp/src/features/hub/HubEmpty.tsx` (edit): CTA → `/srez`.

**Steps:**

1. Прочти `webapp/DESIGN_SYSTEM.md` + эталоны `RungActive`, `ProblemTopicsCard`, `Mascot`, `ClosurePage`.
2. Создай `webapp/src/features/srez/SrezPage.tsx`:
   - на mount: `startSrez()` (useState + один вызов; можно useQuery с `queryKey:['srez']`, `enabled` при первом входе). При загрузке — состояние loading (текст «Готовим срез…»), error — `HubError`-подобный ретрай, empty (0 задач) — Mascot celebrate + «Пока нечего проверять» + CTA на `/`.
   - индекс текущей задачи в `useState(0)`; поле ответа `useState('')`.
   - «Проверить»: `answerSrez(problem_id, answer, elapsed)` → показать фидбек (Mascot `oops` при неверном, `hi` при верном; НИКОГДА не показывай правильный ответ — его нет на клиенте) → через ~900мс перейти к следующей; вести счётчик неверных.
   - на финале: Mascot `celebrate`, «Нашли {wrongCount} тем для прокачки», ApButton «К разбору» → `queryClient.invalidateQueries({ queryKey: ['wrong-tasks'] })` + `navigate('/')`.
   - Телеметрия (fire-and-forget, `import { track }`): на start `track('srez_started')`; на каждый ответ `track('srez_answered', { problem_id, is_correct })`; на финале `track('srez_finished', { wrong_count })`.
   - Каждый компонент имеет loading/error/empty/success. Один primary-CTA на экране. Учебный текст ≥18px. Только токены/`Ap*`.
3. В `webapp/src/App.tsx` добавь маршрут `/srez` в блок вложенных Routes (рядом с `/analytics`):
```tsx
                <Route path="/srez" element={<SrezPage />} />
```
   и импорт `import { SrezPage } from './features/srez/SrezPage'`.
4. В `webapp/src/features/hub/HubEmpty.tsx` замени CTA:
```tsx
      <ApButton variant="primary" size="m" onClick={() => navigate('/srez')}>
        Пройти мини-срез
      </ApButton>
```
   (текст «Всё разобрано 🎉» оставь — HubEmpty показывается и когда ошибок нет; но CTA ведёт на срез, чтобы свежий ученик мог начать. Заголовок/подзаголовок НЕ переписывай сверх этой строки.)
5. Гейты (в `webapp/`): `npx tsc --noEmit` (кроме известной ошибки LoginPage из Task 5 — если Task 7 ещё не сделан, порядок задач допускает временную ошибку; финально tsc чист после Task 7), `npm run lint:design`, `npm run build`.
6. **Бинарный DoD:** `lint:design`/vitest/build зелёные; ровно один primary-CTA на экране среза; состояния loading/error/empty/success присутствуют; скриншот Playwright 390×844 экрана среза (задача + прогресс) и финала. НЕ показан правильный ответ ни в каком состоянии (запрет §2.5).
7. Commit: `feat(pilot-web): экран мини-среза /srez + CTA HubEmpty`.

---

## Task 7 — UI consent: чекбокс на регистрации + hub-карточка + обработка consent_required

> **v5-протокол.** Прочти `webapp/DESIGN_SYSTEM.md`. Consent-карточка — `ApCard tone="attn-soft"` (тёплый амбер,
> НЕ красный) + `Mascot mood="thinking"`; кнопки «Разрешаю» (primary) / «Позже» (ghost). Эталоны: `HubHero`, `DiagnosisCard`.

**Целевой макет hub-карточки (над списком ошибок):**
```
┌──────── ApCard attn-soft ────────┐
│  Mascot thinking                  │
│  «Спросим родителя»               │  ← h3
│  Чтобы разбирать ошибки по фото,  │  ← текст ≥16px
│  нужно согласие родителя.         │
│  [ Разрешаю ]   Позже             │  ← primary + ghost (ghost не текст-ссылка главного действия)
└───────────────────────────────────┘
```

**Files:**
- `webapp/src/features/auth/LoginPage.tsx` (edit): чекбокс на шаге `register-pin`; проброс в `register(...)`.
- `webapp/src/features/hub/ConsentCard.tsx` (new).
- `webapp/src/features/hub/HubPage.tsx` (edit): показать `ConsentCard`, когда `photo_consent == null`.
- `webapp/src/features/auth/useMe.ts` или существующий источник профиля (edit/new): отдать `photo_consent` (проверь, есть ли хук профиля; если нет — сделай лёгкий `fetch('/api/auth/me')` через существующий паттерн, НЕ изобретай глобальный стор).
- Drill diagnose-flow (`webapp/src/features/drill/useDiagnoseFlow.ts`) (edit): на `ApiError.status === 403` показать consent-состояние вместо generic-ошибки.

**Steps:**

1. Прочти `webapp/DESIGN_SYSTEM.md` + эталоны `HubHero`, `DiagnosisCard`. Найди, как HubPage/Drill получают профиль (grep `auth/me`, `photo_consent`).
2. В `LoginPage.tsx` шаг `register-pin`: добавь `const [consent, setConsent] = useState(false)` и под `ApTextField` — чекбокс (нативный `<input type="checkbox">` в лейбле, стилизованный токенами; текст-черновик):
   «Разрешаю использовать фото работ моего ребёнка для обучения модели. *(текст на проверку юристу)*»
   В `handleRegisterPin` вызови `register(phone.trim(), name.trim(), pin.trim(), consent)`. Регистрация НЕ блокируется, если чекбокс снят (consent можно дать позже на hub).
3. Создай `ConsentCard.tsx`: `ApCard tone="attn-soft"`, `Mascot thinking`, заголовок «Спросим родителя», текст, ApButton primary «Разрешаю» → `postConsent(true)` + инвалидация профиля; ghost «Позже» → `sessionStorage.setItem('kodi.consent.dismissed','1')` + локально скрыть. Все состояния (loading на «Разрешаю», disabled).
4. В `HubPage.tsx`: получи `photo_consent` из профиля; если `photo_consent == null` И `sessionStorage.getItem('kodi.consent.dismissed') !== '1'` — рендерь `<ConsentCard />` над `StatusRow`/списком. Показывай карточку и в ветке `total === 0`, и когда есть задачи (перед `HubEmpty`/списком). НЕ ломай существующие ветки isPending/isError.
5. В drill diagnose-flow: где ловится ошибка `postDiagnose`, добавь ветку `if (err instanceof ApiError && err.status === 403)` → выставить состояние «нужен consent» и отрендерить `ConsentCard` (переиспользуй компонент) вместо `DiagnosisError`. После успешного `postConsent(true)` — позволить повторить фото.
6. Телеметрия (fire-and-forget): `track('photo_submitted')` при отправке фото (если уже не добавлено). НЕ добавляй лишних событий сверх списка в спеке.
7. Гейты (в `webapp/`): `npx tsc --noEmit` (теперь ЧИСТ — 4-й аргумент register добавлен), `npm run lint:design`, `npm run build`, `npx vitest run`.
8. **Бинарный DoD:** гейты зелёные; consent-карточка НЕ красная (attn-soft); один primary-CTA в карточке; состояния loading/disabled; скриншот 390×844 hub с consent-карточкой; проверено, что `photo_consent==null` показывает карточку, «Позже» прячет её до перезагрузки сессии.
9. Commit: `feat(pilot-web): consent — чекбокс регистрации, hub-карточка, обработка 403 в drill`.

---

## Task 8 — Финальная интеграция + E2E

**Files:** без новых (проверочная задача). При находках — точечные правки в затронутых файлах.

**Steps:**

1. Backend: `TEST_DATABASE_URL=... .venv/bin/pytest backend/tests/ -x -q` → все зелёные (новые + существующие).
2. Frontend (в `webapp/`): `npx tsc --noEmit` (0 ошибок), `npm run lint:design`, `npm run build`, `npx vitest run` — всё зелёное.
3. E2E через Playwright MCP (свежий контейнер/дев, same-origin, JWT в localStorage — см. правило live-проверки):
   - Свежий ученик регистрируется (без consent) → hub показывает consent-карточку.
   - HubEmpty/hub CTA «Пройти мини-срез» → `/srez` → пройти 12 задач, часть ответить неверно.
   - После финала → hub → в списке «Твои ошибки» непусто (build_wrong_tasks увидел `source='diagnostic'` неверные).
   - Открыть drill первой ошибки → грузится.
   - Нажать «Разрешаю» в consent-карточке → карточка исчезает; фото-диагноз больше не даёт 403.
   - Owner: `GET /api/trainer/events/export?format=csv` (с owner-токеном) → CSV со строками событий (srez_started/answered/finished, hub_opened).
4. Скриншоты 390×844: экран среза, hub с consent-карточкой — приложить к итогу.
5. Проверка инварианта: `SELECT count(*) FROM events` растёт после прохода; `SELECT count(*) FROM attempts WHERE source='diagnostic' AND is_correct=false` = числу неверных ответов среза.
6. Commit: `test(pilot): E2E пилот-подготовки — срез→ошибки→drill, consent, экспорт событий`.
7. Вызови Skill `wrap`.

---

## Проверочные критерии всего блока (из спеки)
- pytest зелёный (юнит выбора среза + integration srez/consent/events + все существующие).
- tsc/lint:design/build/vitest зелёные; скриншоты 390×844 среза и hub-consent.
- E2E: свежий ученик → срез → wrong-tasks непуст → drill открывается; consent 403→200; CSV-экспорт owner-only.
