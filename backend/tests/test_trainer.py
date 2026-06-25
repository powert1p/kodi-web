"""Интеграционный тест match_fingerprint (core/trainer.py).

Требует TEST_DATABASE_URL. Схема пересоздаётся перед каждым тестом (drop_all/create_all
в фикстуре db_session из conftest.py).

Сценарии:
  1. Linked-поиск: decomp запись с problems_db_id == problem_id →
       match_fingerprint находит fingerprint по normalized wrong_answer.
  2. Correct-answer → None: если ответ совпадает с правильным ответом задачи,
       fingerprint не возвращается (ни один wrong_answer не равен правильному).
  3. Unlinked-поиск (fallback): decomp запись с problems_db_id IS NULL,
       но (node_id, answer) совпадают с DB-задачей → найдена через fallback.
"""

import pytest
from sqlalchemy import text


# ─── фикстуры ────────────────────────────────────────────────────────────────

@pytest.fixture
def node_id() -> str:
    """Тестовый узел."""
    return "AR01"


@pytest.fixture
def correct_answer() -> str:
    """Правильный ответ задачи."""
    return "108"


@pytest.fixture
def wrong_answer_fp() -> str:
    """Неверный ответ, хранящийся в fingerprint."""
    return "80"


async def _seed_base(session, node_id: str) -> None:
    """Вставляет минимальный узел AR01."""
    await session.execute(
        text(
            "INSERT INTO nodes (id, name_ru, name_kz, bkt_p_t, bkt_p_g, bkt_p_s) "
            "VALUES (:nid, 'Тест', 'Тест', 0.3, 0.05, 0.1) "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {"nid": node_id},
    )


async def _insert_problem(session, node_id: str, answer: str) -> int:
    """Вставляет DB-задачу, возвращает её id."""
    row = await session.execute(
        text(
            "INSERT INTO problems (node_id, text_ru, answer) "
            "VALUES (:nid, 'Задача', :ans) RETURNING id"
        ),
        {"nid": node_id, "ans": answer},
    )
    return row.scalar_one()


async def _insert_decomp(session, idx: int, node_id: str, answer: str,
                          problems_db_id: int | None) -> None:
    """Вставляет запись decomposition_problems."""
    await session.execute(
        text(
            "INSERT INTO decomposition_problems "
            "(idx, node_id, answer, problems_db_id) "
            "VALUES (:idx, :nid, :ans, :dbid)"
        ),
        {"idx": idx, "nid": node_id, "ans": answer, "dbid": problems_db_id},
    )


async def _insert_fingerprint(session, decomp_idx: int,
                               micro_skill: str, wrong_answer: str,
                               mistake_ru: str) -> None:
    """Вставляет fingerprint для decomp_idx."""
    await session.execute(
        text(
            "INSERT INTO problem_fingerprints "
            "(decomp_idx, micro_skill, wrong_answer, mistake_ru) "
            "VALUES (:didx, :ms, :wa, :mr)"
        ),
        {"didx": decomp_idx, "ms": micro_skill, "wa": wrong_answer, "mr": mistake_ru},
    )


# ─── тест 1: linked-поиск + нормализованное сравнение ───────────────────────

@pytest.mark.asyncio
async def test_match_fingerprint_linked(db_session, node_id, correct_answer, wrong_answer_fp):
    """Linked-путь: problems_db_id == problem_id → fingerprint найден (с trailing space)."""
    from core.trainer import match_fingerprint

    await _seed_base(db_session, node_id)
    pid = await _insert_problem(db_session, node_id, correct_answer)

    # decomp запись явно привязана к DB-задаче через problems_db_id
    await _insert_decomp(db_session, idx=100, node_id=node_id, answer=correct_answer,
                         problems_db_id=pid)
    await _insert_fingerprint(db_session, decomp_idx=100,
                               micro_skill="int_add_sub",
                               wrong_answer=wrong_answer_fp,
                               mistake_ru="Перепутал знаки при вычитании")
    await db_session.commit()

    # answer_given с trailing пробелом — должна пройти нормализацию
    result = await match_fingerprint(db_session, problem_id=pid, answer_given="80 ")

    assert result is not None, "Ожидался fingerprint, получен None"
    assert result.micro_skill == "int_add_sub"
    assert result.mistake_ru == "Перепутал знаки при вычитании"
    assert result.wrong_answer == wrong_answer_fp
    assert result.decomp_idx == 100


# ─── тест 2: правильный ответ → None ────────────────────────────────────────

@pytest.mark.asyncio
async def test_match_fingerprint_correct_answer_returns_none(db_session, node_id, correct_answer, wrong_answer_fp):
    """Если ответ совпадает с правильным ответом задачи — fingerprint не возвращается."""
    from core.trainer import match_fingerprint

    await _seed_base(db_session, node_id)
    pid = await _insert_problem(db_session, node_id, correct_answer)

    await _insert_decomp(db_session, idx=200, node_id=node_id, answer=correct_answer,
                         problems_db_id=pid)
    await _insert_fingerprint(db_session, decomp_idx=200,
                               micro_skill="int_add_sub",
                               wrong_answer=wrong_answer_fp,
                               mistake_ru="Перепутал знаки при вычитании")
    await db_session.commit()

    # Правильный ответ "108" не совпадает ни с одним wrong_answer fingerprint → None
    result = await match_fingerprint(db_session, problem_id=pid, answer_given=correct_answer)
    assert result is None, f"При верном ответе ожидался None, получен {result}"


# ─── тест 3: unlinked decomp — fallback по (node_id, answer) ─────────────────

@pytest.mark.asyncio
async def test_match_fingerprint_unlinked_fallback(db_session, node_id, correct_answer, wrong_answer_fp):
    """Unlinked-путь: decomp.problems_db_id IS NULL → fallback по (node_id, answer)."""
    from core.trainer import match_fingerprint

    await _seed_base(db_session, node_id)
    pid = await _insert_problem(db_session, node_id, correct_answer)

    # decomp запись НЕ привязана (problems_db_id=NULL), но совпадает по (node_id, answer)
    await _insert_decomp(db_session, idx=300, node_id=node_id, answer=correct_answer,
                         problems_db_id=None)
    await _insert_fingerprint(db_session, decomp_idx=300,
                               micro_skill="int_add_sub",
                               wrong_answer=wrong_answer_fp,
                               mistake_ru="Перепутал знаки при вычитании")
    await db_session.commit()

    result = await match_fingerprint(db_session, problem_id=pid, answer_given="80 ")

    assert result is not None, "Fallback по (node_id, answer) должен найти fingerprint"
    assert result.micro_skill == "int_add_sub"
    assert result.decomp_idx == 300


# ═══════════════════════════════════════════════════════════════
# Task 5: route_state + build_wrong_tasks
# ═══════════════════════════════════════════════════════════════

# ─── route_state: table-driven ───────────────────────────────────────────────

@pytest.mark.parametrize("mastery,expected_state", [
    (0.0,  "revisit"),
    (0.39, "revisit"),
    (0.40, "almost"),   # граница: 0.40 уже НЕ revisit
    (0.5,  "almost"),
    (0.69, "almost"),
    (0.70, "got"),      # граница: 0.70 уже got
    (0.9,  "got"),
    (1.0,  "got"),
])
def test_route_state(mastery: float, expected_state: str) -> None:
    """route_state возвращает правильный уровень по трём порогам."""
    from core.trainer import route_state

    assert route_state(mastery) == expected_state


# ─── вспомогательные seed-функции для build_wrong_tasks ─────────────────────

async def _seed_student(session, student_id: int) -> None:
    """Вставляет студента с заданным id."""
    await session.execute(
        text(
            "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
            "VALUES (:sid, true, 'ru', NOW(), false) "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {"sid": student_id},
    )


async def _seed_node(session, node_id: str, name_ru: str) -> None:
    """Вставляет узел графа."""
    await session.execute(
        text(
            "INSERT INTO nodes (id, name_ru, name_kz, bkt_p_t, bkt_p_g, bkt_p_s) "
            "VALUES (:nid, :name, :name, 0.3, 0.05, 0.1) "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {"nid": node_id, "name": name_ru},
    )


async def _seed_problem(session, node_id: str, text_ru: str, answer: str) -> int:
    """Вставляет задачу, возвращает её id."""
    row = await session.execute(
        text(
            "INSERT INTO problems (node_id, text_ru, answer) "
            "VALUES (:nid, :txt, :ans) RETURNING id"
        ),
        {"nid": node_id, "txt": text_ru, "ans": answer},
    )
    return row.scalar_one()


async def _seed_decomp_with_steps(
    session,
    decomp_idx: int,
    node_id: str,
    answer: str,
    problems_db_id: int | None,
    *,
    verified: bool = True,
) -> None:
    """Вставляет decomp-запись + один шаг решения."""
    await session.execute(
        text(
            "INSERT INTO decomposition_problems "
            "(idx, node_id, answer, all_steps_verified, problems_db_id) "
            "VALUES (:idx, :nid, :ans, :verified, :dbid)"
        ),
        {"idx": decomp_idx, "nid": node_id, "ans": answer,
         "verified": verified, "dbid": problems_db_id},
    )
    await session.execute(
        text(
            "INSERT INTO problem_steps "
            "(decomp_idx, n, instruction_ru, micro_skill, expected_value) "
            "VALUES (:didx, 1, 'Шаг 1', 'test_skill', '42')"
        ),
        {"didx": decomp_idx},
    )


async def _seed_attempt(
    session,
    student_id: int,
    problem_id: int,
    node_id: str,
    answer_given: str,
    source: str = "diagnostic",
    created_at_offset_days: int = 0,
) -> None:
    """Вставляет неверную попытку."""
    await session.execute(
        text(
            "INSERT INTO attempts "
            "(student_id, problem_id, node_id, answer_given, is_correct, source, created_at) "
            "VALUES (:sid, :pid, :nid, :ans, false, :src, "
            "        NOW() - make_interval(days => :offset))"
        ),
        {
            "sid": student_id, "pid": problem_id, "nid": node_id,
            "ans": answer_given, "src": source, "offset": created_at_offset_days,
        },
    )


async def _seed_mastery(session, student_id: int, node_id: str, p_mastery: float) -> None:
    """Вставляет/обновляет mastery студента по узлу."""
    await session.execute(
        text(
            "INSERT INTO mastery (student_id, node_id, p_mastery, attempts_total, attempts_correct) "
            "VALUES (:sid, :nid, :pm, 0, 0) "
            "ON CONFLICT (student_id, node_id) DO UPDATE SET p_mastery = :pm"
        ),
        {"sid": student_id, "nid": node_id, "pm": p_mastery},
    )


# ─── тест: build_wrong_tasks основной сценарий ───────────────────────────────

@pytest.mark.asyncio
async def test_build_wrong_tasks_main(db_session) -> None:
    """
    Основной сценарий build_wrong_tasks:

    - Проблема #1: привязана к decomp (linked) → steps из linked decomp.
    - Проблема #2: нет linked decomp, но есть same-node verified → steps из него.
    - Дубль попытки на задачу #1: оставляем только одну (latest).
    - Возвращаются ровно 2 WrongTask.
    """
    from core.trainer import build_wrong_tasks

    STUDENT_ID = 9001
    NODE_A = "AR01"
    NODE_B = "AR02"

    # ── сиды ────────────────────────────────────────────────────
    await _seed_student(db_session, STUDENT_ID)
    await _seed_node(db_session, NODE_A, "Арифметика А")
    await _seed_node(db_session, NODE_B, "Арифметика Б")

    # Задача 1 — узел A, linked decomp
    pid1 = await _seed_problem(db_session, NODE_A, "Задача 1", "108")
    await _seed_decomp_with_steps(
        db_session, decomp_idx=500, node_id=NODE_A,
        answer="108", problems_db_id=pid1, verified=True,
    )

    # Задача 2 — узел B, нет linked decomp, но есть same-node verified decomp
    pid2 = await _seed_problem(db_session, NODE_B, "Задача 2", "64")
    await _seed_decomp_with_steps(
        db_session, decomp_idx=501, node_id=NODE_B,
        answer="64", problems_db_id=None, verified=True,
    )

    # Mastery
    await _seed_mastery(db_session, STUDENT_ID, NODE_A, 0.55)
    await _seed_mastery(db_session, STUDENT_ID, NODE_B, 0.30)

    # Попытки: задача 1 — две неверные (старая + свежая), задача 2 — одна неверная
    await _seed_attempt(db_session, STUDENT_ID, pid1, NODE_A,
                        answer_given="90", created_at_offset_days=3)
    await _seed_attempt(db_session, STUDENT_ID, pid1, NODE_A,
                        answer_given="85", created_at_offset_days=1)  # самая свежая
    await _seed_attempt(db_session, STUDENT_ID, pid2, NODE_B,
                        answer_given="60", created_at_offset_days=2)

    await db_session.commit()

    # ── вызов ───────────────────────────────────────────────────
    tasks = await build_wrong_tasks(db_session, STUDENT_ID, days=14, limit=30)

    # ── утверждения ─────────────────────────────────────────────
    assert len(tasks) == 2, f"Ожидалось 2 задачи, получено {len(tasks)}"

    by_pid = {t.problem_id: t for t in tasks}

    # Задача 1: дубль дедуплицирован → wrong_answer из самой свежей попытки ("85")
    t1 = by_pid[pid1]
    assert t1.wrong_answer == "85", f"Ожидался wrong_answer='85', получен '{t1.wrong_answer}'"
    assert t1.statement == "Задача 1"
    assert t1.answer == "108"
    assert t1.topic_label == "Арифметика А"
    assert t1.node_id == NODE_A
    assert len(t1.steps) == 1, "Задача 1 должна иметь 1 шаг из linked decomp"
    assert t1.decomp_idx == 500
    assert t1.state == "almost"   # mastery=0.55 → "almost"

    # Задача 2: same-node verified decomp → steps заполнены
    t2 = by_pid[pid2]
    assert t2.wrong_answer == "60"
    assert t2.statement == "Задача 2"
    assert t2.answer == "64"
    assert t2.topic_label == "Арифметика Б"
    assert len(t2.steps) == 1, "Задача 2 должна иметь 1 шаг из same-node decomp"
    assert t2.decomp_idx == 501
    assert t2.state == "revisit"  # mastery=0.30 → "revisit"


# ═══════════════════════════════════════════════════════════════
# Task 6: route_level + pick_easier_decomp + pick_verification_problem
# ═══════════════════════════════════════════════════════════════

# ─── route_level: table-driven ──────────────────────────────────────────────

@pytest.mark.parametrize("mastery,expected_level", [
    (0.0,  1),
    (0.39, 1),
    (0.40, 2),   # граница: 0.40 уже уровень 2
    (0.5,  2),
    (0.69, 2),
    (0.70, 3),   # граница: 0.70 уже уровень 3
    (0.9,  3),
])
def test_route_level(mastery: float, expected_level: int) -> None:
    """route_level корректно разбивает mastery по трём уровням."""
    from core.trainer import route_level
    assert route_level(mastery) == expected_level


# ─── pick_easier_decomp: возвращает запись с меньшим числом шагов ───────────

@pytest.mark.asyncio
async def test_pick_easier_decomp_fewest_steps(db_session) -> None:
    """
    Два decomp-записи с одним micro_skill — pick_easier_decomp выбирает ту, у
    которой меньше шагов (1 шаг vs 3 шага).
    """
    from core.trainer import pick_easier_decomp

    NODE = "AR04"
    MICRO = "frac_simplify"

    # Вставляем узел
    await db_session.execute(
        text(
            "INSERT INTO nodes (id, name_ru, name_kz, bkt_p_t, bkt_p_g, bkt_p_s) "
            "VALUES (:nid, 'Дроби', 'Дроби', 0.3, 0.05, 0.1) ON CONFLICT (id) DO NOTHING"
        ),
        {"nid": NODE},
    )

    # decomp 601 — 3 шага
    await db_session.execute(
        text(
            "INSERT INTO decomposition_problems "
            "(idx, node_id, answer, primary_micro_skill, all_steps_verified) "
            "VALUES (:idx, :nid, '1/2', :ms, true)"
        ),
        {"idx": 601, "nid": NODE, "ms": MICRO},
    )
    for step_n in (1, 2, 3):
        await db_session.execute(
            text(
                "INSERT INTO problem_steps "
                "(decomp_idx, n, instruction_ru, micro_skill, expected_value) "
                "VALUES (:didx, :n, 'Шаг', :ms, '0')"
            ),
            {"didx": 601, "n": step_n, "ms": MICRO},
        )

    # decomp 602 — 1 шаг
    await db_session.execute(
        text(
            "INSERT INTO decomposition_problems "
            "(idx, node_id, answer, primary_micro_skill, all_steps_verified) "
            "VALUES (:idx, :nid, '3/4', :ms, true)"
        ),
        {"idx": 602, "nid": NODE, "ms": MICRO},
    )
    await db_session.execute(
        text(
            "INSERT INTO problem_steps "
            "(decomp_idx, n, instruction_ru, micro_skill, expected_value) "
            "VALUES (:didx, 1, 'Шаг', :ms, '0')"
        ),
        {"didx": 602, "ms": MICRO},
    )

    await db_session.commit()

    result = await pick_easier_decomp(db_session, micro_skill=MICRO, exclude_idx=None)
    assert result is not None, "Ожидалась запись с наименьшим числом шагов"
    assert result.idx == 602, f"Ожидался decomp 602 (1 шаг), получен {result.idx}"


@pytest.mark.asyncio
async def test_pick_easier_decomp_excludes_idx(db_session) -> None:
    """Если единственный подходящий decomp исключён — возвращается None."""
    from core.trainer import pick_easier_decomp

    NODE = "AR05"
    MICRO = "int_multiply"

    await db_session.execute(
        text(
            "INSERT INTO nodes (id, name_ru, name_kz, bkt_p_t, bkt_p_g, bkt_p_s) "
            "VALUES (:nid, 'Умножение', 'Умножение', 0.3, 0.05, 0.1) ON CONFLICT (id) DO NOTHING"
        ),
        {"nid": NODE},
    )
    await db_session.execute(
        text(
            "INSERT INTO decomposition_problems "
            "(idx, node_id, answer, primary_micro_skill, all_steps_verified) "
            "VALUES (:idx, :nid, '6', :ms, true)"
        ),
        {"idx": 700, "nid": NODE, "ms": MICRO},
    )
    await db_session.execute(
        text(
            "INSERT INTO problem_steps "
            "(decomp_idx, n, instruction_ru, micro_skill, expected_value) "
            "VALUES (700, 1, 'Умножь', :ms, '6')"
        ),
        {"ms": MICRO},
    )
    await db_session.commit()

    # Исключаем единственный decomp — ожидаем None
    result = await pick_easier_decomp(db_session, micro_skill=MICRO, exclude_idx=700)
    assert result is None, f"Ожидался None при exclude_idx={700}, получен {result}"


# ─── pick_verification_problem: другая задача того же узла ──────────────────

@pytest.mark.asyncio
async def test_pick_verification_problem_returns_other(db_session) -> None:
    """Два problem на одном node — pick_verification_problem возвращает второй."""
    from core.trainer import pick_verification_problem

    NODE = "AR06"
    await db_session.execute(
        text(
            "INSERT INTO nodes (id, name_ru, name_kz, bkt_p_t, bkt_p_g, bkt_p_s) "
            "VALUES (:nid, 'Проверка', 'Проверка', 0.3, 0.05, 0.1) ON CONFLICT (id) DO NOTHING"
        ),
        {"nid": NODE},
    )

    r1 = await db_session.execute(
        text("INSERT INTO problems (node_id, text_ru, answer) VALUES (:nid, 'Задача A', '10') RETURNING id"),
        {"nid": NODE},
    )
    pid1 = r1.scalar_one()

    r2 = await db_session.execute(
        text("INSERT INTO problems (node_id, text_ru, answer) VALUES (:nid, 'Задача B', '20') RETURNING id"),
        {"nid": NODE},
    )
    pid2 = r2.scalar_one()

    await db_session.commit()

    result = await pick_verification_problem(db_session, NODE, exclude_problem_id=pid1)
    assert result is not None, "Ожидалась вторая задача того же узла"
    assert result.id == pid2, f"Ожидался problem_id={pid2}, получен {result.id}"


@pytest.mark.asyncio
async def test_pick_verification_problem_exclude_works(db_session) -> None:
    """Если единственная задача исключена — возвращается None."""
    from core.trainer import pick_verification_problem

    NODE = "AR07"
    await db_session.execute(
        text(
            "INSERT INTO nodes (id, name_ru, name_kz, bkt_p_t, bkt_p_g, bkt_p_s) "
            "VALUES (:nid, 'Одна задача', 'Одна задача', 0.3, 0.05, 0.1) ON CONFLICT (id) DO NOTHING"
        ),
        {"nid": NODE},
    )
    r = await db_session.execute(
        text("INSERT INTO problems (node_id, text_ru, answer) VALUES (:nid, 'Только одна', '5') RETURNING id"),
        {"nid": NODE},
    )
    only_pid = r.scalar_one()
    await db_session.commit()

    result = await pick_verification_problem(db_session, NODE, exclude_problem_id=only_pid)
    assert result is None, f"Ожидался None при единственной задаче, получен {result}"


# ─── тест: попытки за пределами окна не включаются ───────────────────────────

@pytest.mark.asyncio
async def test_build_wrong_tasks_window(db_session) -> None:
    """Попытка старше days=7 не должна попасть в результат."""
    from core.trainer import build_wrong_tasks

    STUDENT_ID = 9002
    NODE_A = "AR03"

    await _seed_student(db_session, STUDENT_ID)
    await _seed_node(db_session, NODE_A, "Арифметика В")

    pid = await _seed_problem(db_session, NODE_A, "Старая задача", "10")

    # Попытка 10 дней назад — за пределами дефолтного 14-дневного окна она видна,
    # но если ограничить days=7 — не должна попасть.
    await _seed_attempt(db_session, STUDENT_ID, pid, NODE_A,
                        answer_given="9", created_at_offset_days=10)

    await db_session.commit()

    tasks_14 = await build_wrong_tasks(db_session, STUDENT_ID, days=14, limit=30)
    assert len(tasks_14) == 1, "За 14 дней задача должна попасть"

    tasks_7 = await build_wrong_tasks(db_session, STUDENT_ID, days=7, limit=30)
    assert len(tasks_7) == 0, "За 7 дней задача не должна попасть (10 дней назад)"
