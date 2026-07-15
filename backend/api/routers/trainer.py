"""Роутер тренажёра ошибок: /api/trainer/wrong-tasks, /api/trainer/analytics,
/api/trainer/diagnose.

Не растёт api/routes.py — отдельный модуль согласно AUDIT API-3.
Использует _get_current_student из routes.py (JWT-логику не дублируем).
"""

from __future__ import annotations

import csv
import io
import json
import logging
import math
from pathlib import Path
import re
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Form, HTTPException, Query, Request, UploadFile
from fastapi import File as FastApiFile
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes import _get_current_student, ai_ip_limit, limiter
from core.agent_context import build_agent_context
from core.bkt import record_attempt
from core.config import settings
from core.grading import check_answer
from core.llm_openai import LlmUnavailable, StepClassification, classify_step_photo, diagnose_photo
from core.srez import pick_srez_problems
from core.step_content import safe_step_instruction
from core.trainer import (
    StepDTO,
    WrongTask,
    build_problem_topics,
    build_wrong_tasks,
    match_fingerprint,
    pick_easier_decomp,
    pick_verification_problem,
)
from core.tutor import (
    generate_tutor_reply,
    sanitize_tutor_output,
    tutor_unavailable_fallback,
)
from db.models import Problem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trainer", tags=["trainer"])

_SAFE_DIAGNOSIS_CAUSE = (
    "На этом шаге решение расходится с правилом. "
    "Сравни действие с предыдущей строкой и проверь, что изменилось."
)
_SAFE_DIAGNOSIS_TRANSCRIPTION = "Фото решения распознано."


def _sanitise_diagnosis_cause(value: object) -> str | None:
    """Закрывает legacy free-form cause_text на любом child-visible read."""
    if value is None:
        return None
    return _SAFE_DIAGNOSIS_CAUSE


# ── Pydantic v2 response-схемы ────────────────────────────────────────────────


class StepOut(BaseModel):
    """Один шаг декомпозиции для клиента."""

    n: int
    instruction_ru: str
    micro_skill: str
    # Человеческая подпись умения (micro_skills.label_ru); None — код не найден в
    # каталоге. Фронт обязан показывать её вместо micro_skill (запрет §2.2).
    micro_skill_label: str | None
    kind: str
    reveal: Any  # None или строка — оставляем гибким


class WrongTaskOut(BaseModel):
    """Задача тренажёра с декомпозицией и маршрутом."""

    id: str
    problem_id: int
    node_id: str
    topic_label: str
    statement: str
    primary_micro_skill: str | None
    # Человеческая подпись primary_micro_skill (micro_skills.label_ru); см. §2.2
    primary_micro_skill_label: str | None
    decomp_idx: int | None
    steps: list[StepOut]
    state: str
    wrong_answer: str
    mastery: float
    # Карточка метода узла «Как решать» (nodes.theory_ru); None пока не сгенерирована.
    theory_ru: str | None


class WrongTasksResponse(BaseModel):
    """Ответ эндпоинта /wrong-tasks."""

    tasks: list[WrongTaskOut]
    # Была ли у ученика ХОТЬ ОДНА попытка (любой источник: срез/практика/экзамен).
    # Разводит два пустых состояния hub: false → новичок (онбординг),
    # true + пустой список → ветеран, все ошибки закрыты. Default False —
    # обратная совместимость со старыми клиентами, читающими только tasks.
    has_activity: bool = False


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


class ProblemTopicOut(BaseModel):
    """Одна проблемная тема для hub."""

    topic_id: str
    strand: str | None
    name_ru: str | None
    error_count: int
    top_micro_skills: list[str]
    nodes_mastery_avg: float
    closure_progress: float


class ProblemTopicsResponse(BaseModel):
    """Ответ /problem-topics."""

    topics: list[ProblemTopicOut]


# ── Маппинг dataclass → Pydantic ─────────────────────────────────────────────


