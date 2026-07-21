"""Единый durable journey: адаптация → диагностика → фото → guided → перенос."""

from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import math
import unicodedata
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, File as FastApiFile, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from api.routes import _get_current_student, ai_ip_limit, limiter
from core.bkt import (
    MASTERY_MIN_ACCURACY,
    MASTERY_MIN_CORRECT,
    MASTERY_THRESHOLD,
    is_mastered,
    record_attempt,
)
from core.config import settings
from core.grading import (
    check_answer,
    is_step_reference_supported,
)
from core.journey import (
    DIAGNOSTIC_ANCHORS,
    DIAGNOSTIC_EASIER,
    DIAGNOSTIC_SKILLS,
    EXAM_MAP,
    TOPIC_BLUEPRINTS,
    build_route,
    diagnostic_mastery_prior,
    diagnostic_score,
    initial_diagnostic,
    topic_blueprint,
)
from core.llm_openai import (
    GuidedAnswerResult,
    LlmUnavailable,
    TypedAnswerResult,
    evaluate_guided_answer,
    evaluate_solution_photo,
    evaluate_typed_answer,
)
from core.step_content import (
    guided_input_contract,
    safe_step_instruction,
)
from core.tutor import feedback_contains_protected_value
from db.models import (
    DecompositionProblem,
    JourneyAttempt,
    Mastery,
    Problem,
    ProblemStep,
    Student,
    StudentJourney,
)
import db.base as db_base


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/journey", tags=["journey"])

_MAX_PHOTO_BYTES = 8 * 1024 * 1024
_MAX_PHOTO_PIXELS = 24_000_000
_PHOTO_CONFIDENCE_THRESHOLD = 0.65
_PHOTO_PROCESSING_TIMEOUT = timedelta(minutes=3)
_TYPED_PROCESSING_TIMEOUT = timedelta(seconds=60)
_GUIDED_PROCESSING_TIMEOUT = timedelta(seconds=60)
_MAX_TYPED_ANSWER_CHARS = 500
_MAX_TYPED_CHECK_SUMMARY_CHARS = 1_000
_MAX_TYPED_HISTORY_ENTRIES = 6
_MAX_TYPED_HISTORY_ANSWER_CHARS = 500
_TYPED_ANSWER_CONFIDENCE_THRESHOLD = 0.65
_TYPED_ANSWER_VERDICTS = {"correct", "incorrect", "unsure"}
_TYPED_ANSWER_ERROR_FOCUSES = {
    "none",
    "interpretation",
    "calculation",
    "units",
    "format",
    "unknown",
}
_ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
}
_EXPECTED_FORMATS = {
    "image/jpeg": {"JPEG"},
    "image/png": {"PNG"},
    "image/webp": {"WEBP"},
    "image/heic": {"HEIF", "HEIC"},
    "image/heif": {"HEIF", "HEIC"},
}
_WORKSPACE_RECOVERY_REASONS = {
    "unreadable",
    "wrong_photo",
    "unsure",
    "provider_error",
}
_WORKSPACE_RENDER_STAGES = {
    "independent_task",
    "photo_feedback",
    "photo_recovery",
    "guided_step",
    "transfer_task",
    "transfer_feedback",
}
_WorkspaceProjection = Literal[
    "independent_task",
    "typed_processing",
    "guided_processing",
    "photo_processing",
    "photo_feedback",
    "photo_recovery",
    "guided_step",
    "transfer_task",
    "transfer_feedback",
]
_WorkspaceMode = Literal["independent", "transfer"]
_TypedCompletionStatus = Literal["accepted", "provider_error"]
_GuidedCompletionStatus = Literal["accepted", "provider_error"]
_TYPED_COMPLETION_TASKS: set[
    asyncio.Task[tuple[_TypedCompletionStatus, dict[str, Any]]]
] = set()
_GUIDED_COMPLETION_TASKS: set[
    asyncio.Task[tuple[_GuidedCompletionStatus, dict[str, Any]]]
] = set()


class ProfileBody(BaseModel):
    revision: int = Field(ge=0)
    target: str = Field(min_length=1, max_length=40)
    weekly_goal: int = Field(ge=2, le=7)
    session_minutes: Literal[20, 30, 45] = 30
    target_window: Literal["spring-2027", "later"] = "spring-2027"
    prep_experience: Literal["new", "self", "teacher"] = "new"
    weak_topics: list[str] = Field(default_factory=list, max_length=3)
    strong_topics: list[str] = Field(default_factory=list, max_length=3)
    mock_math_band: Literal["not-taken", "0-20", "21-30", "31-40"] = "not-taken"
    language: Literal["ru"] = "ru"


class ProfileDraftBody(ProfileBody):
    screen: Literal[0, 1, 2, 3]
    substep: Literal[0, 1, 2] = 0


class ContinueBody(BaseModel):
    revision: int = Field(ge=0)
    action: str = Field(min_length=1, max_length=50)


class DiagnosticAnswerBody(BaseModel):
    revision: int = Field(ge=0)
    question_id: int = Field(ge=0)
    answer: str = Field(min_length=1, max_length=500)
    client_attempt_id: str = Field(min_length=8, max_length=64)


class HelpBody(BaseModel):
    revision: int = Field(ge=0)
    problem_id: int = Field(gt=0)


class GuidedAnswerBody(BaseModel):
    revision: int = Field(ge=0)
    problem_id: int = Field(gt=0)
    step_n: int = Field(ge=1)
    answer: str = Field(min_length=1, max_length=500)
    client_attempt_id: str = Field(min_length=8, max_length=64)


class TypedAnswerBody(BaseModel):
    revision: int = Field(ge=0)
    problem_id: int = Field(gt=0)
    answer: str
    client_attempt_id: str = Field(min_length=8, max_length=64)


class RetryPhotoBody(BaseModel):
    revision: int = Field(ge=0)


def _hash_parts(*parts: str | bytes) -> str:
    digest = hashlib.sha256()
    for part in parts:
        value = part.encode("utf-8") if isinstance(part, str) else part
        digest.update(len(value).to_bytes(8, "big"))
        digest.update(value)
    return digest.hexdigest()


def _normalise_typed_text(value: object, *, max_chars: int) -> str | None:
    """Нормализует bounded text и отбрасывает control-символы."""

    if not isinstance(value, str):
        return None
    normalised = unicodedata.normalize("NFKC", value)
    if any(
        unicodedata.category(char).startswith("C")
        and char not in {"\t", "\n", "\r"}
        for char in normalised
    ):
        return None
    normalised = " ".join(normalised.split())
    if not normalised or len(normalised) > max_chars:
        return None
    return normalised


def _normalise_typed_answer(value: object) -> str | None:
    """Приводит короткий ответ к единому безопасному виду для AI и idempotency."""

    return _normalise_typed_text(value, max_chars=_MAX_TYPED_ANSWER_CHARS)


def _typed_feedback_payload(raw: object) -> dict[str, Any]:
    """Собирает UI-feedback только из backend-owned enum и статических текстов."""

    data = raw if isinstance(raw, dict) else {}
    verdict = data.get("verdict")
    focus = data.get("error_focus")
    reason = data.get("reason")
    counted = data.get("counts_for_mastery") is True
    generic = {
        "verdict": "unsure",
        "message": "Не удалось надёжно проверить ответ. Попробуй ещё раз или отправь фото.",
        "error_focus": "unknown",
        "counts_for_mastery": False,
    }
    if verdict == "correct" and focus == "format":
        return {
            "verdict": "correct",
            "message": (
                "Ответ по смыслу верный. Открываем следующую задачу."
            ),
            "error_focus": "format",
            "counts_for_mastery": False,
        }
    if verdict == "correct" and focus == "none":
        return {
            "verdict": "correct",
            "message": "Ответ подтверждён. Открываем следующую задачу.",
            "error_focus": "none",
            "counts_for_mastery": False,
        }
    if verdict == "incorrect" and focus in _TYPED_ANSWER_ERROR_FOCUSES - {"none"}:
        messages = {
            "interpretation": "Проверь, что именно спрашивается в условии, и попробуй ещё раз.",
            "calculation": "Проверь вычисления и попробуй ещё раз.",
            "units": "Проверь единицы измерения и попробуй ещё раз.",
            "format": "Проверь формат ответа и попробуй ещё раз.",
            "unknown": "Проверь ответ и попробуй ещё раз.",
        }
        return {
            "verdict": "incorrect",
            "message": messages[focus],
            "error_focus": focus,
            "counts_for_mastery": counted,
        }
    if verdict == "unsure" and focus == "unknown" and reason == "provider_error":
        return {
            "verdict": "unsure",
            "message": "Проверка временно недоступна. Повтори проверку или отправь фото.",
            "error_focus": "unknown",
            "counts_for_mastery": False,
        }
    return generic


def _clear_typed_feedback(activity: dict[str, Any]) -> None:
    activity.pop("typed_feedback", None)


def _set_stage(journey: StudentJourney, stage: str) -> None:
    """Переход не переносит formative typed-feedback на новый экран."""

    activity = dict(journey.activity or {})
    _clear_typed_feedback(activity)
    journey.activity = activity
    journey.stage = stage


async def _journey_for_student(
    db,
    *,
    student_id: int,
    for_update: bool = False,
) -> StudentJourney:
    await db.execute(
        pg_insert(StudentJourney)
        .values(student_id=student_id)
        .on_conflict_do_nothing(constraint="uq_student_journeys_student")
    )
    query = select(StudentJourney).where(StudentJourney.student_id == student_id)
    if for_update:
        query = query.execution_options(populate_existing=True).with_for_update()
    journey = (await db.execute(query)).scalar_one_or_none()
    if journey is None:  # pragma: no cover - DB invariant
        raise HTTPException(status_code=500, detail="Не удалось открыть маршрут")
    return journey


async def _state_conflict(
    db,
    student,
    journey: StudentJourney,
    *,
    code: str,
    message: str,
) -> None:
    """Возвращает безопасное authoritative state вместе с конфликтом."""
    raise HTTPException(
        status_code=409,
        detail={
            "code": code,
            "message": message,
            "current_revision": journey.revision,
            "state": await _render(db, student, journey),
        },
    )


async def _require_revision(
    db,
    student,
    journey: StudentJourney,
    revision: int,
) -> None:
    if journey.revision != revision:
        await _state_conflict(
            db,
            student,
            journey,
            code="stale_revision",
            message="Экран уже изменился. Открыто актуальное состояние.",
        )


async def _ensure_not_processing(db, student, journey: StudentJourney) -> None:
    activity = dict(journey.activity or {})
    if activity.get("processing_client_attempt_id"):
        await _state_conflict(
            db,
            student,
            journey,
            code="photo_processing",
            message="Предыдущее фото ещё проверяется.",
        )
    if activity.get("typed_processing_client_attempt_id"):
        await _state_conflict(
            db,
            student,
            journey,
            code="typed_processing",
            message="Предыдущий ответ ещё проверяется.",
        )
    if activity.get("guided_processing_client_attempt_id"):
        await _state_conflict(
            db,
            student,
            journey,
            code="guided_processing",
            message="Текущий шаг ещё проверяется.",
        )


def _profile_payload(body: ProfileBody) -> dict[str, Any]:
    if body.target != "nis-grade-7":
        raise HTTPException(status_code=422, detail="Поддерживается цель NIS, 7 класс")
    topic_ids = {skill["id"] for skill in DIAGNOSTIC_SKILLS.values()}
    weak_topics = list(dict.fromkeys(body.weak_topics))
    strong_topics = list(dict.fromkeys(body.strong_topics))
    if (
        len(weak_topics) != len(body.weak_topics)
        or len(strong_topics) != len(body.strong_topics)
        or not set(weak_topics).issubset(topic_ids)
        or not set(strong_topics).issubset(topic_ids)
        or set(weak_topics) & set(strong_topics)
    ):
        raise HTTPException(
            status_code=422,
            detail="Сильные и сложные темы должны быть разными блоками диагностики",
        )
    return {
        "target": body.target,
        "weekly_goal": body.weekly_goal,
        "session_minutes": body.session_minutes,
        "target_window": body.target_window,
        "prep_experience": body.prep_experience,
        "weak_topics": weak_topics,
        "strong_topics": strong_topics,
        "mock_math_band": body.mock_math_band,
        "language": body.language,
    }


async def _problem_by_content_idx(db, content_idx: int) -> Problem:
    problem = (
        await db.execute(select(Problem).where(Problem.content_idx == content_idx))
    ).scalar_one_or_none()
    if problem is None:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "content_unavailable",
                "message": "Материал маршрута ещё не загружен.",
            },
        )
    return problem


async def _current_problem(db, journey: StudentJourney) -> Problem:
    if journey.current_problem_id is None:
        raise HTTPException(status_code=409, detail="В маршруте не выбрана задача")
    problem = await db.get(Problem, journey.current_problem_id)
    if problem is None:
        raise HTTPException(status_code=503, detail="Задача маршрута недоступна")
    return problem


def _route_topic(journey: StudentJourney) -> dict[str, Any]:
    route = dict(journey.route or {})
    topics = list(route.get("topics") or [])
    index = int(route.get("index", 0))
    if index < 0 or index >= len(topics):
        raise HTTPException(status_code=409, detail="Маршрут ученика повреждён")
    return dict(topics[index])


def _problem_payload(problem: Problem, topic: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": problem.id,
        "content_idx": problem.content_idx,
        "node_id": problem.node_id,
        "statement": problem.text_ru,
        "topic": {"id": topic["id"], "title": topic["title"]},
    }


async def _steps_for_problem(db, problem: Problem) -> list[ProblemStep]:
    if problem.content_idx is None:
        return []
    return list(
        (
            await db.execute(
                select(ProblemStep)
                .where(ProblemStep.decomp_idx == problem.content_idx)
                .order_by(ProblemStep.n)
            )
        ).scalars()
    )


