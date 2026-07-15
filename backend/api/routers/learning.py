"""Один серверный маршрут обучения: пример → опоры → самостоятельность → перенос."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from api.routes import _get_current_student
from core.bkt import record_attempt
from core.grading import check_answer
from core.learning import (
    get_lesson,
    load_learning_manifest,
    student_activity_payload,
)
from db.models import LearningAttempt, LearningSession, Problem


router = APIRouter(prefix="/api/learning", tags=["learning"])


class LessonBody(BaseModel):
    lesson_id: str = Field(min_length=1, max_length=80)


class LearningAnswerBody(LessonBody):
    activity_id: str = Field(min_length=1, max_length=80)
    activity_index: int = Field(ge=0)
    answer: str = Field(min_length=1, max_length=500)
    client_attempt_id: str = Field(min_length=8, max_length=64)
    response_time_ms: int | None = Field(default=None, ge=0, le=3_600_000)


def _lesson_or_404(lesson_id: str) -> tuple[dict[str, Any], str]:
    lesson = get_lesson(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Урок не найден")
    return lesson, load_learning_manifest()["version"]


def _lesson_summary(lesson: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": lesson["id"],
        "title": lesson["title"],
        "lesson_title": lesson["lesson_title"],
        "goal": lesson["goal"],
        "result_label": lesson["result_label"],
        "duration_minutes": lesson["duration_minutes"],
    }


async def _find_session(
    db,
    *,
    student_id: int,
    lesson_id: str,
    manifest_version: str,
    for_update: bool = False,
) -> LearningSession | None:
    query = select(LearningSession).where(
        LearningSession.student_id == student_id,
        LearningSession.lesson_id == lesson_id,
        LearningSession.manifest_version == manifest_version,
    )
    if for_update:
        query = query.with_for_update()
    return (await db.execute(query)).scalar_one_or_none()


async def _get_or_create_session(
    db,
    *,
    student_id: int,
    lesson_id: str,
    manifest_version: str,
) -> LearningSession:
    await db.execute(
        pg_insert(LearningSession)
        .values(
            student_id=student_id,
            lesson_id=lesson_id,
            manifest_version=manifest_version,
            status="active",
            current_activity_idx=0,
        )
        .on_conflict_do_nothing(
            constraint="uq_learning_session_student_lesson_version"
        )
    )
    learning_session = await _find_session(
        db,
        student_id=student_id,
        lesson_id=lesson_id,
        manifest_version=manifest_version,
    )
    if learning_session is None:  # pragma: no cover — инвариант БД
        raise HTTPException(status_code=500, detail="Не удалось открыть урок")
    return learning_session


async def _problem_for_activity(db, lesson: dict[str, Any], activity: dict[str, Any]) -> Problem:
    problem = (
        await db.execute(
            select(Problem).where(Problem.content_idx == activity["content_idx"])
        )
    ).scalar_one_or_none()
    if problem is None or problem.node_id != lesson["node_id"]:
        raise HTTPException(
            status_code=503,
            detail="Материал урока ещё не загружен",
        )
    return problem


async def _activity_attempts(db, session_id: int, activity_id: str) -> list[LearningAttempt]:
    return list(
        (
            await db.execute(
                select(LearningAttempt)
                .where(
                    LearningAttempt.session_id == session_id,
                    LearningAttempt.activity_id == activity_id,
                )
                .order_by(LearningAttempt.created_at.desc(), LearningAttempt.id.desc())
            )
        ).scalars()
    )


async def _result_payload(
    db,
    learning_session: LearningSession,
    lesson: dict[str, Any],
) -> dict[str, Any]:
    mastery_ids = {
        activity["id"]
        for activity in lesson["activities"]
        if activity.get("counts_for_mastery")
    }
    transfer_ids = {
        activity["id"]
        for activity in lesson["activities"]
        if activity["role"] == "transfer"
    }
    attempts = list(
        (
            await db.execute(
                select(LearningAttempt).where(
                    LearningAttempt.session_id == learning_session.id,
                    LearningAttempt.is_correct.is_(True),
                    LearningAttempt.activity_id.in_(mastery_ids),
                )
            )
        ).scalars()
    )
    completed_ids = {attempt.activity_id for attempt in attempts}
    unsupported_ids = {
        attempt.activity_id for attempt in attempts if attempt.support_level == 0
    }
    return {
        "title": "Теперь ты умеешь",
        "skill": lesson["result_label"],
        "independent_completed": len(completed_ids & mastery_ids),
        "transfer_completed": len(completed_ids & transfer_ids),
        "without_support": len(unsupported_ids),
        "evidence_label": "2 самостоятельных задания, одно — с переносом на новую ситуацию",
    }


async def _session_state(
    db,
    learning_session: LearningSession,
    lesson: dict[str, Any],
    *,
    feedback: dict[str, Any] | None = None,
) -> dict[str, Any]:
    activities = lesson["activities"]
    is_completed = (
        learning_session.status == "completed"
        or learning_session.current_activity_idx >= len(activities)
    )
    if is_completed:
        return {
            "session_id": learning_session.id,
            "status": "completed",
            "lesson": _lesson_summary(lesson),
            "progress": {
                "current": len(activities),
                "total": len(activities),
                "completed": len(activities),
            },
            "activity": None,
            "feedback": feedback,
            "result": await _result_payload(db, learning_session, lesson),
        }

    activity = activities[learning_session.current_activity_idx]
    problem = await _problem_for_activity(db, lesson, activity)
    attempts = await _activity_attempts(db, learning_session.id, activity["id"])
    wrong_count = sum(1 for attempt in attempts if not attempt.is_correct)
    support_level = min(wrong_count, len(activity.get("hint_levels", [])))
    payload = student_activity_payload(
        activity,
        statement=problem.text_ru,
        answer_type=problem.answer_type,
        support_level=support_level,
        last_answer=attempts[0].answer_given if attempts else None,
    )
    payload.pop("content_idx", None)
    return {
        "session_id": learning_session.id,
        "status": "active",
        "lesson": _lesson_summary(lesson),
        "progress": {
            "current": learning_session.current_activity_idx + 1,
            "total": len(activities),
            "completed": learning_session.current_activity_idx,
        },
        "activity": payload,
        "feedback": feedback,
        "result": None,
    }


async def _current_path_payload(db, *, student_id: int) -> dict[str, Any]:
    manifest = load_learning_manifest()
    path = manifest["path"]
    block_lessons = [
        lesson
        for lesson in manifest["lessons"]
        if lesson["node_id"] == path["current_block_id"]
    ]
    sessions = [
        await _find_session(
            db,
            student_id=student_id,
            lesson_id=lesson["id"],
            manifest_version=manifest["version"],
        )
        for lesson in block_lessons
    ]
    completed_lessons = sum(
        session is not None and session.status == "completed"
        for session in sessions
    )
    current_index = next(
        (
            index
            for index, session in enumerate(sessions)
            if session is None or session.status != "completed"
        ),
        len(block_lessons) - 1,
    )
    path_payload = {
        "id": path["id"],
        "title": path["title"],
        "current_block": {
            "id": path["current_block_id"],
            "title": path["current_block_title"],
            "completed_lessons": completed_lessons,
            "total_lessons": len(block_lessons),
        },
    }
    if not block_lessons:
        return {"path": path_payload, "lesson": None}

    lesson = block_lessons[current_index]
    learning_session = sessions[current_index]
    status = learning_session.status if learning_session else "not_started"
    action_label = {
        "not_started": "Начать урок",
        "active": "Продолжить",
        "completed": "Посмотреть результат",
    }.get(status, "Продолжить")
    completed = (
        learning_session.current_activity_idx
        if learning_session is not None
        else 0
    )
    current_role = None
    if status != "completed" and completed < len(lesson["activities"]):
        current_role = lesson["activities"][completed]["role"]
    return {
        "path": path_payload,
        "lesson": {
            **_lesson_summary(lesson),
            "status": status,
            "progress": {
                "completed": min(completed, len(lesson["activities"])),
                "total": len(lesson["activities"]),
                "current_role": current_role,
            },
            "primary_action": {
                "label": action_label,
                "lesson_id": lesson["id"],
            },
        },
    }


@router.get("/path/current")
async def learning_current_path(request: Request):
    db, student = await _get_current_student(request)
    try:
        return await _current_path_payload(db, student_id=student.id)
    finally:
        await db.close()


@router.post("/start")
async def learning_start(request: Request, body: LessonBody):
    lesson, manifest_version = _lesson_or_404(body.lesson_id)
    db, student = await _get_current_student(request)
    try:
        learning_session = await _get_or_create_session(
            db,
            student_id=student.id,
            lesson_id=lesson["id"],
            manifest_version=manifest_version,
        )
        await db.commit()
        return await _session_state(db, learning_session, lesson)
    finally:
        await db.close()


@router.post("/advance")
async def learning_advance(request: Request, body: LessonBody):
    lesson, manifest_version = _lesson_or_404(body.lesson_id)
    db, student = await _get_current_student(request)
    try:
        learning_session = await _find_session(
            db,
            student_id=student.id,
            lesson_id=lesson["id"],
            manifest_version=manifest_version,
            for_update=True,
        )
        if learning_session is None:
            raise HTTPException(status_code=409, detail="Сначала начни урок")
        if learning_session.status == "completed":
            return await _session_state(db, learning_session, lesson)

        activity = lesson["activities"][learning_session.current_activity_idx]
        if activity["role"] != "worked":
            raise HTTPException(status_code=409, detail="На этом шаге нужен ответ")
        learning_session.current_activity_idx += 1
        learning_session.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return await _session_state(db, learning_session, lesson)
    finally:
        await db.close()


@router.post("/answer")
async def learning_answer(request: Request, body: LearningAnswerBody):
    lesson, manifest_version = _lesson_or_404(body.lesson_id)
    db, student = await _get_current_student(request)
    try:
        learning_session = await _find_session(
            db,
            student_id=student.id,
            lesson_id=lesson["id"],
            manifest_version=manifest_version,
            for_update=True,
        )
        if learning_session is None:
            raise HTTPException(status_code=409, detail="Сначала начни урок")

        duplicate = (
            await db.execute(
                select(LearningAttempt).where(
                    LearningAttempt.session_id == learning_session.id,
                    LearningAttempt.client_attempt_id == body.client_attempt_id,
                )
            )
        ).scalar_one_or_none()
        if duplicate is not None:
            return await _session_state(
                db,
                learning_session,
                lesson,
                feedback={
                    "is_correct": duplicate.is_correct,
                    "message": "Ответ уже учтён.",
                    "is_duplicate": True,
                },
            )

        if learning_session.status == "completed":
            current_state = await _session_state(db, learning_session, lesson)
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "stale_activity",
                    "message": "Урок уже продвинулся дальше.",
                    "state": current_state,
                },
            )
        activity = lesson["activities"][learning_session.current_activity_idx]
        if (
            body.activity_index != learning_session.current_activity_idx
            or body.activity_id != activity["id"]
        ):
            current_state = await _session_state(db, learning_session, lesson)
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "stale_activity",
                    "message": "Этот ответ относится к уже завершённому шагу.",
                    "state": current_state,
                },
            )
        if activity["role"] == "worked":
            raise HTTPException(status_code=409, detail="Сначала разбери пример")

        problem = await _problem_for_activity(db, lesson, activity)
        prior_attempts = await _activity_attempts(
            db,
            learning_session.id,
            activity["id"],
        )
        support_level = min(
            sum(1 for attempt in prior_attempts if not attempt.is_correct),
            len(activity.get("hint_levels", [])),
        )
        is_correct = check_answer(
            body.answer,
            str(activity["expected_answer"]),
            activity.get("answer_type") or problem.answer_type,
        )
        counts_for_mastery = bool(activity.get("counts_for_mastery"))
        db.add(
            LearningAttempt(
                session_id=learning_session.id,
                client_attempt_id=body.client_attempt_id,
                activity_id=activity["id"],
                content_idx=activity["content_idx"],
                problem_id=problem.id,
                answer_given=body.answer,
                is_correct=is_correct,
                support_level=support_level,
                counts_for_mastery=counts_for_mastery,
                response_time_ms=body.response_time_ms,
            )
        )
        if counts_for_mastery:
            await record_attempt(
                db,
                student.id,
                problem,
                body.answer,
                is_correct,
                response_time_ms=body.response_time_ms,
                source="learning",
            )

        if is_correct:
            learning_session.current_activity_idx += 1
            if learning_session.current_activity_idx >= len(lesson["activities"]):
                learning_session.status = "completed"
                learning_session.completed_at = datetime.now(timezone.utc)
        learning_session.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return await _session_state(
            db,
            learning_session,
            lesson,
            feedback={
                "is_correct": is_correct,
                "message": (
                    "Верно. Двигаемся дальше."
                    if is_correct
                    else "Пока не сходится. Проверь, что в задаче остаётся неизменным."
                ),
                "is_duplicate": False,
            },
        )
    finally:
        await db.close()
