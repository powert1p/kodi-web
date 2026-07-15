"""Инварианты единой identity банка задач и декомпозиций."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


_BACKEND = Path(__file__).resolve().parents[1]


def _load_banks():
    problems = json.loads(
        (_BACKEND / "data" / "problems_v10.json").read_text(encoding="utf-8")
    )["problems"]
    decompositions = json.loads(
        (_BACKEND / "data" / "full_decomposition_v1.json").read_text(encoding="utf-8")
    )["problems"]
    return problems, decompositions


def test_problem_model_has_stable_content_idx():
    """DB identity не должна зависеть от autoincrement id или порядка строк."""
    from db.models import Problem

    column = Problem.__table__.c.content_idx

    assert column.nullable is True
    assert column.index is True
    assert column.unique is True


def test_problem_and_decomposition_banks_align_by_content_idx():
    """Один content_idx означает одно условие, один узел и один ответ."""
    problems, decompositions = _load_banks()

    assert len(problems) == len(decompositions) == 2525
    for content_idx, (problem, decomp) in enumerate(zip(problems, decompositions)):
        assert decomp["idx"] == content_idx
        assert decomp["node_id"] == problem["node_id"], content_idx
        assert str(decomp["answer"]) == str(problem["answer"]), content_idx


def test_problem_text_is_unique_natural_key_for_safe_backfill():
    """Existing-БД можно недеструктивно backfill-ить по (node_id, text_ru)."""
    problems, _ = _load_banks()
    keys = [(problem["node_id"], problem["text_ru"]) for problem in problems]

    assert len(keys) == len(set(keys))


class _SeedSession:
    def __init__(self):
        self.added = []
        self.commits = 0

    def add(self, value):
        self.added.append(value)

    async def execute(self, *_args, **_kwargs):
        return None

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_fresh_seed_assigns_content_idx_from_canonical_order(tmp_path, monkeypatch):
    """Fresh-БД получает тот же stable key, что decomposition.idx."""
    from db import seed

    fixture = tmp_path / "problems.json"
    fixture.write_text(
        json.dumps(
            {
                "problems": [
                    {"node_id": "AR01", "text_ru": "A", "answer": "1"},
                    {"node_id": "AR01", "text_ru": "B", "answer": "2"},
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(seed, "_find_problems_path", lambda: fixture)
    session = _SeedSession()

    inserted = await seed._insert_all_problems(session)

    assert inserted == 2
    assert [problem.content_idx for problem in session.added] == [0, 1]
    assert session.commits == 1


class _BackfillResult:
    rowcount = 2525


class _BackfillSession:
    def __init__(self):
        self.params = None
        self.commits = 0

    async def execute(self, _statement, params):
        self.params = params
        return _BackfillResult()

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_existing_database_backfill_uses_unique_natural_key():
    """Migration связывает строки по тексту, а не по опасному ORDER BY id + zip."""
    from db.seed import backfill_problem_content_idx

    problems, _ = _load_banks()
    session = _BackfillSession()

    updated = await backfill_problem_content_idx(session)

    assert updated == 2525
    assert len(session.params) == 2525
    assert session.params[0] == {
        "content_idx": 0,
        "node_id": problems[0]["node_id"],
        "text_ru": problems[0]["text_ru"],
    }
    assert session.params[-1]["content_idx"] == 2524
    assert session.commits == 1


class _CanonicalSyncResult:
    rowcount = 2


class _CanonicalSyncSession:
    def __init__(self):
        self.calls = []
        self.commits = 0

    async def execute(self, statement, params):
        self.calls.append((str(statement), params))
        return _CanonicalSyncResult()

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_existing_database_content_sync_uses_content_idx_not_row_order(
    tmp_path,
    monkeypatch,
):
    """Исправления answer/solution доходят до existing-БД по stable identity."""
    from db import seed

    fixture = tmp_path / "problems.json"
    fixture.write_text(
        json.dumps(
            {
                "problems": [
                    {
                        "node_id": "CV03",
                        "text_ru": "Задача A",
                        "text_kz": "A",
                        "answer": "2031;8124",
                        "answer_type": "choice",
                        "solution_ru": "Верное решение A",
                    },
                    {
                        "node_id": "GE01",
                        "text_ru": "Задача B",
                        "answer": "24",
                        "solution_ru": "Верное решение B",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(seed, "_find_problems_path", lambda: fixture)
    session = _CanonicalSyncSession()

    synced = await seed.sync_canonical_problems(session)

    assert synced == 2
    statement, rows = session.calls[0]
    assert "ON CONFLICT (content_idx) DO UPDATE" in statement
    assert "ORDER BY id" not in statement
    assert rows[0]["content_idx"] == 0
    assert rows[0]["answer"] == "2031;8124"
    assert rows[1]["content_idx"] == 1
    assert rows[1]["solution_ru"] == "Верное решение B"
    assert session.commits == 1