async def _mastery_payload(db, student_id: int, node_id: str) -> dict[str, Any]:
    mastery = await db.get(Mastery, (student_id, node_id))
    return _mastery_row_payload(mastery)


def _mastery_row_payload(mastery: Mastery | None) -> dict[str, Any]:
    value = float(mastery.p_mastery) if mastery is not None else 0.0
    total = max(int(mastery.attempts_total), 0) if mastery is not None else 0
    correct = max(int(mastery.attempts_correct), 0) if mastery is not None else 0
    accuracy = correct / total if total else None
    return {
        "value": round(value, 3),
        "threshold": MASTERY_THRESHOLD,
        "reached": mastery is not None and is_mastered(mastery),
        "evidence": {
            "correct": correct,
            "required_correct": MASTERY_MIN_CORRECT,
            "remaining_correct": max(MASTERY_MIN_CORRECT - correct, 0),
            "total": total,
            "accuracy": round(accuracy, 3) if accuracy is not None else None,
            "minimum_accuracy": MASTERY_MIN_ACCURACY,
            "probability_reached": value >= MASTERY_THRESHOLD,
            "correct_reached": correct >= MASTERY_MIN_CORRECT,
            "accuracy_reached": accuracy is None or accuracy >= MASTERY_MIN_ACCURACY,
        },
    }


def _normalise_workspace_verdict(raw: Any) -> tuple[str, str | None]:
    """Проецирует legacy verdict в закрытый AI-owned словарь workspace."""

    if raw == "correct":
        return "correct", None
    if raw == "incorrect":
        return "needs_revision", None
    if isinstance(raw, str) and raw in _WORKSPACE_RECOVERY_REASONS:
        return "uncertain", raw
    return "uncertain", "unknown"


def _processing_source_stage(
    journey: StudentJourney,
    problem: Problem,
    attempt: JourneyAttempt | None,
) -> str:
    """Берёт mode у конкретной попытки, включая retry из photo_recovery."""

    if (
        attempt is not None
        and attempt.journey_id == journey.id
        and attempt.problem_id == problem.id
        and attempt.stage in {"independent_task", "transfer_task"}
    ):
        return attempt.stage

    feedback_stage = dict(journey.feedback or {}).get("return_stage")
    if feedback_stage in {"independent_task", "transfer_task"}:
        return str(feedback_stage)
    if journey.stage in {"independent_task", "transfer_task"}:
        return journey.stage
    return "independent_task"


def _workspace_mode(
    projection: _WorkspaceProjection,
    journey: StudentJourney,
    problem: Problem,
    processing_attempt: JourneyAttempt | None = None,
) -> _WorkspaceMode:
    if projection in {"transfer_task", "transfer_feedback"}:
        return "transfer"
    if projection == "photo_recovery":
        return (
            "transfer"
            if dict(journey.feedback or {}).get("return_stage") == "transfer_task"
            else "independent"
        )
    if projection in {"photo_processing", "typed_processing"}:
        return (
            "transfer"
            if _processing_source_stage(journey, problem, processing_attempt)
            == "transfer_task"
            else "independent"
        )
    return "independent"


def _workspace_position(
    journey: StudentJourney,
    topic: dict[str, Any],
    mode: _WorkspaceMode,
) -> int:
    blueprint = topic_blueprint(str(topic["id"]))
    sequence = [
        int(blueprint["target_content_idx"]),
        int(blueprint["transfer_content_idx"]),
        *(int(value) for value in blueprint["reinforcement_content_indices"]),
    ]
    try:
        return sequence.index(int(journey.current_decomp_idx)) + 1
    except (TypeError, ValueError):
        return 2 if mode == "transfer" else 1


