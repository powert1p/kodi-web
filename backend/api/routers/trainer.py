"""Роутер тренажёра ошибок: /api/trainer/wrong-tasks, /api/trainer/analytics,
/api/trainer/diagnose.

Не растёт api/routes.py — отдельный модуль согласно AUDIT API-3.
Использует _get_current_student из routes.py (JWT-логику не дублируем).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Form, HTTPException, Query, Request, UploadFile
from fastapi import File as FastApiFile
from pydantic import BaseModel
from sqlalchemy import text

from api.routes import _get_current_student
from core.config import settings
from core.llm_openai import LlmUnavailable, diagnose_photo
from core.trainer import (
    StepDTO,
    WrongTask,
    build_problem_topics,
    build_wrong_tasks,
    match_fingerprint,
    resolve_decomp,
)

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


# ── Pydantic-схема ответа /diagnose ──────────────────────────────────────────

class DiagnosisOut(BaseModel):
    """Ответ эндпоинта /diagnose."""

    transcription: str
    failed_step: int | None
    cause_text: str
    level: int
    micro_skill: str | None
    confidence: float
    image_ref: str          # путь относительно photo_dir


# ── Ограничение размера загружаемого фото ────────────────────────────────────

_MAX_PHOTO_BYTES = 8 * 1024 * 1024  # 8 МБ


@router.post("/diagnose", response_model=DiagnosisOut)
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
      5. resolve_decomp → canonical_steps; correct_answer из задачи.
      6. diagnose_photo (LlmUnavailable → 503).
      7. Сохраняем файл: settings.photo_dir/{student_id}/{uuid}.jpg.
      8. INSERT INTO error_captures.
      9. UPSERT INTO recurring_errors (если micro_skill известен).
      10. Возвращаем DiagnosisOut.
    """
    session, student = await _get_current_student(request)
    try:
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
        _ALLOWED_CONTENT_TYPES = {
            "image/jpeg",
            "image/png",
            "image/webp",
            "image/heic",
            "image/heif",
        }
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
        if len(image_bytes) > _MAX_PHOTO_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Фото превышает лимит {_MAX_PHOTO_BYTES // (1024 * 1024)} МБ",
            )

        # ── 3. Определяем wrong_answer ────────────────────────────────────────
        wrong_answer: str | None = None
        if attempt_id is not None:
            # Берём answer_given из конкретной попытки (если принадлежит студенту)
            att_row = await session.execute(
                text(
                    "SELECT answer_given FROM attempts "
                    "WHERE id = :aid AND student_id = :sid AND problem_id = :pid"
                ),
                {"aid": attempt_id, "sid": student.id, "pid": problem_id},
            )
            att = att_row.fetchone()
            if att is not None:
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

        # ── 5. resolve_decomp → canonical_steps ──────────────────────────────
        decomp = await resolve_decomp(session, problem_id=problem_id, node_id=node_id, answer=correct_answer)
        canonical_steps: list[dict] = []
        if decomp is not None:
            steps_rows = await session.execute(
                text(
                    "SELECT n, instruction_ru, expected_value FROM problem_steps "
                    "WHERE decomp_idx = :didx ORDER BY n"
                ),
                {"didx": decomp.idx},
            )
            canonical_steps = [
                {"n": s.n, "instruction_ru": s.instruction_ru, "expected_value": s.expected_value}
                for s in steps_rows
            ]

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

        # ── 7. Вычисляем image_ref заранее (путь относительно photo_dir) ────────
        # Вычисляем до коммита; запись файла — после коммита (во избежание orphan-файлов)
        file_name = f"{uuid4().hex}.jpg"
        image_ref = f"{student.id}/{file_name}"

        # ── 8. INSERT INTO error_captures ─────────────────────────────────────
        # model берём из первого элемента цепочки (именно та, что используется first-in-chain)
        model_name: str = settings.openai_model_chain[0] if settings.openai_model_chain else "unknown"
        # Используем micro_skill из vision-результата; fallback — из fingerprint
        failed_micro_skill: str | None = result.micro_skill or fallback_micro_skill

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
                "aid": attempt_id,
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
        if failed_micro_skill:
            await session.execute(
                text(
                    "INSERT INTO recurring_errors "
                    "(student_id, micro_skill, node_id, error_count, last_seen_at, last_cause_text, resolved, created_at) "
                    "VALUES (:sid, :ms, :nid, 1, NOW(), :cause, false, NOW()) "
                    "ON CONFLICT (student_id, micro_skill) DO UPDATE SET "
                    "  error_count = recurring_errors.error_count + 1, "
                    "  last_seen_at = NOW(), "
                    "  last_cause_text = EXCLUDED.last_cause_text, "
                    "  node_id = EXCLUDED.node_id"
                ),
                {
                    "sid": student.id,
                    "ms": failed_micro_skill,
                    "nid": node_id,
                    "cause": result.cause_text,
                },
            )

        # ── Коммит DB ────────────────────────────────────────────────────────
        # Сначала коммитим — строка в БД первична; файл на диске — артефакт.
        # Если файл не запишется, строка уже сохранена и проблема детектируема.
        await session.commit()

    finally:
        await session.close()

    # ── Запись файла фото на диск (ПОСЛЕ коммита) ────────────────────────────
    # photo_dir из settings — абсолютный путь на хосте
    # Делается вне try/finally-блока сессии: DB-строка уже есть, ошибка ФС не критична.
    photo_dir = Path(settings.photo_dir)
    student_dir = photo_dir / str(student.id)
    try:
        student_dir.mkdir(parents=True, exist_ok=True)
        file_path = student_dir / file_name
        file_path.write_bytes(image_bytes)
    except Exception as exc:  # noqa: BLE001
        # Логируем предупреждение; не возвращаем 500 — DB-запись уже успешна
        logger.warning(
            "Не удалось записать фото на диск (image_ref=%s): %s",
            image_ref,
            exc,
        )

    return DiagnosisOut(
        transcription=result.transcription,
        failed_step=result.failed_step,
        cause_text=result.cause_text,
        level=result.level,
        micro_skill=result.micro_skill,
        confidence=result.confidence,
        image_ref=image_ref,
    )
