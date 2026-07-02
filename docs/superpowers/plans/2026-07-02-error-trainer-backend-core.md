# Implementation Plan — Тренажёр ошибок: ядро + ИИ-тьютор

**Спека:** `docs/specs/2026-07-02-error-trainer-backend-core.md` · **Ветка:** feat/error-trainer-mobile

## Goal
Довести флоу тренажёра ошибок до конца: живой verification (closure с мока → сервер), агрегат «проблемные темы» в hub, единый context-pack для ИИ, multi-turn чат-тьютор после диагноза, синхронизация analytics-контракта FE↔BE, endpoint climb-down.

## Architecture
- Backend слои: handler (`api/routers/trainer.py`) → core-алгоритм (`core/trainer.py`, `core/agent_context.py`, `core/tutor.py`) → ORM (`db/models.py`). Core не знает об HTTP, принимает `AsyncSession` аргументом.
- Таксономия агрегации = CC-слой: `error_captures`/`recurring_errors`/`mastery` → `problems.node_id` → `nodes.topic_id` → `topics`. Fallback агрегата — всегда через `problems.node_id` (не через decomposition), чтобы practice-попытки без decomp-линка не терялись.
- Чат в БД (`tutor_sessions`/`tutor_messages`), не in-memory. Context-pack (`build_agent_context`) — единая точка сборки grounding для diagnose и чата.
- Frontend (`webapp/`): TanStack Query хуки поверх raw-fetch в `lib/api.ts`, типы-зеркало в `lib/types.ts`, AiPlus-компоненты (ApCard/ApButton/ApInformer, orange #FF8C00, DM Sans).

## Tech Stack
- Backend: Python 3.11, FastAPI, SQLAlchemy 2.0 async + asyncpg, Pydantic v2, slowapi, Gemini flash через OpenAI-compat (`core/llm_openai.py`).
- Frontend: React 19, TypeScript strict, Tailwind v4, TanStack Query, Vitest.

## Global Constraints
- **Async ВСЕГДА**: `async def` хендлеры, `await session.execute(...)`, `async_sessionmaker`. Никогда sync DB.
- **SQL только параметризованный**: `text()` с bind-параметрами; `= ANY(:arr)` для массивов (asyncpg-native); НИКОГДА f-string/конкатенация.
- **DDL идемпотентно в `run.py`** (`CREATE TABLE IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS`). Alembic нет. `Base.metadata.create_all` в тестах строит схему из моделей.
- **TDD**: failing test → run (падает) → implementation → run (зелёный) → commit. Каждая таска — независимо тестируемый кусок.
- **pytest против реального Postgres** через `TEST_DATABASE_URL` (имя БД содержит `test`); без переменной DB-тесты skip. Фикстуры — `db_session`, паттерн `client_with_student` из `backend/tests/test_trainer_api.py`. LLM в тестах — monkeypatch (не реальный вызов).
- **Комментарии на русском**, термины английские. Early return, макс 3 уровня вложенности.
- **Frontend**: `tsc -b` + `vite build` без ошибок; vitest зелёный; AiPlus-дизайн; не хардкодить строки-URL.
- **НЕ трогать**: `node.tag`, `micro_skills.domain` (legacy), core-логику `diagnose_photo`, порядок diagnose response-схемы, remap micro_skill.
- Команда backend-тестов: `.venv/bin/pytest backend/tests/ -x -q` (env `TEST_DATABASE_URL` задан). Команда frontend: из `webapp/` — `npm run test -- --run` и `npm run build`.
- **Проверено разведкой:** колонка `recurring_errors.resolved` УЖЕ существует (models.py:338 + run.py:128 DDL) — ALTER НЕ нужен.

---

### Task 1: Модели TutorSession/TutorMessage + DDL в run.py + тест схемы

**Files**
- Modify: `backend/db/models.py` (добавить 2 класса в конец файла, после `RecurringError`, стр. ~342)
- Modify: `backend/run.py` (добавить 2 CREATE TABLE + индекс в список `for stmt in [...]`, перед закрывающей `]` на стр. 134)
- Test: `backend/tests/test_tutor_schema.py` (Create)

**Interfaces**
- Produces: таблица `tutor_sessions(id PK, student_id FK students, problem_id FK problems, node_id, created_at)`; таблица `tutor_messages(id PK, session_id FK tutor_sessions CASCADE, role, content, created_at)`; индекс `idx_tutor_messages_session`.
- ORM-классы `TutorSession`, `TutorMessage` в `db.models`.

Шаги:
- [ ] Test: создать `backend/tests/test_tutor_schema.py`:
```python
"""Тест схемы чат-тьютора: таблицы tutor_sessions / tutor_messages создаются и связаны."""
from __future__ import annotations

import os

os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
from sqlalchemy import text

_TEST_URL = os.getenv("TEST_DATABASE_URL")


@pytest.mark.asyncio
async def test_tutor_tables_exist_and_link(db_session):
    """tutor_sessions + tutor_messages существуют; FK-каскад работает."""
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан")

    # Сид минимального студента + узла + задачи
    await db_session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (9100, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ))
    await db_session.execute(text(
        "INSERT INTO nodes (id, name_ru, name_kz, bkt_p_t, bkt_p_g, bkt_p_s) "
        "VALUES ('TS01', 'тема', 'тема', 0.3, 0.05, 0.1) ON CONFLICT (id) DO NOTHING"
    ))
    pid = (await db_session.execute(text(
        "INSERT INTO problems (node_id, text_ru, answer) VALUES ('TS01', 'q', '1') RETURNING id"
    ))).scalar_one()

    sid = (await db_session.execute(text(
        "INSERT INTO tutor_sessions (student_id, problem_id, node_id, created_at) "
        "VALUES (9100, :pid, 'TS01', NOW()) RETURNING id"
    ), {"pid": pid})).scalar_one()

    await db_session.execute(text(
        "INSERT INTO tutor_messages (session_id, role, content, created_at) "
        "VALUES (:sid, 'user', 'привет', NOW())"
    ), {"sid": sid})
    await db_session.commit()

    cnt = (await db_session.execute(text(
        "SELECT COUNT(*) FROM tutor_messages WHERE session_id = :sid"
    ), {"sid": sid})).scalar_one()
    assert cnt == 1
```
- [ ] Run: `.venv/bin/pytest backend/tests/test_tutor_schema.py -x -q` → падает (таблиц нет).
- [ ] Implementation: в `backend/db/models.py` в конец файла добавить:
```python
class TutorSession(Base):
    """Сессия чата с ИИ-тьютором: одна на (студент, задача)."""

    __tablename__ = "tutor_sessions"
    __table_args__ = (
        Index("idx_tutor_sessions_student_problem", "student_id", "problem_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    problem_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )
    node_id: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False
    )


class TutorMessage(Base):
    """Одна реплика чата тьютора (user/assistant)."""

    __tablename__ = "tutor_messages"
    __table_args__ = (
        Index("idx_tutor_messages_session", "session_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tutor_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # 'user' | 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False
    )
```
- [ ] Implementation: в `backend/run.py` в список `for stmt in [...]`, ПЕРЕД строкой 133 (`"CREATE INDEX IF NOT EXISTS idx_recurring_errors_micro_skill ..."`) добавить (внутри списка, между recurring_errors-блоком и его индексом — или сразу после индекса recurring_errors, до закрывающей `]`):
```python
            # ── чат-тьютор: сессии + сообщения ──
            """
            CREATE TABLE IF NOT EXISTS tutor_sessions (
                id          SERIAL      PRIMARY KEY,
                student_id  BIGINT      NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                problem_id  INTEGER     NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
                node_id     VARCHAR(10) NOT NULL,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_tutor_sessions_student_problem ON tutor_sessions (student_id, problem_id)",
            """
            CREATE TABLE IF NOT EXISTS tutor_messages (
                id          SERIAL      PRIMARY KEY,
                session_id  INTEGER     NOT NULL REFERENCES tutor_sessions(id) ON DELETE CASCADE,
                role        VARCHAR(16) NOT NULL,
                content     TEXT        NOT NULL,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_tutor_messages_session ON tutor_messages (session_id)",
```
- [ ] Run: `.venv/bin/pytest backend/tests/test_tutor_schema.py -x -q` → зелёный.
- [ ] Commit: `git add -A && git commit -m "feat(trainer): tutor_sessions/tutor_messages модели + DDL"`

---

### Task 2: core/agent_context.py — build_agent_context + тесты

**Files**
- Create: `backend/core/agent_context.py`
- Test: `backend/tests/test_agent_context.py`

**Interfaces**
- Produces:
```python
@dataclass
class AgentContext:
    problem_id: int
    node_id: str
    statement: str
    correct_answer: str
    canonical_steps: list[dict]   # [{n, instruction_ru, expected_value, micro_skill}]
    fingerprints: list[dict]      # [{micro_skill, wrong_answer, mistake_ru}]
    past_diagnoses: list[dict]    # [{cause_text, failed_micro_skill, created_at_iso}]
    recurring_errors: list[dict]  # [{micro_skill, error_count, last_cause_text}]
    node_mastery: float
    topic: dict | None            # {topic_id, strand, name_ru}

async def build_agent_context(session, *, student_id: int, problem_id: int, decomp_idx: int | None = None) -> AgentContext
```
- Consumes: `core.trainer.resolve_decomp` (для выбора decomp когда `decomp_idx` не задан).
- Consumed by: Task 6 (`core/tutor.py`), Task 7 (diagnose merge).

Шаги:
- [ ] Test: создать `backend/tests/test_agent_context.py`:
```python
"""Тесты build_agent_context — сборка grounding-пакета из БД."""
from __future__ import annotations

import os

os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
from sqlalchemy import text


async def _seed(session):
    await session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (9200, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ))
    await session.execute(text(
        "INSERT INTO topics (id, strand, grade, order_idx, name_ru, name_kz) "
        "VALUES ('6.PC', 'PC', 6, 1, 'Проценты', 'Пайыздар') ON CONFLICT (id) DO NOTHING"
    ))
    await session.execute(text(
        "INSERT INTO nodes (id, name_ru, name_kz, topic_id, bkt_p_t, bkt_p_g, bkt_p_s) "
        "VALUES ('PC02', 'Проценты', 'Пайыздар', '6.PC', 0.3, 0.05, 0.1) ON CONFLICT (id) DO NOTHING"
    ))
    pid = (await session.execute(text(
        "INSERT INTO problems (node_id, text_ru, answer) VALUES ('PC02', 'Найди 20% от 800', '160') RETURNING id"
    ))).scalar_one()
    await session.execute(text(
        "INSERT INTO decomposition_problems (idx, node_id, answer, primary_micro_skill, all_steps_verified, problems_db_id) "
        "VALUES (99001, 'PC02', '160', 'percent_base', true, :pid)"
    ), {"pid": pid})
    await session.execute(text(
        "INSERT INTO problem_steps (decomp_idx, n, instruction_ru, micro_skill, expected_value) "
        "VALUES (99001, 1, 'Перевести процент в дробь', 'percent_to_frac', '0.2')"
    ))
    await session.execute(text(
        "INSERT INTO problem_fingerprints (decomp_idx, micro_skill, wrong_answer, mistake_ru) "
        "VALUES (99001, 'percent_base', '20', 'Взял процент как число')"
    ))
    await session.execute(text(
        "INSERT INTO mastery (student_id, node_id, p_mastery) VALUES (9200, 'PC02', 0.42) "
        "ON CONFLICT (student_id, node_id) DO UPDATE SET p_mastery = 0.42"
    ))
    await session.execute(text(
        "INSERT INTO recurring_errors (student_id, micro_skill, node_id, error_count, last_cause_text, resolved, created_at) "
        "VALUES (9200, 'percent_base', 'PC02', 4, 'Путает базу', false, NOW()) "
        "ON CONFLICT (student_id, micro_skill) DO NOTHING"
    ))
    await session.commit()
    return pid


@pytest.mark.asyncio
async def test_build_agent_context_full(db_session):
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL не задан")
    from core.agent_context import build_agent_context

    pid = await _seed(db_session)
    ctx = await build_agent_context(db_session, student_id=9200, problem_id=pid)

    assert ctx.node_id == "PC02"
    assert ctx.correct_answer == "160"
    assert ctx.canonical_steps and ctx.canonical_steps[0]["instruction_ru"] == "Перевести процент в дробь"
    assert any(f["mistake_ru"] == "Взял процент как число" for f in ctx.fingerprints)
    assert abs(ctx.node_mastery - 0.42) < 1e-9
    assert any(r["micro_skill"] == "percent_base" for r in ctx.recurring_errors)
    assert ctx.topic and ctx.topic["name_ru"] == "Проценты"


@pytest.mark.asyncio
async def test_build_agent_context_unknown_problem(db_session):
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL не задан")
    from core.agent_context import build_agent_context

    with pytest.raises(ValueError):
        await build_agent_context(db_session, student_id=9200, problem_id=987654)
```
- [ ] Run: `.venv/bin/pytest backend/tests/test_agent_context.py -x -q` → падает (модуля нет).
- [ ] Implementation: создать `backend/core/agent_context.py`:
```python
"""Сборка grounding-пакета для ИИ (diagnose-промпт и чат-тьютор).

Единая точка: из БД собираем максимум контекста вокруг (студент, задача) —
условие, канонические шаги, fingerprints, прошлые диагнозы, recurring_errors,
mastery узла, тему. Используется core/tutor.py и api/routers/trainer.diagnose.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.trainer import resolve_decomp


@dataclass
class AgentContext:
    """Grounding-пакет вокруг (студент, задача)."""

    problem_id: int
    node_id: str
    statement: str
    correct_answer: str
    canonical_steps: list[dict]
    fingerprints: list[dict]
    past_diagnoses: list[dict]
    recurring_errors: list[dict]
    node_mastery: float
    topic: dict | None


async def build_agent_context(
    session: AsyncSession,
    *,
    student_id: int,
    problem_id: int,
    decomp_idx: int | None = None,
) -> AgentContext:
    """Собирает AgentContext. Raises ValueError если задача не найдена."""
    prob = (await session.execute(
        text("SELECT id, node_id, text_ru, answer FROM problems WHERE id = :pid"),
        {"pid": problem_id},
    )).fetchone()
    if prob is None:
        raise ValueError(f"Задача {problem_id} не найдена")

    node_id: str = prob.node_id
    correct_answer: str = prob.answer

    # ── decomp: явный decomp_idx или resolve_decomp ──
    if decomp_idx is None:
        decomp = await resolve_decomp(
            session, problem_id=problem_id, node_id=node_id, answer=correct_answer
        )
        resolved_idx = decomp.idx if decomp is not None else None
    else:
        resolved_idx = decomp_idx

    canonical_steps: list[dict] = []
    fingerprints: list[dict] = []
    if resolved_idx is not None:
        steps_rows = await session.execute(
            text(
                "SELECT n, instruction_ru, micro_skill, expected_value FROM problem_steps "
                "WHERE decomp_idx = :didx ORDER BY n"
            ),
            {"didx": resolved_idx},
        )
        canonical_steps = [
            {"n": s.n, "instruction_ru": s.instruction_ru,
             "expected_value": s.expected_value, "micro_skill": s.micro_skill}
            for s in steps_rows
        ]
        fp_rows = await session.execute(
            text(
                "SELECT micro_skill, wrong_answer, mistake_ru FROM problem_fingerprints "
                "WHERE decomp_idx = :didx"
            ),
            {"didx": resolved_idx},
        )
        fingerprints = [
            {"micro_skill": f.micro_skill, "wrong_answer": f.wrong_answer, "mistake_ru": f.mistake_ru}
            for f in fp_rows
        ]

    # ── прошлые диагнозы ученика на этом узле (до 5 свежих) ──
    diag_rows = await session.execute(
        text(
            "SELECT cause_text, failed_micro_skill, created_at FROM error_captures "
            "WHERE student_id = :sid AND node_id = :nid "
            "ORDER BY created_at DESC LIMIT 5"
        ),
        {"sid": student_id, "nid": node_id},
    )
    past_diagnoses = [
        {"cause_text": d.cause_text, "failed_micro_skill": d.failed_micro_skill,
         "created_at_iso": d.created_at.isoformat() if d.created_at else None}
        for d in diag_rows
    ]

    # ── recurring_errors по релевантным micro_skills (узел + шаги) ──
    step_skills = [s["micro_skill"] for s in canonical_steps if s.get("micro_skill")]
    re_rows = await session.execute(
        text(
            "SELECT re.micro_skill, re.error_count, re.last_cause_text "
            "FROM recurring_errors re "
            "WHERE re.student_id = :sid "
            "  AND (re.node_id = :nid OR re.micro_skill = ANY(:skills)) "
            "ORDER BY re.error_count DESC LIMIT 10"
        ),
        {"sid": student_id, "nid": node_id, "skills": step_skills},
    )
    recurring_errors = [
        {"micro_skill": r.micro_skill, "error_count": r.error_count, "last_cause_text": r.last_cause_text}
        for r in re_rows
    ]

    # ── mastery узла ──
    mastery_val = (await session.execute(
        text("SELECT p_mastery FROM mastery WHERE student_id = :sid AND node_id = :nid"),
        {"sid": student_id, "nid": node_id},
    )).scalar()
    node_mastery = float(mastery_val) if mastery_val is not None else 0.0

    # ── тема ──
    topic_row = await session.execute(
        text(
            "SELECT t.id, t.strand, t.name_ru FROM nodes n "
            "JOIN topics t ON t.id = n.topic_id WHERE n.id = :nid"
        ),
        {"nid": node_id},
    )
    tr = topic_row.fetchone()
    topic = {"topic_id": tr.id, "strand": tr.strand, "name_ru": tr.name_ru} if tr else None

    return AgentContext(
        problem_id=problem_id,
        node_id=node_id,
        statement=prob.text_ru,
        correct_answer=correct_answer,
        canonical_steps=canonical_steps,
        fingerprints=fingerprints,
        past_diagnoses=past_diagnoses,
        recurring_errors=recurring_errors,
        node_mastery=node_mastery,
        topic=topic,
    )
```
- [ ] Run: `.venv/bin/pytest backend/tests/test_agent_context.py -x -q` → зелёный.
- [ ] Commit: `git add -A && git commit -m "feat(trainer): core/agent_context.build_agent_context — grounding-пакет"`

---

### Task 3: build_problem_topics + GET /problem-topics + SQL-инвариант-тест

**Files**
- Modify: `backend/core/trainer.py` (добавить dataclass `ProblemTopicRow` + `build_problem_topics`, в конец файла)
- Modify: `backend/api/routers/trainer.py` (добавить Pydantic `ProblemTopicOut`/`ProblemTopicsResponse` + endpoint `GET /problem-topics`)
- Test: `backend/tests/test_problem_topics.py`

**Interfaces**
- Produces (core):
```python
@dataclass
class ProblemTopicRow:
    topic_id: str
    strand: str | None
    name_ru: str | None
    error_count: int
    top_micro_skills: list[str]
    nodes_mastery_avg: float
    closure_progress: float  # 0..1 = resolved / total recurring_errors в теме

async def build_problem_topics(session, student_id: int) -> list[ProblemTopicRow]
```
- Produces (HTTP): `GET /api/trainer/problem-topics` → `{topics: [{topic_id, strand, name_ru, error_count, top_micro_skills, nodes_mastery_avg, closure_progress}]}`
- Агрегация error_count — через `error_captures → problems.node_id → nodes.topic_id` (fallback-путь, независим от decomposition).

Шаги:
- [ ] Test: создать `backend/tests/test_problem_topics.py`:
```python
"""Тесты агрегата проблемных тем + SQL-инвариант error_count."""
from __future__ import annotations

import os

os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
from sqlalchemy import text


async def _seed(session, sid=9300):
    await session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (:sid, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ), {"sid": sid})
    await session.execute(text(
        "INSERT INTO topics (id, strand, grade, order_idx, name_ru, name_kz) "
        "VALUES ('6.PC', 'PC', 6, 1, 'Проценты', 'Пайыздар') ON CONFLICT (id) DO NOTHING"
    ))
    await session.execute(text(
        "INSERT INTO nodes (id, name_ru, name_kz, topic_id, bkt_p_t, bkt_p_g, bkt_p_s) "
        "VALUES ('PC02', 'Проценты', 'Пайыздар', '6.PC', 0.3, 0.05, 0.1) ON CONFLICT (id) DO NOTHING"
    ))
    pid = (await session.execute(text(
        "INSERT INTO problems (node_id, text_ru, answer) VALUES ('PC02', 'q', '1') RETURNING id"
    ))).scalar_one()
    # 3 error_captures на PC02
    for i in range(3):
        await session.execute(text(
            "INSERT INTO error_captures (student_id, problem_id, node_id, image_ref, created_at) "
            "VALUES (:sid, :pid, 'PC02', :img, NOW())"
        ), {"sid": sid, "pid": pid, "img": f"x/{i}.jpg"})
    await session.execute(text(
        "INSERT INTO recurring_errors (student_id, micro_skill, node_id, error_count, resolved, created_at) "
        "VALUES (:sid, 'percent_base', 'PC02', 3, false, NOW()) ON CONFLICT DO NOTHING"
    ), {"sid": sid})
    await session.execute(text(
        "INSERT INTO recurring_errors (student_id, micro_skill, node_id, error_count, resolved, created_at) "
        "VALUES (:sid, 'percent_change', 'PC02', 1, true, NOW()) ON CONFLICT DO NOTHING"
    ), {"sid": sid})
    await session.commit()
    return pid


@pytest.mark.asyncio
async def test_problem_topics_invariant(db_session):
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL не задан")
    from core.trainer import build_problem_topics

    await _seed(db_session)
    rows = await build_problem_topics(db_session, 9300)
    pc = next(r for r in rows if r.topic_id == "6.PC")

    # SQL-инвариант: error_count == raw count error_captures по topic
    raw = (await db_session.execute(text(
        "SELECT COUNT(*) FROM error_captures ec "
        "JOIN problems p ON p.id = ec.problem_id "
        "JOIN nodes n ON n.id = p.node_id "
        "WHERE n.topic_id = '6.PC' AND ec.student_id = 9300"
    ))).scalar_one()
    assert pc.error_count == raw == 3
    assert "percent_base" in pc.top_micro_skills
    # closure_progress = 1 resolved из 2 = 0.5
    assert abs(pc.closure_progress - 0.5) < 1e-9


@pytest.mark.asyncio
async def test_problem_topics_empty_student(db_session):
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL не задан")
    from core.trainer import build_problem_topics

    await db_session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (9399, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ))
    await db_session.commit()
    rows = await build_problem_topics(db_session, 9399)
    assert rows == []
```
- [ ] Run: `.venv/bin/pytest backend/tests/test_problem_topics.py -x -q` → падает.
- [ ] Implementation: в `backend/core/trainer.py` в конец файла добавить:
```python
# ═══════════════════════════════════════════════════════════════════════════════
# Проблемные темы: агрегат student × topic (CC-таксономия)
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ProblemTopicRow:
    """Агрегат по теме для hub тренажёра."""

    topic_id: str
    strand: str | None
    name_ru: str | None
    error_count: int
    top_micro_skills: list[str]
    nodes_mastery_avg: float
    closure_progress: float  # 0..1: доля resolved recurring_errors в теме


async def build_problem_topics(session: AsyncSession, student_id: int) -> list[ProblemTopicRow]:
    """Агрегирует ошибки ученика по темам (CC-слой).

    error_count — через error_captures → problems.node_id → nodes.topic_id → topics.
    Fallback гарантирован: агрегация НЕ зависит от decomposition-линка (practice ok).
    top_micro_skills / closure_progress — из recurring_errors по узлам темы.
    nodes_mastery_avg — средний p_mastery по узлам темы (default 0.0).
    """
    # ── error_count по темам ──
    err_rows = await session.execute(
        text(
            "SELECT n.topic_id, t.strand, t.name_ru, COUNT(ec.id) AS error_count "
            "FROM error_captures ec "
            "JOIN problems p ON p.id = ec.problem_id "
            "JOIN nodes n ON n.id = p.node_id "
            "LEFT JOIN topics t ON t.id = n.topic_id "
            "WHERE ec.student_id = :sid AND n.topic_id IS NOT NULL "
            "GROUP BY n.topic_id, t.strand, t.name_ru "
            "ORDER BY error_count DESC"
        ),
        {"sid": student_id},
    )
    topics: dict[str, ProblemTopicRow] = {}
    for r in err_rows:
        topics[r.topic_id] = ProblemTopicRow(
            topic_id=r.topic_id, strand=r.strand, name_ru=r.name_ru,
            error_count=r.error_count, top_micro_skills=[],
            nodes_mastery_avg=0.0, closure_progress=0.0,
        )
    if not topics:
        return []

    tids = list(topics.keys())

    # ── recurring_errors по темам: top skills + closure progress ──
    re_rows = await session.execute(
        text(
            "SELECT n.topic_id, re.micro_skill, re.error_count, re.resolved "
            "FROM recurring_errors re "
            "JOIN nodes n ON n.id = re.node_id "
            "WHERE re.student_id = :sid AND n.topic_id = ANY(:tids) "
            "ORDER BY re.error_count DESC"
        ),
        {"sid": student_id, "tids": tids},
    )
    resolved_cnt: dict[str, int] = {t: 0 for t in tids}
    total_cnt: dict[str, int] = {t: 0 for t in tids}
    for r in re_rows:
        tid = r.topic_id
        if tid not in topics:
            continue
        total_cnt[tid] += 1
        if r.resolved:
            resolved_cnt[tid] += 1
        if len(topics[tid].top_micro_skills) < 3:
            topics[tid].top_micro_skills.append(r.micro_skill)

    # ── средний mastery по узлам темы ──
    m_rows = await session.execute(
        text(
            "SELECT n.topic_id, AVG(m.p_mastery) AS avg_m "
            "FROM mastery m JOIN nodes n ON n.id = m.node_id "
            "WHERE m.student_id = :sid AND n.topic_id = ANY(:tids) "
            "GROUP BY n.topic_id"
        ),
        {"sid": student_id, "tids": tids},
    )
    for r in m_rows:
        if r.topic_id in topics:
            topics[r.topic_id].nodes_mastery_avg = float(r.avg_m) if r.avg_m is not None else 0.0

    # ── closure_progress ──
    for tid, row in topics.items():
        total = total_cnt.get(tid, 0)
        row.closure_progress = (resolved_cnt.get(tid, 0) / total) if total else 0.0

    return sorted(topics.values(), key=lambda x: x.error_count, reverse=True)
```
- [ ] Implementation: в `backend/api/routers/trainer.py`:
  - в импорт из `core.trainer` (стр. 23) добавить `build_problem_topics`.
  - после класса `AnalyticsResponse` (стр. 91) добавить:
```python
class ProblemTopicOut(BaseModel):
    """Одна проблемная тема для hub."""

    topic_id: str
    strand: str | None
    name_ru: str | None
    error_count: int
    top_micro_skills: list[str]
    nodes_mastery_avg: float
    closure_progress: float


class ProblemTopicsResponse(BaseModel):
    """Ответ /problem-topics."""

    topics: list[ProblemTopicOut]
```
  - после endpoint `get_analytics` (стр. 221) добавить:
```python
@router.get("/problem-topics", response_model=ProblemTopicsResponse)
async def get_problem_topics(request: Request) -> ProblemTopicsResponse:
    """Проблемные темы ученика (CC-агрегат): ошибки, топ-умения, прогресс закрытия."""
    session, student = await _get_current_student(request)
    try:
        rows = await build_problem_topics(session, student_id=student.id)
    finally:
        await session.close()
    return ProblemTopicsResponse(topics=[
        ProblemTopicOut(
            topic_id=r.topic_id, strand=r.strand, name_ru=r.name_ru,
            error_count=r.error_count, top_micro_skills=r.top_micro_skills,
            nodes_mastery_avg=r.nodes_mastery_avg, closure_progress=r.closure_progress,
        )
        for r in rows
    ])
```
- [ ] Run: `.venv/bin/pytest backend/tests/test_problem_topics.py -x -q` → зелёный.
- [ ] Commit: `git add -A && git commit -m "feat(trainer): build_problem_topics + GET /problem-topics"`

---

### Task 4: POST /verification/start + /verification/answer + resolved update

**Files**
- Modify: `backend/api/routers/trainer.py` (импорт `pick_verification_problem` + `check_answer`; 2 endpoint + схемы)
- Test: `backend/tests/test_verification_api.py`

**Interfaces**
- Consumes: `core.trainer.pick_verification_problem(session, node_id, exclude_problem_id) -> VerificationProblemRow(id, node_id, text_ru, answer, sub_difficulty)`; `core.grading.check_answer(student_answer, correct_answer, answer_type=None) -> bool`.
- Produces:
  - `POST /api/trainer/verification/start` body `{problem_id: int, micro_skill?: str}` → `{problem_id, node_id, topic_label, statement, micro_skill, xp}` (404 если задача/проверочная не найдена).
  - `POST /api/trainer/verification/answer` body `{problem_id: int, answer: str, micro_skill?: str}` → `{correct: bool}`; при correct+micro_skill: `UPDATE recurring_errors SET resolved=true`. Критерий закрытия — одна верная (MVP).

Шаги:
- [ ] Test: создать `backend/tests/test_verification_api.py` (использует паттерн `client_with_student` — импортируй фикстуру локально копией сид-хелперов; ниже автономная фикстура):
```python
"""Интеграционные тесты verification-эндпоинтов closure."""
from __future__ import annotations

import os

os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

_TEST_URL = os.getenv("TEST_DATABASE_URL")


@pytest_asyncio.fixture
async def vclient(db_session):
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан")
    SID = 9400
    await db_session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (:sid, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ), {"sid": SID})
    await db_session.execute(text(
        "INSERT INTO nodes (id, name_ru, name_kz, bkt_p_t, bkt_p_g, bkt_p_s) "
        "VALUES ('VF01', 'Проверка', 'Проверка', 0.3, 0.05, 0.1) ON CONFLICT (id) DO NOTHING"
    ))
    p1 = (await db_session.execute(text(
        "INSERT INTO problems (node_id, text_ru, answer, sub_difficulty) "
        "VALUES ('VF01', 'drill-задача', '10', 2) RETURNING id"
    ))).scalar_one()
    p2 = (await db_session.execute(text(
        "INSERT INTO problems (node_id, text_ru, answer, sub_difficulty) "
        "VALUES ('VF01', 'контрольная', '20', 2) RETURNING id"
    ))).scalar_one()
    await db_session.execute(text(
        "INSERT INTO recurring_errors (student_id, micro_skill, node_id, error_count, resolved, created_at) "
        "VALUES (:sid, 'vf_skill', 'VF01', 2, false, NOW()) ON CONFLICT DO NOTHING"
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
        yield ac, token, p1, p2, SID
    db_base.async_session = o1
    routes_module.async_session = o2
    await eng.dispose()


@pytest.mark.asyncio
async def test_verification_start_returns_other_problem(vclient):
    ac, token, p1, p2, sid = vclient
    resp = await ac.post("/api/trainer/verification/start",
                         headers={"Authorization": f"Bearer {token}"},
                         json={"problem_id": p1, "micro_skill": "vf_skill"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["problem_id"] == p2
    assert body["statement"] == "контрольная"
    assert body["node_id"] == "VF01"


@pytest.mark.asyncio
async def test_verification_answer_correct_resolves(vclient):
    ac, token, p1, p2, sid = vclient
    resp = await ac.post("/api/trainer/verification/answer",
                         headers={"Authorization": f"Bearer {token}"},
                         json={"problem_id": p2, "answer": "20", "micro_skill": "vf_skill"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["correct"] is True

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    eng = create_async_engine(_TEST_URL)
    fac = async_sessionmaker(eng, expire_on_commit=False)
    async with fac() as s:
        res = (await s.execute(text(
            "SELECT resolved FROM recurring_errors WHERE student_id = :sid AND micro_skill = 'vf_skill'"
        ), {"sid": sid})).scalar_one()
    await eng.dispose()
    assert res is True


@pytest.mark.asyncio
async def test_verification_answer_wrong_not_resolved(vclient):
    ac, token, p1, p2, sid = vclient
    resp = await ac.post("/api/trainer/verification/answer",
                         headers={"Authorization": f"Bearer {token}"},
                         json={"problem_id": p2, "answer": "99", "micro_skill": "vf_skill"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["correct"] is False


@pytest.mark.asyncio
async def test_verification_start_no_token_401(vclient):
    ac, token, p1, p2, sid = vclient
    resp = await ac.post("/api/trainer/verification/start", json={"problem_id": p1})
    assert resp.status_code == 401
```
- [ ] Run: `.venv/bin/pytest backend/tests/test_verification_api.py -x -q` → падает.
- [ ] Implementation: в `backend/api/routers/trainer.py`:
  - импорт из `core.trainer` (стр. 23) добавить `pick_verification_problem`.
  - в начало файла добавить `from core.grading import check_answer`.
  - после endpoint `post_diagnose` (конец файла) добавить:
```python
# ── Verification (closure): проверочная задача того же навыка ─────────────────

class VerificationStartIn(BaseModel):
    problem_id: int
    micro_skill: str | None = None


class VerificationStartOut(BaseModel):
    problem_id: int
    node_id: str
    topic_label: str
    statement: str
    micro_skill: str | None
    xp: int


class VerificationAnswerIn(BaseModel):
    problem_id: int
    answer: str
    micro_skill: str | None = None


class VerificationAnswerOut(BaseModel):
    correct: bool


_VERIFICATION_XP = 30


@router.post("/verification/start", response_model=VerificationStartOut)
async def post_verification_start(request: Request, payload: VerificationStartIn) -> VerificationStartOut:
    """Даёт контрольную задачу того же узла (другую), чтобы закрыть ошибку."""
    session, _student = await _get_current_student(request)
    try:
        prob = (await session.execute(
            text("SELECT node_id FROM problems WHERE id = :pid"),
            {"pid": payload.problem_id},
        )).fetchone()
        if prob is None:
            raise HTTPException(status_code=404, detail=f"Задача {payload.problem_id} не найдена")
        node_id: str = prob.node_id

        vp = await pick_verification_problem(
            session, node_id=node_id, exclude_problem_id=payload.problem_id
        )
        if vp is None:
            raise HTTPException(status_code=404, detail="Нет проверочной задачи для этого узла")

        topic_label = (await session.execute(
            text("SELECT name_ru FROM nodes WHERE id = :nid"), {"nid": node_id}
        )).scalar() or node_id
    finally:
        await session.close()

    return VerificationStartOut(
        problem_id=vp.id, node_id=vp.node_id, topic_label=topic_label,
        statement=vp.text_ru, micro_skill=payload.micro_skill, xp=_VERIFICATION_XP,
    )


@router.post("/verification/answer", response_model=VerificationAnswerOut)
async def post_verification_answer(request: Request, payload: VerificationAnswerIn) -> VerificationAnswerOut:
    """Проверяет ответ на контрольную. Верно + micro_skill → recurring_errors.resolved=true."""
    session, student = await _get_current_student(request)
    try:
        prob = (await session.execute(
            text("SELECT answer, answer_type FROM problems WHERE id = :pid"),
            {"pid": payload.problem_id},
        )).fetchone()
        if prob is None:
            raise HTTPException(status_code=404, detail=f"Задача {payload.problem_id} не найдена")

        correct = check_answer(payload.answer, prob.answer, prob.answer_type)

        if correct and payload.micro_skill:
            await session.execute(
                text(
                    "UPDATE recurring_errors SET resolved = true "
                    "WHERE student_id = :sid AND micro_skill = :ms"
                ),
                {"sid": student.id, "ms": payload.micro_skill},
            )
            await session.commit()
    finally:
        await session.close()

    return VerificationAnswerOut(correct=correct)
```
- [ ] Run: `.venv/bin/pytest backend/tests/test_verification_api.py -x -q` → зелёный.
- [ ] Commit: `git add -A && git commit -m "feat(trainer): verification/start + verification/answer (closure на живых данных)"`

---

### Task 5: GET /easier — climb-down

**Files**
- Modify: `backend/api/routers/trainer.py` (импорт `pick_easier_decomp`; endpoint + схема)
- Test: `backend/tests/test_easier_api.py`

**Interfaces**
- Consumes: `core.trainer.pick_easier_decomp(session, *, micro_skill, exclude_idx) -> EasierDecompRow(idx, node_id, answer, primary_micro_skill, all_steps_verified, step_count)`.
- Produces: `GET /api/trainer/easier?micro_skill=<str>&exclude_idx=<int?>` → `{decomp_idx, node_id, answer, primary_micro_skill, step_count, steps: [StepOut]}` (404 если нет).

Шаги:
- [ ] Test: создать `backend/tests/test_easier_api.py`:
```python
"""Тест climb-down endpoint /easier."""
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
    SID = 9500
    await db_session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (:sid, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ), {"sid": SID})
    await db_session.execute(text(
        "INSERT INTO nodes (id, name_ru, name_kz, bkt_p_t, bkt_p_g, bkt_p_s) "
        "VALUES ('EZ01', 'Легче', 'Легче', 0.3, 0.05, 0.1) ON CONFLICT (id) DO NOTHING"
    ))
    # два decomp: idx=98001 (2 шага, текущий), idx=98002 (1 шаг, полегче)
    await db_session.execute(text(
        "INSERT INTO decomposition_problems (idx, node_id, answer, primary_micro_skill, all_steps_verified) "
        "VALUES (98001, 'EZ01', '5', 'ez_skill', true), (98002, 'EZ01', '3', 'ez_skill', true)"
    ))
    await db_session.execute(text(
        "INSERT INTO problem_steps (decomp_idx, n, instruction_ru, micro_skill, expected_value) VALUES "
        "(98001, 1, 'шаг1', 'ez_skill', '2'), (98001, 2, 'шаг2', 'ez_skill', '5'), "
        "(98002, 1, 'один шаг', 'ez_skill', '3')"
    ))
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
        yield ac, token
    db_base.async_session = o1
    routes_module.async_session = o2
    await eng.dispose()


@pytest.mark.asyncio
async def test_easier_returns_fewest_steps(eclient):
    ac, token = eclient
    resp = await ac.get("/api/trainer/easier?micro_skill=ez_skill&exclude_idx=98001",
                        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["decomp_idx"] == 98002
    assert body["step_count"] == 1
    assert len(body["steps"]) == 1


@pytest.mark.asyncio
async def test_easier_404_unknown_skill(eclient):
    ac, token = eclient
    resp = await ac.get("/api/trainer/easier?micro_skill=nonexistent",
                        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404
```
- [ ] Run: `.venv/bin/pytest backend/tests/test_easier_api.py -x -q` → падает.
- [ ] Implementation: в `backend/api/routers/trainer.py`:
  - импорт из `core.trainer` (стр. 23) добавить `pick_easier_decomp`.
  - в конец файла добавить:
```python
# ── Climb-down: decomp полегче для того же навыка ─────────────────────────────

class EasierDecompOut(BaseModel):
    decomp_idx: int
    node_id: str
    answer: str
    primary_micro_skill: str | None
    step_count: int
    steps: list[StepOut]


@router.get("/easier", response_model=EasierDecompOut)
async def get_easier(
    request: Request,
    micro_skill: str = Query(..., description="Код микро-умения"),
    exclude_idx: int | None = Query(None, description="Исключить текущий decomp_idx"),
) -> EasierDecompOut:
    """Возвращает decomp с наименьшим числом шагов для навыка (climb-down)."""
    session, _student = await _get_current_student(request)
    try:
        row = await pick_easier_decomp(session, micro_skill=micro_skill, exclude_idx=exclude_idx)
        if row is None:
            raise HTTPException(status_code=404, detail="Нет более простой декомпозиции для навыка")
        steps_raw = await session.execute(
            text(
                "SELECT n, instruction_ru, micro_skill, expected_value FROM problem_steps "
                "WHERE decomp_idx = :didx ORDER BY n"
            ),
            {"didx": row.idx},
        )
        steps = [
            StepOut(n=s.n, instruction_ru=s.instruction_ru, micro_skill=s.micro_skill,
                    expected_value=s.expected_value, kind="compute", reveal=None)
            for s in steps_raw
        ]
    finally:
        await session.close()

    return EasierDecompOut(
        decomp_idx=row.idx, node_id=row.node_id, answer=row.answer,
        primary_micro_skill=row.primary_micro_skill, step_count=row.step_count, steps=steps,
    )
```
- [ ] Run: `.venv/bin/pytest backend/tests/test_easier_api.py -x -q` → зелёный.
- [ ] Commit: `git add -A && git commit -m "feat(trainer): GET /easier climb-down endpoint"`

---

### Task 6: core/tutor.py + chat_reply + POST /tutor/chat + rate-limit

**Files**
- Modify: `backend/core/llm_openai.py` (добавить `chat_reply(messages)`)
- Create: `backend/core/tutor.py`
- Modify: `backend/api/routers/trainer.py` (импорт `limiter`, `generate_tutor_reply`; endpoint + схемы)
- Test: `backend/tests/test_tutor_api.py`

**Interfaces**
- Produces (`llm_openai`): `async def chat_reply(messages: list[dict]) -> str` (без vision; `_get_active_client` + model_chain; `LlmUnavailable` при недоступности).
- Produces (`tutor`): `def build_system_prompt(ctx: AgentContext) -> str`; `async def generate_tutor_reply(session, *, student_id, problem_id, decomp_idx, user_message, history) -> str`.
- Produces (HTTP): `POST /api/trainer/tutor/chat` body `{problem_id: int, decomp_idx?: int, message: str}` → `{session_id, reply, history: [{role, content}]}`. Rate-limit `@limiter.limit("15/minute")`.
- Consumes: `core.agent_context.build_agent_context`.

Шаги:
- [ ] Test: создать `backend/tests/test_tutor_api.py`:
```python
"""Интеграционный тест чата тьютора (LLM замокан)."""
from __future__ import annotations

import os

os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

_TEST_URL = os.getenv("TEST_DATABASE_URL")


@pytest_asyncio.fixture
async def tclient(db_session, monkeypatch):
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан")
    SID = 9600
    await db_session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (:sid, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ), {"sid": SID})
    await db_session.execute(text(
        "INSERT INTO nodes (id, name_ru, name_kz, bkt_p_t, bkt_p_g, bkt_p_s) "
        "VALUES ('TU01', 'Тема', 'Тема', 0.3, 0.05, 0.1) ON CONFLICT (id) DO NOTHING"
    ))
    pid = (await db_session.execute(text(
        "INSERT INTO problems (node_id, text_ru, answer) VALUES ('TU01', 'q', '1') RETURNING id"
    ))).scalar_one()
    await db_session.commit()

    from api.routes import _create_token
    token = _create_token(SID)

    # Мокаем LLM на уровне endpoint-импорта
    async def _fake_reply(*args, **kwargs):
        return "Подумай, что меняется на втором шаге?"
    monkeypatch.setattr("api.routers.trainer.generate_tutor_reply", _fake_reply)

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
async def test_tutor_chat_creates_session_and_persists(tclient):
    ac, token, pid, sid = tclient
    resp = await ac.post("/api/trainer/tutor/chat",
                         headers={"Authorization": f"Bearer {token}"},
                         json={"problem_id": pid, "message": "не понял этот шаг"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["reply"].startswith("Подумай")
    # history: user + assistant
    assert len(body["history"]) == 2
    assert body["history"][0]["role"] == "user"
    assert body["history"][1]["role"] == "assistant"

    # второй ход — та же сессия, history растёт
    resp2 = await ac.post("/api/trainer/tutor/chat",
                          headers={"Authorization": f"Bearer {token}"},
                          json={"problem_id": pid, "message": "а дальше?"})
    body2 = resp2.json()
    assert body2["session_id"] == body["session_id"]
    assert len(body2["history"]) == 4


@pytest.mark.asyncio
async def test_tutor_chat_no_token_401(tclient):
    ac, token, pid, sid = tclient
    resp = await ac.post("/api/trainer/tutor/chat", json={"problem_id": pid, "message": "hi"})
    assert resp.status_code == 401
```
- [ ] Run: `.venv/bin/pytest backend/tests/test_tutor_api.py -x -q` → падает.
- [ ] Implementation: в `backend/core/llm_openai.py` в конец файла добавить:
```python
# ─── текстовый чат (тьютор, без vision) ───────────────────────────────────────

async def chat_reply(messages: list[dict]) -> str:
    """Возвращает текст ответа модели на список messages (system+history+user).

    Использует активного провайдера (Gemini flash по умолчанию) без изображений.
    Raises LlmUnavailable если клиент недоступен или все модели chain упали.
    """
    client, model_chain = _get_active_client()
    if client is None:
        raise LlmUnavailable("Chat клиент недоступен: пустой ключ или пакет openai не установлен.")

    from core.config import settings  # noqa: PLC0415
    provider = settings.vision_provider

    last_exc: Exception | None = None
    for model in model_chain:
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=800,
                ),
                timeout=_OPENAI_TIMEOUT,
            )
            return response.choices[0].message.content or ""
        except asyncio.TimeoutError as exc:
            logger.warning("%s chat timeout (model=%s)", provider, model)
            last_exc = exc
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s chat error (model=%s): %s", provider, model, type(exc).__name__)
            last_exc = exc

    raise LlmUnavailable(
        f"Все модели в {provider}_model_chain недоступны (chat, {type(last_exc).__name__})"
    )
```
- [ ] Implementation: создать `backend/core/tutor.py`:
```python
"""Чат-тьютор: сократический диалог поверх grounding-пакета.

Строит system-промпт из AgentContext (условие, шаги, правильный ответ, ошибки,
mastery), запрещает раскрывать финальный ответ, вызывает chat_reply.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from core.agent_context import AgentContext, build_agent_context
from core.llm_openai import chat_reply

# Максимум реплик истории, передаваемых модели (защита контекста/цены)
_MAX_HISTORY = 20


def build_system_prompt(ctx: AgentContext) -> str:
    """Собирает сократический system-промпт из grounding-пакета."""
    steps = "\n".join(
        f"  Шаг {s['n']}: {s['instruction_ru']} → {s['expected_value']}"
        for s in ctx.canonical_steps
    ) or "  (шаги недоступны)"
    fps = "\n".join(
        f"  - {f['micro_skill']}: неверный ответ «{f['wrong_answer']}» — {f['mistake_ru']}"
        for f in ctx.fingerprints
    ) or "  (нет типовых ошибок)"
    recurring = "\n".join(
        f"  - {r['micro_skill']}: {r['error_count']} раз(а); {r['last_cause_text'] or ''}"
        for r in ctx.recurring_errors
    ) or "  (нет повторяющихся ошибок)"
    topic_line = f"{ctx.topic['name_ru']} ({ctx.topic['strand']})" if ctx.topic else "—"

    return (
        "Ты — доброжелательный математический тьютор Кёди. Ведёшь диалог с учеником "
        "на русском, помогаешь разобрать ошибку в конкретной задаче.\n\n"
        f"ЗАДАЧА:\n{ctx.statement}\n\n"
        f"ПРАВИЛЬНЫЙ ОТВЕТ (для тебя, НЕ называй ученику): {ctx.correct_answer}\n\n"
        f"КАНОНИЧЕСКИЕ ШАГИ:\n{steps}\n\n"
        f"ТИПОВЫЕ ОШИБКИ НА ЭТОЙ ЗАДАЧЕ:\n{fps}\n\n"
        f"ПОВТОРЯЮЩИЕСЯ ОШИБКИ ЭТОГО УЧЕНИКА:\n{recurring}\n\n"
        f"ТЕМА: {topic_line}. Владение узлом: {ctx.node_mastery:.2f} (0..1).\n\n"
        "ПРАВИЛА ДИАЛОГА:\n"
        "1. Задавай наводящие вопросы, веди к решению по шагам — НИКОГДА не называй "
        "финальный ответ напрямую.\n"
        "2. Отталкивайся от того, что ученик уже написал; хвали верные шаги.\n"
        "3. Пиши коротко (2-4 предложения), по-человечески, без формул-простыней.\n"
        "4. Если ученик застрял — дай подсказку на ОДИН следующий шаг, не на всё решение."
    )


async def generate_tutor_reply(
    session: AsyncSession,
    *,
    student_id: int,
    problem_id: int,
    decomp_idx: int | None,
    user_message: str,
    history: list[dict],
) -> str:
    """Генерирует ответ тьютора: context-pack → system → chat_reply.

    history — список {role, content} прошлых реплик (без текущего user_message).
    """
    ctx = await build_agent_context(
        session, student_id=student_id, problem_id=problem_id, decomp_idx=decomp_idx
    )
    system = build_system_prompt(ctx)
    trimmed = history[-_MAX_HISTORY:]
    messages = [{"role": "system", "content": system}]
    messages.extend({"role": h["role"], "content": h["content"]} for h in trimmed)
    messages.append({"role": "user", "content": user_message})
    return await chat_reply(messages)
```
- [ ] Implementation: в `backend/api/routers/trainer.py`:
  - добавить импорты: `from api.routes import _get_current_student, limiter` (заменить существующий импорт `_get_current_student` на строку с `limiter`); `from core.tutor import generate_tutor_reply`.
  - в конец файла добавить:
```python
# ── Чат-тьютор: multi-turn диалог после диагноза ──────────────────────────────

class TutorChatIn(BaseModel):
    problem_id: int
    decomp_idx: int | None = None
    message: str


class TutorMessageOut(BaseModel):
    role: str
    content: str


class TutorChatOut(BaseModel):
    session_id: int
    reply: str
    history: list[TutorMessageOut]


@router.post("/tutor/chat", response_model=TutorChatOut)
@limiter.limit("15/minute")
async def post_tutor_chat(request: Request, payload: TutorChatIn) -> TutorChatOut:
    """Один ход диалога с тьютором. Сессия auto-create по (студент, задача)."""
    session, student = await _get_current_student(request)
    try:
        # Проверяем задачу (404)
        prob = (await session.execute(
            text("SELECT node_id FROM problems WHERE id = :pid"),
            {"pid": payload.problem_id},
        )).fetchone()
        if prob is None:
            raise HTTPException(status_code=404, detail=f"Задача {payload.problem_id} не найдена")

        # Reuse или create сессии
        sess_row = (await session.execute(
            text(
                "SELECT id FROM tutor_sessions "
                "WHERE student_id = :sid AND problem_id = :pid "
                "ORDER BY id DESC LIMIT 1"
            ),
            {"sid": student.id, "pid": payload.problem_id},
        )).fetchone()
        if sess_row is None:
            session_id = (await session.execute(
                text(
                    "INSERT INTO tutor_sessions (student_id, problem_id, node_id, created_at) "
                    "VALUES (:sid, :pid, :nid, NOW()) RETURNING id"
                ),
                {"sid": student.id, "pid": payload.problem_id, "nid": prob.node_id},
            )).scalar_one()
        else:
            session_id = sess_row.id

        # История из БД
        hist_rows = await session.execute(
            text(
                "SELECT role, content FROM tutor_messages "
                "WHERE session_id = :sess ORDER BY id"
            ),
            {"sess": session_id},
        )
        history = [{"role": h.role, "content": h.content} for h in hist_rows]

        # Генерация ответа (LLM)
        reply = await generate_tutor_reply(
            session,
            student_id=student.id,
            problem_id=payload.problem_id,
            decomp_idx=payload.decomp_idx,
            user_message=payload.message,
            history=history,
        )

        # Persist обе реплики
        await session.execute(
            text(
                "INSERT INTO tutor_messages (session_id, role, content, created_at) VALUES "
                "(:sess, 'user', :u, NOW()), (:sess, 'assistant', :a, NOW())"
            ),
            {"sess": session_id, "u": payload.message, "a": reply},
        )
        await session.commit()

        # Итоговая история
        full = await session.execute(
            text("SELECT role, content FROM tutor_messages WHERE session_id = :sess ORDER BY id"),
            {"sess": session_id},
        )
        out_history = [TutorMessageOut(role=r.role, content=r.content) for r in full]
    finally:
        await session.close()

    return TutorChatOut(session_id=session_id, reply=reply, history=out_history)
```
- [ ] Run: `.venv/bin/pytest backend/tests/test_tutor_api.py -x -q` → зелёный.
- [ ] Commit: `git add -A && git commit -m "feat(trainer): чат-тьютор — core/tutor + POST /tutor/chat + chat_reply"`

---

### Task 7: Слить diagnose-промпт на build_agent_context (schema неизменна)

**Files**
- Modify: `backend/api/routers/trainer.py` (в `post_diagnose` заменить ручную сборку `canonical_steps` на `build_agent_context`)
- Test: прогон существующих `test_trainer_api.py` (diagnose-тесты 7-13) — регресс, без новых тестов.

**Interfaces**
- Consumes: `core.agent_context.build_agent_context`.
- Инвариант: response-схема `DiagnosisOut` и поведение (error_captures/recurring_errors) НЕ меняются — только источник `canonical_steps`.

Шаги:
- [ ] Run (baseline): `.venv/bin/pytest backend/tests/test_trainer_api.py -x -q` → зелёный (до изменений).
- [ ] Implementation: в `backend/api/routers/trainer.py`:
  - импорт `from core.agent_context import build_agent_context`.
  - в `post_diagnose` заменить блок «── 5. resolve_decomp → canonical_steps ──» (стр. 352-366) на:
```python
        # ── 5. Grounding через единый context-pack ───────────────────────────
        agent_ctx = await build_agent_context(
            session, student_id=student.id, problem_id=problem_id
        )
        canonical_steps: list[dict] = [
            {"n": s["n"], "instruction_ru": s["instruction_ru"], "expected_value": s["expected_value"]}
            for s in agent_ctx.canonical_steps
        ]
```
  - Оставить всё остальное (resolve_decomp более не нужен в этом хендлере, но его импорт используется в других местах — НЕ удалять импорт из `core.trainer`).
- [ ] Run: `.venv/bin/pytest backend/tests/test_trainer_api.py -x -q` → зелёный (все diagnose-тесты проходят).
- [ ] Run (полный backend): `.venv/bin/pytest backend/tests/ -x -q` → зелёный.
- [ ] Commit: `git add -A && git commit -m "refactor(trainer): diagnose grounding через build_agent_context"`

---

### Task 8: Frontend types.ts + api.ts (analytics-контракт fix + новые fetch/хуки) + vitest

**Files**
- Modify: `webapp/src/lib/types.ts`
- Modify: `webapp/src/lib/api.ts`
- Test: `webapp/src/test/api.test.ts` (добавить тесты новых функций)

**Interfaces**
- Produces (types): `RecurringErrorOut`, `GlobalErrorOut`, `AnalyticsData {my_top, global_top?}`, `ProblemTopic`, `TutorMessage`, `VerificationProblemDTO`, `TutorChatResponse`.
- Produces (api): `fetchAnalytics()→AnalyticsData|null` (без mock), `asAnalyticsData` по `my_top`; `fetchProblemTopics`/`useProblemTopics`; `startVerification`/`answerVerification`; `sendTutorMessage`; `fetchEasier`.

Шаги:
- [ ] Test: в `webapp/src/test/api.test.ts` добавить в конец:
```typescript
import { asAnalyticsData, fetchProblemTopics, startVerification, answerVerification, sendTutorMessage } from '../lib/api'

describe('asAnalyticsData (my_top контракт)', () => {
  it('нормализует {my_top} в AnalyticsData', () => {
    const raw = { my_top: [{ micro_skill: 'pc', label_ru: 'Проценты', error_count: 3, last_cause_text: null, node_id: 'PC02' }] }
    const result = asAnalyticsData(raw)
    expect(result?.my_top).toHaveLength(1)
    expect(result?.my_top[0]?.micro_skill).toBe('pc')
  })
  it('возвращает null если my_top отсутствует', () => {
    expect(asAnalyticsData({ foo: 1 })).toBeNull()
  })
})

describe('fetchProblemTopics', () => {
  it('парсит {topics}', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ topics: [{ topic_id: '6.PC', strand: 'PC', name_ru: 'Проценты', error_count: 3, top_micro_skills: ['pc'], nodes_mastery_avg: 0.4, closure_progress: 0.5 }] }),
    }))
    const result = await fetchProblemTopics()
    expect(result).toHaveLength(1)
    expect(result[0]?.topic_id).toBe('6.PC')
  })
})

describe('verification', () => {
  it('startVerification постит problem_id', async () => {
    let body: string | null = null
    vi.stubGlobal('fetch', vi.fn().mockImplementation((_u: string, init: RequestInit) => {
      body = init.body as string
      return Promise.resolve({ ok: true, json: async () => ({ problem_id: 2, node_id: 'VF01', topic_label: 'x', statement: 'q', micro_skill: 'vf', xp: 30 }) })
    }))
    const res = await startVerification(1, 'vf')
    expect(res.problem_id).toBe(2)
    expect(JSON.parse(body as unknown as string).problem_id).toBe(1)
  })
  it('answerVerification возвращает correct', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ correct: true }) }))
    const res = await answerVerification(2, '20', 'vf')
    expect(res.correct).toBe(true)
  })
})

describe('sendTutorMessage', () => {
  it('возвращает reply + history', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ session_id: 1, reply: 'подумай', history: [{ role: 'user', content: 'hi' }, { role: 'assistant', content: 'подумай' }] }),
    }))
    const res = await sendTutorMessage(1, 'hi')
    expect(res.reply).toBe('подумай')
    expect(res.history).toHaveLength(2)
  })
})
```
- [ ] Run: `cd webapp && npm run test -- --run src/test/api.test.ts` → падает (функций нет).
- [ ] Implementation: в `webapp/src/lib/types.ts` заменить блок `ErrorType`/`AnalyticsData` (стр. 41-59) на:
```typescript
/** Запись повторяющейся ошибки ученика (зеркало BE RecurringErrorOut). */
export interface RecurringErrorOut {
  micro_skill: string
  label_ru: string | null
  error_count: number
  last_cause_text: string | null
  node_id: string | null
}

/** Глобальный топ ошибок (только для владельца). */
export interface GlobalErrorOut {
  micro_skill: string
  label_ru: string | null
  total_errors: number
  students_affected: number
}

/** Аналитика тренажёра (зеркало BE AnalyticsResponse). */
export interface AnalyticsData {
  my_top: RecurringErrorOut[]
  global_top?: GlobalErrorOut[]
}

/** Проблемная тема ученика (зеркало BE ProblemTopicOut). */
export interface ProblemTopic {
  topic_id: string
  strand: string | null
  name_ru: string | null
  error_count: number
  top_micro_skills: string[]
  nodes_mastery_avg: number
  closure_progress: number
}

/** Одна реплика чата тьютора. */
export interface TutorMessage {
  role: 'user' | 'assistant'
  content: string
}

/** Ответ POST /tutor/chat. */
export interface TutorChatResponse {
  session_id: number
  reply: string
  history: TutorMessage[]
}

/** Контрольная задача из BE verification/start. */
export interface VerificationProblemDTO {
  problem_id: number
  node_id: string
  topic_label: string
  statement: string
  micro_skill: string | null
  xp: number
}
```
- [ ] Implementation: в `webapp/src/lib/api.ts`:
  - удалить импорт `MOCK_ANALYTICS` (стр. 8).
  - обновить import типов (стр. 6): `import type { WrongTask, Diagnosis, AnalyticsData, ProblemTopic, TutorChatResponse, VerificationProblemDTO } from './types'`.
  - заменить `fetchAnalytics` (стр. 120-139) и `asAnalyticsData` (стр. 142-147) на:
```typescript
export async function fetchAnalytics(): Promise<unknown> {
  const res = await apiFetch(`${API_BASE}/trainer/analytics`, { headers: authHeaders() })
  return res.json()
}

/** Нормализует unknown-ответ аналитики в AnalyticsData (или null). */
export function asAnalyticsData(raw: unknown): AnalyticsData | null {
  if (!raw || typeof raw !== 'object') return null
  const myTop = (raw as { my_top?: unknown }).my_top
  if (!Array.isArray(myTop)) return null
  const globalTop = (raw as { global_top?: unknown }).global_top
  return {
    my_top: myTop as AnalyticsData['my_top'],
    global_top: Array.isArray(globalTop) ? (globalTop as AnalyticsData['global_top']) : undefined,
  }
}
```
  - добавить в конец файла (перед последней строкой хуков или после `useDiagnose`):
```typescript
// ── Проблемные темы ──
export async function fetchProblemTopics(): Promise<ProblemTopic[]> {
  const res = await apiFetch(`${API_BASE}/trainer/problem-topics`, { headers: authHeaders() })
  const data = (await res.json()) as { topics?: ProblemTopic[] }
  return data.topics ?? []
}

export function useProblemTopics() {
  return useQuery({
    queryKey: ['problem-topics'],
    queryFn: fetchProblemTopics,
    staleTime: 60_000,
  })
}

// ── Verification (closure) ──
export async function startVerification(problemId: number, microSkill?: string | null): Promise<VerificationProblemDTO> {
  const res = await apiFetch(`${API_BASE}/trainer/verification/start`, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ problem_id: problemId, micro_skill: microSkill ?? null }),
  })
  return res.json() as Promise<VerificationProblemDTO>
}

export async function answerVerification(problemId: number, answer: string, microSkill?: string | null): Promise<{ correct: boolean }> {
  const res = await apiFetch(`${API_BASE}/trainer/verification/answer`, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ problem_id: problemId, answer, micro_skill: microSkill ?? null }),
  })
  return res.json() as Promise<{ correct: boolean }>
}

// ── Чат тьютора ──
export async function sendTutorMessage(problemId: number, message: string, decompIdx?: number | null): Promise<TutorChatResponse> {
  const res = await apiFetch(`${API_BASE}/trainer/tutor/chat`, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ problem_id: problemId, message, decomp_idx: decompIdx ?? null }),
  })
  return res.json() as Promise<TutorChatResponse>
}

// ── Climb-down ──
export async function fetchEasier(microSkill: string, excludeIdx?: number | null): Promise<unknown> {
  const params = new URLSearchParams({ micro_skill: microSkill })
  if (excludeIdx != null) params.set('exclude_idx', String(excludeIdx))
  const res = await apiFetch(`${API_BASE}/trainer/easier?${params.toString()}`, { headers: authHeaders() })
  return res.json()
}
```
  - в существующем тесте `fetchAnalytics` (api.test.ts стр. 69-80): ответ `{total, mastered}` больше не проходит через fallback — функция теперь возвращает raw json, тест `expect(result).toEqual(mockData)` остаётся зелёным (fetchAnalytics возвращает json как есть). Не менять этот тест.
- [ ] Run: `cd webapp && npm run test -- --run` → зелёный.
- [ ] Run: `cd webapp && npm run build` → tsc+vite без ошибок (если `MOCK_ANALYTICS` больше нигде не импортируется — файл `analytics/mock.ts` остаётся dead, это ок).
- [ ] Commit: `git add -A && git commit -m "feat(webapp): analytics my_top контракт + problem-topics/verification/tutor API"`

---

### Task 9: Frontend — hub-блок «Мои проблемные темы»

**Files**
- Create: `webapp/src/features/hub/ProblemTopicsCard.tsx`
- Modify: `webapp/src/features/hub/HubPage.tsx`

**Interfaces**
- Consumes: `useProblemTopics()` из `lib/api`, тип `ProblemTopic`.
- Produces: секция над списком «Твои ошибки» с темами (name_ru, error_count, closure_progress как полоса).

Шаги:
- [ ] Implementation: создать `webapp/src/features/hub/ProblemTopicsCard.tsx`:
```typescript
import type { CSSProperties } from 'react'
import { useProblemTopics } from '../../lib/api'

// Блок «Мои проблемные темы» (AiPlus ap-card): тема → число ошибок → полоса
// прогресса закрытия. Скрывается пока тем нет (empty — не показываем шум).
export function ProblemTopicsCard({ delay = 0 }: { delay?: number }) {
  const { data, isPending } = useProblemTopics()
  if (isPending || !data || data.length === 0) return null

  const topics = data.slice(0, 5)

  return (
    <section
      className="ap-card reveal flex flex-col gap-3 p-4"
      style={{ '--reveal-delay': `${delay}ms` } as CSSProperties}
    >
      <div className="flex items-center gap-2">
        <h2 className="text-h3 text-text-primary">Мои проблемные темы</h2>
        <span className="ml-auto text-caption1 text-text-secondary">закрой ошибки</span>
      </div>
      <ul className="flex flex-col gap-3">
        {topics.map((t) => {
          const pct = Math.round(t.closure_progress * 100)
          return (
            <li key={t.topic_id} className="flex flex-col gap-1.5">
              <div className="flex items-baseline gap-2">
                <span className="text-caption1-medium text-text-primary">{t.name_ru ?? t.topic_id}</span>
                <span className="font-num ml-auto inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-bg-secondary px-1.5 text-caption2-medium tabular-nums text-text-dark-gray">
                  {t.error_count}
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-bg-secondary">
                <div
                  className="h-full rounded-full bg-[var(--color-text-brand,#FF8C00)] transition-[width] duration-500"
                  style={{ width: `${pct}%` }}
                  role="progressbar"
                  aria-valuenow={pct}
                  aria-valuemin={0}
                  aria-valuemax={100}
                />
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
```
- [ ] Implementation: в `webapp/src/features/hub/HubPage.tsx`:
  - добавить импорт: `import { ProblemTopicsCard } from './ProblemTopicsCard'`.
  - вставить `<ProblemTopicsCard delay={100} />` между блоком `<HubHero .../>` (стр. 49-54) и блоком заголовка «Твои ошибки» (стр. 56):
```tsx
          <ProblemTopicsCard delay={100} />
```
- [ ] Run: `cd webapp && npm run build` → зелёный.
- [ ] Commit: `git add -A && git commit -m "feat(webapp): hub-блок «Мои проблемные темы»"`

---

### Task 10: Frontend — чат-панель тьютора в drill

**Files**
- Create: `webapp/src/features/drill/TutorPanel.tsx`
- Modify: `webapp/src/features/drill/DrillPage.tsx`

**Interfaces**
- Consumes: `sendTutorMessage(problemId, message, decompIdx?)`, тип `TutorMessage`.
- Produces: чат-панель под `DiagnosisCard`, видимая когда `flow.status === 'result'`; states: idle/sending/error.

Шаги:
- [ ] Implementation: создать `webapp/src/features/drill/TutorPanel.tsx`:
```typescript
import { useState } from 'react'
import { ApButton } from '../../components/ApButton'
import { Mascot } from '../../components/Mascot'
import { sendTutorMessage, ApiError } from '../../lib/api'
import type { TutorMessage } from '../../lib/types'

interface TutorPanelProps {
  problemId: number
  decompIdx?: number | null
}

// Чат-тьютор после диагноза (AiPlus ap-card): ученик спрашивает — Кёди наводит,
// не раскрывая финальный ответ. Multi-turn, история с сервера. States: idle/sending/error.
export function TutorPanel({ problemId, decompIdx }: TutorPanelProps) {
  const [history, setHistory] = useState<TutorMessage[]>([])
  const [input, setInput] = useState('')
  const [status, setStatus] = useState<'idle' | 'sending' | 'error'>('idle')

  async function send() {
    const msg = input.trim()
    if (!msg || status === 'sending') return
    setStatus('sending')
    setInput('')
    try {
      const res = await sendTutorMessage(problemId, msg, decompIdx)
      setHistory(res.history)
      setStatus('idle')
    } catch (err) {
      const detail = err instanceof ApiError && err.status === 429
        ? 'Слишком много вопросов подряд — подожди минуту.'
        : 'Кёди задумался. Попробуй ещё раз.'
      setHistory((h) => [...h, { role: 'assistant', content: detail }])
      setStatus('error')
    }
  }

  return (
    <article className="ap-card flex flex-col gap-3 p-4">
      <div className="flex items-center gap-2">
        <Mascot mood="think" size={36} className="shrink-0" />
        <span className="text-caption1-medium text-text-primary">Спроси Кёди про этот шаг</span>
      </div>

      {history.length > 0 && (
        <ul className="flex flex-col gap-2">
          {history.map((m, i) => (
            <li
              key={i}
              className={
                m.role === 'user'
                  ? 'self-end rounded-2xl rounded-br-sm bg-bg-secondary px-3 py-2 text-caption1 text-text-primary'
                  : 'self-start rounded-2xl rounded-bl-sm bg-bg-tertiary px-3 py-2 text-caption1 text-text-primary'
              }
            >
              {m.content}
            </li>
          ))}
        </ul>
      )}

      <div className="flex items-end gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              void send()
            }
          }}
          rows={1}
          placeholder="Например: почему тут не 20?"
          className="min-h-[40px] flex-1 resize-none rounded-lg border border-stroke-primary-disabled bg-bg-primary px-3 py-2 text-caption1 text-text-primary outline-none focus:border-[var(--color-text-brand,#FF8C00)]"
        />
        <ApButton
          variant="filled"
          size="m"
          disabled={status === 'sending' || input.trim().length === 0}
          onClick={() => void send()}
        >
          {status === 'sending' ? '…' : 'Спросить'}
        </ApButton>
      </div>
    </article>
  )
}
```
- [ ] Implementation: в `webapp/src/features/drill/DrillPage.tsx`:
  - добавить импорт: `import { TutorPanel } from './TutorPanel'`.
  - в блоке `flow.status === 'result' && flow.diagnosis` (стр. 142-148) после `<DiagnosisCard ... />` добавить панель (внутри того же блока — обернуть в фрагмент):
```tsx
          {flow.status === 'result' && flow.diagnosis && (
            <>
              <DiagnosisCard
                diagnosis={flow.diagnosis}
                stepLabel={stepLabel}
                onCorrect={flow.reset}
              />
              <TutorPanel problemId={task.problem_id} decompIdx={task.decomp_idx} />
            </>
          )}
```
- [ ] Run: `cd webapp && npm run build` → зелёный.
- [ ] Commit: `git add -A && git commit -m "feat(webapp): чат-панель тьютора в drill после диагноза"`

---

### Task 11: Frontend — closure на живой API + analytics рендер my_top

**Files**
- Modify: `webapp/src/features/closure/useClosure.ts`
- Modify: `webapp/src/features/closure/ClosurePage.tsx`
- Modify: `webapp/src/features/analytics/AnalyticsPage.tsx`

**Interfaces**
- Consumes: `startVerification`, `answerVerification`, `asAnalyticsData` (my_top).
- Produces: closure тянет контрольную с `verification/start`, проверяет через `verification/answer`; analytics рендерит `my_top`.

Шаги:
- [ ] Implementation: заменить `webapp/src/features/closure/useClosure.ts` целиком:
```typescript
import { useCallback, useEffect, useState } from 'react'
import { startVerification, answerVerification } from '../../lib/api'
import type { VerificationProblemDTO } from '../../lib/types'

/** Статус закрепления: загрузка / решает / ошибся / закрыл / ошибка сети. */
export type ClosureStatus = 'loading' | 'solving' | 'wrong' | 'correct' | 'error'

interface ClosureState {
  status: ClosureStatus
  problem: VerificationProblemDTO | null
  attempts: number
  check: (value: string) => void
  resume: () => void
}

// Живое закрепление: контрольная приходит с verification/start (тот же узел,
// другая задача), проверка — verification/answer (server-side). Верно → 'correct'
// + сервер помечает recurring_errors.resolved. Неверно → 'wrong' (мягкий ретрай).
export function useClosure(
  drillProblemId: number,
  microSkill: string | null,
  onClosed?: () => void,
): ClosureState {
  const [status, setStatus] = useState<ClosureStatus>('loading')
  const [problem, setProblem] = useState<VerificationProblemDTO | null>(null)
  const [attempts, setAttempts] = useState(0)

  useEffect(() => {
    let alive = true
    startVerification(drillProblemId, microSkill)
      .then((p) => {
        if (!alive) return
        setProblem(p)
        setStatus('solving')
      })
      .catch(() => {
        if (alive) setStatus('error')
      })
    return () => {
      alive = false
    }
  }, [drillProblemId, microSkill])

  const check = useCallback(
    (value: string) => {
      if (!problem) return
      answerVerification(problem.problem_id, value, microSkill)
        .then((res) => {
          if (res.correct) {
            setStatus('correct')
            onClosed?.()
            return
          }
          setAttempts((n) => n + 1)
          setStatus('wrong')
        })
        .catch(() => setStatus('error'))
    },
    [problem, microSkill, onClosed],
  )

  const resume = useCallback(() => {
    setStatus((s) => (s === 'wrong' ? 'solving' : s))
  }, [])

  return { status, problem, attempts, check, resume }
}
```
- [ ] Implementation: в `webapp/src/features/closure/ClosurePage.tsx` заменить источник данных (стр. 9, 17-18) — вместо `MOCK_VERIFICATION` брать `taskId` из роута и вызывать живой хук. Точнее:
  - удалить `import { MOCK_VERIFICATION } from './mock'`.
  - добавить `import { useParams } from 'react-router-dom'` (или использовать существующий способ получения taskId — closure-роут `/closure/:taskId`), а также использовать кэш wrong-tasks для получения `problem_id`+`micro_skill` по taskId через `useWrongTask`:
```tsx
import { useWrongTask } from '../../lib/api'
```
  - заменить строки 16-19:
```tsx
export function ClosurePage() {
  const navigate = useNavigate()
  const { taskId } = useParams<{ taskId: string }>()
  const { data: task } = useWrongTask(taskId ?? '')
  const closure = useClosure(task?.problem_id ?? 0, task?.primary_micro_skill ?? null)

  const isDone = closure.status === 'correct'
  const problem = closure.problem
```
  - в JSX, где раньше использовался `problem.topic_label` / `problem.xp` / `problem.micro_skill` — теперь `problem` может быть `null` во время загрузки: добавить guard. В секции intro заменить `problem.topic_label` на `problem?.topic_label ?? task?.topic_label ?? ''`. Для `ClosureCelebration` (isDone) использовать `xp={problem?.xp ?? 30}` и `microSkill={problem?.micro_skill ?? task?.primary_micro_skill ?? ''}`.
  - `VerificationCard` (проверка ответа): передать `problem` и `closure.check`; если `problem` null или `closure.status === 'loading'` — показать спиннер/skeleton (простой `<p className="text-caption1 text-text-secondary">Готовлю контрольную…</p>`); если `closure.status === 'error'` — сообщение об ошибке с кнопкой «К срезу».
  - `VerificationCard` сейчас берёт `problem` типа локального `VerificationProblem` (mock) с полем `expected`/`unit`. Обновить `VerificationCard` props на `VerificationProblemDTO` (без `expected`/`unit` — проверка теперь на сервере через `closure.check`): убрать клиентский `answersMatch`, вызывать `onCheck(value)`. Передавать `unit=''` дефолтом или убрать подпись единицы (unit больше не приходит с BE — можно опустить). Точный минимум: `VerificationCard` принимает `{ statement: string; onCheck: (v: string) => void; status: ClosureStatus }`.
- [ ] Implementation: в `webapp/src/features/analytics/AnalyticsPage.tsx` заменить блок построения items (стр. 19-45) на рендер `my_top`:
```tsx
  const analytics = asAnalyticsData(data)
  const items = analytics
    ? [...analytics.my_top].sort((a, b) => b.error_count - a.error_count)
    : []

  if (items.length === 0) return <AnalyticsEmpty />

  const max = items[0]?.error_count ?? 1

  return (
    <div className="flex flex-col gap-4">
      <div className="reveal" style={{ '--reveal-delay': '0ms' } as CSSProperties}>
        <AnalyticsHeader total={items.length} />
      </div>

      <ul className="flex flex-col gap-3">
        {items.map((item, i) => (
          <li key={item.micro_skill}>
            <ErrorBar
              item={{
                micro_skill: item.micro_skill,
                label: item.label_ru ?? item.micro_skill,
                topic_label: item.node_id ?? '',
                count: item.error_count,
                last_cause: item.last_cause_text,
              }}
              ratio={item.error_count / max}
              rank={i + 1}
              delay={70 + i * 60}
            />
          </li>
        ))}
      </ul>
    </div>
  )
```
  - NB: `ErrorBar` принимает `item: ErrorType`. `ErrorType` больше не экспортируется из types.ts (Task 8 удалил). Добавить локальный тип в `ErrorBar.tsx` ИЛИ вернуть `ErrorType` в types.ts. Решение: вернуть `ErrorType` в types.ts как view-модель (не BE-контракт) — добавить обратно в types.ts:
```typescript
/** View-модель строки аналитики (не BE-контракт; строится из RecurringErrorOut). */
export interface ErrorType {
  micro_skill: string
  label: string
  topic_label: string
  count: number
  last_cause: string | null
}
```
- [ ] Run: `cd webapp && npm run build` → зелёный (tsc strict).
- [ ] Run: `cd webapp && npm run test -- --run` → зелёный.
- [ ] Commit: `git add -A && git commit -m "feat(webapp): closure на живой verification API + analytics my_top рендер"`

---

## Self-review
- **Coverage vs спека:** verification (T4), problem-topics+инвариант (T3), agent_context (T2), tutor chat (T6), climb-down (T5), diagnose-merge (T7), analytics-контракт+FE API (T8), hub-темы (T9), чат-панель (T10), closure-live+analytics-render (T11), tutor-таблицы+resolved-проверка (T1). Все пункты Scope покрыты.
- **Placeholders:** код инлайн полностью; единственные текстовые уточнения — в T11 для `ClosurePage`/`VerificationCard` (даны точные props и guard-правила, т.к. эти компоненты меняются точечно под null-состояние — исполнитель применяет описанные правки, весь новый код `useClosure`/`AnalyticsPage`/`ErrorType` дан целиком).
- **Type consistency:** BE `AnalyticsResponse{my_top, global_top}` ↔ FE `AnalyticsData{my_top, global_top?}` ✓; `ProblemTopicOut` ↔ `ProblemTopic` ✓; `VerificationStartOut` ↔ `VerificationProblemDTO` ✓; `TutorChatOut` ↔ `TutorChatResponse` ✓. `ErrorType` возвращён как view-модель (T11), т.к. `ErrorBar` его потребляет.
- **Interfaces стыковка:** `build_agent_context` (T2) → потребляется T6 и T7; `pick_verification_problem`/`pick_easier_decomp`/`check_answer`/`limiter` — существующие сигнатуры, проверены по коду; `chat_reply` (T6, llm_openai) → `generate_tutor_reply` (T6, tutor) → endpoint (T6).
- **resolved-колонка:** УЖЕ существует (проверено run.py:128 + models.py:338) — Task 1 её не добавляет, только tutor-таблицы. Отражено в заметке Task 1.
- **Финальные Playwright + деплой** — вне плана (делает оркестратор).