async def _latest_photo_attempt(
    db,
    *,
    journey_id: int,
    problem_id: int,
    kind: Literal["independent_photo", "transfer_photo"],
) -> JourneyAttempt | None:
    return (
        await db.execute(
            select(JourneyAttempt)
            .where(
                JourneyAttempt.journey_id == journey_id,
                JourneyAttempt.problem_id == problem_id,
                JourneyAttempt.kind == kind,
            )
            .order_by(JourneyAttempt.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _workspace_envelope(
    db,
    journey: StudentJourney,
    *,
    projection: _WorkspaceProjection,
    problem: Problem,
    topic: dict[str, Any],
    processing_attempt: JourneyAttempt | None = None,
) -> dict[str, Any]:
    """Единая additive-проекция active learning поверх legacy next_step."""

    feedback = dict(journey.feedback or {})
    activity = dict(journey.activity or {})
    mode = _workspace_mode(projection, journey, problem, processing_attempt)
    typed_feedback = activity.get("typed_feedback")
    typed_feedback_data = typed_feedback if isinstance(typed_feedback, dict) else {}
    preserved_typed_answer = _normalise_typed_answer(
        typed_feedback_data.get("answer")
    )
    has_typed_feedback = (
        projection in {"independent_task", "transfer_task"}
        and bool(typed_feedback_data)
    )

    evidence_status = {
        "independent_task": "empty",
        "typed_processing": "processing",
        "guided_processing": "processing",
        "photo_processing": "processing",
        "photo_feedback": "checked",
        "photo_recovery": "preserved",
        "guided_step": "guided",
        "transfer_task": "empty",
        "transfer_feedback": "checked",
    }[projection]
    if has_typed_feedback:
        evidence_status = "checked"
    evidence_label: str | None = None
    if projection in {"typed_processing", "guided_processing"}:
        evidence_label = (
            processing_attempt.answer_given
            if processing_attempt is not None and processing_attempt.answer_given
            else "Ответ сохранён"
        )
    elif projection == "photo_processing":
        evidence_label = (
            processing_attempt.original_filename
            if processing_attempt is not None and processing_attempt.original_filename
            else "solution.jpg"
        )
    elif projection == "photo_recovery":
        preserved_photo = feedback.get("preserved_photo")
        preserved_label = (
            preserved_photo.get("name") if isinstance(preserved_photo, dict) else None
        )
        evidence_label = (
            preserved_label
            if isinstance(preserved_label, str) and preserved_label
            else "solution.jpg"
        )
    elif projection in {"photo_feedback", "transfer_feedback"}:
        latest_attempt = await _latest_photo_attempt(
            db,
            journey_id=journey.id,
            problem_id=problem.id,
            kind=(
                "transfer_photo"
                if projection == "transfer_feedback"
                else "independent_photo"
            ),
        )
        if latest_attempt is not None and latest_attempt.original_filename:
            evidence_label = latest_attempt.original_filename
    elif has_typed_feedback:
        evidence_label = preserved_typed_answer or "Ответ сохранён"

    context_kind = {
        "independent_task": "closed",
        "typed_processing": "processing",
        "guided_processing": "processing",
        "photo_processing": "processing",
        "photo_feedback": "feedback",
        "photo_recovery": "uncertain",
        "guided_step": "guided",
        "transfer_task": "closed",
        "transfer_feedback": "feedback",
    }[projection]
    if has_typed_feedback:
        context_kind = (
            "uncertain"
            if typed_feedback_data.get("verdict") == "unsure"
            else "feedback"
        )
    verdict: str | None = None
    recovery_reason: str | None = None
    if projection in {"photo_feedback", "transfer_feedback"}:
        verdict, recovery_reason = _normalise_workspace_verdict(
            feedback.get("verdict")
        )
    elif projection == "photo_recovery":
        verdict = "uncertain"
        _ignored_verdict, recovery_reason = _normalise_workspace_verdict(
            feedback.get("reason")
        )
    elif has_typed_feedback:
        verdict = (
            "needs_revision"
            if typed_feedback_data.get("verdict") == "incorrect"
            else "uncertain"
        )
        if typed_feedback_data.get("reason") == "provider_error":
            recovery_reason = "provider_error"

    return {
        "workspace_version": 1,
        "task": {
            "journey_id": journey.id,
            "problem_id": problem.id,
            "topic": {"id": topic["id"], "title": topic["title"]},
            "mode": mode,
            "statement": problem.text_ru,
            "position": _workspace_position(journey, topic, mode),
        },
        "learner_evidence": {
            "kind": (
                "typed"
                if projection in {"typed_processing", "guided_processing"}
                or has_typed_feedback
                else "photo"
            ),
            "status": evidence_status,
            "label": evidence_label,
        },
        "context_layer": {
            "kind": context_kind,
            "verdict": verdict,
            "recovery_reason": recovery_reason,
        },
        "response": {
            "default_mode": (
                "typed"
                if projection in {"typed_processing", "guided_processing"}
                or has_typed_feedback
                else "photo"
            ),
            "typed_available": projection in {"independent_task", "transfer_task"},
            "help_available": projection == "independent_task",
        },
        "support": {
            "used": bool(activity.get("support_used", False)),
            "highest_hint_rung": 0,
        },
    }


def _guided_step_payload(
    step: ProblemStep,
    *,
    problem: Problem,
    total: int,
) -> dict[str, Any]:
    instruction = safe_step_instruction(
        step.instruction_ru,
        expected_value=step.expected_value,
        correct_answer=problem.answer,
    )
    input_contract = guided_input_contract(
        instruction,
        expected_value=step.expected_value,
    )
    return {
        "number": step.n,
        "total": total,
        "instruction": instruction,
        **input_contract,
    }


async def _render(db, student, journey: StudentJourney) -> dict[str, Any]:
    stage = journey.stage
    context: dict[str, Any] = {
        "exam_map": EXAM_MAP,
        "profile": dict(journey.profile_data or {}),
        "route": dict(journey.route or {}),
    }

    processing_client_attempt_id = dict(journey.activity or {}).get(
        "processing_client_attempt_id"
    )
    if processing_client_attempt_id:
        attempt = await _existing_attempt(
            db,
            student_id=student.id,
            client_attempt_id=str(processing_client_attempt_id),
        )
        problem = await _current_problem(db, journey)
        topic = _route_topic(journey)
        next_step = {
            "type": "photo_processing",
            "title": "Проверяем ход решения",
            "problem": _problem_payload(problem, topic),
            "message": (
                "Сверяем каждый шаг с условием. Экран можно обновить — "
                "фото и прогресс уже сохранены."
            ),
            "preserved_photo": {
                "name": (
                    attempt.original_filename
                    if attempt is not None and attempt.original_filename
                    else "solution.jpg"
                )
            },
            "primary_action": "Проверить статус",
        }
        workspace = await _workspace_envelope(
            db,
            journey,
            projection="photo_processing",
            problem=problem,
            topic=topic,
            processing_attempt=attempt,
        )
        return {
            "journey_id": journey.id,
            "revision": journey.revision,
            "next_step": next_step,
            "context": context,
            **workspace,
        }

    guided_processing_client_attempt_id = dict(journey.activity or {}).get(
        "guided_processing_client_attempt_id"
    )
    if guided_processing_client_attempt_id:
        attempt = await _existing_attempt(
            db,
            student_id=student.id,
            client_attempt_id=str(guided_processing_client_attempt_id),
        )
        problem = await _current_problem(db, journey)
        topic = _route_topic(journey)
        steps = await _steps_for_problem(db, problem)
        step_n = int(dict(journey.activity or {}).get("guided_step", 1))
        step = next((item for item in steps if item.n == step_n), None)
        if step is None:
            raise HTTPException(status_code=409, detail="Шаг разбора недоступен")
        next_step = {
            "type": "guided_processing",
            "title": "Проверяем этот шаг",
            "problem": _problem_payload(problem, topic),
            "step": _guided_step_payload(step, problem=problem, total=len(steps)),
            "message": "AI проверяет смысл записи. Ответ уже сохранён.",
            "preserved_answer": {
                "value": (
                    attempt.answer_given
                    if attempt is not None and attempt.answer_given
                    else "Ответ сохранён"
                )
            },
            "primary_action": "Проверить статус",
        }
        workspace = await _workspace_envelope(
            db,
            journey,
            projection="guided_processing",
            problem=problem,
            topic=topic,
            processing_attempt=attempt,
        )
        return {
            "journey_id": journey.id,
            "revision": journey.revision,
            "next_step": next_step,
            "context": context,
            **workspace,
        }

    typed_processing_client_attempt_id = dict(journey.activity or {}).get(
        "typed_processing_client_attempt_id"
    )
    if typed_processing_client_attempt_id:
        attempt = await _existing_attempt(
            db,
            student_id=student.id,
            client_attempt_id=str(typed_processing_client_attempt_id),
        )
        problem = await _current_problem(db, journey)
        topic = _route_topic(journey)
        next_step = {
            "type": "typed_processing",
            "title": "Проверяем ответ",
            "problem": _problem_payload(problem, topic),
            "message": (
                "AI сопоставляет ответ с условием. Экран можно обновить — "
                "ответ и прогресс уже сохранены."
            ),
            "preserved_answer": {
                "value": (
                    attempt.answer_given
                    if attempt is not None and attempt.answer_given
                    else "Ответ сохранён"
                )
            },
            "primary_action": "Проверить статус",
        }
        workspace = await _workspace_envelope(
            db,
            journey,
            projection="typed_processing",
            problem=problem,
            topic=topic,
            processing_attempt=attempt,
        )
        return {
            "journey_id": journey.id,
            "revision": journey.revision,
            "next_step": next_step,
            "context": context,
            **workspace,
        }

    if stage == "profile":
        stored_profile = dict(journey.profile_data or {})
        draft = {
            "target": "nis-grade-7",
            "weekly_goal": 4,
            "session_minutes": 30,
            "target_window": "spring-2027",
            "prep_experience": "new",
            "weak_topics": [],
            "strong_topics": [],
            "mock_math_band": "not-taken",
            "language": "ru",
            **{
                key: value
                for key, value in stored_profile.items()
                if key not in {"onboarding_screen", "onboarding_substep"}
            },
        }
        next_step = {
            "type": "profile",
            "student": {
                "name": student.first_name or student.full_name or "Ученик",
                "grade": student.grade,
            },
            "title": "Начнём с тебя",
            "description": "Сначала настроим цель, затем определим стартовый уровень.",
            "screen": int(stored_profile.get("onboarding_screen", 0)),
            "substep": int(stored_profile.get("onboarding_substep", 0)),
            "screen_count": 4,
            "draft": draft,
            "primary_action": "Настроить подготовку",
        }
    elif stage == "exam_map":
        next_step = {
            "type": "exam_map",
            "title": "Что будет на отборе NIS",
            "scope_note": EXAM_MAP["scope_note"],
            "primary_action": "Перейти к диагностике",
        }
    elif stage == "diagnostic_intro":
        next_step = {
            "type": "diagnostic_intro",
            "title": "Найдём твою точку старта",
            "description": (
                "Пять опорных задач. Если ответ вызывает сомнение, система даст "
                "более простой вопрос по тому же навыку."
            ),
            "estimated_minutes": 8,
            "primary_action": "Начать диагностику",
        }
    elif stage == "diagnostic_question":
        diagnostic = dict(journey.diagnostic or {})
        queue = list(diagnostic.get("queue") or [])
        position = int(diagnostic.get("position", 0))
        if position >= len(queue):
            raise HTTPException(status_code=409, detail="Диагностика уже завершена")
        problem = await _problem_by_content_idx(db, int(queue[position]))
        next_step = {
            "type": "diagnostic_question",
            "title": "Диагностика",
            "progress": {
                "answered": position,
                "current": position + 1,
                "planned": len(queue),
            },
            "question": {
                "id": problem.content_idx,
                "statement": problem.text_ru,
                "answer_type": problem.answer_type or "text",
            },
            "primary_action": "Ответить",
        }
    elif stage == "diagnostic_result":
        correct, total = diagnostic_score(dict(journey.diagnostic or {}))
        route = dict(journey.route or {})
        next_step = {
            "type": "diagnostic_result",
            "title": "Точка старта найдена",
            "score": {"correct": correct, "total": total},
            "skill_profile": list(route.get("skill_profile") or []),
            "description": (
                "Это не оценка. По ответам мы выбрали темы, которые быстрее всего "
                "дадут рост на математических блоках."
            ),
            "primary_action": "Показать мой маршрут",
        }
    elif stage == "route_ready":
        route = dict(journey.route or {})
        next_step = {
            "type": "route_ready",
            "title": "Твой первый маршрут",
            "topics": list(route.get("topics") or []),
            "primary_action": "Начать первую тему",
        }
    elif stage == "lesson_intro":
        topic = _route_topic(journey)
        next_step = {
            "type": "lesson_intro",
            "topic": topic,
            "title": topic["title"],
            "description": topic["reason"],
            "goal": topic["goal"],
            "primary_action": "Начать задачу",
        }
    elif stage in {"independent_task", "transfer_task"}:
        problem = await _current_problem(db, journey)
        topic = _route_topic(journey)
        is_transfer = stage == "transfer_task"
        next_step = {
            "type": stage,
            "title": "Проверка переноса" if is_transfer else "Реши самостоятельно",
            "mode": "transfer" if is_transfer else "independent",
            "problem": _problem_payload(problem, topic),
            "instruction": (
                "Реши задачу и отправь короткий ответ или фото полного решения."
            ),
            "photo_required": False,
            "help_available": not is_transfer,
            "photo_consent_required": student.photo_consent is not True,
            "primary_action": "Сфотографировать решение",
        }
        activity = dict(journey.activity or {})
        if "typed_feedback" in activity:
            next_step["typed_feedback"] = _typed_feedback_payload(
                activity["typed_feedback"]
            )
            typed_feedback = activity["typed_feedback"]
            preserved_answer = (
                _normalise_typed_answer(typed_feedback.get("answer"))
                if isinstance(typed_feedback, dict)
                else None
            )
            if preserved_answer is not None:
                next_step["preserved_answer"] = {"value": preserved_answer}
    elif stage == "guided_step":
        problem = await _current_problem(db, journey)
        topic = _route_topic(journey)
        steps = await _steps_for_problem(db, problem)
        step_n = int(dict(journey.activity or {}).get("guided_step", 1))
        step = next((item for item in steps if item.n == step_n), None)
        if step is None:
            raise HTTPException(status_code=409, detail="Шаг разбора недоступен")
        next_step = {
            "type": "guided_step",
            "title": "Разберём эту же задачу",
            "problem": _problem_payload(problem, topic),
            "step": {
                **_guided_step_payload(step, problem=problem, total=len(steps)),
            },
            "feedback": dict(journey.activity or {}).get("guided_feedback"),
            "photo_required": False,
            "mastery_note": (
                "Разбор не повышает уровень. Его подтвердит новая самостоятельная задача."
            ),
            "primary_action": "Проверить шаг",
        }
    elif stage in {"photo_feedback", "photo_recovery", "transfer_feedback"}:
        problem = await _current_problem(db, journey)
        topic = _route_topic(journey)
        feedback = dict(journey.feedback or {})
        next_step = {
            "type": stage,
            "problem": _problem_payload(problem, topic),
            **feedback,
        }
    elif stage == "topic_result":
        topic = _route_topic(journey)
        next_step = {
            "type": "topic_result",
            "title": "Навык подтверждён",
            "topic": topic,
            "mastery": await _mastery_payload(db, student.id, topic["id"]),
            "primary_action": "Перейти к следующей теме",
        }
    elif stage == "route_complete":
        next_step = {
            "type": "route_complete",
            "title": "Первый маршрут пройден",
            "description": "Результаты сохранены. Следующий маршрут будет собран по новым данным.",
            "primary_action": "Посмотреть результат",
        }
    else:  # pragma: no cover - durable-state invariant
        raise HTTPException(status_code=500, detail=f"Неизвестный этап: {stage}")

    workspace: dict[str, Any] = {}
    if stage in _WORKSPACE_RENDER_STAGES:
        workspace = await _workspace_envelope(
            db,
            journey,
            projection=stage,
            problem=problem,
            topic=topic,
        )

    return {
        "journey_id": journey.id,
        "revision": journey.revision,
        "next_step": next_step,
        "context": context,
        **workspace,
    }


async def _existing_attempt(
    db,
    *,
    student_id: int,
    client_attempt_id: str,
    for_update: bool = False,
) -> JourneyAttempt | None:
    query = select(JourneyAttempt).where(
        JourneyAttempt.student_id == student_id,
        JourneyAttempt.client_attempt_id == client_attempt_id,
    )
    if for_update:
        query = query.execution_options(populate_existing=True).with_for_update()
    return (await db.execute(query)).scalar_one_or_none()


def _start_photo_processing(journey: StudentJourney, client_attempt_id: str) -> str:
    """Выдаёт конкретному provider-вызову уникальную lease."""

    lease_id = uuid4().hex
    activity = dict(journey.activity or {})
    _clear_typed_feedback(activity)
    activity["processing_client_attempt_id"] = client_attempt_id
    activity["processing_lease_id"] = lease_id
    journey.activity = activity
    return lease_id


def _clear_photo_processing(activity: dict[str, Any]) -> None:
    activity.pop("processing_client_attempt_id", None)
    activity.pop("processing_lease_id", None)


def _start_text_processing(
    journey: StudentJourney,
    client_attempt_id: str,
    *,
    kind: Literal["typed", "guided"],
) -> str:
    """Выдаёт typed/guided provider-вызову отдельную CAS-lease."""
    lease_id = uuid4().hex
    activity = dict(journey.activity or {})
    if kind == "typed":
        _clear_typed_feedback(activity)
    else:
        activity["guided_feedback"] = None
    activity[f"{kind}_processing_client_attempt_id"] = client_attempt_id
    activity[f"{kind}_processing_lease_id"] = lease_id
    journey.activity = activity
    return lease_id


def _clear_text_processing(
    activity: dict[str, Any],
    *,
    kind: Literal["typed", "guided"],
) -> None:
    activity.pop(f"{kind}_processing_client_attempt_id", None)
    activity.pop(f"{kind}_processing_lease_id", None)


def _start_typed_processing(journey: StudentJourney, client_attempt_id: str) -> str:
    return _start_text_processing(journey, client_attempt_id, kind="typed")


def _clear_typed_processing(activity: dict[str, Any]) -> None:
    _clear_text_processing(activity, kind="typed")


def _start_guided_processing(journey: StudentJourney, client_attempt_id: str) -> str:
    return _start_text_processing(journey, client_attempt_id, kind="guided")


def _clear_guided_processing(activity: dict[str, Any]) -> None:
    _clear_text_processing(activity, kind="guided")


async def _require_photo_lease(
    db,
    *,
    student,
    journey: StudentJourney,
    attempt: JourneyAttempt,
    expected_lease_id: str,
) -> None:
    """CAS-guard: устаревший provider-вызов не меняет новое состояние."""

    activity = dict(journey.activity or {})
    if (
        attempt.status != "processing"
        or activity.get("processing_client_attempt_id") != attempt.client_attempt_id
        or activity.get("processing_lease_id") != expected_lease_id
    ):
        await _state_conflict(
            db,
            student,
            journey,
            code="photo_invocation_superseded",
            message="Уже запущена более новая проверка фото.",
        )
    return None


async def _require_text_lease(
    db,
    *,
    student,
    journey: StudentJourney,
    attempt: JourneyAttempt,
    source_stage: str,
    source_problem_id: int,
    expected_lease_id: str,
    kind: Literal["typed", "guided"],
    source_step_n: int | None = None,
) -> None:
    """CAS-guard: старый typed/guided provider-вызов не меняет новый экран."""

    activity = dict(journey.activity or {})
    other_kind = "guided" if kind == "typed" else "typed"
    owns_expected_lease = (
        activity.get(f"{kind}_processing_client_attempt_id")
        == attempt.client_attempt_id
        and activity.get(f"{kind}_processing_lease_id") == expected_lease_id
    )
    step_is_current = (
        source_step_n is None
        or int(activity.get("guided_step", 0)) == source_step_n
    )
    if (
        attempt.status != "processing"
        or attempt.journey_id != journey.id
        or attempt.stage != source_stage
        or attempt.problem_id != source_problem_id
        or journey.stage != source_stage
        or journey.current_problem_id != source_problem_id
        or activity.get("processing_client_attempt_id")
        or activity.get(f"{other_kind}_processing_client_attempt_id")
        or activity.get(f"{kind}_processing_client_attempt_id")
        != attempt.client_attempt_id
        or activity.get(f"{kind}_processing_lease_id") != expected_lease_id
        or not step_is_current
    ):
        # Если lease уже выдана повторному вызову, поздний старый result не имеет
        # права помечать общий attempt superseded: новая lease всё ещё владелец.
        if attempt.status == "processing" and owns_expected_lease:
            attempt.status = "superseded"
            attempt.verdict = "superseded"
            attempt.counts_for_mastery = False
            await db.flush()
            attempt.response_payload = await _render(db, student, journey)
            await db.commit()
        await _state_conflict(
            db,
            student,
            journey,
            code=f"{kind}_invocation_superseded",
            message="Уже открыт более новый экран или запущена другая проверка.",
        )
    return None


async def _require_typed_lease(
    db,
    *,
    student,
    journey: StudentJourney,
    attempt: JourneyAttempt,
    source_stage: str,
    source_problem_id: int,
    expected_lease_id: str,
) -> None:
    await _require_text_lease(
        db,
        student=student,
        journey=journey,
        attempt=attempt,
        source_stage=source_stage,
        source_problem_id=source_problem_id,
        expected_lease_id=expected_lease_id,
        kind="typed",
    )


async def _require_guided_lease(
    db,
    *,
    student,
    journey: StudentJourney,
    attempt: JourneyAttempt,
    source_problem_id: int,
    source_step_n: int,
    expected_lease_id: str,
) -> None:
    await _require_text_lease(
        db,
        student=student,
        journey=journey,
        attempt=attempt,
        source_stage="guided_step",
        source_problem_id=source_problem_id,
        source_step_n=source_step_n,
        expected_lease_id=expected_lease_id,
        kind="guided",
    )


async def _record_mastery_evidence_once(
    db,
    *,
    student_id: int,
    attempt: JourneyAttempt,
    problem: Problem,
    is_correct: bool,
    source_stage: str,
    evidence_label: str,
    eligible: bool = True,
) -> dict[str, Any]:
    """Учитывает максимум одно evidence каждого исхода на задачу.

    Подсказанная практика завершает задачу, но не меняет mastery. Повторный
    одинаковый outcome на той же задаче также не меняет mastery.
    """

    if not eligible:
        return await _mastery_payload(db, student_id, problem.node_id)

    already_counted = (
        await db.execute(
            select(JourneyAttempt.id)
            .where(
                JourneyAttempt.student_id == student_id,
                JourneyAttempt.problem_id == problem.id,
                JourneyAttempt.verdict == ("correct" if is_correct else "incorrect"),
                JourneyAttempt.counts_for_mastery.is_(True),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if already_counted is not None:
        return await _mastery_payload(db, student_id, problem.node_id)

    mastery = await record_attempt(
        db,
        student_id=student_id,
        problem=problem,
        answer_given=evidence_label,
        is_correct=is_correct,
        source=(
            "journey_transfer"
            if source_stage == "transfer_task"
            else "journey_independent"
        ),
    )
    attempt.counts_for_mastery = True
    return _mastery_row_payload(mastery)


async def _typed_untrusted_history(
    db,
    *,
    journey_id: int,
    problem_id: int,
) -> list[dict[str, str]]:
    """Возвращает короткую history текущей задачи только для fenced prompt-блока."""

    attempts = list(
        (
            await db.execute(
                select(JourneyAttempt)
                .where(
                    JourneyAttempt.journey_id == journey_id,
                    JourneyAttempt.problem_id == problem_id,
                    JourneyAttempt.status.in_(("accepted", "provider_error")),
                )
                .order_by(JourneyAttempt.created_at.desc(), JourneyAttempt.id.desc())
                .limit(_MAX_TYPED_HISTORY_ENTRIES)
            )
        ).scalars()
    )
    history: list[dict[str, str]] = []
    for previous in reversed(attempts):
        item = {
            "kind": previous.kind,
            "verdict": previous.verdict or "unknown",
        }
        if previous.kind.endswith("_typed"):
            answer = _normalise_typed_text(
                previous.answer_given,
                max_chars=_MAX_TYPED_HISTORY_ANSWER_CHARS,
            )
            if answer is not None:
                item["student_answer"] = answer
        history.append(item)
    return history


def _typed_trusted_context(
    *,
    journey: StudentJourney,
    problem: Problem,
    topic: dict[str, Any],
    source_stage: str,
) -> dict[str, object]:
    """Строит bounded server-owned контекст без learner input и hidden UI leakage."""

    activity = dict(journey.activity or {})
    return {
        "journey": {"id": journey.id, "revision": journey.revision},
        "stage": source_stage,
        "topic": {"id": str(topic["id"]), "title": str(topic["title"])},
        "problem": {
            "id": problem.id,
            "content_idx": journey.current_decomp_idx,
            "node_id": problem.node_id,
        },
        "support": {
            "used": bool(activity.get("support_used", False)),
            "highest_hint_rung": 0,
        },
    }


async def _recover_stale_photo_processing(
    db,
    *,
    student_id: int,
    journey: StudentJourney,
) -> JourneyAttempt | None:
    """Переводит зависшую AI-проверку в повторную проверку сохранённого фото."""

    activity = dict(journey.activity or {})
    client_attempt_id = activity.get("processing_client_attempt_id")
    if not client_attempt_id:
        return None

    attempt = (
        await db.execute(
            select(JourneyAttempt).where(
                JourneyAttempt.journey_id == journey.id,
                JourneyAttempt.student_id == student_id,
                JourneyAttempt.client_attempt_id == str(client_attempt_id),
            )
        )
    ).scalar_one_or_none()
    if attempt is None:
        _clear_photo_processing(activity)
        journey.activity = activity
        journey.revision += 1
        return None
    if attempt.status != "processing":
        _clear_photo_processing(activity)
        journey.activity = activity
        journey.revision += 1
        return None

    updated_at = attempt.updated_at or attempt.created_at
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - updated_at < _PHOTO_PROCESSING_TIMEOUT:
        return None

    source_stage = attempt.stage
    if source_stage not in {"independent_task", "transfer_task"}:
        source_stage = (
            journey.stage
            if journey.stage in {"independent_task", "transfer_task"}
            else "independent_task"
        )
    _clear_photo_processing(activity)
    journey.activity = activity
    _set_stage(journey, "photo_recovery")
    journey.feedback = _recovery_feedback(
        reason="provider_error",
        filename=attempt.original_filename or "solution.jpg",
        return_stage=source_stage,
    )
    journey.revision += 1
    attempt.status = "provider_error"
    attempt.verdict = "provider_error"
    return attempt


async def _recover_stale_typed_processing(
    db,
    *,
    student_id: int,
    journey: StudentJourney,
) -> JourneyAttempt | None:
    """Закрывает зависшую typed-проверку безопасным retryable feedback."""

    activity = dict(journey.activity or {})
    client_attempt_id = activity.get("typed_processing_client_attempt_id")
    if not client_attempt_id:
        return None
    attempt = (
        await db.execute(
            select(JourneyAttempt).where(
                JourneyAttempt.journey_id == journey.id,
                JourneyAttempt.student_id == student_id,
                JourneyAttempt.client_attempt_id == str(client_attempt_id),
            )
        )
    ).scalar_one_or_none()
    if attempt is None or attempt.status != "processing":
        _clear_typed_processing(activity)
        journey.activity = activity
        return None
    updated_at = attempt.updated_at or attempt.created_at
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - updated_at < _TYPED_PROCESSING_TIMEOUT:
        return None

    _clear_typed_processing(activity)
    activity["typed_feedback"] = {
        "verdict": "unsure",
        "error_focus": "unknown",
        "reason": "provider_error",
        "answer": attempt.answer_given,
    }
    journey.activity = activity
    attempt.status = "provider_error"
    attempt.verdict = "provider_error"
    attempt.counts_for_mastery = False
    return attempt


async def _recover_stale_guided_processing(
    db,
    *,
    student_id: int,
    journey: StudentJourney,
) -> JourneyAttempt | None:
    """Закрывает зависшую guided-проверку, сохраняя ответ для повтора."""

    activity = dict(journey.activity or {})
    client_attempt_id = activity.get("guided_processing_client_attempt_id")
    if not client_attempt_id:
        return None
    attempt = (
        await db.execute(
            select(JourneyAttempt).where(
                JourneyAttempt.journey_id == journey.id,
                JourneyAttempt.student_id == student_id,
                JourneyAttempt.client_attempt_id == str(client_attempt_id),
            )
        )
    ).scalar_one_or_none()
    if attempt is None or attempt.status != "processing":
        _clear_guided_processing(activity)
        journey.activity = activity
        return None
    updated_at = attempt.updated_at or attempt.created_at
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - updated_at < _GUIDED_PROCESSING_TIMEOUT:
        return None

    _clear_guided_processing(activity)
    activity["guided_feedback"] = {
        "verdict": "unsure",
        "message": "AI временно не ответил. Твоя запись сохранена — попробуй ещё раз.",
        "answer": attempt.answer_given,
        "reason": "provider_error",
    }
    journey.activity = activity
    attempt.status = "provider_error"
    attempt.verdict = "provider_error"
    attempt.counts_for_mastery = False
    return attempt


async def _idempotent_payload_or_conflict(
    db,
    student,
    journey: StudentJourney,
    attempt: JourneyAttempt,
    *,
    payload_hash: str,
) -> dict[str, Any]:
    if attempt.payload_hash != payload_hash:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "idempotency_conflict",
                "message": "Этот идентификатор уже использован для другого действия.",
            },
        )
    response = dict(attempt.response_payload) if attempt.response_payload is not None else None
    response_revision = response.get("revision") if response is not None else None
    response_journey_id = response.get("journey_id") if response is not None else None
    same_journey = attempt.journey_id == journey.id

    if attempt.status == "processing":
        activity = dict(journey.activity or {})
        if (
            not same_journey
            or activity.get("processing_client_attempt_id") != attempt.client_attempt_id
        ):
            await _state_conflict(
                db,
                student,
                journey,
                code="stale_revision",
                message="Этот ответ относится к более раннему экрану.",
            )
        raise HTTPException(
            status_code=409,
            detail={"code": "photo_processing", "message": "Фото ещё проверяется."},
        )
    if (
        not same_journey
        or response is None
        or response_journey_id != journey.id
        or response_revision != journey.revision
    ):
        await _state_conflict(
            db,
            student,
            journey,
            code="stale_revision",
            message="Этот ответ относится к более раннему экрану.",
        )
    if attempt.status == "provider_error":
        raise HTTPException(
            status_code=503,
            detail={
                "code": "ai_unavailable",
                "message": "Проверка фото временно недоступна. Снимок сохранён.",
                "state": response,
            },
        )
    return response


async def _typed_idempotent_payload_or_conflict(
    db,
    student,
    journey: StudentJourney,
    attempt: JourneyAttempt,
    *,
    payload_hash: str,
) -> dict[str, Any]:
    """Идемпотентность typed-ответа с terminal-state и retry semantics."""

    if attempt.payload_hash != payload_hash:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "idempotency_conflict",
                "message": "Этот идентификатор уже использован для другого действия.",
            },
        )
    response = dict(attempt.response_payload) if attempt.response_payload is not None else None
    same_journey = attempt.journey_id == journey.id
    response_is_current = (
        response is not None
        and response.get("journey_id") == journey.id
        and response.get("revision") == journey.revision
    )
    activity = dict(journey.activity or {})
    if attempt.status == "processing":
        if (
            same_journey
            and activity.get("typed_processing_client_attempt_id")
            == attempt.client_attempt_id
        ):
            await _state_conflict(
                db,
                student,
                journey,
                code="typed_processing",
                message="Ответ ещё проверяется.",
            )
        await _state_conflict(
            db,
            student,
            journey,
            code="typed_invocation_superseded",
            message="Этот ответ относится к более раннему экрану.",
        )
    if attempt.status == "superseded":
        await _state_conflict(
            db,
            student,
            journey,
            code="typed_invocation_superseded",
            message="Этот ответ относится к более раннему экрану.",
        )
    if not same_journey or not response_is_current:
        await _state_conflict(
            db,
            student,
            journey,
            code="stale_revision",
            message="Этот ответ относится к более раннему экрану.",
        )
    if attempt.status == "provider_error":
        raise HTTPException(
            status_code=503,
            detail={
                "code": "ai_unavailable",
                "message": "Проверка ответа временно недоступна.",
                "state": response,
            },
        )
    if attempt.status != "accepted":
        await _state_conflict(
            db,
            student,
            journey,
            code="typed_invocation_superseded",
            message="Этот ответ больше не может быть применён.",
        )
    return response


async def _guided_idempotent_payload_or_conflict(
    db,
    student,
    journey: StudentJourney,
    attempt: JourneyAttempt,
    *,
    payload_hash: str,
) -> dict[str, Any]:
    """Идемпотентность guided-ответа с retry после provider error."""

    if attempt.payload_hash != payload_hash:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "idempotency_conflict",
                "message": "Этот идентификатор уже использован для другого действия.",
            },
        )
    response = dict(attempt.response_payload) if attempt.response_payload is not None else None
    same_journey = attempt.journey_id == journey.id
    response_is_current = (
        response is not None
        and response.get("journey_id") == journey.id
        and response.get("revision") == journey.revision
    )
    activity = dict(journey.activity or {})
    if attempt.status == "processing":
        if (
            same_journey
            and activity.get("guided_processing_client_attempt_id")
            == attempt.client_attempt_id
        ):
            await _state_conflict(
                db,
                student,
                journey,
                code="guided_processing",
                message="Шаг ещё проверяется.",
            )
        await _state_conflict(
            db,
            student,
            journey,
            code="guided_invocation_superseded",
            message="Этот ответ относится к более раннему шагу.",
        )
    if attempt.status == "superseded":
        await _state_conflict(
            db,
            student,
            journey,
            code="guided_invocation_superseded",
            message="Этот ответ относится к более раннему шагу.",
        )
    if not same_journey or not response_is_current:
        await _state_conflict(
            db,
            student,
            journey,
            code="stale_revision",
            message="Этот ответ относится к более раннему шагу.",
        )
    if attempt.status == "provider_error":
        raise HTTPException(
            status_code=503,
            detail={
                "code": "ai_unavailable",
                "message": "Проверка шага временно недоступна.",
                "state": response,
            },
        )
    if attempt.status != "accepted":
        await _state_conflict(
            db,
            student,
            journey,
            code="guided_invocation_superseded",
            message="Этот ответ больше не может быть применён.",
        )
    return response