def _step_to_out(step: StepDTO, *, correct_answer: object | None = None) -> StepOut:
    """Конвертирует StepDTO → StepOut."""
    return StepOut(
        n=step.n,
        instruction_ru=safe_step_instruction(
            step.instruction_ru,
            expected_value=step.expected_value,
            correct_answer=correct_answer,
        ),
        micro_skill=step.micro_skill,
        micro_skill_label=step.micro_skill_label,
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
        primary_micro_skill=task.primary_micro_skill,
        primary_micro_skill_label=task.primary_micro_skill_label,
        decomp_idx=task.decomp_idx,
        steps=[_step_to_out(s, correct_answer=task.answer) for s in task.steps],
        state=task.state,
        wrong_answer=task.wrong_answer,
        mastery=task.mastery,
        theory_ru=task.theory_ru,
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
        # has_activity — был ли у ученика ХОТЬ ОДИН attempt (любой источник и
        # результат). Разводит пустой hub: новичок (онбординг) vs ветеранка,
        # у которой все ошибки закрыты. EXISTS не тянет строки — только факт.
        has_activity = bool(
            (
                await session.execute(
                    text("SELECT EXISTS (SELECT 1 FROM attempts WHERE student_id = :sid)"),
                    {"sid": student.id},
                )
            ).scalar()
        )
    finally:
        await session.close()

    return WrongTasksResponse(
        tasks=[_task_to_out(t) for t in tasks],
        has_activity=has_activity,
    )


# ── Серверная проверка typed-answer одного шага ──────────────────────────────

class StepAnswerIn(BaseModel):
    problem_id: int = Field(ge=1)
    decomp_idx: int | None = Field(default=None, ge=0)
    step_n: int = Field(ge=1)
    answer: str = Field(min_length=1, max_length=256)

    @field_validator("answer")
    @classmethod
    def answer_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("answer must not be blank")
        return value


class StepAnswerOut(BaseModel):
    correct: bool
    hint: str | None
    step_n: int


class DrillStateOut(BaseModel):
    solved_step_ns: list[int]


async def _previous_drill_steps_solved(
    session: AsyncSession,
    *,
    student_id: int,
    problem_id: int,
    decomp_idx: int,
    step_n: int,
) -> bool:
    """Проверяет, что все предыдущие canonical-шаги подтверждены сервером."""
    if step_n <= 1:
        return True

    result = await session.execute(
        text(
            "SELECT NOT EXISTS ("
            "  SELECT 1 FROM problem_steps previous "
            "  WHERE previous.decomp_idx = :didx AND previous.n < :step_n "
            "    AND NOT ("
            "      EXISTS ("
            "        SELECT 1 FROM drill_step_attempts typed "
            "        WHERE typed.student_id = :sid AND typed.problem_id = :pid "
            "          AND typed.decomp_idx = :didx AND typed.step_n = previous.n "
            "          AND typed.is_correct = true"
            "      ) OR EXISTS ("
            "        SELECT 1 FROM step_submissions photo "
            "        WHERE photo.student_id = :sid AND photo.problem_id = :pid "
            "          AND photo.decomp_idx = :didx AND photo.step_n = previous.n "
            "          AND photo.verdict = 'match'"
            "      )"
            "    )"
            ")"
        ),
        {
            "sid": student_id,
            "pid": problem_id,
            "didx": decomp_idx,
            "step_n": step_n,
        },
    )
    return bool(result.scalar())


def _contiguous_step_numbers(values: list[int]) -> list[int]:
    """Не позволяет старым разрозненным submission перескочить пропущенный шаг."""
    contiguous: list[int] = []
    for value in sorted(set(values)):
        if value != len(contiguous) + 1:
            break
        contiguous.append(value)
    return contiguous


@router.post("/step-answer", response_model=StepAnswerOut)
@limiter.limit("60/minute")
async def post_step_answer(request: Request, payload: StepAnswerIn) -> StepAnswerOut:
    """Проверяет введённый шаг на сервере и не возвращает скрытый эталон.

    Для canonical decomposition проверяем строгую identity-связь с задачей.
    Если у задачи нет опубликованной декомпозиции, единственный fallback-шаг
    проверяется по финальному ответу самой задачи.
    """
    session, student = await _get_current_student(request)
    try:
        if payload.decomp_idx is None:
            if payload.step_n != 1:
                raise HTTPException(status_code=404, detail="Шаг не найден")
            step = (await session.execute(
                text(
                    "SELECT p.answer AS expected_value, p.answer_type, "
                    "       NULL::varchar AS micro_skill, "
                    "       NULL::text AS instruction_ru, "
                    "       EXISTS ("
                    "         SELECT 1 FROM decomposition_problems dp "
                    "         WHERE dp.node_id = p.node_id "
                    "           AND dp.answer = p.answer "
                    "           AND dp.all_steps_verified = true "
                    "           AND dp.needs_review = false "
                    "           AND (p.content_idx = dp.idx OR dp.problems_db_id = p.id) "
                    "           AND EXISTS ("
                    "             SELECT 1 FROM problem_steps ps WHERE ps.decomp_idx = dp.idx"
                    "           )"
                    "       ) AS has_published_decomposition "
                    "FROM problems p WHERE p.id = :pid"
                ),
                {"pid": payload.problem_id},
            )).fetchone()
        else:
            step = (await session.execute(
                text(
                    "SELECT ps.expected_value, p.answer_type, ps.micro_skill, "
                    "       ps.instruction_ru, p.answer AS correct_answer "
                    "FROM problems p "
                    "JOIN decomposition_problems dp ON dp.idx = :didx "
                    "JOIN problem_steps ps ON ps.decomp_idx = dp.idx AND ps.n = :step_n "
                    "WHERE p.id = :pid "
                    "  AND dp.node_id = p.node_id "
                    "  AND dp.answer = p.answer "
                    "  AND dp.all_steps_verified = true "
                    "  AND dp.needs_review = false "
                    "  AND (p.content_idx = dp.idx OR dp.problems_db_id = p.id) "
                    "LIMIT 1"
                ),
                {
                    "pid": payload.problem_id,
                    "didx": payload.decomp_idx,
                    "step_n": payload.step_n,
                },
            )).fetchone()

        if step is None:
            raise HTTPException(status_code=404, detail="Шаг не найден")
        if payload.decomp_idx is None and step.has_published_decomposition:
            raise HTTPException(
                status_code=409,
                detail="Для задачи доступно пошаговое решение",
            )

        if payload.decomp_idx is not None and not await _previous_drill_steps_solved(
            session,
            student_id=student.id,
            problem_id=payload.problem_id,
            decomp_idx=payload.decomp_idx,
            step_n=payload.step_n,
        ):
            raise HTTPException(
                status_code=409,
                detail="Сначала заверши предыдущий шаг",
            )

        correct = check_answer(payload.answer, step.expected_value, step.answer_type)
        hint: str | None = None
        if not correct and payload.decomp_idx is not None:
            # mistake_ru может содержать скрытый expected_value и не доказывает,
            # что ребёнок совершил именно эту ошибку. Возвращаем только уже
            # показанную инструкцию текущего шага.
            safe_instruction = safe_step_instruction(
                step.instruction_ru,
                expected_value=step.expected_value,
                correct_answer=step.correct_answer,
            )
            hint = f"Проверь этот шаг ещё раз: {safe_instruction}"

        await session.execute(
            text(
                "INSERT INTO drill_step_attempts "
                "(student_id, problem_id, decomp_idx, step_n, is_correct, source, created_at) "
                "VALUES (:sid, :pid, :didx, :step_n, :correct, 'input', NOW())"
            ),
            {
                "sid": student.id,
                "pid": payload.problem_id,
                "didx": payload.decomp_idx,
                "step_n": payload.step_n,
                "correct": correct,
            },
        )
        await session.commit()
    finally:
        await session.close()

    return StepAnswerOut(correct=correct, hint=hint, step_n=payload.step_n)


@router.get("/drill-state", response_model=DrillStateOut)
async def get_drill_state(
    request: Request,
    problem_id: int = Query(..., ge=1),
    decomp_idx: int | None = Query(default=None, ge=0),
) -> DrillStateOut:
    """Возвращает только подтверждённые сервером шаги текущего ученика."""
    session, student = await _get_current_student(request)
    try:
        problem_exists = (await session.execute(
            text("SELECT 1 FROM problems WHERE id = :pid"),
            {"pid": problem_id},
        )).scalar()
        if not problem_exists:
            raise HTTPException(status_code=404, detail="Задача не найдена")

        if decomp_idx is None:
            rows = await session.execute(
                text(
                    "SELECT DISTINCT step_n FROM drill_step_attempts "
                    "WHERE student_id = :sid AND problem_id = :pid "
                    "  AND decomp_idx IS NULL AND is_correct = true "
                    "ORDER BY step_n"
                ),
                {"sid": student.id, "pid": problem_id},
            )
        else:
            rows = await session.execute(
                text(
                    "SELECT step_n FROM ("
                    "  SELECT step_n FROM drill_step_attempts "
                    "  WHERE student_id = :sid AND problem_id = :pid "
                    "    AND decomp_idx = :didx AND is_correct = true "
                    "  UNION "
                    "  SELECT step_n FROM step_submissions "
                    "  WHERE student_id = :sid AND problem_id = :pid "
                    "    AND decomp_idx = :didx AND verdict = 'match'"
                    ") solved ORDER BY step_n"
                ),
                {"sid": student.id, "pid": problem_id, "didx": decomp_idx},
            )
        solved_step_ns = _contiguous_step_numbers(
            [int(value) for value in rows.scalars().all()]
        )
    finally:
        await session.close()

    return DrillStateOut(solved_step_ns=solved_step_ns)


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
                last_cause_text=_sanitise_diagnosis_cause(row.last_cause_text),
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


@router.get("/problem-topics", response_model=ProblemTopicsResponse)
async def get_problem_topics(request: Request) -> ProblemTopicsResponse:
    """Проблемные темы ученика (CC-агрегат): ошибки, топ-умения, прогресс закрытия."""
    session, student = await _get_current_student(request)
    try:
        rows = await build_problem_topics(session, student_id=student.id)
    finally:
        await session.close()
    return ProblemTopicsResponse(topics=[
        ProblemTopicOut(
            topic_id=r.topic_id, strand=r.strand, name_ru=r.name_ru,
            error_count=r.error_count, top_micro_skills=r.top_micro_skills,
            nodes_mastery_avg=r.nodes_mastery_avg, closure_progress=r.closure_progress,
        )
        for r in rows
    ])


# ── Согласие родителя на использование фото (Блок 1.0) ───────────────────────

class ConsentIn(BaseModel):
    photo_consent: bool


@router.post("/consent")
@limiter.limit("10/minute")
async def post_consent(request: Request, payload: ConsentIn) -> dict:
    """Проставляет согласие родителя на использование фото + timestamp."""
    session, student = await _get_current_student(request)
    try:
        await session.execute(
            text(
                "UPDATE students SET photo_consent = :c, "
                "photo_consent_at = CASE WHEN :c THEN NOW() ELSE photo_consent_at END "
                "WHERE id = :sid"
            ),
            {"c": payload.photo_consent, "sid": student.id},
        )
        await session.commit()
    finally:
        await session.close()
    return {"photo_consent": payload.photo_consent}


# ── Pydantic-схема ответа /diagnose ──────────────────────────────────────────

class DiagnosisOut(BaseModel):
    """Ответ эндпоинта /diagnose."""

    transcription: str
    failed_step: int | None
    cause_text: str
    level: int
    micro_skill: str | None
    # Человеческая подпись micro_skill (micro_skills.label_ru); None — умение не
    # определено или код не найден в каталоге (запрет §2.2 DESIGN_SYSTEM).
    micro_skill_label: str | None
    confidence: float
    image_ref: str          # путь относительно photo_dir


# ── Ограничение размера загружаемого фото ────────────────────────────────────

_MAX_PHOTO_BYTES = 8 * 1024 * 1024  # 8 МБ
_ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}
_EXPECTED_IMAGE_FORMATS = {
    "image/jpeg": {"JPEG"},
    "image/png": {"PNG"},
    "image/webp": {"WEBP"},
    "image/heic": {"HEIF", "HEIC"},
    "image/heif": {"HEIF", "HEIC"},
}
_IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
}
_IMAGE_MEDIA_TYPES_BY_SUFFIX = {
    suffix: content_type for content_type, suffix in _IMAGE_EXTENSIONS.items()
}


