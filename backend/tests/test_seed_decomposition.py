"""Интеграционный тест сидирования банка декомпозиций.

Требует TEST_DATABASE_URL. Использует небольшой fixtures/decomp_sample.json
(4 записи: одна uniquely-linked, одна ambiguous → NULL, две без совпадения).

Фикстура:
    idx=0: AR01, answer='68'  → unique match → linked (db_linked=1)
    idx=1: AR01, answer='999' → нет в problems → NULL
    idx=2: AR01, answer='46'  → нет в problems → NULL
    idx=3: AR01, answer='77'  → AMBIGUOUS (два problems с (AR01,'77')) → NULL

Assertions:
    decomp_problems == 4
    db_linked == 1   (ровно одна запись совпала уникально)
    steps == 5       (1 + 1 + 2 + 1 по каждому idx)
    fingerprint по decomp_idx=2 найден (wrong_answer='80')
    idx=3 имеет problems_db_id IS NULL (ambiguous → не линкуем)
"""

import os
import pathlib
import pytest
import pytest_asyncio
from sqlalchemy import text

# ─── путь к маленькой фикстуре ───────────────────────────────────────────────
FIXTURE_PATH = pathlib.Path(__file__).parent / "fixtures" / "decomp_sample.json"

# Точное число шагов по фикстуре: idx0=1, idx1=1, idx2=2, idx3=1
EXPECTED_STEPS = 5


# ─── фикстура: узлы + задачи ─────────────────────────────────────────────────

@pytest_asyncio.fixture
async def seeded_graph(db_session):
    """Сид минимального графа: узел AR01 + задачи для проверки линковки.

    Задачи:
    - (AR01, '68')  — одна штука → unique match с idx=0.
    - (AR01, '77')  — ДВЕ штуки → ambiguous → idx=3 получит problems_db_id=NULL.
    """
    # Создаём узел AR01 (bkt_* — NOT NULL без server_default)
    await db_session.execute(
        text(
            "INSERT INTO nodes (id, name_ru, name_kz, bkt_p_t, bkt_p_g, bkt_p_s) "
            "VALUES ('AR01', 'Арифметика', 'Арифметика', 0.3, 0.05, 0.1) "
            "ON CONFLICT (id) DO NOTHING"
        )
    )
    # Одна задача — unique match с idx=0
    await db_session.execute(
        text(
            "INSERT INTO problems (node_id, text_ru, answer) "
            "VALUES ('AR01', 'Тестовая задача 1', '68')"
        )
    )
    # Две задачи с одинаковым ответом '77' → ambiguous → idx=3 не линкуется
    await db_session.execute(
        text(
            "INSERT INTO problems (node_id, text_ru, answer) "
            "VALUES ('AR01', 'Задача A с ответом 77', '77')"
        )
    )
    await db_session.execute(
        text(
            "INSERT INTO problems (node_id, text_ru, answer) "
            "VALUES ('AR01', 'Задача B с ответом 77', '77')"
        )
    )
    await db_session.commit()
    return "AR01"


# ─── основной тест ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_seed_decomposition_basic(db_session, seeded_graph):
    """Базовая проверка сидирования: counts, link, ambiguous, steps, fingerprints."""
    from db.seed_decomposition import seed_decomposition

    result = await seed_decomposition(db_session, json_path=FIXTURE_PATH)

    # ── счётчики ─────────────────────────────────────────────────────────────
    assert result["micro_skills"] == 2, f"micro_skills expected 2, got {result['micro_skills']}"
    assert result["decomp_problems"] == 4, f"decomp_problems expected 4, got {result['decomp_problems']}"
    # db_linked == 1: только idx=0 (unique); idx=3 ambiguous → не линкуется
    assert result["db_linked"] == 1, f"db_linked expected 1, got {result['db_linked']}"
    assert result["steps"] == EXPECTED_STEPS, (
        f"steps expected {EXPECTED_STEPS}, got {result['steps']}"
    )
    assert result["fingerprints"] > 0, "fingerprints должны быть > 0"

    # ── точное число шагов в БД ──────────────────────────────────────────────
    # idx0=1 шаг, idx1=1 шаг, idx2=2 шага, idx3=1 шаг → итого 5
    step_count = (
        await db_session.execute(text("SELECT count(*) FROM problem_steps"))
    ).scalar()
    assert step_count == EXPECTED_STEPS, (
        f"problem_steps в БД: expected {EXPECTED_STEPS}, got {step_count}"
    )

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
            text("SELECT problems_db_id FROM decomposition_problems WHERE idx = :idx"),
            {"idx": 0},
        )
    ).fetchone()
    assert row is not None, "decomp idx=0 не найден"
    assert row.problems_db_id is not None, "idx=0 должен быть linked (problems_db_id не NULL)"

    # ── не-linked записи без совпадения: idx=1 и idx=2 имеют problems_db_id NULL ──
    # idx=1: answer='999' — нет в problems
    # idx=2: answer='46'  — нет в problems
    for no_link_idx in (1, 2):
        row = (
            await db_session.execute(
                text(
                    "SELECT problems_db_id FROM decomposition_problems WHERE idx = :idx"
                ),
                {"idx": no_link_idx},
            )
        ).fetchone()
        assert row is not None, f"decomp idx={no_link_idx} не найден"
        assert row.problems_db_id is None, (
            f"idx={no_link_idx} ожидается NULL problems_db_id, got {row.problems_db_id}"
        )

    # ── M2: ambiguous case — idx=3, answer='77' → две задачи в DB → NULL ─────
    # Проверяет фильтр GROUP BY … HAVING count(*)=1: при двух совпадениях
    # lookup не содержит пары (AR01,'77'), поэтому problems_db_id остаётся NULL.
    row_ambig = (
        await db_session.execute(
            text(
                "SELECT problems_db_id FROM decomposition_problems WHERE idx = :idx"
            ),
            {"idx": 3},
        )
    ).fetchone()
    assert row_ambig is not None, "decomp idx=3 (ambiguous) не найден"
    assert row_ambig.problems_db_id is None, (
        f"idx=3 ambiguous: ожидается problems_db_id=NULL, got {row_ambig.problems_db_id}"
    )


@pytest.mark.asyncio
async def test_seed_idempotent(db_session, seeded_graph):
    """Повторный вызов seed_decomposition должен завершаться без ошибок и возвращать нули."""
    from db.seed_decomposition import seed_decomposition

    result1 = await seed_decomposition(db_session, json_path=FIXTURE_PATH)
    # Второй вызов — без FORCE_RESEED → skip (return нули)
    result2 = await seed_decomposition(db_session, json_path=FIXTURE_PATH)

    # Первый вызов засеял данные
    assert result1["decomp_problems"] == 4

    # Второй вызов пропустил — все счётчики 0
    assert result2["decomp_problems"] == 0
    assert result2["micro_skills"] == 0

    # Строки не задублировались
    count = (
        await db_session.execute(
            text("SELECT count(*) FROM decomposition_problems")
        )
    ).scalar()
    assert count == 4, f"После двух seed-вызовов ожидается 4 строки, got {count}"