@router.get("/current")
async def get_current_journey(request: Request) -> dict[str, Any]:
    db, student = await _get_current_student(request)
    try:
        journey = await _journey_for_student(
            db,
            student_id=student.id,
            for_update=True,
        )
        recovered_attempt = await _recover_stale_photo_processing(
            db,
            student_id=student.id,
            journey=journey,
        )
        recovered_typed_attempt = await _recover_stale_typed_processing(
            db,
            student_id=student.id,
            journey=journey,
        )
        recovered_guided_attempt = await _recover_stale_guided_processing(
            db,
            student_id=student.id,
            journey=journey,
        )
        response = await _render(db, student, journey)
        if recovered_attempt is not None:
            recovered_attempt.response_payload = response
        if recovered_typed_attempt is not None:
            recovered_typed_attempt.response_payload = response
        if recovered_guided_attempt is not None:
            recovered_guided_attempt.response_payload = response
        await db.commit()
        return response
    finally:
        await db.close()


@router.post("/profile/draft")
async def post_profile_draft(
    request: Request,
    body: ProfileDraftBody,
) -> dict[str, Any]:
    db, student = await _get_current_student(request)
    try:
        journey = await _journey_for_student(
            db,
            student_id=student.id,
            for_update=True,
        )
        await _ensure_not_processing(db, student, journey)
        await _require_revision(db, student, journey, body.revision)
        if journey.stage != "profile":
            raise HTTPException(status_code=409, detail="Профиль уже настроен")
        journey.profile_data = {
            **_profile_payload(body),
            "onboarding_screen": body.screen,
            "onboarding_substep": body.substep if body.screen == 1 else 0,
        }
        journey.revision += 1
        await db.flush()
        response = await _render(db, student, journey)
        await db.commit()
        return response
    finally:
        await db.close()


@router.post("/profile")
async def post_profile(request: Request, body: ProfileBody) -> dict[str, Any]:
    db, student = await _get_current_student(request)
    try:
        journey = await _journey_for_student(
            db,
            student_id=student.id,
            for_update=True,
        )
        await _ensure_not_processing(db, student, journey)
        await _require_revision(db, student, journey, body.revision)
        if journey.stage != "profile":
            raise HTTPException(status_code=409, detail="Профиль уже настроен")
        journey.profile_data = _profile_payload(body)
        _set_stage(journey, "exam_map")
        journey.revision += 1
        await db.flush()
        response = await _render(db, student, journey)
        await db.commit()
        return response
    finally:
        await db.close()