def _is_valid_image_payload(image_bytes: bytes, content_type: str) -> bool:
    """Декодирует upload и сверяет реальный формат с заявленным MIME."""
    try:
        if content_type in {"image/heic", "image/heif"}:
            import pillow_heif  # noqa: PLC0415

            pillow_heif.register_heif_opener()
        from PIL import Image  # noqa: PLC0415

        with Image.open(io.BytesIO(image_bytes)) as image:
            actual_format = (image.format or "").upper()
            image.verify()
        return actual_format in _EXPECTED_IMAGE_FORMATS[content_type]
    except (KeyError, OSError, ValueError):
        return False


@router.post("/diagnose", response_model=DiagnosisOut)
@limiter.limit("10/minute")
@ai_ip_limit
async def post_diagnose(
    request: Request,
    problem_id: int = Form(..., description="ID задачи из таблицы problems"),
    attempt_id: int | None = Form(None, description="ID попытки (опционально)"),
    photo: UploadFile = FastApiFile(..., description="Фото рукописного решения"),
) -> DiagnosisOut:
    """Принимает фото решения ученика → grounded vision-диагностика → сохраняет память ошибки.

    Flow:
      1. Auth; загружаем задачу (404 если нет).
      2. Читаем байты фото; size-guard ≤8 МБ (413).
      3. Определяем wrong_answer: из попытки attempt_id или из последней неверной попытки.
      4. match_fingerprint → fingerprint_hint.
      5. build_agent_context → canonical_steps; correct_answer из задачи.
      6. diagnose_photo (LlmUnavailable → 503).
      7. Сохраняем файл: settings.photo_dir/{student_id}/{uuid}.jpg.
      8. INSERT INTO error_captures.
      9. UPSERT INTO recurring_errors (если micro_skill известен).
      10. Возвращаем DiagnosisOut.
    """
    session, student = await _get_current_student(request)
    file_path: Path | None = None
    db_committed = False
    try:
        # Сбор фото гейтится согласием родителя (Блок 1.0). Проверяем ДО любой работы.
        if student.photo_consent is not True:
            raise HTTPException(
                status_code=403,
                detail={"code": "consent_required",
                        "message": "Нужно согласие родителя на использование фото."},
            )

        # ── 1. Загружаем задачу (404 если нет) ───────────────────────────────
        prob_row = await session.execute(
            text("SELECT id, node_id, text_ru, answer FROM problems WHERE id = :pid"),
            {"pid": problem_id},
        )
        problem = prob_row.fetchone()
        if problem is None:
            raise HTTPException(status_code=404, detail=f"Задача {problem_id} не найдена")

        node_id: str = problem.node_id
        correct_answer: str = problem.answer

        # ── 2. Читаем байты фото; size-guard ─────────────────────────────────

        # Быстрая проверка по Content-Length до чтения в память:
        # реальный backstop — nginx client_max_body_size (задаётся при деплое)
        if photo.size is not None and photo.size > _MAX_PHOTO_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Фото превышает лимит {_MAX_PHOTO_BYTES // (1024 * 1024)} МБ",
            )

        # Проверка content_type: только допустимые форматы изображений
        if photo.content_type is None:
            # Если content_type не передан — считаем JPEG (мобильные клиенты)
            content_type: str = "image/jpeg"
        elif photo.content_type not in _ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=415,
                detail="Поддерживаются только JPEG/PNG/WEBP/HEIC",
            )
        else:
            content_type = photo.content_type

        image_bytes = await photo.read()
        if not image_bytes:
            raise HTTPException(status_code=422, detail="Фото не должно быть пустым")
        # Постчтение-проверка: Content-Length может лгать, сверяемся по факту
        if len(image_bytes) > _MAX_PHOTO_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Фото превышает лимит {_MAX_PHOTO_BYTES // (1024 * 1024)} МБ",
            )
        if not _is_valid_image_payload(image_bytes, content_type):
            raise HTTPException(
                status_code=422,
                detail="Файл не является корректным изображением выбранного формата",
            )

        # ── 3. Определяем wrong_answer ────────────────────────────────────────
        wrong_answer: str | None = None
        persisted_attempt_id: int | None = None
        if attempt_id is not None:
            # Явный attempt_id обязан принадлежать текущему ученику и задаче.
            # Иначе не запускаем дорогой Vision и не сохраняем чужой FK.
            att_row = await session.execute(
                text(
                    "SELECT answer_given FROM attempts "
                    "WHERE id = :aid AND student_id = :sid AND problem_id = :pid"
                ),
                {"aid": attempt_id, "sid": student.id, "pid": problem_id},
            )
            att = att_row.fetchone()
            if att is None:
                raise HTTPException(status_code=404, detail="Попытка для этой задачи не найдена")
            persisted_attempt_id = attempt_id
            wrong_answer = att.answer_given
        else:
            # Последняя неверная попытка этого студента на этой задаче
            latest_row = await session.execute(
                text(
                    "SELECT answer_given FROM attempts "
                    "WHERE student_id = :sid AND problem_id = :pid AND is_correct = false "
                    "ORDER BY created_at DESC LIMIT 1"
                ),
                {"sid": student.id, "pid": problem_id},
            )
            latest = latest_row.fetchone()
            if latest is not None:
                wrong_answer = latest.answer_given

        # ── 4. match_fingerprint → fingerprint_hint ───────────────────────────
        fingerprint_hint: str | None = None
        fallback_micro_skill: str | None = None
        if wrong_answer is not None:
            fp = await match_fingerprint(session, problem_id=problem_id, answer_given=wrong_answer)
            if fp is not None:
                fingerprint_hint = fp.mistake_ru
                fallback_micro_skill = fp.micro_skill

        # ── 5. Grounding через единый context-pack ───────────────────────────
        agent_ctx = await build_agent_context(
            session, student_id=student.id, problem_id=problem_id
        )
        canonical_steps: list[dict] = [
            {
                "n": s["n"],
                "instruction_ru": s["instruction_ru"],
                "expected_value": s["expected_value"],
                "micro_skill": s.get("micro_skill"),
            }
            for s in agent_ctx.canonical_steps
        ]
        canonical_micro_skills = {
            str(step["micro_skill"])
            for step in canonical_steps
            if step.get("micro_skill")
        }

        # ── 6. Вызываем vision-диагностику (LlmUnavailable → 503) ────────────
        try:
            result = await diagnose_photo(
                image_bytes=image_bytes,
                content_type=content_type,
                statement=problem.text_ru,
                canonical_steps=canonical_steps,
                correct_answer=correct_answer,
                wrong_answer=wrong_answer,
                fingerprint_hint=fingerprint_hint,
            )
        except LlmUnavailable as exc:
            logger.warning("LLM недоступен для diagnose: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="Сервис анализа фото временно недоступен. Попробуйте позже.",
            ) from exc

        try:
            confidence = float(result.confidence)
        except (TypeError, ValueError, OverflowError):
            confidence = 0.0
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            confidence = 0.0
        result.confidence = confidence

        valid_steps = {int(step["n"]) for step in canonical_steps}
        if (
            isinstance(result.failed_step, bool)
            or not isinstance(result.failed_step, int)
            or result.failed_step not in valid_steps
        ):
            result.failed_step = None

        try:
            level = int(result.level)
        except (TypeError, ValueError, OverflowError):
            level = 2
        result.level = level if level in {1, 2, 3} else 2

        # OCR и cause_text — свободный model output: semantic post-filter не
        # способен доказать отсутствие перефразированного ответа. Сохраняем и
        # возвращаем только серверные строки; Gemini влияет лишь на bounded
        # metadata (failed_step/micro_skill/confidence/level).
        result.transcription = _SAFE_DIAGNOSIS_TRANSCRIPTION

        micro_skill = result.micro_skill if isinstance(result.micro_skill, str) else None
        micro_skill = micro_skill.strip() if micro_skill else None
        if micro_skill is not None and re.fullmatch(r"[a-z0-9_]{1,50}", micro_skill) is None:
            micro_skill = None
        result.micro_skill = micro_skill

        # Vision не может придумывать durable-навыки: код обязан одновременно
        # существовать в каталоге и быть привязан к шагам/grounded fingerprint
        # именно этой задачи.
        failed_step_micro_skill: str | None = None
        if result.failed_step is not None:
            failed_step_micro_skill = next(
                (
                    str(step["micro_skill"])
                    for step in canonical_steps
                    if step["n"] == result.failed_step and step.get("micro_skill")
                ),
                None,
            )

        result_micro_skill_label: str | None = None
        if result.micro_skill:
            result_micro_skill_label = (
                await session.execute(
                    text("SELECT label_ru FROM micro_skills WHERE code = :ms"),
                    {"ms": result.micro_skill},
                )
            ).scalar()
            if (
                result_micro_skill_label is None
                or result.micro_skill != failed_step_micro_skill
            ):
                logger.warning(
                    "Vision micro_skill отброшен как не-grounded для failed_step "
                    "(problem_id=%s, failed_step=%s, micro_skill=%s)",
                    problem_id,
                    result.failed_step,
                    result.micro_skill,
                )
                result.micro_skill = None
                result_micro_skill_label = None

        validated_fallback_micro_skill: str | None = None
        if fallback_micro_skill:
            fallback_exists = (
                await session.execute(
                    text("SELECT 1 FROM micro_skills WHERE code = :ms"),
                    {"ms": fallback_micro_skill},
                )
            ).scalar()
            if (
                fallback_exists is not None
                and fallback_micro_skill in canonical_micro_skills
                and (
                    result.failed_step is None
                    or fallback_micro_skill == failed_step_micro_skill
                )
            ):
                validated_fallback_micro_skill = fallback_micro_skill

        result.cause_text = _SAFE_DIAGNOSIS_CAUSE

        # ── 7. Сохраняем фото до записи истории ────────────────────────────────
        # Запись в БД не должна ссылаться на отсутствующий файл. Если последующая
        # транзакция не завершится, finally удалит сохранённый артефакт.
        file_name = f"{uuid4().hex}{_IMAGE_EXTENSIONS[content_type]}"
        image_ref = f"{student.id}/{file_name}"
        file_path = Path(settings.photo_dir) / image_ref
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(image_bytes)
        except OSError as exc:
            logger.error("Не удалось сохранить фото (image_ref=%s): %s", image_ref, exc)
            raise HTTPException(
                status_code=503,
                detail="Не удалось сохранить фото. Попробуйте ещё раз.",
            ) from exc

        # ── 8. INSERT INTO error_captures ─────────────────────────────────────
        # Provenance приходит от реально успешной итерации provider fallback-chain.
        provider_name = result.provider if isinstance(result.provider, str) else "unknown"
        used_model = result.model if isinstance(result.model, str) else "unknown"
        model_name = f"{provider_name.strip() or 'unknown'}:{used_model.strip() or 'unknown'}"[:50]
        # Нулевая уверенность сохраняется для аудита, но не должна загрязнять
        # adaptive memory и менять будущий маршрут ученика.
        failed_micro_skill: str | None = None
        if result.confidence > 0.0:
            failed_micro_skill = result.micro_skill or validated_fallback_micro_skill

        await session.execute(
            text(
                "INSERT INTO error_captures "
                "(student_id, attempt_id, problem_id, node_id, image_ref, "
                " transcription, failed_step, failed_micro_skill, cause_text, "
                " level, model, confidence, created_at) "
                "VALUES (:sid, :aid, :pid, :nid, :img, "
                "        :trans, :fstep, :fms, :cause, "
                "        :lvl, :model, :conf, NOW())"
            ),
            {
                "sid": student.id,
                "aid": persisted_attempt_id,
                "pid": problem_id,
                "nid": node_id,
                "img": image_ref,
                "trans": result.transcription,
                "fstep": result.failed_step,
                "fms": failed_micro_skill,
                "cause": result.cause_text,
                "lvl": result.level,
                "model": model_name,
                "conf": result.confidence,
            },
        )

        # ── 9. UPSERT INTO recurring_errors (только если micro_skill известен) ─
        if failed_micro_skill and result.confidence > 0.0:
            await session.execute(
                text(
                    "INSERT INTO recurring_errors "
                    "(student_id, micro_skill, node_id, error_count, last_seen_at, last_cause_text, resolved, created_at) "
                    "VALUES (:sid, :ms, :nid, 1, NOW(), :cause, false, NOW()) "
                    "ON CONFLICT (student_id, micro_skill) DO UPDATE SET "
                    "  error_count = recurring_errors.error_count + 1, "
                    "  last_seen_at = NOW(), "
                    "  last_cause_text = EXCLUDED.last_cause_text, "
                    "  node_id = EXCLUDED.node_id, "
                    "  resolved = false"
                ),
                {
                    "sid": student.id,
                    "ms": failed_micro_skill,
                    "nid": node_id,
                    "cause": result.cause_text,
                },
            )

        # ── Коммит DB ────────────────────────────────────────────────────────
        await session.commit()
        db_committed = True

    finally:
        if file_path is not None and not db_committed:
            try:
                file_path.unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("Не удалось удалить orphan-фото %s: %s", file_path, exc)
        await session.close()

    return DiagnosisOut(
        transcription=result.transcription,
        failed_step=result.failed_step,
        cause_text=result.cause_text,
        level=result.level,
        micro_skill=result.micro_skill,
        micro_skill_label=result_micro_skill_label,
        confidence=result.confidence,
        image_ref=image_ref,
    )


