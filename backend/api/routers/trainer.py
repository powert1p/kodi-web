"""Роутер тренажёра ошибок: /api/trainer/wrong-tasks + /api/trainer/analytics.

Не растёт api/routes.py — отдельный модуль согласно AUDIT API-3.
Использует _get_current_student из routes.py (JWT-логику не дублируем).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
from sqlalchemy import text

from api.routes import _get_current_student
from core.config import settings
from core.trainer import StepDTO, WrongTask, build_wrong_tasks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trainer", tags=["trainer"])


# ── Pydantic v2 response-схемы ────────────────────────────────────────────────


class StepOut(BaseModel):
    """Один шаг декомпозиции для клиента."""

    n: int
    instruction_ru: str
    micro_skill: str
    expected_value: str
    kind: str
    reveal: Any  # None или строка — оставляем гибким


class WrongTaskOut(BaseModel):
    """Задача тренажёра с декомпозицией и маршрутом."""

    id: str
    problem_id: int
    node_id: str
    topic_label: str
    statement: str
    answer: str
    primary_micro_skill: str | None
    decomp_idx: int | None
    steps: list[StepOut]
    state: str
    wrong_answer: str
    mastery: float


class WrongTasksResponse(BaseModel):
    """Ответ эндпоинта /wrong-tasks."""

    tasks: list[WrongTaskOut]


class RecurringErrorOut(BaseModel):
    """Запись топа повторяющихся ошибок студента."""

    micro_skill: str
    label_ru: str | None   # из micro_skills, может отсутствовать
    error_count: int
    last_cause_text: str | None
    node_id: str | None


class GlobalErrorOut(BaseModel):
    """Запись агрегированного топа ошибок (только для владельца)."""

    micro_skill: str
    label_ru: str | None
    total_errors: int
    students_affected: int


class AnalyticsResponse(BaseModel):
    """Ответ эндпоинта /analytics."""

    my_top: list[RecurringErrorOut]
    global_top: list[GlobalErrorOut] | None = None


# ── Маппинг dataclass → Pydantic ─────────────────────────────────────────────


def _step_to_out(step: StepDTO) -> StepOut:
    """Конвертирует StepDTO → StepOut."""
    return StepOut(
        n=step.n,
        instruction_ru=step.instruction_ru,
        micro_skill=step.micro_skill,
        expected_value=step.expected_value,
        kind=step.kind,
        reveal=step.reveal,
    )


def _task_to_out(task: WrongTask) -> WrongTaskOut:
    """Конвертирует WrongTask → WrongTaskOut."""
    return WrongTaskOut(
        id=task.id,
        problem_id=task.problem_id,
        node_id=task.node_id,
        topic_label=task.topic_label,
        statement=task.statement,
        answer=task.answer,
        primary_micro_skill=task.primary_micro_skill,
        decomp_idx=task.decomp_idx,
        steps=[_step_to_out(s) for s in task.steps],
        state=task.state,
        wrong_answer=task.wrong_answer,
        mastery=task.mastery,
    )


# ── Эндпоинты ────────────────────────────────────────────────────────────────


@router.get("/wrong-tasks", response_model=WrongTasksResponse)
async def get_wrong_tasks(
    request: Request,
    days: int = Query(14, ge=1, le=90, description="Окно в днях (1-90)"),
    limit: int = Query(30, ge=1, le=50, description="Максимум задач (1-50)"),
) -> WrongTasksResponse:
    """Список задач из неверных попыток студента за последние days дней.

    Возвращает до limit задач, дедуплицированных по problem_id (самая свежая попытка).
    Каждая задача включает декомпозицию (steps), маршрутный статус (state) и mastery узла.
    """
    session, student = await _get_current_student(request)
    try:
        tasks = await build_wrong_tasks(
            session,
            student_id=student.id,
            days=days,
            limit=limit,
        )
    finally:
        await session.close()

    return WrongTasksResponse(tasks=[_task_to_out(t) for t in tasks])


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(request: Request) -> AnalyticsResponse:
    """Аналитика повторяющихся ошибок для текущего студента.

    my_top  — топ умений по числу ошибок студента (до 20).
    global_top — агрегат по всем студентам (только если student_id == settings.owner_student_id).

    LEFT JOIN с micro_skills для получения label_ru.
    Параметризованный SQL, без f-строк.
    """
    session, student = await _get_current_student(request)
    try:
        # ── Топ ошибок текущего студента ─────────────────────────────────────
        my_rows = await session.execute(
            text(
                "SELECT re.micro_skill, ms.label_ru, re.error_count, "
                "       re.last_cause_text, re.node_id "
                "FROM recurring_errors re "
                "LEFT JOIN micro_skills ms ON ms.code = re.micro_skill "
                "WHERE re.student_id = :sid "
                "ORDER BY re.error_count DESC "
                "LIMIT 20"
            ),
            {"sid": student.id},
        )
        my_top = [
            RecurringErrorOut(
                micro_skill=row.micro_skill,
                label_ru=row.label_ru,
                error_count=row.error_count,
                last_cause_text=row.last_cause_text,
                node_id=row.node_id,
            )
            for row in my_rows
        ]

        # ── Глобальный топ — только для владельца ────────────────────────────
        global_top: list[GlobalErrorOut] | None = None
        is_owner = (
            settings.owner_student_id != 0
            and student.id == settings.owner_student_id
        )
        if is_owner:
            global_rows = await session.execute(
                text(
                    "SELECT re.micro_skill, ms.label_ru, "
                    "       SUM(re.error_count) AS total_errors, "
                    "       COUNT(DISTINCT re.student_id) AS students_affected "
                    "FROM recurring_errors re "
                    "LEFT JOIN micro_skills ms ON ms.code = re.micro_skill "
                    "GROUP BY re.micro_skill, ms.label_ru "
                    "ORDER BY total_errors DESC "
                    "LIMIT 50"
                )
            )
            global_top = [
                GlobalErrorOut(
                    micro_skill=row.micro_skill,
                    label_ru=row.label_ru,
                    total_errors=row.total_errors,
                    students_affected=row.students_affected,
                )
                for row in global_rows
            ]
    finally:
        await session.close()

    return AnalyticsResponse(my_top=my_top, global_top=global_top)