async def _set_current_topic(db, journey: StudentJourney) -> None:
    topic = _route_topic(journey)
    journey.current_topic_id = str(topic["id"])
    journey.current_problem_id = None
    journey.current_decomp_idx = None


async def _set_problem(
    db,
    journey: StudentJourney,
    *,
    content_idx: int,
    mode: str,
) -> Problem:
    problem = await _problem_by_content_idx(db, content_idx)
    decomposition = await db.get(DecompositionProblem, content_idx)
    if decomposition is None or not decomposition.all_steps_verified:
        raise HTTPException(status_code=503, detail="Разбор задачи ещё не проверен")
    steps = await _steps_for_problem(db, problem)
    if not steps or any(
        not is_step_reference_supported(step.expected_value) for step in steps
    ):
        raise HTTPException(
            status_code=503,
            detail={
                "code": "solution_reference_unsupported",
                "message": "Для задачи ещё не готов надёжный разбор.",
            },
        )
    journey.current_problem_id = problem.id
    journey.current_decomp_idx = content_idx
    journey.activity = {
        "mode": mode,
        "guided_step": 1,
        "support_used": mode == "guided",
    }
    return problem


def _next_transfer_content_idx(
    journey: StudentJourney,
    blueprint: dict[str, Any],
) -> int:
    sequence = [
        int(blueprint["transfer_content_idx"]),
        *(int(value) for value in blueprint.get("reinforcement_content_indices") or []),
    ]
    if not sequence:  # pragma: no cover - product contract invariant
        raise HTTPException(status_code=503, detail="Задачи переноса ещё не загружены")
    current = journey.current_decomp_idx
    if current not in sequence:
        return sequence[0]
    return sequence[(sequence.index(current) + 1) % len(sequence)]


@router.post("/continue")
async def post_continue(request: Request, body: ContinueBody) -> dict[str, Any]:
    db, student = await _get_current_student(request)
    try:
        journey = await _journey_for_student(
            db,
            student_id=student.id,
            for_update=True,
        )
        await _ensure_not_processing(db, student, journey)
        await _require_revision(db, student, journey, body.revision)

        transition = (journey.stage, body.action)
        if transition == ("exam_map", "open_diagnostic_intro"):
            _set_stage(journey, "diagnostic_intro")
        elif transition == ("diagnostic_intro", "start_diagnostic"):
            journey.diagnostic = initial_diagnostic(dict(journey.profile_data or {}))
            _set_stage(journey, "diagnostic_question")
        elif transition == ("diagnostic_result", "show_route"):
            _set_stage(journey, "route_ready")
        elif transition == ("route_ready", "start_lesson"):
            await _set_current_topic(db, journey)
            _set_stage(journey, "lesson_intro")
        elif transition == ("lesson_intro", "start_task"):
            blueprint = topic_blueprint(_route_topic(journey)["id"])
            await _set_problem(
                db,
                journey,
                content_idx=int(blueprint["target_content_idx"]),
                mode="independent",
            )
            _set_stage(journey, "independent_task")
        elif journey.stage == "photo_recovery" and body.action == "retry_photo":
            feedback = dict(journey.feedback or {})
            if feedback.get("reason") == "provider_error":
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "saved_photo_retry_required",
                        "message": "Повторите проверку уже сохранённого фото.",
                    },
                )
            return_stage = feedback.get("return_stage")
            if return_stage not in {"independent_task", "transfer_task"}:
                raise HTTPException(status_code=409, detail="Нельзя повторить это фото")
            _set_stage(journey, return_stage)
            journey.feedback = {}
        elif journey.stage == "photo_feedback" and body.action in {
            "start_transfer",
            "continue_transfer",
        }:
            if dict(journey.feedback or {}).get("verdict") != "correct":
                raise HTTPException(status_code=409, detail="Сначала исправьте решение")
            blueprint = topic_blueprint(_route_topic(journey)["id"])
            await _set_problem(
                db,
                journey,
                content_idx=int(blueprint["transfer_content_idx"]),
                mode="transfer",
            )
            _set_stage(journey, "transfer_task")
            journey.feedback = {}
        elif journey.stage == "photo_feedback" and body.action == "retry_task":
            if dict(journey.feedback or {}).get("verdict") != "incorrect":
                raise HTTPException(status_code=409, detail="Верное решение нельзя повторять")
            _set_stage(journey, "independent_task")
            journey.feedback = {}
        elif journey.stage == "photo_feedback" and body.action == "review_with_help":
            if dict(journey.feedback or {}).get("verdict") != "incorrect":
                raise HTTPException(status_code=409, detail="Разбор для этого решения не нужен")
            problem = await _current_problem(db, journey)
            steps = await _steps_for_problem(db, problem)
            if not steps:
                raise HTTPException(status_code=503, detail="Разбор задачи ещё не загружен")
            _set_stage(journey, "guided_step")
            journey.feedback = {}
            journey.activity = {
                "mode": "guided",
                "guided_step": 1,
                "support_used": True,
                "guided_feedback": None,
            }
        elif journey.stage == "transfer_feedback" and body.action == "retry_task":
            if dict(journey.feedback or {}).get("verdict") != "incorrect":
                raise HTTPException(status_code=409, detail="Верное решение нельзя повторять")
            _set_stage(journey, "transfer_task")
            journey.feedback = {}
        elif journey.stage == "transfer_feedback" and body.action == "continue_transfer":
            feedback = dict(journey.feedback or {})
            mastery = dict(feedback.get("mastery") or {})
            if feedback.get("verdict") != "correct" or mastery.get("reached") is not False:
                raise HTTPException(status_code=409, detail="Дополнительная задача не нужна")
            blueprint = topic_blueprint(_route_topic(journey)["id"])
            await _set_problem(
                db,
                journey,
                content_idx=_next_transfer_content_idx(journey, blueprint),
                mode="transfer",
            )
            _set_stage(journey, "transfer_task")
            journey.feedback = {}
        elif journey.stage == "transfer_feedback" and body.action == "finish_topic":
            if dict(journey.feedback or {}).get("verdict") != "correct":
                raise HTTPException(status_code=409, detail="Перенос ещё не подтверждён")
            mastery = await db.get(Mastery, (student.id, journey.current_topic_id))
            if mastery is None or not is_mastered(mastery):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "mastery_not_reached",
                        "message": "Нужно подтвердить навык ещё одной самостоятельной задачей.",
                    },
                )
            _set_stage(journey, "topic_result")
        elif journey.stage == "topic_result" and body.action == "next_lesson":
            route = dict(journey.route or {})
            topics = [dict(topic) for topic in route.get("topics") or []]
            index = int(route.get("index", 0))
            if index < len(topics):
                topics[index]["status"] = "completed"
            completed = list(route.get("completed") or [])
            if journey.current_topic_id and journey.current_topic_id not in completed:
                completed.append(journey.current_topic_id)
            index += 1
            if index >= len(topics):
                _set_stage(journey, "route_complete")
                journey.completed_at = datetime.now(timezone.utc)
            else:
                topics[index]["status"] = "next"
                journey.route = {
                    **route,
                    "topics": topics,
                    "index": index,
                    "completed": completed,
                }
                await _set_current_topic(db, journey)
                _set_stage(journey, "lesson_intro")
            if index >= len(topics):
                journey.route = {
                    **route,
                    "topics": topics,
                    "index": index,
                    "completed": completed,
                }
        else:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "invalid_transition",
                    "message": "Это действие недоступно на текущем экране.",
                },
            )

        journey.revision += 1
        await db.flush()
        response = await _render(db, student, journey)
        await db.commit()
        return response
    finally:
        await db.close()


async def _seed_diagnostic_mastery(db, student_id: int, diagnostic: dict[str, Any]) -> None:
    for node_id, blueprint in TOPIC_BLUEPRINTS.items():
        anchor = int(blueprint["diagnostic_anchor"])
        initial_p = diagnostic_mastery_prior(diagnostic, anchor)
        await db.execute(
            pg_insert(Mastery)
            .values(
                student_id=student_id,
                node_id=node_id,
                p_mastery=initial_p,
                attempts_total=0,
                attempts_correct=0,
            )
            .on_conflict_do_nothing(index_elements=["student_id", "node_id"])
        )


@router.post("/diagnostic/answer")
async def post_diagnostic_answer(
    request: Request,
    body: DiagnosticAnswerBody,
) -> dict[str, Any]:
    db, student = await _get_current_student(request)
    payload_hash = _hash_parts(str(body.question_id), body.answer.strip())
    try:
        journey = await _journey_for_student(
            db,
            student_id=student.id,
            for_update=True,
        )
        existing = await _existing_attempt(
            db,
            student_id=student.id,
            client_attempt_id=body.client_attempt_id,
            for_update=True,
        )
        if existing is not None:
            return await _idempotent_payload_or_conflict(
                db,
                student,
                journey,
                existing,
                payload_hash=payload_hash,
            )
        await _ensure_not_processing(db, student, journey)
        await _require_revision(db, student, journey, body.revision)
        if journey.stage != "diagnostic_question":
            raise HTTPException(status_code=409, detail="Диагностика сейчас не активна")

        diagnostic = dict(journey.diagnostic or {})
        queue = list(diagnostic.get("queue") or [])
        position = int(diagnostic.get("position", 0))
        if position >= len(queue) or int(queue[position]) != body.question_id:
            await _state_conflict(
                db,
                student,
                journey,
                code="question_mismatch",
                message="Открыт другой вопрос.",
            )
        problem = await _problem_by_content_idx(db, body.question_id)
        correct = check_answer(body.answer, problem.answer, problem.answer_type)
        answers = [dict(answer) for answer in diagnostic.get("answers") or []]
        answers.append(
            {
                "question_id": body.question_id,
                "node_id": problem.node_id,
                "correct": correct,
            }
        )
        if not correct and body.question_id in DIAGNOSTIC_EASIER:
            easier = DIAGNOSTIC_EASIER[body.question_id]
            if easier not in queue and all(
                int(answer["question_id"]) != easier for answer in answers
            ):
                queue.insert(position + 1, easier)
        position += 1
        completed = position >= len(queue)
        journey.diagnostic = {
            "queue": queue,
            "position": position,
            "answers": answers,
            "completed": completed,
        }
        previous_stage = journey.stage
        if completed:
            journey.route = build_route(journey.diagnostic)
            _set_stage(journey, "diagnostic_result")
            student.diagnostic_complete = True
            await _seed_diagnostic_mastery(db, student.id, journey.diagnostic)
        journey.revision += 1

        attempt = JourneyAttempt(
            journey_id=journey.id,
            student_id=student.id,
            client_attempt_id=body.client_attempt_id,
            kind="diagnostic",
            stage=previous_stage,
            topic_id=problem.node_id,
            problem_id=problem.id,
            payload_hash=payload_hash,
            answer_given=body.answer.strip(),
            status="accepted",
            verdict="correct" if correct else "incorrect",
            counts_for_mastery=False,
        )
        db.add(attempt)
        await db.flush()
        response = await _render(db, student, journey)
        attempt.response_payload = response
        await db.commit()
        return response
    finally:
        await db.close()


@router.post("/help")
async def post_help(request: Request, body: HelpBody) -> dict[str, Any]:
    db, student = await _get_current_student(request)
    try:
        journey = await _journey_for_student(
            db,
            student_id=student.id,
            for_update=True,
        )
        await _ensure_not_processing(db, student, journey)
        await _require_revision(db, student, journey, body.revision)
        if journey.stage != "independent_task" or journey.current_problem_id != body.problem_id:
            await _state_conflict(
                db,
                student,
                journey,
                code="problem_mismatch",
                message="Разбор недоступен для этой задачи.",
            )
        problem = await _current_problem(db, journey)
        steps = await _steps_for_problem(db, problem)
        if not steps:
            raise HTTPException(status_code=503, detail="Разбор задачи ещё не загружен")
        _set_stage(journey, "guided_step")
        journey.activity = {
            "mode": "guided",
            "guided_step": 1,
            "support_used": True,
            "guided_feedback": None,
        }
        journey.revision += 1
        await db.flush()
        response = await _render(db, student, journey)
        await db.commit()
        return response
    finally:
        await db.close()


def _normalise_guided_result(
    result: GuidedAnswerResult,
    *,
    answer: str,
    protected_values: list[object],
) -> tuple[str, str]:
    """Повторно валидирует AI-verdict и не выпускает готовый ответ в feedback."""

    confidence = _typed_confidence(result.confidence)
    answer_echo = _normalise_typed_answer(result.answer_echo)
    feedback = _normalise_typed_text(result.feedback, max_chars=500)
    structurally_valid = (
        result.verdict in _TYPED_ANSWER_VERDICTS
        and confidence is not None
        and result.evidence_verified
        and answer_echo == answer
    )
    if not structurally_valid:
        return "unsure", "AI не смог надёжно проверить этот шаг. Попробуй записать действие иначе."
    if (
        result.verdict in {"correct", "incorrect"}
        and confidence < _TYPED_ANSWER_CONFIDENCE_THRESHOLD
    ):
        return "unsure", "AI не уверен в проверке. Уточни запись текущего действия."

    verdict = result.verdict
    safe_feedback = feedback
    if safe_feedback and feedback_contains_protected_value(
        safe_feedback,
        protected_values,
    ):
        safe_feedback = None
    if verdict == "correct":
        return verdict, safe_feedback or "Да, этот переход работает."
    if verdict == "incorrect":
        return verdict, safe_feedback or "Проверь действие в этом шаге и попробуй ещё раз."
    return verdict, safe_feedback or "AI не уверен в проверке. Уточни запись текущего действия."