# ── Пошаговая сдача: фото одного шага лесенки (Блок 1.2) ──────────────────────

class StepSubmitOut(BaseModel):
    """Ответ эндпоинта /step-submit."""

    verdict: str            # match | mismatch | unsure
    hint: str | None        # инструкция текущего шага при mismatch, иначе None
    confidence: float
    step_n: int


@router.post("/step-submit", response_model=StepSubmitOut)
@limiter.limit("15/minute")
@ai_ip_limit
async def post_step_submit(
    request: Request,
    decomp_idx: int = Form(...),
    step_n: int = Form(...),
    problem_id: int = Form(...),
    photo: UploadFile = FastApiFile(...),
) -> StepSubmitOut:
    """Принимает фото одного шага лесенки → узкая vision-классификация → мягкий вердикт.

    Flow:
      1. Auth + consent-гейт (как /diagnose).
      2. size/content-type гейты (413/415) — паттерн /diagnose.
      3. Загружаем шаг из problem_steps (404 если нет).
      4. statement — из problems, если problem_id передан.
      5. classify_step_photo (LlmUnavailable → 503).
      6. Порог: match/mismatch с confidence ниже threshold → unsure
         (false-reject хуже пропуска — мягкость по умолчанию).
      7. При mismatch — только подсказка по текущему шагу без скрытого эталона.
      8. Атомарно сохраняем файл и INSERT в step_submissions (включая unsure).
    """
    session, student = await _get_current_student(request)
    try:
        # Сбор фото гейтится согласием родителя (Блок 1.0)
        if student.photo_consent is not True:
            raise HTTPException(
                status_code=403,
                detail={"code": "consent_required",
                        "message": "Нужно согласие родителя на использование фото."},
            )

        # ── size-guard по Content-Length (быстрая проверка до чтения в память) ──
        if photo.size is not None and photo.size > _MAX_PHOTO_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Фото превышает лимит {_MAX_PHOTO_BYTES // (1024 * 1024)} МБ",
            )

        # Проверка content_type: только допустимые форматы изображений
        if photo.content_type is None:
            # Если content_type не передан — считаем JPEG (мобильные клиенты)
            content_type: str = "image/jpeg"
        elif photo.content_type not in _ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=415,
                detail="Поддерживаются только JPEG/PNG/WEBP/HEIC",
            )
        else:
            content_type = photo.content_type

        image_bytes = await photo.read()
        # Постчтение-проверка: Content-Length может лгать, сверяемся по факту
        if not image_bytes:
            raise HTTPException(status_code=422, detail="Фото пустое")
        if len(image_bytes) > _MAX_PHOTO_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Фото превышает лимит {_MAX_PHOTO_BYTES // (1024 * 1024)} МБ",
            )
        if not _is_valid_image_payload(image_bytes, content_type):
            raise HTTPException(
                status_code=422,
                detail="Файл не является корректным изображением выбранного формата",
            )

        # ── Шаг + строгая identity-связь с задачей (404 если нет) ────────────
        step_row = (await session.execute(
            text(
                "SELECT ps.n, ps.instruction_ru, ps.micro_skill, ps.expected_value, "
                "       p.text_ru AS statement, p.answer AS correct_answer "
                "FROM problems p "
                "JOIN decomposition_problems dp ON dp.idx = :d "
                "JOIN problem_steps ps ON ps.decomp_idx = dp.idx AND ps.n = :n "
                "WHERE p.id = :pid "
                "  AND dp.node_id = p.node_id "
                "  AND dp.answer = p.answer "
                "  AND dp.all_steps_verified = true "
                "  AND dp.needs_review = false "
                "  AND (p.content_idx = dp.idx OR dp.problems_db_id = p.id) "
                "LIMIT 1"
            ),
            {"d": decomp_idx, "n": step_n, "pid": problem_id},
        )).fetchone()
        if step_row is None:
            raise HTTPException(status_code=404,
                detail=f"Шаг {step_n} декомпозиции {decomp_idx} не найден")

        if not await _previous_drill_steps_solved(
            session,
            student_id=student.id,
            problem_id=problem_id,
            decomp_idx=decomp_idx,
            step_n=step_n,
        ):
            raise HTTPException(
                status_code=409,
                detail="Сначала заверши предыдущий шаг",
            )

        # ── Классификация (LlmUnavailable → 503) ─────────────────────────────
        try:
            cls: StepClassification = await classify_step_photo(
                image_bytes=image_bytes, content_type=content_type,
                statement=step_row.statement, instruction_ru=step_row.instruction_ru,
                expected_value=step_row.expected_value,
            )
        except LlmUnavailable as exc:
            logger.warning("LLM недоступен для step-submit: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="Сервис проверки фото временно недоступен. Попробуйте позже.",
            ) from exc

        # ── Порог: неуверенный match/mismatch → unsure ───────────────────────
        # ⚠️ Ревью Task 2: verdict валидируем против допустимого набора — всё
        # неожиданное трактуем как 'unsure' (мягкость: false-reject хуже пропуска).
        verdict = (
            cls.verdict
            if isinstance(cls.verdict, str)
            and cls.verdict in {"match", "mismatch", "unsure"}
            else "unsure"
        )
        try:
            confidence = float(cls.confidence)
        except (TypeError, ValueError, OverflowError):
            confidence = 0.0
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            confidence = 0.0
            verdict = "unsure"
        elif verdict in {"match", "mismatch"} and confidence < settings.step_confidence_threshold:
            verdict = "unsure"

        # ── Grounded hint только при mismatch ────────────────────────────────
        # mistake_ru не показываем: контент может раскрыть expected_value.
        # Fingerprint используем только как аналитическую метку при точном
        # совпадении наблюдения с текущими decomposition/micro_skill.
        hint: str | None = None
        matched_ms: str | None = None
        seen_value = cls.seen_value.strip()[:500] if isinstance(cls.seen_value, str) else None
        if not seen_value:
            seen_value = None
        if verdict == "mismatch":
            fp = None
            if seen_value:
                candidate = await match_fingerprint(
                    session,
                    problem_id=problem_id,
                    answer_given=seen_value,
                )
                if (
                    candidate is not None
                    and candidate.decomp_idx == decomp_idx
                    and candidate.micro_skill == step_row.micro_skill
                ):
                    fp = candidate

            safe_instruction = safe_step_instruction(
                step_row.instruction_ru,
                expected_value=step_row.expected_value,
                correct_answer=step_row.correct_answer,
            )
            hint = f"Проверь этот шаг ещё раз: {safe_instruction}"
            if fp is not None:
                matched_ms = step_row.micro_skill

        # ── Путь фото (относительно photo_dir) ───────────────────────────────
        file_name = f"{uuid4().hex}{_IMAGE_EXTENSIONS[content_type]}"
        photo_path = f"steps/{student.id}/{file_name}"
        file_path = Path(settings.photo_dir) / photo_path

        # Сначала гарантируем durable-файл. Иначе нельзя отвечать успехом и
        # оставлять в БД submission, у которого фактически нет изображения.
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(image_bytes)
        except OSError as exc:
            logger.error("Не удалось сохранить фото шага (%s): %s", photo_path, exc)
            raise HTTPException(
                status_code=503,
                detail="Не удалось сохранить фото. Попробуйте ещё раз.",
            ) from exc

        # ── INSERT ВСЕГДА (включая unsure) ───────────────────────────────────
        try:
            await session.execute(
                text("INSERT INTO step_submissions "
                     "(student_id, decomp_idx, step_n, problem_id, verdict, confidence, "
                     " matched_micro_skill, photo_path, created_at) "
                     "VALUES (:sid,:d,:n,:pid,:v,:conf,:ms,:path,NOW())"),
                {"sid": student.id, "d": decomp_idx, "n": step_n, "pid": problem_id,
                 "v": verdict, "conf": confidence, "ms": matched_ms, "path": photo_path},
            )
            await session.commit()
        except Exception:
            try:
                file_path.unlink(missing_ok=True)
            except OSError as cleanup_exc:
                logger.error("Не удалось удалить orphan-фото %s: %s", photo_path, cleanup_exc)
            raise
    finally:
        await session.close()

    return StepSubmitOut(verdict=verdict, hint=hint, confidence=confidence, step_n=step_n)


