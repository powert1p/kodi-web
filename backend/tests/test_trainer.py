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
