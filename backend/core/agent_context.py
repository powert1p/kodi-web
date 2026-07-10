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
    # Метод узла (nodes.theory_ru): «как решать» одним абзацем. Колонка появляется
    # мягко (параллельная задача 1d ТЗ) — None пока её нет. Default для обратной
    # совместимости с hand-constructed AgentContext (тесты).
    node_theory: str | None = None


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

    # ── метод узла (nodes.theory_ru) ──
    # Колонку добавляет параллельная задача 1d ТЗ. SELECT * не падает на её
    # отсутствии (выбирает только существующие столбцы), getattr → None. Так код
    # не ломается на схеме без theory_ru и подхватит её, как только появится.
    node_row = (await session.execute(
        text("SELECT * FROM nodes WHERE id = :nid"),
        {"nid": node_id},
    )).fetchone()
    node_theory = getattr(node_row, "theory_ru", None) if node_row is not None else None

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
        node_theory=node_theory,
    )