# ── Verification (closure): проверочная задача того же навыка ─────────────────

class VerificationStartIn(BaseModel):
    problem_id: int
    micro_skill: str | None = None


class VerificationStartOut(BaseModel):
    problem_id: int
    node_id: str
    topic_label: str
    statement: str
    micro_skill: str | None
    # Человеческая подпись micro_skill (micro_skills.label_ru); §2.2 — запрет
    # голых кодов в UI. micro_skill здесь эхо клиентского payload, поэтому
    # подпись ищем явным lookup, а не переносим готовое значение из БД.
    micro_skill_label: str | None
    xp: int


class VerificationAnswerIn(BaseModel):
    problem_id: int
    answer: str
    micro_skill: str | None = None


class VerificationAnswerOut(BaseModel):
    correct: bool


_VERIFICATION_XP = 30


@router.post("/verification/start", response_model=VerificationStartOut)
async def post_verification_start(request: Request, payload: VerificationStartIn) -> VerificationStartOut:
    """Даёт контрольную задачу того же узла (другую), чтобы закрыть ошибку."""
    session, _student = await _get_current_student(request)
    try:
        prob = (await session.execute(
            text("SELECT node_id FROM problems WHERE id = :pid"),
            {"pid": payload.problem_id},
        )).fetchone()
        if prob is None:
            raise HTTPException(status_code=404, detail=f"Задача {payload.problem_id} не найдена")

        node_id: str = prob.node_id

        vp = await pick_verification_problem(
            session, node_id=node_id, exclude_problem_id=payload.problem_id
        )
        if vp is None:
            raise HTTPException(status_code=404, detail="Нет проверочной задачи для этого узла")

        topic_label = (await session.execute(
            text("SELECT name_ru FROM nodes WHERE id = :nid"), {"nid": node_id}
        )).scalar() or node_id

        # Человеческая подпись micro_skill (эхо клиента) — lookup явным запросом
        micro_skill_label: str | None = None
        if payload.micro_skill:
            micro_skill_label = (
                await session.execute(
                    text("SELECT label_ru FROM micro_skills WHERE code = :ms"),
                    {"ms": payload.micro_skill},
                )
            ).scalar()
    finally:
        await session.close()

    return VerificationStartOut(
        problem_id=vp.id, node_id=vp.node_id, topic_label=topic_label,
        statement=vp.text_ru, micro_skill=payload.micro_skill,
        micro_skill_label=micro_skill_label, xp=_VERIFICATION_XP,
    )


