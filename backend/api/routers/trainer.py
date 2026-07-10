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
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Form, HTTPException, Query, Request, UploadFile
from fastapi import File as FastApiFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import text

from api.routes import _get_current_student, limiter
from core.agent_context import build_agent_context
from core.config import settings
from core.grading import check_answer
from core.llm_openai import LlmUnavailable, StepClassification, classify_step_photo, diagnose_photo
from core.srez import pick_srez_problems
from core.trainer import (
    StepDTO,
    WrongTask,
    build_problem_topics,
    build_wrong_tasks,
    match_fingerprint,
    pick_easier_decomp,
    pick_verification_problem,
)
from core.tutor import generate_tutor_reply

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trainer", tags=["trainer"])


# ── Pydantic v2 response-схемы ────────────────────────────────────────────────


class StepOut(BaseModel):
    """Один шаг декомпозиции для клиента."""

    n: int
    instruction_ru: str
    micro_skill: str
    # Человеческая подпись умения (micro_skills.label_ru); None — код не найден в
    # каталоге. Фронт обязан показывать её вместо micro_skill (запрет §2.2).
    micro_skill_label: str | None
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


def _step_to_out(step: StepDTO) -> StepOut:
    """Конвертирует StepDTO → StepOut."""
    return StepOut(
        n=step.n,
        instruction_ru=step.instruction_ru,
        micro_skill=step.micro_skill,
        micro_skill_label=step.micro_skill_label,
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
        primary_micro_skill_label=task.primary_micro_skill_label,
        decomp_idx=task.decomp_idx,
        steps=[_step_to_out(s) for s in task.steps],
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
      5. build_agent_context → canonical_steps; correct_answer из задачи.
      6. diagnose_photo (LlmUnavailable → 503).
      7. Сохраняем файл: settings.photo_dir/{student_id}/{uuid}.jpg.
      8. INSERT INTO error_captures.
      9. UPSERT INTO recurring_errors (если micro_skill известен).
      10. Возвращаем DiagnosisOut.
    """
    session, student = await _get_current_student(request)
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

        # ── 5. Grounding через единый context-pack ───────────────────────────
        agent_ctx = await build_agent_context(
            session, student_id=student.id, problem_id=problem_id
        )
        canonical_steps: list[dict] = [
            {"n": s["n"], "instruction_ru": s["instruction_ru"], "expected_value": s["expected_value"]}
            for s in agent_ctx.canonical_steps
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

        # Человеческая подпись умения для клиента (§2.2 — запрет голых кодов в UI).
        # Подпись строим для result.micro_skill — того же кода, что уходит в ответ
        # (DiagnosisOut.micro_skill), а не для failed_micro_skill (может включать
        # fallback-код из fingerprint, который клиенту не отдаётся).
        result_micro_skill_label: str | None = None
        if result.micro_skill:
            result_micro_skill_label = (
                await session.execute(
                    text("SELECT label_ru FROM micro_skills WHERE code = :ms"),
                    {"ms": result.micro_skill},
                )
            ).scalar()

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
        micro_skill_label=result_micro_skill_label,
        confidence=result.confidence,
        image_ref=image_ref,
    )


# ── Пошаговая сдача: фото одного шага лесенки (Блок 1.2) ──────────────────────

class StepSubmitOut(BaseModel):
    """Ответ эндпоинта /step-submit."""

    verdict: str            # match | mismatch | unsure
    hint: str | None        # mistake_ru при mismatch, иначе None (expected_value не раскрываем)
    confidence: float
    step_n: int


@router.post("/step-submit", response_model=StepSubmitOut)
@limiter.limit("15/minute")
async def post_step_submit(
    request: Request,
    decomp_idx: int = Form(...),
    step_n: int = Form(...),
    problem_id: int | None = Form(None),
    photo: UploadFile = FastApiFile(...),
) -> StepSubmitOut:
    """Принимает фото одного шага лесенки → узкая vision-классификация → мягкий вердикт.

    Flow:
      1. Auth + consent-гейт (как /diagnose).
      2. size/content-type гейты (413/415) — паттерн /diagnose.
      3. Загружаем шаг из problem_steps (404 если нет).
      4. statement — из problems, если problem_id передан.
      5. classify_step_photo (LlmUnavailable → 503).
      6. Порог: mismatch с confidence < settings.step_confidence_threshold → unsure
         (false-reject хуже пропуска — мягкость по умолчанию).
      7. При mismatch — fingerprint-hint из problem_fingerprints по (decomp_idx, micro_skill).
      8. INSERT INTO step_submissions ВСЕГДА (включая unsure).
      9. Файл фото — на диск ПОСЛЕ коммита (steps/{student_id}/{uuid}.jpg).
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

        # ── Шаг из problem_steps (404 если нет) ──────────────────────────────
        step_row = (await session.execute(
            text("SELECT n, instruction_ru, micro_skill, expected_value FROM problem_steps "
                 "WHERE decomp_idx = :d AND n = :n"),
            {"d": decomp_idx, "n": step_n},
        )).fetchone()
        if step_row is None:
            raise HTTPException(status_code=404,
                detail=f"Шаг {step_n} декомпозиции {decomp_idx} не найден")

        # ── statement (контекст) — если problem_id задан ─────────────────────
        statement = ""
        if problem_id is not None:
            prob = (await session.execute(
                text("SELECT text_ru FROM problems WHERE id = :pid"),
                {"pid": problem_id},
            )).fetchone()
            if prob is not None:
                statement = prob.text_ru

        # ── Классификация (LlmUnavailable → 503) ─────────────────────────────
        try:
            cls: StepClassification = await classify_step_photo(
                image_bytes=image_bytes, content_type=content_type,
                statement=statement, instruction_ru=step_row.instruction_ru,
                expected_value=step_row.expected_value,
            )
        except LlmUnavailable as exc:
            logger.warning("LLM недоступен для step-submit: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="Сервис проверки фото временно недоступен. Попробуйте позже.",
            ) from exc

        # ── Порог: mismatch с низкой confidence → unsure ─────────────────────
        # ⚠️ Ревью Task 2: verdict валидируем против допустимого набора — всё
        # неожиданное трактуем как 'unsure' (мягкость: false-reject хуже пропуска).
        verdict = cls.verdict if cls.verdict in {"match", "mismatch", "unsure"} else "unsure"
        if verdict == "mismatch" and cls.confidence < settings.step_confidence_threshold:
            verdict = "unsure"

        # ── fingerprint-hint только при mismatch ─────────────────────────────
        hint: str | None = None
        matched_ms: str | None = None
        if verdict == "mismatch":
            fp = (await session.execute(
                text("SELECT mistake_ru FROM problem_fingerprints "
                     "WHERE decomp_idx = :d AND micro_skill = :ms LIMIT 1"),
                {"d": decomp_idx, "ms": step_row.micro_skill},
            )).fetchone()
            if fp is not None:
                hint = fp.mistake_ru
                matched_ms = step_row.micro_skill

        # ── Путь фото (относительно photo_dir) ───────────────────────────────
        file_name = f"{uuid4().hex}.jpg"
        photo_path = f"steps/{student.id}/{file_name}"

        # ── INSERT ВСЕГДА (включая unsure) ───────────────────────────────────
        await session.execute(
            text("INSERT INTO step_submissions "
                 "(student_id, decomp_idx, step_n, problem_id, verdict, confidence, "
                 " matched_micro_skill, photo_path, created_at) "
                 "VALUES (:sid,:d,:n,:pid,:v,:conf,:ms,:path,NOW())"),
            {"sid": student.id, "d": decomp_idx, "n": step_n, "pid": problem_id,
             "v": verdict, "conf": cls.confidence, "ms": matched_ms, "path": photo_path},
        )
        await session.commit()
    finally:
        await session.close()

    # ── Файл фото — на диск ПОСЛЕ коммита (паттерн /diagnose) ───────────────
    photo_dir = Path(settings.photo_dir)
    student_dir = photo_dir / "steps" / str(student.id)
    try:
        student_dir.mkdir(parents=True, exist_ok=True)
        (student_dir / file_name).write_bytes(image_bytes)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Не удалось записать фото шага (%s): %s", photo_path, exc)

    return StepSubmitOut(verdict=verdict, hint=hint, confidence=cls.confidence, step_n=step_n)


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
    """Проверяет ответ на контрольную. Верно + micro_skill → recurring_errors.resolved=true."""
    session, student = await _get_current_student(request)
    try:
        prob = (await session.execute(
            text("SELECT node_id, answer, answer_type FROM problems WHERE id = :pid"),
            {"pid": payload.problem_id},
        )).fetchone()
        if prob is None:
            raise HTTPException(status_code=404, detail=f"Задача {payload.problem_id} не найдена")

        correct = check_answer(payload.answer, prob.answer, prob.answer_type)

        if correct:
            # recurring_errors ключуется ДИАГНОСТИРОВАННЫМ failed_micro_skill, а не
            # payload.micro_skill (это primary_micro_skill decomp'а FE) — ключи расходятся.
            # Резолвим по node_id проверочной задачи, а не по micro_skill.
            await session.execute(
                text(
                    "UPDATE recurring_errors SET resolved = true "
                    "WHERE student_id = :sid AND node_id = :nid AND resolved = false"
                ),
                {"sid": student.id, "nid": prob.node_id},
            )
            await session.commit()
    finally:
        await session.close()

    return VerificationAnswerOut(correct=correct)


# ── Climb-down: decomp полегче для того же навыка ─────────────────────────────

class EasierDecompOut(BaseModel):
    decomp_idx: int
    node_id: str
    answer: str
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
            StepOut(n=s.n, instruction_ru=s.instruction_ru, micro_skill=s.micro_skill,
                    micro_skill_label=s.micro_skill_label,
                    expected_value=s.expected_value, kind="compute", reveal=None)
            for s in steps_raw
        ]
    finally:
        await session.close()

    return EasierDecompOut(
        decomp_idx=row.idx, node_id=row.node_id, answer=row.answer,
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
    message: str


class TutorMessageOut(BaseModel):
    role: str
    content: str


class TutorChatOut(BaseModel):
    session_id: int
    reply: str
    history: list[TutorMessageOut]


@router.post("/tutor/chat", response_model=TutorChatOut)
@limiter.limit("15/minute")
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

        # Генерация ответа (LLM); LlmUnavailable → 503 (паттерн diagnose_photo)
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
            raise HTTPException(
                status_code=503,
                detail="Тьютор временно недоступен. Попробуйте позже.",
            ) from exc

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
        out_history = [TutorMessageOut(role=r.role, content=r.content) for r in full]
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
    return Response(content=file_path.read_bytes(), media_type="image/jpeg")
