"""Интеграционный тест сидирования банка декомпозиций.

Требует TEST_DATABASE_URL. Использует небольшой fixtures/decomp_sample.json
(3 записи: одна uniquely-linked, одна без совпадения, одна — тоже linked если AR01+answer
совпадёт). Фикстура засевает nodes + problems, потом вызывает seed_decomposition.

Assertions (brief Step 1):
    decomp_problems == 3
    db_linked == 1   (ровно одна запись совпала по (node_id, answer))
    steps присутствуют
    fingerprint по decomp_idx=2 найден (wrong_answer='80')
"""

import os
import pathlib
import pytest
import pytest_asyncio
from sqlalchemy import text

# ─── путь к маленькой фикстуре ───────────────────────────────────────────────
FIXTURE_PATH = pathlib.Path(__file__).parent / "fixtures" / "decomp_sample.json"


# ─── фикстура: узлы + задача-совпадение (AR01, answer='68') ──────────────────

@pytest_asyncio.fixture
async def seeded_graph(db_session):
    """Сид минимального графа: узел AR01 + одна задача (AR01, '68').

    Эта задача будет uniquely matched с decomp-записью idx=0.
    """
    # Создаём узел AR01 (bkt_* — not-null с дефолтами в Python-слое, не server_default)
    await db_session.execute(
        text(
            "INSERT INTO nodes (id, name_ru, name_kz, bkt_p_t, bkt_p_g, bkt_p_s) "
            "VALUES ('AR01', 'Арифметика', 'Арифметика', 0.3, 0.05, 0.1) "
            "ON CONFLICT (id) DO NOTHING"
        )
    )
    # Одна задача — ровно один ответ '68' для AR01 → unique match → db_linked=1
    await db_session.execute(
        text(
            "INSERT INTO problems (node_id, text_ru, answer) "
            "VALUES ('AR01', 'Тестовая задача', '68')"
        )
    )
    await db_session.commit()
    return "AR01"


# ─── тест ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_seed_decomposition_basic(db_session, seeded_graph):
    """Базовая проверка сидирования: counts, link, steps, fingerprints."""
    from db.seed_decomposition import seed_decomposition

    result = await seed_decomposition(db_session, json_path=FIXTURE_PATH)

    # ── счётчики ─────────────────────────────────────────────────────────────
    assert result["micro_skills"] == 2, f"micro_skills expected 2, got {result['micro_skills']}"
    assert result["decomp_problems"] == 3, f"decomp_problems expected 3, got {result['decomp_problems']}"
    assert result["db_linked"] == 1, f"db_linked expected 1, got {result['db_linked']}"
    assert result["steps"] > 0, "steps должны быть > 0"
    assert result["fingerprints"] > 0, "fingerprints должны быть > 0"

    # ── шаги присутствуют ────────────────────────────────────────────────────
    step_count = (
        await db_session.execute(text("SELECT count(*) FROM problem_steps"))
    ).scalar()
    assert step_count > 0, "problem_steps пустые"

    # ── fingerprint по decomp_idx=2 найден ───────────────────────────────────
    fp = (
        await db_session.execute(
            text(
                "SELECT wrong_answer, mistake_ru FROM problem_fingerprints "
                "WHERE decomp_idx = 2 AND wrong_answer = '80'"
            )
        )
    ).fetchone()
    assert fp is not None, "fingerprint (decomp_idx=2, wrong_answer='80') не найден"
    assert "знаки" in fp.mistake_ru or "знак" in fp.mistake_ru, (
        f"mistake_ru не содержит ожидаемый текст: {fp.mistake_ru}"
    )

    # ── linked запись: idx=0 имеет problems_db_id (не NULL) ──────────────────
    row = (
        await db_session.execute(
            text("SELECT problems_db_id FROM decomposition_problems WHERE idx = 0")
        )
    ).fetchone()
    assert row is not None, "decomp idx=0 не найден"
    assert row.problems_db_id is not None, "idx=0 должен быть linked (problems_db_id не NULL)"

    # ── не-linked записи: idx=1 и idx=2 имеют problems_db_id NULL ────────────
    # idx=1: answer='999' — нет в problems → NULL
    # idx=2: answer='46' — нет в problems → NULL
    for no_link_idx in (1, 2):
        row = (
            await db_session.execute(
                text(f"SELECT problems_db_id FROM decomposition_problems WHERE idx = {no_link_idx}")
            )
        ).fetchone()
        assert row is not None, f"decomp idx={no_link_idx} не найден"
        assert row.problems_db_id is None, (
            f"idx={no_link_idx} ожидается NULL problems_db_id, got {row.problems_db_id}"
        )


@pytest.mark.asyncio
async def test_seed_idempotent(db_session, seeded_graph):
    """Повторный вызов seed_decomposition должен завершаться без ошибок и возвращать нули."""
    from db.seed_decomposition import seed_decomposition

    result1 = await seed_decomposition(db_session, json_path=FIXTURE_PATH)
    # Второй вызов — без FORCE_RESEED → skip (return нули или тот же результат)
    result2 = await seed_decomposition(db_session, json_path=FIXTURE_PATH)

    # Первый вызов засеял данные
    assert result1["decomp_problems"] == 3

    # Второй вызов пропустил (или overwrite) — главное без ошибок
    # При skip: все счётчики 0; при FORCE_RESEED: тоже 3
    # Проверяем что строки не задублировались
    count = (
        await db_session.execute(
            text("SELECT count(*) FROM decomposition_problems")
        )
    ).scalar()
    assert count == 3, f"После двух seed-вызовов ожидается 3 строки, got {count}"