@router.post("/verification/answer", response_model=VerificationAnswerOut)
async def post_verification_answer(request: Request, payload: VerificationAnswerIn) -> VerificationAnswerOut:
    """Проверяет контрольную, обновляет прогресс и закрывает ошибку при верном ответе."""
    session, student = await _get_current_student(request)
    try:
        problem = await session.get(Problem, payload.problem_id)
        if problem is None:
            raise HTTPException(status_code=404, detail=f"Задача {payload.problem_id} не найдена")

        correct = check_answer(payload.answer, problem.answer, problem.answer_type)
        # Контрольная — самостоятельная попытка на перенос, поэтому она должна
        # попадать в историю и BKT. source='closure' также служит устойчивым
        # доказательством закрытия очереди: новый неверный ответ позднее снова её откроет.
        await record_attempt(
            session,
            student.id,
            problem,
            payload.answer,
            correct,
            source="closure",
        )

        if correct:
            # recurring_errors ключуется ДИАГНОСТИРОВАННЫМ failed_micro_skill, а не
            # payload.micro_skill (это primary_micro_skill decomp'а FE) — ключи расходятся.
            # Резолвим по node_id проверочной задачи, а не по micro_skill.
            await session.execute(
                text(
                    "UPDATE recurring_errors SET resolved = true "
                    "WHERE student_id = :sid AND node_id = :nid AND resolved = false"
                ),
                {"sid": student.id, "nid": problem.node_id},
            )
        await session.commit()
    finally:
        await session.close()

    return VerificationAnswerOut(correct=correct)


# ── Climb-down: decomp полегче для того же навыка ─────────────────────────────

class EasierDecompOut(BaseModel):
    decomp_idx: int
    node_id: str
    primary_micro_skill: str | None
    step_count: int
    steps: list[StepOut]


@router.get("/easier", response_model=EasierDecompOut)
async def get_easier(
    request: Request,
    micro_skill: str = Query(..., description="Код микро-умения"),
    exclude_idx: int | None = Query(None, description="Исключить текущий decomp_idx"),
) -> EasierDecompOut:
    """Возвращает decomp с наименьшим числом шагов для навыка (climb-down)."""
    session, _student = await _get_current_student(request)
    try:
        row = await pick_easier_decomp(session, micro_skill=micro_skill, exclude_idx=exclude_idx)
        if row is None:
            raise HTTPException(status_code=404, detail="Нет более простой декомпозиции для навыка")
        # LEFT JOIN micro_skills — человеческая подпись умения шага (§2.2)
        steps_raw = await session.execute(
            text(
                "SELECT ps.n, ps.instruction_ru, ps.micro_skill, ps.expected_value, "
                "       ms.label_ru AS micro_skill_label "
                "FROM problem_steps ps "
                "LEFT JOIN micro_skills ms ON ms.code = ps.micro_skill "
                "WHERE ps.decomp_idx = :didx ORDER BY ps.n"
            ),
            {"didx": row.idx},
        )
        steps = [
            StepOut(n=s.n, instruction_ru=safe_step_instruction(
                        s.instruction_ru,
                        expected_value=s.expected_value,
                        correct_answer=row.answer,
                    ), micro_skill=s.micro_skill,
                    micro_skill_label=s.micro_skill_label,
                    kind="compute", reveal=None)
            for s in steps_raw
        ]
    finally:
        await session.close()

    return EasierDecompOut(
        decomp_idx=row.idx, node_id=row.node_id,
        primary_micro_skill=row.primary_micro_skill, step_count=row.step_count, steps=steps,
    )


