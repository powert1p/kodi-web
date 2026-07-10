"""Тесты заливки карточек теории (backend/scripts/seed_theory.py).

Чистая валидация validate_cards — без БД. Интеграция «theory_ru доезжает до
build_wrong_tasks» — против реальной *_test БД (skip без TEST_DATABASE_URL).
"""

import sys
from pathlib import Path

# scripts/ не пакет — добавляем в sys.path, как остальные backend-скрипты в тестах.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from sqlalchemy import text  # noqa: E402

from seed_theory import validate_cards  # noqa: E402


# ── Чистая валидация (без БД) ────────────────────────────────────────────────


def test_validate_cards_happy_path():
    """Все id существуют и уникальны → все в to_apply, ни дублей, ни missing."""
    cards = [{"id": "AL01", "theory_ru": "t1"}, {"id": "AR01", "theory_ru": "t2"}]
    v = validate_cards(cards, {"AL01", "AR01", "EQ01"})
    assert v.to_apply == {"AL01": "t1", "AR01": "t2"}
    assert v.duplicate_ids == []
    assert v.missing_ids == []


def test_validate_cards_skips_missing_node():
    """id, которого нет среди узлов → в missing_ids и НЕ применяется (не падаем)."""
    cards = [{"id": "AL01", "theory_ru": "t1"}, {"id": "ZZ99", "theory_ru": "t2"}]
    v = validate_cards(cards, {"AL01"})
    assert v.to_apply == {"AL01": "t1"}
    assert v.missing_ids == ["ZZ99"]
    assert v.duplicate_ids == []


def test_validate_cards_duplicate_first_wins():
    """Дубль id между файлами → первое вхождение применяется, дубль в duplicate_ids."""
    cards = [
        {"id": "AL01", "theory_ru": "first"},
        {"id": "AL01", "theory_ru": "second"},
    ]
    v = validate_cards(cards, {"AL01"})
    assert v.to_apply == {"AL01": "first"}
    assert v.card_map["AL01"] == "first"
    assert v.duplicate_ids == ["AL01"]


def test_validate_cards_partial_set_ok():
    """Частичный набор (57/114): узлы без карточки просто не попадают в to_apply."""
    cards = [{"id": "AL01", "theory_ru": "t1"}]
    v = validate_cards(cards, {"AL01", "AR01", "EQ01", "FR04"})
    assert v.to_apply == {"AL01": "t1"}
    assert v.missing_ids == []  # missing — про карточки без узла, а не наоборот


# ── Интеграция: theory_ru доезжает до build_wrong_tasks ──────────────────────


async def test_theory_ru_flows_to_wrong_tasks(db_session):
    """Узел с theory_ru → задача из build_wrong_tasks несёт этот текст."""
    from core.trainer import build_wrong_tasks

    SID = 8801
    THEORY = "**Метод** — делай так.\n\n**Пример** — 2+2=4."
    await db_session.execute(
        text(
            "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
            "VALUES (:sid, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
        ),
        {"sid": SID},
    )
    await db_session.execute(
        text(
            "INSERT INTO nodes (id, name_ru, name_kz, theory_ru, bkt_p_t, bkt_p_g, bkt_p_s) "
            "VALUES ('TH01', 'Тема', 'Тема', :th, 0.3, 0.05, 0.1) ON CONFLICT (id) DO NOTHING"
        ),
        {"th": THEORY},
    )
    pid = (
        await db_session.execute(
            text(
                "INSERT INTO problems (node_id, text_ru, answer) "
                "VALUES ('TH01', 'q', '5') RETURNING id"
            )
        )
    ).scalar_one()
    await db_session.execute(
        text(
            "INSERT INTO attempts "
            "(student_id, problem_id, node_id, answer_given, is_correct, source, created_at) "
            "VALUES (:sid, :pid, 'TH01', '4', false, 'diagnostic', NOW())"
        ),
        {"sid": SID, "pid": pid},
    )
    await db_session.commit()

    tasks = await build_wrong_tasks(db_session, student_id=SID)
    assert len(tasks) == 1
    assert tasks[0].theory_ru == THEORY
