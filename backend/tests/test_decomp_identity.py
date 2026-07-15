"""Регрессии точной привязки задачи к декомпозиции без тестовой БД."""

from __future__ import annotations

from types import SimpleNamespace

import pytest


class _Result:
    def __init__(self, rows):
        self._rows = list(rows)

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


class _ScriptedSession:
    def __init__(self, *results: _Result):
        self._results = list(results)

    async def execute(self, *_args, **_kwargs):
        return self._results.pop(0)


class _IdentityAwareSession:
    def __init__(self, exact, legacy):
        self.exact = exact
        self.legacy = legacy
        self.queries = []

    async def execute(self, statement, *_args, **_kwargs):
        query = str(statement)
        self.queries.append(query)
        if "content_idx" in query:
            return _Result([self.exact])
        if "problems_db_id" in query:
            return _Result([self.legacy])
        return _Result([])


@pytest.mark.asyncio
async def test_resolve_decomp_does_not_borrow_another_problem_from_same_node():
    """Совпадение только по node_id не даёт права показывать чужие шаги."""
    from core.trainer import resolve_decomp

    other_problem = SimpleNamespace(
        idx=77,
        node_id="PC06",
        answer="50",
        primary_micro_skill="percent_mix",
        all_steps_verified=True,
        needs_review=False,
        primary_micro_skill_label="Смеси",
    )
    session = _ScriptedSession(
        _Result([]),
        _Result([]),
        _Result([other_problem]),
    )

    result = await resolve_decomp(
        session,
        problem_id=42,
        node_id="PC06",
        answer="30",
    )

    assert result is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("all_steps_verified", "needs_review"),
    [(False, False), (True, True)],
)
async def test_resolve_decomp_rejects_unpublishable_linked_decomposition(
    all_steps_verified: bool,
    needs_review: bool,
):
    """Даже явная старая ссылка не обходит content-quality gate."""
    from core.trainer import resolve_decomp

    linked = SimpleNamespace(
        idx=12,
        node_id="PC06",
        answer="30",
        primary_micro_skill="percent_mix",
        all_steps_verified=all_steps_verified,
        needs_review=needs_review,
        primary_micro_skill_label="Смеси",
    )
    session = _ScriptedSession(_Result([]), _Result([linked]), _Result([]))

    result = await resolve_decomp(
        session,
        problem_id=42,
        node_id="PC06",
        answer="30",
    )

    assert result is None


@pytest.mark.asyncio
async def test_resolve_decomp_prefers_stable_content_idx_over_ambiguous_legacy_link():
    """Одинаковые node/answer не должны победить exact canonical identity."""
    from core.trainer import resolve_decomp

    exact = SimpleNamespace(
        idx=42,
        node_id="PC06",
        answer="30",
        primary_micro_skill="dilution",
        all_steps_verified=True,
        needs_review=False,
        primary_micro_skill_label="Разбавление",
    )
    legacy_wrong_problem = SimpleNamespace(
        idx=12,
        node_id="PC06",
        answer="30",
        primary_micro_skill="mixing",
        all_steps_verified=True,
        needs_review=False,
        primary_micro_skill_label="Смешивание",
    )
    session = _IdentityAwareSession(exact, legacy_wrong_problem)

    result = await resolve_decomp(
        session,
        problem_id=9001,
        node_id="PC06",
        answer="30",
    )

    assert result is not None
    assert result.idx == 42
    assert "content_idx" in session.queries[0]


@pytest.mark.asyncio
async def test_resolve_decomp_rejects_ambiguous_same_node_answer_fallback():
    """Две декомпозиции с одинаковым ответом — это не точная identity."""
    from core.trainer import resolve_decomp

    candidates = [
        SimpleNamespace(
            idx=idx,
            node_id="PC06",
            answer="30",
            primary_micro_skill=micro_skill,
            all_steps_verified=True,
            needs_review=False,
            primary_micro_skill_label=label,
        )
        for idx, micro_skill, label in (
            (12, "dilution", "Разбавление"),
            (42, "mixing", "Смешивание"),
        )
    ]
    session = _ScriptedSession(_Result([]), _Result([]), _Result(candidates))

    result = await resolve_decomp(
        session,
        problem_id=9001,
        node_id="PC06",
        answer="30",
    )

    assert result is None


@pytest.mark.asyncio
async def test_resolve_decomp_rejects_unique_foreign_same_answer_fallback():
    """Даже единственный same-answer кандидат не доказывает identity."""
    from core.trainer import resolve_decomp

    foreign = SimpleNamespace(
        idx=77,
        node_id="PC06",
        answer="30",
        primary_micro_skill="mixing",
        all_steps_verified=True,
        needs_review=False,
        primary_micro_skill_label="Смешивание",
    )
    session = _ScriptedSession(_Result([]), _Result([]), _Result([foreign]))

    result = await resolve_decomp(
        session,
        problem_id=9001,
        node_id="PC06",
        answer="30",
    )

    assert result is None