# ── Чат-тьютор: multi-turn диалог после диагноза ──────────────────────────────

class TutorChatIn(BaseModel):
    problem_id: int
    decomp_idx: int | None = None
    # Ступень лесенки, на которой застрял ученик (опционально) — тьютор фокусирует
    # диалог именно на ней. None → общий диалог по задаче. ge=1: мусорные значения
    # (отрицательные/ноль) не должны попадать в текст промпта.
    step_n: int | None = Field(default=None, ge=1)
    message: str = Field(min_length=1, max_length=1000)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message must not be blank")
        return value


class TutorMessageOut(BaseModel):
    role: str
    content: str


class TutorChatOut(BaseModel):
    session_id: int
    reply: str
    history: list[TutorMessageOut]


@router.post("/tutor/chat", response_model=TutorChatOut)
@limiter.limit("15/minute")
@ai_ip_limit
async def post_tutor_chat(request: Request, payload: TutorChatIn) -> TutorChatOut:
    """Один ход диалога с тьютором. Сессия auto-create по (студент, задача)."""
    session, student = await _get_current_student(request)
    try:
        # Проверяем задачу (404)
        prob = (await session.execute(
            text("SELECT node_id FROM problems WHERE id = :pid"),
            {"pid": payload.problem_id},
        )).fetchone()
        if prob is None:
            raise HTTPException(status_code=404, detail=f"Задача {payload.problem_id} не найдена")

        if payload.decomp_idx is not None:
            valid_decomp = (await session.execute(
                text(
                    "SELECT 1 FROM decomposition_problems dp "
                    "JOIN problems p ON p.id = :pid "
                    "WHERE dp.idx = :didx "
                    "  AND dp.node_id = p.node_id "
                    "  AND dp.answer = p.answer "
                    "  AND dp.all_steps_verified = true "
                    "  AND dp.needs_review = false "
                    "  AND (p.content_idx = dp.idx OR dp.problems_db_id = p.id) "
                    "LIMIT 1"
                ),
                {"pid": payload.problem_id, "didx": payload.decomp_idx},
            )).scalar()
            if valid_decomp is None:
                raise HTTPException(
                    status_code=404,
                    detail="Декомпозиция не относится к выбранной задаче",
                )

        # Reuse или create сессии
        sess_row = (await session.execute(
            text(
                "SELECT id FROM tutor_sessions "
                "WHERE student_id = :sid AND problem_id = :pid "
                "ORDER BY id DESC LIMIT 1"
            ),
            {"sid": student.id, "pid": payload.problem_id},
        )).fetchone()
        if sess_row is None:
            # ON CONFLICT DO NOTHING — защита от гонки при параллельных запросах
            # (два запроса могут одновременно не найти сессию в SELECT выше).
            # Опирается на UNIQUE (student_id, problem_id) в модели TutorSession.
            insert_row = (await session.execute(
                text(
                    "INSERT INTO tutor_sessions (student_id, problem_id, node_id, created_at) "
                    "VALUES (:sid, :pid, :nid, NOW()) "
                    "ON CONFLICT (student_id, problem_id) DO NOTHING "
                    "RETURNING id"
                ),
                {"sid": student.id, "pid": payload.problem_id, "nid": prob.node_id},
            )).fetchone()
            if insert_row is None:
                # Конфликт — параллельный запрос уже создал сессию; забираем её id
                session_id = (await session.execute(
                    text(
                        "SELECT id FROM tutor_sessions "
                        "WHERE student_id = :sid AND problem_id = :pid "
                        "ORDER BY id DESC LIMIT 1"
                    ),
                    {"sid": student.id, "pid": payload.problem_id},
                )).scalar_one()
            else:
                session_id = insert_row.id
        else:
            session_id = sess_row.id

        # История из БД
        hist_rows = await session.execute(
            text(
                "SELECT role, content FROM tutor_messages "
                "WHERE session_id = :sess ORDER BY id"
            ),
            {"sess": session_id},
        )
        history = [{"role": h.role, "content": h.content} for h in hist_rows]

        # Генерация ответа (LLM). При сбое не оставляем ребёнка в тупике:
        # сохраняем честный безопасный вопрос без чисел и ожидаемых ответов.
        try:
            reply = await generate_tutor_reply(
                session,
                student_id=student.id,
                problem_id=payload.problem_id,
                decomp_idx=payload.decomp_idx,
                step_n=payload.step_n,
                user_message=payload.message,
                history=history,
            )
        except LlmUnavailable as exc:
            logger.warning("LLM недоступен для tutor/chat: %s", exc)
            reply = tutor_unavailable_fallback()
        # Defense-in-depth: даже устаревший/замоканный generator не может
        # записать и вернуть free-form assistant-текст.
        reply = sanitize_tutor_output(reply)

        # Persist обе реплики
        await session.execute(
            text(
                "INSERT INTO tutor_messages (session_id, role, content, created_at) VALUES "
                "(:sess, 'user', :u, NOW()), (:sess, 'assistant', :a, NOW())"
            ),
            {"sess": session_id, "u": payload.message, "a": reply},
        )
        await session.commit()

        # Итоговая история
        full = await session.execute(
            text("SELECT role, content FROM tutor_messages WHERE session_id = :sess ORDER BY id"),
            {"sess": session_id},
        )
        out_history = [
            TutorMessageOut(
                role=r.role,
                content=(
                    sanitize_tutor_output(r.content)
                    if r.role == "assistant"
                    else r.content
                ),
            )
            for r in full
        ]
    finally:
        await session.close()

    return TutorChatOut(session_id=session_id, reply=reply, history=out_history)


# ── Мини-срез: быстрый онбординг из 12 задач (Блок 1.0) ───────────────────────

class SrezTaskOut(BaseModel):
    problem_id: int
    statement: str
    answer_type: str | None
    node_title: str
    position: int
    total: int


class SrezStartOut(BaseModel):
    tasks: list[SrezTaskOut]


class SrezAnswerIn(BaseModel):
    problem_id: int
    answer: str
    elapsed_ms: int | None = None


class SrezAnswerOut(BaseModel):
    is_correct: bool