async def _apply_guided_result(
    db,
    *,
    student,
    journey: StudentJourney,
    attempt: JourneyAttempt,
    problem: Problem,
    steps: list[ProblemStep],
    result: GuidedAnswerResult,
    source_step_n: int,
    answer: str,
    expected_lease_id: str,
) -> dict[str, Any]:
    """Применяет только AI-verdict активного шага; mastery не меняется."""

    await _require_guided_lease(
        db,
        student=student,
        journey=journey,
        attempt=attempt,
        source_problem_id=problem.id,
        source_step_n=source_step_n,
        expected_lease_id=expected_lease_id,
    )
    current_step = next((item for item in steps if item.n == source_step_n), None)
    if current_step is None:  # pragma: no cover - content invariant
        raise RuntimeError("Активный guided-шаг потерян")
    protected_values = [problem.answer]
    protected_values.extend(
        item.expected_value for item in steps if item.n >= source_step_n
    )
    verdict, message = _normalise_guided_result(
        result,
        answer=answer,
        protected_values=protected_values,
    )
    activity = dict(journey.activity or {})
    _clear_guided_processing(activity)
    attempt.status = "accepted"
    attempt.verdict = verdict
    confidence = _typed_confidence(result.confidence)
    attempt.confidence = confidence if confidence is not None else 0.0
    attempt.provider = result.provider
    attempt.model = result.model
    attempt.counts_for_mastery = False

    if verdict == "correct":
        next_step = next((item for item in steps if item.n > source_step_n), None)
        if next_step is not None:
            activity["guided_step"] = next_step.n
            activity["guided_feedback"] = {
                "verdict": "correct",
                "message": message,
                "answer": answer,
                "completed_step_n": source_step_n,
            }
            journey.activity = activity
        else:
            blueprint = topic_blueprint(_route_topic(journey)["id"])
            await _set_problem(
                db,
                journey,
                content_idx=int(blueprint["transfer_content_idx"]),
                mode="transfer",
            )
            _set_stage(journey, "transfer_task")
    else:
        activity["guided_feedback"] = {
            "verdict": verdict,
            "message": message,
            "answer": answer,
            "completed_step_n": source_step_n,
        }
        journey.activity = activity

    journey.revision += 1
    await db.flush()
    response = await _render(db, student, journey)
    attempt.response_payload = response
    await db.commit()
    return response


async def _mark_guided_provider_error(
    db,
    *,
    student,
    journey: StudentJourney,
    attempt: JourneyAttempt,
    source_problem_id: int,
    source_step_n: int,
    expected_lease_id: str,
) -> dict[str, Any]:
    await _require_guided_lease(
        db,
        student=student,
        journey=journey,
        attempt=attempt,
        source_problem_id=source_problem_id,
        source_step_n=source_step_n,
        expected_lease_id=expected_lease_id,
    )
    activity = dict(journey.activity or {})
    _clear_guided_processing(activity)
    activity["guided_feedback"] = {
        "verdict": "unsure",
        "message": "AI временно не ответил. Твоя запись сохранена — попробуй ещё раз.",
        "answer": attempt.answer_given,
        "completed_step_n": source_step_n,
        "reason": "provider_error",
    }
    journey.activity = activity
    attempt.status = "provider_error"
    attempt.verdict = "provider_error"
    attempt.counts_for_mastery = False
    await db.flush()
    state = await _render(db, student, journey)
    attempt.response_payload = state
    await db.commit()
    return state


def _guided_completion_finished(
    task: asyncio.Task[tuple[_GuidedCompletionStatus, dict[str, Any]]],
) -> None:
    _GUIDED_COMPLETION_TASKS.discard(task)
    if task.cancelled():
        logger.warning("Фоновая guided-проверка отменена до durable результата")
        return
    error = task.exception()
    if error is not None:
        logger.error(
            "Фоновая guided-проверка завершилась с ошибкой",
            exc_info=(type(error), error, error.__traceback__),
        )


async def _complete_guided_attempt(
    *,
    student_id: int,
    client_attempt_id: str,
    source_problem_id: int,
    source_step_n: int,
    answer: str,
    expected_lease_id: str,
    statement: str,
    step_instruction: str,
    expected_value: str,
) -> tuple[_GuidedCompletionStatus, dict[str, Any]]:
    """Доводит AI-проверку шага до durable состояния независимо от HTTP."""

    provider_unavailable = False
    result: GuidedAnswerResult | None = None
    try:
        result = await evaluate_guided_answer(
            statement=statement,
            step_number=source_step_n,
            step_instruction=step_instruction,
            expected_value=expected_value,
            submitted_answer=answer,
        )
    except LlmUnavailable:
        provider_unavailable = True

    async with db_base.async_session() as db:
        student = await db.get(Student, student_id)
        if student is None:  # pragma: no cover - FK/auth invariant
            raise RuntimeError("Ученик guided-попытки потерян")
        journey = await _journey_for_student(
            db,
            student_id=student_id,
            for_update=True,
        )
        attempt = await _existing_attempt(
            db,
            student_id=student_id,
            client_attempt_id=client_attempt_id,
            for_update=True,
        )
        if attempt is None:  # pragma: no cover - DB invariant
            raise RuntimeError("Guided-попытка потеряна")
        problem = await db.get(Problem, source_problem_id)
        if problem is None:  # pragma: no cover - FK/content invariant
            raise RuntimeError("Задача guided-попытки потеряна")
        steps = await _steps_for_problem(db, problem)

        if provider_unavailable:
            state = await _mark_guided_provider_error(
                db,
                student=student,
                journey=journey,
                attempt=attempt,
                source_problem_id=source_problem_id,
                source_step_n=source_step_n,
                expected_lease_id=expected_lease_id,
            )
            return "provider_error", state
        if result is None:  # pragma: no cover - control-flow invariant
            raise RuntimeError("AI не вернул guided-результат")
        state = await _apply_guided_result(
            db,
            student=student,
            journey=journey,
            attempt=attempt,
            problem=problem,
            steps=steps,
            result=result,
            source_step_n=source_step_n,
            answer=answer,
            expected_lease_id=expected_lease_id,
        )
        return "accepted", state


@router.post("/guided/answer")
@limiter.limit("20/minute")
@ai_ip_limit
async def post_guided_answer(
    request: Request,
    body: GuidedAnswerBody,
) -> dict[str, Any]:
    """Проверяет один guided-шаг только через AI и атомарно двигает маршрут."""

    db, student = await _get_current_student(request)
    try:
        answer = _normalise_typed_answer(body.answer)
        if answer is None:
            raise HTTPException(
                status_code=422,
                detail="Ответ должен содержать от 1 до 500 безопасных символов.",
            )
        payload_hash = _hash_parts(str(body.problem_id), str(body.step_n), answer)
        journey = await _journey_for_student(
            db,
            student_id=student.id,
            for_update=True,
        )
        recovered_attempt = await _recover_stale_guided_processing(
            db,
            student_id=student.id,
            journey=journey,
        )
        if recovered_attempt is not None:
            await db.flush()
            recovered_attempt.response_payload = await _render(db, student, journey)
            await db.commit()
            journey = await _journey_for_student(
                db,
                student_id=student.id,
                for_update=True,
            )
        existing = await _existing_attempt(
            db,
            student_id=student.id,
            client_attempt_id=body.client_attempt_id,
            for_update=True,
        )
        retrying_provider_error = existing is not None and existing.status == "provider_error"
        if existing is not None and not retrying_provider_error:
            return await _guided_idempotent_payload_or_conflict(
                db,
                student,
                journey,
                existing,
                payload_hash=payload_hash,
            )
        if retrying_provider_error:
            if (
                existing.payload_hash != payload_hash
                or existing.answer_given != answer
                or existing.problem_id != body.problem_id
                or existing.step_n != body.step_n
            ):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "idempotency_conflict",
                        "message": "Этот идентификатор уже использован для другого действия.",
                    },
                )

        activity = dict(journey.activity or {})
        if activity.get("processing_client_attempt_id"):
            await _state_conflict(
                db,
                student,
                journey,
                code="photo_processing",
                message="Предыдущее фото ещё проверяется.",
            )
        if activity.get("typed_processing_client_attempt_id"):
            await _state_conflict(
                db,
                student,
                journey,
                code="typed_processing",
                message="Предыдущий ответ ещё проверяется.",
            )
        if activity.get("guided_processing_client_attempt_id"):
            await _state_conflict(
                db,
                student,
                journey,
                code="guided_processing",
                message="Предыдущий шаг ещё проверяется.",
            )
        await _require_revision(db, student, journey, body.revision)
        if journey.stage != "guided_step" or journey.current_problem_id != body.problem_id:
            await _state_conflict(
                db,
                student,
                journey,
                code="problem_mismatch",
                message="Сейчас открыта другая задача.",
            )
        if int(activity.get("guided_step", 1)) != body.step_n:
            await _state_conflict(
                db,
                student,
                journey,
                code="step_mismatch",
                message="Сейчас открыт другой шаг.",
            )
        if retrying_provider_error and (
            existing.journey_id != journey.id
            or existing.stage != journey.stage
            or existing.problem_id != journey.current_problem_id
            or existing.step_n != body.step_n
        ):
            await _state_conflict(
                db,
                student,
                journey,
                code="stale_revision",
                message="Этот ответ относится к более раннему шагу.",
            )

        problem = await _current_problem(db, journey)
        steps = await _steps_for_problem(db, problem)
        step = next((item for item in steps if item.n == body.step_n), None)
        if step is None:
            raise HTTPException(status_code=409, detail="Шаг не найден")
        lease_id = _start_guided_processing(journey, body.client_attempt_id)
        if retrying_provider_error:
            attempt = existing
            attempt.status = "processing"
            attempt.verdict = None
            attempt.confidence = None
            attempt.provider = None
            attempt.model = None
            attempt.counts_for_mastery = False
            attempt.response_payload = None
        else:
            attempt = JourneyAttempt(
                journey_id=journey.id,
                student_id=student.id,
                client_attempt_id=body.client_attempt_id,
                kind="guided",
                stage="guided_step",
                topic_id=journey.current_topic_id,
                problem_id=problem.id,
                step_n=body.step_n,
                payload_hash=payload_hash,
                answer_given=answer,
                status="processing",
                counts_for_mastery=False,
            )
            db.add(attempt)
        await db.commit()

        completion = asyncio.create_task(
            _complete_guided_attempt(
                student_id=student.id,
                client_attempt_id=body.client_attempt_id,
                source_problem_id=problem.id,
                source_step_n=body.step_n,
                answer=answer,
                expected_lease_id=lease_id,
                statement=problem.text_ru,
                step_instruction=step.instruction_ru,
                expected_value=step.expected_value,
            ),
            name=f"guided-completion-{student.id}-{body.client_attempt_id}",
        )
        _GUIDED_COMPLETION_TASKS.add(completion)
        completion.add_done_callback(_guided_completion_finished)
        completion_status, state = await asyncio.shield(completion)
        if completion_status == "provider_error":
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "ai_unavailable",
                    "message": "Проверка шага временно недоступна.",
                    "state": state,
                },
            )
        return state
    finally:
        await db.close()