@router.post("/srez/start", response_model=SrezStartOut)
async def post_srez_start(request: Request) -> SrezStartOut:
    """Мини-срез: сервер выбирает 12 задач в окне difficulty КЛАССА ученика (разброс тем,
    рост сложности, 2 стретча сверху). Стейт держит клиент. Ответ НЕ содержит ответов/решений."""
    session, student = await _get_current_student(request)
    try:
        # grade тянем из профиля — окно difficulty среза подбирается под класс ученика.
        rows = await pick_srez_problems(
            session, student_id=student.id, count=12, grade=student.grade
        )
    finally:
        await session.close()
    total = len(rows)
    tasks = [
        SrezTaskOut(
            problem_id=r.id, statement=r.statement, answer_type=r.answer_type,
            node_title=r.node_title, position=i + 1, total=total,
        )
        for i, r in enumerate(rows)
    ]
    return SrezStartOut(tasks=tasks)


@router.post("/srez/answer", response_model=SrezAnswerOut)
@limiter.limit("30/minute")
async def post_srez_answer(request: Request, payload: SrezAnswerIn) -> SrezAnswerOut:
    """Проверяет ответ задачи среза и пишет attempt(source='diagnostic').
    НЕ возвращает correct_answer/solution (задачи потом попадут в drill)."""
    session, student = await _get_current_student(request)
    try:
        prob = (await session.execute(
            text("SELECT node_id, answer, answer_type FROM problems WHERE id = :pid"),
            {"pid": payload.problem_id},
        )).fetchone()
        if prob is None:
            raise HTTPException(status_code=404, detail=f"Задача {payload.problem_id} не найдена")
        is_correct = check_answer(payload.answer, prob.answer, prob.answer_type)
        await session.execute(
            text(
                "INSERT INTO attempts "
                "(student_id, problem_id, node_id, answer_given, is_correct, response_time_ms, source, created_at) "
                "VALUES (:sid, :pid, :nid, :ans, :ok, :ms, 'diagnostic', NOW())"
            ),
            {"sid": student.id, "pid": payload.problem_id, "nid": prob.node_id,
             "ans": payload.answer, "ok": is_correct, "ms": payload.elapsed_ms},
        )
        if not is_correct:
            await session.execute(
                text(
                    "UPDATE recurring_errors SET resolved = false "
                    "WHERE student_id = :sid AND node_id = :nid AND resolved = true"
                ),
                {"sid": student.id, "nid": prob.node_id},
            )
        await session.commit()
    finally:
        await session.close()
    return SrezAnswerOut(is_correct=is_correct)


# ── Телеметрия UX: batch-приём событий + owner-only CSV-экспорт (Блок 1.0) ────

class EventIn(BaseModel):
    event_type: str
    payload: dict | None = None


class EventsBatchIn(BaseModel):
    events: list[EventIn]


class EventsBatchOut(BaseModel):
    # received — сколько событий пришло в запросе; inserted — сколько реально записано
    # (после усечения до 20). Раньше поля не было — клиент не видел, что часть батча отброшена.
    received: int
    inserted: int


@router.post("/events", response_model=EventsBatchOut)
@limiter.limit("60/minute")
async def post_events(request: Request, payload: EventsBatchIn) -> EventsBatchOut:
    """Пишет batch событий телеметрии (≤20). Неизвестные event_type НЕ отклоняем."""
    session, student = await _get_current_student(request)
    try:
        received = len(payload.events)
        events = payload.events[:20]  # cap 20 за запрос
        for ev in events:
            await session.execute(
                text(
                    "INSERT INTO events (student_id, event_type, payload, created_at) "
                    "VALUES (:sid, :et, CAST(:pl AS JSONB), NOW())"
                ),
                {"sid": student.id, "et": ev.event_type,
                 "pl": json.dumps(ev.payload) if ev.payload is not None else None},
            )
        await session.commit()
    finally:
        await session.close()
    return EventsBatchOut(received=received, inserted=len(events))


@router.get("/events/export")
async def get_events_export(
    request: Request, format: str = Query("csv", pattern="^csv$")
) -> Response:
    """CSV-выгрузка всех событий. Только владелец (settings.owner_student_id), иначе 403."""
    session, student = await _get_current_student(request)
    try:
        is_owner = settings.owner_student_id != 0 and student.id == settings.owner_student_id
        if not is_owner:
            raise HTTPException(status_code=403, detail="Только для владельца")
        rows = (await session.execute(
            text("SELECT id, student_id, event_type, payload, created_at "
                 "FROM events ORDER BY created_at")
        )).fetchall()
    finally:
        await session.close()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "student_id", "event_type", "payload", "created_at"])
    for r in rows:
        payload = r.payload if isinstance(r.payload, str) else json.dumps(r.payload) if r.payload else ""
        writer.writerow([r.id, r.student_id, r.event_type, payload, r.created_at])
    return Response(content=buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=events.csv"})


# ── Датасет пошаговых сдач: owner-only CSV-экспорт + отдача фото (Блок 1.2) ───


@router.get("/step-submissions/export")
async def get_step_submissions_export(
    request: Request, format: str = Query("csv", pattern="^csv$")
) -> Response:
    """CSV-выгрузка step_submissions (мета). Только владелец, иначе 403.

    photo_path отдаём как есть (относительный путь внутри photo_dir) — абсолютные
    пути на диске наружу не палим.
    """
    session, student = await _get_current_student(request)
    try:
        is_owner = settings.owner_student_id != 0 and student.id == settings.owner_student_id
        if not is_owner:
            raise HTTPException(status_code=403, detail="Только для владельца")
        rows = (await session.execute(
            text(
                "SELECT id, student_id, decomp_idx, step_n, problem_id, verdict, "
                "       confidence, matched_micro_skill, photo_path, created_at "
                "FROM step_submissions ORDER BY created_at"
            )
        )).fetchall()
    finally:
        await session.close()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "id", "student_id", "decomp_idx", "step_n", "problem_id", "verdict",
        "confidence", "matched_micro_skill", "photo_path", "created_at",
    ])
    for r in rows:
        writer.writerow([
            r.id, r.student_id, r.decomp_idx, r.step_n, r.problem_id, r.verdict,
            r.confidence, r.matched_micro_skill, r.photo_path, r.created_at,
        ])
    return Response(content=buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=step_submissions.csv"})


@router.get("/step-photo/{submission_id}")
async def get_step_photo(request: Request, submission_id: int) -> Response:
    """Фото сдачи по id. Только владелец (403). 404 если строки/файла нет.

    Owner-гейт ДО чтения photo_path — не-владельцу не палим сам факт
    существования строки. Путь файла собираем ТОЛЬКО из settings.photo_dir +
    photo_path из БД — никакого пользовательского ввода в путь.
    """
    session, student = await _get_current_student(request)
    try:
        is_owner = settings.owner_student_id != 0 and student.id == settings.owner_student_id
        if not is_owner:
            raise HTTPException(status_code=403, detail="Только для владельца")
        row = (await session.execute(
            text("SELECT photo_path FROM step_submissions WHERE id = :id"),
            {"id": submission_id},
        )).fetchone()
    finally:
        await session.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Сдача не найдена")
    file_path = Path(settings.photo_dir) / row.photo_path
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Файл фото не найден")
    media_type = _IMAGE_MEDIA_TYPES_BY_SUFFIX.get(file_path.suffix.casefold())
    if media_type is None:
        raise HTTPException(status_code=415, detail="Формат сохранённого фото не поддерживается")
    return Response(content=file_path.read_bytes(), media_type=media_type)