def _valid_image(image_bytes: bytes, content_type: str) -> bool:
    from PIL import Image  # noqa: PLC0415

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            if content_type in {"image/heic", "image/heif"}:
                import pillow_heif  # noqa: PLC0415

                pillow_heif.register_heif_opener()

            with Image.open(io.BytesIO(image_bytes)) as image:
                actual_format = (image.format or "").upper()
                if image.width * image.height > _MAX_PHOTO_PIXELS:
                    return False
                image.verify()
        return actual_format in _EXPECTED_FORMATS[content_type]
    except (
        ImportError,
        KeyError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        return False


def _normalise_photo_verdict(result, valid_step_numbers: set[int]) -> tuple[str, int | None]:
    verdict = result.verdict
    failed_step = result.failed_step
    if verdict in {"correct", "incorrect"} and not result.evidence_verified:
        return "unsure", None
    if verdict in {"correct", "incorrect"} and result.confidence < _PHOTO_CONFIDENCE_THRESHOLD:
        return "unsure", None
    if verdict == "incorrect" and failed_step not in valid_step_numbers:
        return "unsure", None
    if verdict not in {"correct", "incorrect", "unreadable", "wrong_photo", "unsure"}:
        return "unsure", None
    return verdict, failed_step if verdict == "incorrect" else None


def _recovery_feedback(
    *,
    reason: str,
    filename: str,
    return_stage: str,
) -> dict[str, Any]:
    messages = {
        "unreadable": "Часть решения не читается. Снимите страницу ровно и при хорошем свете.",
        "wrong_photo": "На снимке не видно решения этой задачи.",
        "unsure": "Не удалось надёжно проверить решение. Попробуйте снять страницу целиком.",
        "provider_error": "Проверка временно недоступна. Фото сохранено — переснимать его не нужно.",
    }
    return {
        "reason": reason,
        "message": messages[reason],
        "preserved_photo": {"name": filename},
        "return_stage": return_stage,
        "primary_action": "Повторить проверку" if reason == "provider_error" else "Переснять фото",
    }


def _canonical_photo_steps(steps: list[ProblemStep]) -> list[dict[str, Any]]:
    return [
        {
            "n": step.n,
            "instruction_ru": step.instruction_ru,
            "expected_value": step.expected_value,
        }
        for step in steps
    ]


async def _apply_photo_result(
    db,
    *,
    student,
    journey: StudentJourney,
    attempt: JourneyAttempt,
    problem: Problem,
    steps: list[ProblemStep],
    result,
    source_stage: str,
    original_filename: str,
    expected_lease_id: str,
) -> dict[str, Any]:
    await _require_photo_lease(
        db,
        student=student,
        journey=journey,
        attempt=attempt,
        expected_lease_id=expected_lease_id,
    )
    activity = dict(journey.activity or {})
    _clear_photo_processing(activity)
    journey.activity = activity

    verdict, failed_step = _normalise_photo_verdict(
        result,
        {step.n for step in steps},
    )
    attempt.status = "accepted"
    attempt.verdict = verdict
    attempt.confidence = result.confidence
    attempt.provider = result.provider
    attempt.model = result.model

    if verdict in {"unreadable", "wrong_photo", "unsure"}:
        _set_stage(journey, "photo_recovery")
        journey.feedback = _recovery_feedback(
            reason=verdict,
            filename=original_filename,
            return_stage=source_stage,
        )
    elif verdict == "incorrect":
        failed = next(step for step in steps if step.n == failed_step)
        confirmed_steps = [
            {"number": step.n, "label": step.instruction_ru}
            for step in steps
            if step.n < failed.n
        ]
        mastery = await _record_mastery_evidence_once(
            db,
            student_id=student.id,
            attempt=attempt,
            problem=problem,
            is_correct=False,
            source_stage=source_stage,
            evidence_label="[whole-photo verified incorrect]",
        )
        _set_stage(
            journey,
            "transfer_feedback" if source_stage == "transfer_task" else "photo_feedback",
        )
        journey.feedback = {
            "verdict": "incorrect",
            "failed_step": failed.n,
            "confirmed_steps": confirmed_steps,
            "correction": failed.instruction_ru,
            "message": (
                "До этого шага ход решения совпадает. Пересчитай только этот переход, "
                "а затем снова отправь решение целиком."
                if confirmed_steps
                else "Первое расхождение уже в начале решения. Пересчитай этот переход, "
                "а затем снова отправь решение целиком."
            ),
            "help_available": source_stage == "independent_task",
            "mastery": mastery,
            "primary_action": "Исправить решение",
        }
    else:
        mastery = await _record_mastery_evidence_once(
            db,
            student_id=student.id,
            attempt=attempt,
            problem=problem,
            is_correct=True,
            source_stage=source_stage,
            evidence_label="[whole-photo verified]",
        )
        mastery_reached = bool(mastery["reached"])
        _set_stage(
            journey,
            "transfer_feedback" if source_stage == "transfer_task" else "photo_feedback",
        )
        journey.feedback = {
            "verdict": "correct",
            "message": (
                "Навык подтверждён на новой задаче."
                if source_stage == "transfer_task" and mastery_reached
                else (
                    "Решение верное. Для подтверждения навыка нужна ещё одна новая задача."
                )
                if source_stage == "transfer_task"
                else "Решение верное. Теперь проверим перенос на новой задаче."
            ),
            "mastery": mastery,
            "primary_action": (
                "Завершить тему" if source_stage == "transfer_task" and mastery_reached
                else "Решить ещё одну задачу" if source_stage == "transfer_task"
                else "Решить новую задачу"
            ),
        }

    journey.revision += 1
    await db.flush()
    response = await _render(db, student, journey)
    attempt.response_payload = response
    await db.commit()
    return response


async def _mark_photo_provider_error(
    db,
    *,
    student,
    journey: StudentJourney,
    attempt: JourneyAttempt,
    source_stage: str,
    original_filename: str,
    expected_lease_id: str,
) -> dict[str, Any]:
    await _require_photo_lease(
        db,
        student=student,
        journey=journey,
        attempt=attempt,
        expected_lease_id=expected_lease_id,
    )
    activity = dict(journey.activity or {})
    _clear_photo_processing(activity)
    journey.activity = activity
    _set_stage(journey, "photo_recovery")
    journey.feedback = _recovery_feedback(
        reason="provider_error",
        filename=original_filename,
        return_stage=source_stage,
    )
    journey.revision += 1
    await db.flush()
    state = await _render(db, student, journey)
    attempt.status = "provider_error"
    attempt.verdict = "provider_error"
    attempt.response_payload = state
    await db.commit()
    return state


def _typed_confidence(value: object) -> float | None:
    """Возвращает допустимую confidence или None для forged/provider значения."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    parsed = float(value)
    if not math.isfinite(parsed) or not 0 <= parsed <= 1:
        return None
    return parsed


def _normalise_typed_result(
    result: TypedAnswerResult,
    *,
    answer: str,
) -> tuple[str, str]:
    """Повторно применяет binary fail-closed gate перед durable-state записью."""

    confidence = _typed_confidence(result.confidence)
    answer_echo = _normalise_typed_answer(result.answer_echo)
    check_summary = _normalise_typed_text(
        result.check_summary,
        max_chars=_MAX_TYPED_CHECK_SUMMARY_CHARS,
    )
    if (
        result.verdict not in _TYPED_ANSWER_VERDICTS
        or result.error_focus not in _TYPED_ANSWER_ERROR_FOCUSES
        or confidence is None
        or not result.evidence_verified
        or answer_echo != answer
        or check_summary is None
    ):
        return "unsure", "unknown"
    if (
        result.verdict in {"correct", "incorrect"}
        and confidence < _TYPED_ANSWER_CONFIDENCE_THRESHOLD
    ):
        return "unsure", "unknown"
    if result.verdict == "correct" and result.error_focus in {"none", "format"}:
        return "correct", result.error_focus
    if result.verdict == "incorrect" and result.error_focus != "none":
        return "incorrect", result.error_focus
    return "unsure", "unknown"


async def _apply_typed_result(
    db,
    *,
    student,
    journey: StudentJourney,
    attempt: JourneyAttempt,
    problem: Problem,
    result: TypedAnswerResult,
    source_stage: str,
    source_problem_id: int,
    answer: str,
    expected_lease_id: str,
) -> dict[str, Any]:
    await _require_typed_lease(
        db,
        student=student,
        journey=journey,
        attempt=attempt,
        source_stage=source_stage,
        source_problem_id=source_problem_id,
        expected_lease_id=expected_lease_id,
    )
    verdict, error_focus = _normalise_typed_result(result, answer=answer)
    activity = dict(journey.activity or {})
    support_used = bool(activity.get("support_used", False))
    _clear_typed_processing(activity)
    journey.activity = activity
    attempt.status = "accepted"
    attempt.verdict = verdict
    confidence = _typed_confidence(result.confidence)
    attempt.confidence = confidence if confidence is not None else 0.0
    attempt.provider = result.provider
    attempt.model = result.model
    attempt.counts_for_mastery = False

    if verdict == "correct":
        mastery = await _record_mastery_evidence_once(
            db,
            student_id=student.id,
            attempt=attempt,
            problem=problem,
            is_correct=True,
            source_stage=source_stage,
            evidence_label="[typed-answer AI verified]",
            eligible=not support_used,
        )
        blueprint = topic_blueprint(_route_topic(journey)["id"])
        if source_stage == "independent_task":
            await _set_problem(
                db,
                journey,
                content_idx=int(blueprint["transfer_content_idx"]),
                mode="transfer",
            )
            _set_stage(journey, "transfer_task")
        elif not support_used and bool(mastery["reached"]):
            _set_stage(journey, "topic_result")
        else:
            await _set_problem(
                db,
                journey,
                content_idx=_next_transfer_content_idx(journey, blueprint),
                mode="transfer",
            )
            _set_stage(journey, "transfer_task")
        journey.feedback = {}
    else:
        counted_for_mastery = False
        if verdict == "incorrect":
            await _record_mastery_evidence_once(
                db,
                student_id=student.id,
                attempt=attempt,
                problem=problem,
                is_correct=False,
                source_stage=source_stage,
                evidence_label="[typed-answer AI verified incorrect]",
                eligible=not support_used,
            )
            counted_for_mastery = attempt.counts_for_mastery
        feedback_activity = dict(journey.activity or {})
        feedback_activity["typed_feedback"] = {
            "verdict": verdict,
            "error_focus": error_focus,
            "counts_for_mastery": counted_for_mastery,
            "answer": answer,
        }
        journey.activity = feedback_activity

    journey.revision += 1
    await db.flush()
    response = await _render(db, student, journey)
    attempt.response_payload = response
    await db.commit()
    return response


async def _mark_typed_provider_error(
    db,
    *,
    student,
    journey: StudentJourney,
    attempt: JourneyAttempt,
    source_stage: str,
    source_problem_id: int,
    expected_lease_id: str,
) -> dict[str, Any]:
    await _require_typed_lease(
        db,
        student=student,
        journey=journey,
        attempt=attempt,
        source_stage=source_stage,
        source_problem_id=source_problem_id,
        expected_lease_id=expected_lease_id,
    )
    activity = dict(journey.activity or {})
    _clear_typed_processing(activity)
    activity["typed_feedback"] = {
        "verdict": "unsure",
        "error_focus": "unknown",
        "reason": "provider_error",
        "answer": attempt.answer_given,
    }
    journey.activity = activity
    attempt.status = "provider_error"
    attempt.verdict = "provider_error"
    attempt.counts_for_mastery = False
    await db.flush()
    state = await _render(db, student, journey)
    attempt.response_payload = state
    await db.commit()
    return state


def _typed_completion_finished(
    task: asyncio.Task[tuple[_TypedCompletionStatus, dict[str, Any]]],
) -> None:
    """Удерживает detached task до конца и не теряет неожиданные ошибки."""

    _TYPED_COMPLETION_TASKS.discard(task)
    if task.cancelled():
        logger.warning("Фоновая typed-проверка отменена до durable результата")
        return
    error = task.exception()
    if error is not None:
        logger.error(
            "Фоновая typed-проверка завершилась с ошибкой",
            exc_info=(type(error), error, error.__traceback__),
        )


async def _complete_typed_attempt(
    *,
    student_id: int,
    client_attempt_id: str,
    source_stage: str,
    source_problem_id: int,
    answer: str,
    expected_lease_id: str,
    statement: str,
    canonical_steps: list[dict[str, Any]],
    correct_answer: str,
    trusted_context: dict[str, object],
    untrusted_history: list[dict[str, str]],
) -> tuple[_TypedCompletionStatus, dict[str, Any]]:
    """Завершает AI-проверку в своей DB-сессии независимо от HTTP-клиента."""

    provider_unavailable = False
    result: TypedAnswerResult | None = None
    try:
        result = await evaluate_typed_answer(
            statement=statement,
            canonical_steps=canonical_steps,
            correct_answer=correct_answer,
            submitted_answer=answer,
            trusted_context=trusted_context,
            untrusted_history=untrusted_history,
        )
    except LlmUnavailable:
        provider_unavailable = True

    async with db_base.async_session() as db:
        student = await db.get(Student, student_id)
        if student is None:  # pragma: no cover - FK/auth invariant
            raise RuntimeError("Ученик typed-попытки потерян")
        journey = await _journey_for_student(
            db,
            student_id=student_id,
            for_update=True,
        )
        attempt = await _existing_attempt(
            db,
            student_id=student_id,
            client_attempt_id=client_attempt_id,
            for_update=True,
        )
        if attempt is None:  # pragma: no cover - DB invariant
            raise RuntimeError("Typed-попытка потеряна")
        problem = await db.get(Problem, source_problem_id)
        if problem is None:  # pragma: no cover - FK/content invariant
            raise RuntimeError("Задача typed-попытки потеряна")

        if provider_unavailable:
            state = await _mark_typed_provider_error(
                db,
                student=student,
                journey=journey,
                attempt=attempt,
                source_stage=source_stage,
                source_problem_id=source_problem_id,
                expected_lease_id=expected_lease_id,
            )
            return "provider_error", state

        if result is None:  # pragma: no cover - control-flow invariant
            raise RuntimeError("AI не вернул typed-результат")
        state = await _apply_typed_result(
            db,
            student=student,
            journey=journey,
            attempt=attempt,
            problem=problem,
            result=result,
            source_stage=source_stage,
            source_problem_id=source_problem_id,
            answer=answer,
            expected_lease_id=expected_lease_id,
        )
        return "accepted", state


@router.post("/answer")
@limiter.limit("10/minute")
@ai_ip_limit
async def post_typed_answer(
    request: Request,
    body: TypedAnswerBody,
) -> dict[str, Any]:
    """Проверяет короткий ответ и атомарно открывает следующий шаг маршрута."""

    db, student = await _get_current_student(request)
    try:
        answer = _normalise_typed_answer(body.answer)
        if answer is None:
            raise HTTPException(
                status_code=422,
                detail="Ответ должен содержать от 1 до 500 безопасных символов.",
            )
        payload_hash = _hash_parts(str(body.problem_id), answer)
        journey = await _journey_for_student(
            db,
            student_id=student.id,
            for_update=True,
        )
        recovered_attempt = await _recover_stale_typed_processing(
            db,
            student_id=student.id,
            journey=journey,
        )
        if recovered_attempt is not None:
            await db.flush()
            recovered_attempt.response_payload = await _render(db, student, journey)
            await db.commit()
            journey = await _journey_for_student(
                db,
                student_id=student.id,
                for_update=True,
            )
        existing = await _existing_attempt(
            db,
            student_id=student.id,
            client_attempt_id=body.client_attempt_id,
            for_update=True,
        )
        retrying_provider_error = existing is not None and existing.status == "provider_error"
        if existing is not None and not retrying_provider_error:
            return await _typed_idempotent_payload_or_conflict(
                db,
                student,
                journey,
                existing,
                payload_hash=payload_hash,
            )

        if retrying_provider_error:
            if (
                existing.payload_hash != payload_hash
                or existing.answer_given != answer
                or existing.problem_id != body.problem_id
            ):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "idempotency_conflict",
                        "message": "Этот идентификатор уже использован для другого действия.",
                    },
                )
            if (
                existing.journey_id != journey.id
                or existing.stage != journey.stage
                or existing.problem_id != journey.current_problem_id
            ):
                await _state_conflict(
                    db,
                    student,
                    journey,
                    code="stale_revision",
                    message="Этот ответ относится к более раннему экрану.",
                )

        activity = dict(journey.activity or {})
        if activity.get("processing_client_attempt_id"):
            await _state_conflict(
                db,
                student,
                journey,
                code="photo_processing",
                message="Предыдущее фото ещё проверяется.",
            )
        if activity.get("typed_processing_client_attempt_id"):
            await _state_conflict(
                db,
                student,
                journey,
                code="typed_processing",
                message="Предыдущий ответ ещё проверяется.",
            )
        if activity.get("guided_processing_client_attempt_id"):
            await _state_conflict(
                db,
                student,
                journey,
                code="guided_processing",
                message="Предыдущий шаг ещё проверяется.",
            )
        await _require_revision(db, student, journey, body.revision)
        if journey.stage not in {"independent_task", "transfer_task"}:
            await _state_conflict(
                db,
                student,
                journey,
                code="stage_mismatch",
                message="Короткий ответ сейчас не ожидается.",
            )
        if journey.current_problem_id != body.problem_id:
            await _state_conflict(
                db,
                student,
                journey,
                code="problem_mismatch",
                message="Открыта другая задача.",
            )
        problem = await _current_problem(db, journey)
        steps = await _steps_for_problem(db, problem)
        if not steps:
            raise HTTPException(status_code=503, detail="Эталон решения ещё не загружен")

        source_stage = journey.stage
        source_problem_id = problem.id
        trusted_context = _typed_trusted_context(
            journey=journey,
            problem=problem,
            topic=_route_topic(journey),
            source_stage=source_stage,
        )
        untrusted_history = await _typed_untrusted_history(
            db,
            journey_id=journey.id,
            problem_id=problem.id,
        )
        lease_id = _start_typed_processing(journey, body.client_attempt_id)
        if retrying_provider_error:
            # journey и attempt уже заблокированы FOR UPDATE. Переход
            # provider_error -> processing вместе с новой lease образует CAS:
            # конкурент после commit увидит только processing и не вызовет AI.
            attempt = existing
            attempt.status = "processing"
            attempt.verdict = None
            attempt.confidence = None
            attempt.provider = None
            attempt.model = None
            attempt.counts_for_mastery = False
            attempt.response_payload = None
        else:
            attempt = JourneyAttempt(
                journey_id=journey.id,
                student_id=student.id,
                client_attempt_id=body.client_attempt_id,
                kind=(
                    "transfer_typed"
                    if source_stage == "transfer_task"
                    else "independent_typed"
                ),
                stage=source_stage,
                topic_id=journey.current_topic_id,
                problem_id=problem.id,
                payload_hash=payload_hash,
                answer_given=answer,
                status="processing",
                counts_for_mastery=False,
            )
            db.add(attempt)
        await db.commit()

        completion = asyncio.create_task(
            _complete_typed_attempt(
                student_id=student.id,
                client_attempt_id=body.client_attempt_id,
                source_stage=source_stage,
                source_problem_id=source_problem_id,
                answer=answer,
                expected_lease_id=lease_id,
                statement=problem.text_ru,
                canonical_steps=_canonical_photo_steps(steps),
                correct_answer=problem.answer,
                trusted_context=trusted_context,
                untrusted_history=untrusted_history,
            ),
            name=f"typed-completion-{student.id}-{body.client_attempt_id}",
        )
        _TYPED_COMPLETION_TASKS.add(completion)
        completion.add_done_callback(_typed_completion_finished)
        completion_status, state = await asyncio.shield(completion)
        if completion_status == "provider_error":
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "ai_unavailable",
                    "message": "Проверка ответа временно недоступна.",
                    "state": state,
                },
            )
        return state
    finally:
        await db.close()


@router.post("/photo/retry")
@limiter.limit("10/minute")
@ai_ip_limit
async def retry_saved_photo(
    request: Request,
    body: RetryPhotoBody,
) -> dict[str, Any]:
    db, student = await _get_current_student(request)
    try:
        if student.photo_consent is not True:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "consent_required",
                    "message": "Нужно согласие родителя на использование фото.",
                },
            )
        journey = await _journey_for_student(
            db,
            student_id=student.id,
            for_update=True,
        )
        await _ensure_not_processing(db, student, journey)
        await _require_revision(db, student, journey, body.revision)
        feedback = dict(journey.feedback or {})
        source_stage = feedback.get("return_stage")
        if (
            journey.stage != "photo_recovery"
            or feedback.get("reason") != "provider_error"
            or source_stage not in {"independent_task", "transfer_task"}
            or journey.current_problem_id is None
        ):
            raise HTTPException(status_code=409, detail="Сохранённое фото сейчас не ожидается")

        attempt = (
            await db.execute(
                select(JourneyAttempt)
                .where(
                    JourneyAttempt.journey_id == journey.id,
                    JourneyAttempt.student_id == student.id,
                    JourneyAttempt.problem_id == journey.current_problem_id,
                    JourneyAttempt.status == "provider_error",
                    JourneyAttempt.photo_ref.is_not(None),
                )
                .order_by(JourneyAttempt.created_at.desc(), JourneyAttempt.id.desc())
                .limit(1)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if attempt is None or attempt.stage != source_stage:
            raise HTTPException(status_code=409, detail="Сохранённая попытка не найдена")

        root = Path(settings.photo_dir).resolve()
        relative_path = Path(attempt.photo_ref or "")
        try:
            file_path = (root / relative_path).resolve()
            file_path.relative_to(root)
        except ValueError:
            file_path = root / "__invalid_photo_ref__"
        content_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".heic": "image/heic",
            ".heif": "image/heif",
        }.get(file_path.suffix.lower())
        if not file_path.is_file() or content_type is None:
            _set_stage(journey, source_stage)
            journey.feedback = {}
            journey.revision += 1
            attempt.status = "photo_missing"
            await db.flush()
            state = await _render(db, student, journey)
            attempt.response_payload = state
            await db.commit()
            return state

        image_bytes = file_path.read_bytes()
        saved_payload_hash = (
            _hash_parts(str(attempt.problem_id), content_type, image_bytes)
            if attempt.problem_id is not None
            else None
        )
        if (
            not image_bytes
            or len(image_bytes) > _MAX_PHOTO_BYTES
            or not _valid_image(image_bytes, content_type)
            or saved_payload_hash != attempt.payload_hash
        ):
            _set_stage(journey, source_stage)
            journey.feedback = {}
            journey.revision += 1
            attempt.status = "photo_missing"
            await db.flush()
            state = await _render(db, student, journey)
            attempt.response_payload = state
            await db.commit()
            return state

        problem = await _current_problem(db, journey)
        steps = await _steps_for_problem(db, problem)
        if not steps:
            raise HTTPException(status_code=503, detail="Эталон решения ещё не загружен")
        attempt_client_id = attempt.client_attempt_id
        attempt_filename = attempt.original_filename or "solution.jpg"
        lease_id = _start_photo_processing(journey, attempt_client_id)
        attempt.status = "processing"
        attempt.response_payload = None
        await db.commit()

        try:
            result = await evaluate_solution_photo(
                image_bytes=image_bytes,
                content_type=content_type,
                statement=problem.text_ru,
                canonical_steps=_canonical_photo_steps(steps),
                correct_answer=problem.answer,
            )
        except LlmUnavailable:
            journey = await _journey_for_student(
                db,
                student_id=student.id,
                for_update=True,
            )
            attempt = await _existing_attempt(
                db,
                student_id=student.id,
                client_attempt_id=attempt_client_id,
                for_update=True,
            )
            if attempt is None:  # pragma: no cover - DB invariant
                raise HTTPException(status_code=500, detail="Попытка фото потеряна")
            state = await _mark_photo_provider_error(
                db,
                student=student,
                journey=journey,
                attempt=attempt,
                source_stage=source_stage,
                original_filename=attempt_filename,
                expected_lease_id=lease_id,
            )
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "ai_unavailable",
                    "message": "Проверка фото временно недоступна. Снимок сохранён.",
                    "state": state,
                },
            )

        journey = await _journey_for_student(
            db,
            student_id=student.id,
            for_update=True,
        )
        attempt = await _existing_attempt(
            db,
            student_id=student.id,
            client_attempt_id=attempt_client_id,
            for_update=True,
        )
        if attempt is None:  # pragma: no cover - DB invariant
            raise HTTPException(status_code=500, detail="Попытка фото потеряна")
        return await _apply_photo_result(
            db,
            student=student,
            journey=journey,
            attempt=attempt,
            problem=problem,
            steps=steps,
            result=result,
            source_stage=source_stage,
            original_filename=attempt_filename,
            expected_lease_id=lease_id,
        )
    finally:
        await db.close()


@router.post("/photo")
@limiter.limit("10/minute")
@ai_ip_limit
async def post_photo(
    request: Request,
    revision: int = Form(..., ge=0),
    problem_id: int = Form(..., gt=0),
    client_attempt_id: str = Form(..., min_length=8, max_length=64),
    photo: UploadFile = FastApiFile(...),
) -> dict[str, Any]:
    db, student = await _get_current_student(request)
    content_type = (photo.content_type or "image/jpeg").split(";", 1)[0].lower()
    try:
        if student.photo_consent is not True:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "consent_required",
                    "message": "Нужно согласие родителя на использование фото.",
                },
            )
        if photo.size is not None and photo.size > _MAX_PHOTO_BYTES:
            raise HTTPException(status_code=413, detail="Фото превышает лимит 8 МБ")
        if content_type not in _ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=415,
                detail="Поддерживаются только JPEG, PNG, WEBP и HEIC",
            )
        image_bytes = await photo.read()
        if not image_bytes:
            raise HTTPException(status_code=422, detail="Фото не должно быть пустым")
        if len(image_bytes) > _MAX_PHOTO_BYTES:
            raise HTTPException(status_code=413, detail="Фото превышает лимит 8 МБ")
        if not _valid_image(image_bytes, content_type):
            raise HTTPException(status_code=422, detail="Файл не является корректным изображением")

        payload_hash = _hash_parts(str(problem_id), content_type, image_bytes)
        journey = await _journey_for_student(
            db,
            student_id=student.id,
            for_update=True,
        )
        existing = await _existing_attempt(
            db,
            student_id=student.id,
            client_attempt_id=client_attempt_id,
            for_update=True,
        )
        if existing is not None:
            return await _idempotent_payload_or_conflict(
                db,
                student,
                journey,
                existing,
                payload_hash=payload_hash,
            )
        await _ensure_not_processing(db, student, journey)
        await _require_revision(db, student, journey, revision)
        if journey.stage not in {"independent_task", "transfer_task"}:
            await _state_conflict(
                db,
                student,
                journey,
                code="stage_mismatch",
                message="Фото сейчас не ожидается.",
            )
        if journey.current_problem_id != problem_id:
            await _state_conflict(
                db,
                student,
                journey,
                code="problem_mismatch",
                message="Открыта другая задача.",
            )
        problem = await _current_problem(db, journey)
        steps = await _steps_for_problem(db, problem)
        if not steps:
            raise HTTPException(status_code=503, detail="Эталон решения ещё не загружен")

        original_filename = Path(photo.filename or "solution.jpg").name[:200]
        suffix = _ALLOWED_CONTENT_TYPES[content_type]
        relative_path = Path("journey") / str(student.id) / f"{uuid4().hex}{suffix}"
        file_path = Path(settings.photo_dir) / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(image_bytes)

        source_stage = journey.stage
        lease_id = _start_photo_processing(journey, client_attempt_id)
        attempt = JourneyAttempt(
            journey_id=journey.id,
            student_id=student.id,
            client_attempt_id=client_attempt_id,
            kind="transfer_photo" if source_stage == "transfer_task" else "independent_photo",
            stage=source_stage,
            topic_id=journey.current_topic_id,
            problem_id=problem.id,
            payload_hash=payload_hash,
            photo_ref=str(relative_path),
            original_filename=original_filename,
            status="processing",
            counts_for_mastery=False,
        )
        db.add(attempt)
        await db.commit()

        try:
            result = await evaluate_solution_photo(
                image_bytes=image_bytes,
                content_type=content_type,
                statement=problem.text_ru,
                canonical_steps=_canonical_photo_steps(steps),
                correct_answer=problem.answer,
            )
        except LlmUnavailable:
            journey = await _journey_for_student(
                db,
                student_id=student.id,
                for_update=True,
            )
            attempt = await _existing_attempt(
                db,
                student_id=student.id,
                client_attempt_id=client_attempt_id,
                for_update=True,
            )
            if attempt is None:  # pragma: no cover - DB invariant
                raise HTTPException(status_code=500, detail="Попытка фото потеряна")
            state = await _mark_photo_provider_error(
                db,
                student=student,
                journey=journey,
                attempt=attempt,
                source_stage=source_stage,
                original_filename=original_filename,
                expected_lease_id=lease_id,
            )
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "ai_unavailable",
                    "message": "Проверка фото временно недоступна. Снимок сохранён.",
                    "state": state,
                },
            )

        journey = await _journey_for_student(
            db,
            student_id=student.id,
            for_update=True,
        )
        attempt = await _existing_attempt(
            db,
            student_id=student.id,
            client_attempt_id=client_attempt_id,
            for_update=True,
        )
        if attempt is None:  # pragma: no cover - DB invariant
            raise HTTPException(status_code=500, detail="Попытка фото потеряна")
        return await _apply_photo_result(
            db,
            student=student,
            journey=journey,
            attempt=attempt,
            problem=problem,
            steps=steps,
            result=result,
            source_stage=source_stage,
            original_filename=original_filename,
            expected_lease_id=lease_id,
        )
    finally:
        await db.close()
