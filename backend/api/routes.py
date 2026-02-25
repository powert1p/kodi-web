"""REST API routes for the kodi-nis-web Flutter client.

Endpoints:
  POST /api/auth/telegram       — Telegram OAuth login
  POST /api/auth/phone/check    — check if phone is registered
  POST /api/auth/phone/register — register with phone + name + PIN
  POST /api/auth/phone/login    — login with phone + PIN
  GET  /api/auth/me             — get current student profile

  GET  /api/stats/me            — personal statistics
  GET  /api/graph/me            — knowledge graph data (JSON)

  GET  /api/practice/next       — next practice problem
  POST /api/practice/answer     — submit answer
  POST /api/practice/skip       — skip problem
  POST /api/practice/report     — report a problem (complaint)

  POST /api/diagnostic/start    — start diagnostic/exam session
  GET  /api/diagnostic/question  — get next diagnostic question
  POST /api/diagnostic/answer   — submit diagnostic answer
  POST /api/diagnostic/finish   — finish diagnostic session
  GET  /api/diagnostic/status   — get diagnostic status
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import random
import time
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from slowapi import Limiter
from slowapi.util import get_remote_address

from core.bkt import MASTERY_THRESHOLD, is_mastered, record_attempt
from core.config import settings

limiter = Limiter(key_func=get_remote_address)
from core.grading import check_answer, check_with_claude
from core.selector import select_next_problem
from db.base import async_session
from db.models import Attempt, Edge, Mastery, Node, Problem, ProblemReport, Student

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

JWT_SECRET = settings.jwt_secret
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 30


# ── Pydantic schemas ─────────────────────────────────────────

class TelegramLoginBody(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int | None = None
    hash: str | None = None

class PhoneCheckBody(BaseModel):
    phone: str
    pin: str = ""

class PhoneRegisterBody(BaseModel):
    phone: str
    name: str
    pin: str

class PhoneLoginBody(BaseModel):
    phone: str
    pin: str

class AnswerBody(BaseModel):
    problem_id: int
    answer: str

class DiagnosticStartBody(BaseModel):
    mode: str = "exam"

class DiagnosticAnswerBody(BaseModel):
    problem_id: int
    answer: str
    elapsed_sec: float = 30.0

class SkipBody(BaseModel):
    problem_id: int
    answer: str = ""

class ReportBody(BaseModel):
    problem_id: int
    reason: str
    student_answer: str = ""

class ExamStartBody(BaseModel):
    num_problems: int = 20
    time_minutes: int = 40


# ── JWT helpers ───────────────────────────────────────────────

def _create_token(student_id: int) -> str:
    payload = {
        "sub": str(student_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> int:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")


async def _get_current_student(request: Request) -> tuple[AsyncSession, Student]:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization")
    student_id = _decode_token(auth[7:])

    session = async_session()
    student = await session.get(Student, student_id)
    if not student:
        await session.close()
        raise HTTPException(status_code=401, detail="Student not found")
    return session, student


# ── PIN hashing ───────────────────────────────────────────────

def _hash_pin(pin: str) -> str:
    import bcrypt
    return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()


def _verify_pin(pin: str, pin_hash: str) -> bool:
    import bcrypt
    # Support legacy SHA256 hashes (64 hex chars) for existing users
    if len(pin_hash) == 64:
        return hmac.compare_digest(hashlib.sha256(pin.encode()).hexdigest(), pin_hash)
    # bcrypt hash
    return bcrypt.checkpw(pin.encode(), pin_hash.encode())


# ── Telegram hash verification ────────────────────────────────

def _verify_telegram_hash(data: dict) -> bool:
    """Verify Telegram login widget data."""
    if not data.get("hash") or not data.get("auth_date"):
        return False
    check_hash = data.pop("hash", "")
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()) if v is not None)
    secret_key = hashlib.sha256(settings.bot_token.encode()).digest()
    hmac_hash = hmac.new(secret_key, data_check.encode(), hashlib.sha256).hexdigest()
    data["hash"] = check_hash
    if not hmac.compare_digest(hmac_hash, check_hash):
        return False
    if time.time() - int(data["auth_date"]) > 86400:
        return False
    return True


# ══════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════════════════════

@router.post("/auth/telegram")
@limiter.limit("10/minute")
async def auth_telegram(request: Request, body: TelegramLoginBody):
    tg_data = body.model_dump(exclude_none=True)
    if not _verify_telegram_hash(tg_data):
        raise HTTPException(status_code=401, detail="Invalid Telegram authentication")

    async with async_session() as session:
        student = await session.get(Student, body.id)
        if not student:
            student = Student(
                id=body.id,
                first_name=body.first_name,
                last_name=body.last_name,
                username=body.username,
                registered=True,
                lang="ru",
            )
            session.add(student)
            await session.commit()
        return {"access_token": _create_token(student.id)}


@router.post("/auth/phone/check")
@limiter.limit("10/minute")
async def auth_phone_check(request: Request, body: PhoneCheckBody):
    phone = body.phone.strip().replace(" ", "").replace("-", "")
    async with async_session() as session:
        result = await session.execute(
            select(Student).where(Student.phone == phone)
        )
        student = result.scalar_one_or_none()
        return {"exists": student is not None}


@router.post("/auth/phone/register")
@limiter.limit("5/minute")
async def auth_phone_register(request: Request, body: PhoneRegisterBody):
    phone = body.phone.strip().replace(" ", "").replace("-", "")
    if not phone or len(phone) < 10:
        raise HTTPException(status_code=400, detail="Некорректный номер телефона")
    if not body.pin or len(body.pin) < 4:
        raise HTTPException(status_code=400, detail="PIN должен быть минимум 4 символа")

    async with async_session() as session:
        existing = await session.execute(
            select(Student).where(Student.phone == phone)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Этот номер уже зарегистрирован")

        student = Student(
            id=int(time.time() * 1_000_000) + random.randint(0, 999_999),
            first_name=body.name,
            full_name=body.name,
            phone=phone,
            pin_hash=_hash_pin(body.pin),
            registered=True,
            lang="ru",
        )
        session.add(student)
        await session.commit()
        return {"access_token": _create_token(student.id)}


@router.post("/auth/phone/login")
@limiter.limit("5/minute")
async def auth_phone_login(request: Request, body: PhoneLoginBody):
    phone = body.phone.strip().replace(" ", "").replace("-", "")
    async with async_session() as session:
        result = await session.execute(
            select(Student).where(Student.phone == phone)
        )
        student = result.scalar_one_or_none()
        if not student:
            raise HTTPException(status_code=401, detail="Неверный номер телефона или PIN")
        if not student.pin_hash:
            raise HTTPException(status_code=401, detail="Для этого аккаунта не установлен PIN. Войдите через Telegram.")
        if not _verify_pin(body.pin, student.pin_hash):
            raise HTTPException(status_code=401, detail="Неверный номер телефона или PIN")
        # Upgrade legacy SHA256 hash to bcrypt on successful login
        if len(student.pin_hash) == 64:
            student.pin_hash = _hash_pin(body.pin)
            await session.commit()
        return {"access_token": _create_token(student.id)}


@router.get("/auth/me")
async def auth_me(request: Request):
    session, student = await _get_current_student(request)
    try:
        paused = student.paused_diagnostic
        has_paused = paused is not None and isinstance(paused, dict) and bool(paused)
        return {
            "id": student.id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "username": student.username,
            "full_name": student.full_name,
            "lang": student.lang,
            "registered": student.registered,
            "diagnostic_complete": student.diagnostic_complete,
            "has_paused_diagnostic": has_paused,
        }
    finally:
        await session.close()


# ══════════════════════════════════════════════════════════════
#  STATS ROUTES
# ══════════════════════════════════════════════════════════════

@router.get("/stats/me")
async def stats_me(request: Request, lang: str = "ru"):
    session, student = await _get_current_student(request)
    try:
        total_nodes_result = await session.execute(select(func.count(Node.id)))
        total_nodes = total_nodes_result.scalar() or 0

        mastered_result = await session.execute(
            select(func.count(Mastery.node_id)).where(
                Mastery.student_id == student.id,
                Mastery.p_mastery >= MASTERY_THRESHOLD,
            )
        )
        mastered_count = mastered_result.scalar() or 0

        attempts_result = await session.execute(
            text("""
                SELECT COUNT(*) AS total,
                       COALESCE(SUM(CASE WHEN is_correct THEN 1 ELSE 0 END), 0) AS correct,
                       AVG(response_time_ms) AS avg_time
                FROM attempts WHERE student_id = :sid AND source NOT IN ('skip', 'report')
            """),
            {"sid": student.id},
        )
        row = attempts_result.one()
        solved = int(row[0] or 0)
        correct = int(row[1] or 0)
        accuracy = round(correct / solved * 100) if solved > 0 else 0
        avg_time_s = round(float(row[2]) / 1000.0, 1) if row[2] else 0.0

        return {
            "solved": solved,
            "correct": correct,
            "accuracy": accuracy,
            "avg_time_s": avg_time_s,
            "mastered_count": mastered_count,
            "total_nodes": total_nodes,
            "current_streak": student.current_streak or 0,
            "longest_streak": student.longest_streak or 0,
        }
    finally:
        await session.close()


# ══════════════════════════════════════════════════════════════
#  GRAPH ROUTES
# ══════════════════════════════════════════════════════════════

_downstream_cache: dict[str, int] | None = None


async def _get_downstream_counts(session: AsyncSession) -> dict[str, int]:
    """Compute downstream node counts (cached — graph doesn't change at runtime)."""
    global _downstream_cache
    if _downstream_cache is not None:
        return _downstream_cache

    edges_result = await session.execute(select(Edge.from_node, Edge.to_node))
    all_edges = edges_result.all()

    nodes_result = await session.execute(select(Node.id))
    all_node_ids = {r[0] for r in nodes_result.all()}

    dependents_map: dict[str, set[str]] = {}
    for from_n, to_n in all_edges:
        dependents_map.setdefault(from_n, set()).add(to_n)

    def _count(nid: str, cache: dict[str, int]) -> int:
        if nid in cache:
            return cache[nid]
        direct = dependents_map.get(nid, set())
        total = len(direct)
        for dep in direct:
            total += _count(dep, cache)
        cache[nid] = total
        return total

    cache: dict[str, int] = {}
    _downstream_cache = {nid: _count(nid, cache) for nid in all_node_ids}
    return _downstream_cache


@router.get("/graph/me")
@limiter.limit("20/minute")
async def graph_me(request: Request, lang: str = "ru"):
    session, student = await _get_current_student(request)
    try:
        from core.web_graph import (
            _build_leaderboard,
            _compute_zones,
            _determine_status,
            _load_answer_details,
        )
        from core.diagnostic import compute_outer_fringe

        nodes_result = await session.execute(select(Node))
        all_nodes = list(nodes_result.scalars().all())

        edges_result = await session.execute(select(Edge.from_node, Edge.to_node))
        all_edges = edges_result.all()
        edge_tuples = [(e[0], e[1]) for e in all_edges]

        mastery_result = await session.execute(
            select(Mastery.node_id, Mastery.p_mastery, Mastery.attempts_correct,
                   Mastery.attempts_total).where(Mastery.student_id == student.id)
        )
        mastery_map = {}
        for row in mastery_result.all():
            mastery_map[row.node_id] = {
                "p_mastery": row.p_mastery,
                "correct": row.attempts_correct,
                "total": row.attempts_total,
            }

        tested_result = await session.execute(
            text("""
                SELECT DISTINCT node_id FROM attempts
                WHERE student_id = :sid AND source IN ('diagnostic', 'exam')
            """),
            {"sid": student.id},
        )
        tested_nodes = {row[0] for row in tested_result.all()}

        answer_details = await _load_answer_details(session, student.id)
        outer_fringe = await compute_outer_fringe(session, student.id)
        fringe_ids = {f["id"] for f in outer_fringe}

        all_node_ids = {n.id for n in all_nodes}
        zones = _compute_zones(all_node_ids, tested_nodes, edge_tuples, fringe_ids)

        prereq_map: dict[str, list[str]] = {}
        for from_n, to_n in edge_tuples:
            prereq_map.setdefault(to_n, []).append(from_n)

        failed_tested = set()
        for nid in tested_nodes:
            m = mastery_map.get(nid)
            if m and m["p_mastery"] < 0.2:
                failed_tested.add(nid)
        blocked_ids = set()
        for nid in all_node_ids:
            if nid in tested_nodes:
                continue
            prereqs = prereq_map.get(nid, [])
            if any(p in failed_tested for p in prereqs):
                blocked_ids.add(nid)

        downstream_counts = await _get_downstream_counts(session)

        nodes_json = []
        for node in all_nodes:
            m = mastery_map.get(node.id)
            p_mastery = m["p_mastery"] if m else 0.0
            status = _determine_status(node.id, tested_nodes, p_mastery, m is not None)
            details = answer_details.get(node.id)

            node_data = {
                "id": node.id,
                "name_ru": node.name_ru,
                "name_kz": node.name_kz or node.name_ru,
                "tag": node.tag or "other",
                "zone": zones.get(node.id, 3),
                "status": status,
                "p_mastery": round(p_mastery, 3) if m else None,
                "is_fringe": node.id in fringe_ids,
                "is_blocked": node.id in blocked_ids,
                "difficulty": node.difficulty or 1,
                "downstream": downstream_counts.get(node.id, 0),
                "q_total": details.get("q_total", 0) if details else 0,
                "q_correct": details.get("q_correct", 0) if details else 0,
            }
            nodes_json.append(node_data)

        edges_json = [{"source": e[0], "target": e[1]} for e in edge_tuples]

        return {
            "nodes": nodes_json,
            "edges": edges_json,
        }
    finally:
        await session.close()


# ══════════════════════════════════════════════════════════════
#  PRACTICE ROUTES
# ══════════════════════════════════════════════════════════════

@router.get("/practice/next")
async def practice_next(
    request: Request,
    count: int = Query(1, ge=1, le=10),
    lang: str = Query("ru", regex="^(ru|kz)$"),
    tag: str | None = Query(None, max_length=30),
    node_id: str | None = Query(None, max_length=10),
):
    session, student = await _get_current_student(request)
    try:
        student.practice_count = (student.practice_count or 0) + 1
        counter = student.practice_count
        await session.flush()

        BLOCK_SIZE = 5

        if node_id:
            # Explicit node request — bypass block logic
            from core.selector import _pick_problem_for_node
            problem = await _pick_problem_for_node(session, student.id, node_id)
            if not problem:
                raise HTTPException(status_code=404, detail="Нет задач для этой темы")
        else:
            # ── Block interleaving ──
            current_node = student.current_practice_node
            problems_done = student.problems_on_current_node or 0
            problem = None

            # Try to continue current block
            if current_node and problems_done < BLOCK_SIZE:
                mastery_row = (await session.execute(
                    select(Mastery).where(
                        Mastery.student_id == student.id,
                        Mastery.node_id == current_node,
                    )
                )).scalar_one_or_none()

                if mastery_row is None or not is_mastered(mastery_row):
                    from core.selector import _pick_problem_for_node
                    problem = await _pick_problem_for_node(
                        session, student.id, current_node,
                    )
                    if problem:
                        student.problems_on_current_node = problems_done + 1

            # Block ended / mastered / no problems → switch topic
            if problem is None:
                problem, new_node = await select_next_problem(
                    session, student.id, exclude_node=current_node,
                )
                if problem and new_node:
                    student.current_practice_node = new_node
                    student.problems_on_current_node = 1

        if not problem:
            raise HTTPException(status_code=404, detail="Все задачи решены! Поздравляем!")

        node = await session.get(Node, problem.node_id)
        node_name = (node.name_ru if lang == "ru" else (node.name_kz or node.name_ru)) if node else problem.node_id
        problem_text = problem.text_ru if lang == "ru" else (problem.text_kz or problem.text_ru)

        await session.commit()

        return {
            "problem_id": problem.id,
            "node_id": problem.node_id,
            "node_name": node_name,
            "text": problem_text,
            "image_path": problem.image_path,
            "answer_type": problem.answer_type,
            "difficulty": problem.difficulty,
            "sub_difficulty": problem.sub_difficulty,
            "count": counter,
        }
    finally:
        await session.close()


@router.post("/practice/answer")
async def practice_answer(request: Request, body: AnswerBody, lang: str = Query("ru")):
    session, student = await _get_current_student(request)
    try:
        problem = await session.get(Problem, body.problem_id)
        if not problem:
            raise HTTPException(status_code=404, detail="Задача не найдена")

        is_correct = check_answer(body.answer, problem.answer, problem.answer_type)
        mastery = await record_attempt(
            session, student.id, problem, body.answer, is_correct, source="practice"
        )
        await session.commit()

        solution = problem.solution_ru if lang == "ru" else (problem.solution_kz or problem.solution_ru)

        return {
            "is_correct": is_correct,
            "correct_answer": problem.answer,
            "solution": solution,
            "p_mastery": round(mastery.p_mastery, 3),
            "is_mastered": is_mastered(mastery),
            "llm_note": None,
        }
    finally:
        await session.close()


@router.post("/practice/skip")
async def practice_skip(request: Request, body: SkipBody):
    session, student = await _get_current_student(request)
    try:
        problem = await session.get(Problem, body.problem_id)
        if not problem:
            return {"ok": True}

        attempt = Attempt(
            student_id=student.id,
            problem_id=problem.id,
            node_id=problem.node_id,
            answer_given="",
            is_correct=False,
            source="skip",
        )
        session.add(attempt)
        await session.commit()
        return {"ok": True}
    finally:
        await session.close()


async def _notify_report(report_id, problem_text, correct_answer, student_answer, reason, ai_verdict=None):
    """Send report notification to admin Telegram."""
    import httpx

    bot_token = getattr(settings, 'bot_token', None)
    admin_ids = getattr(settings, 'admin_ids', [])
    if not bot_token or not admin_ids:
        return  # Skip notification if not configured
    text = (
        f"\U0001f6a8 Жалоба #{report_id}\n"
        f"Задача: {problem_text[:200]}\n"
        f"Правильный ответ: {correct_answer}\n"
        f"Ответ ученика: {student_answer or '—'}\n"
        f"Причина: {reason}\n"
    )
    if ai_verdict:
        action, explanation = ai_verdict
        if action == "fixed":
            text += f"\n\u2705 AI автоматически исправил ответ на: {student_answer}\n"
            text += f"Причина: {explanation}\n"
        elif action == "rejected":
            text += f"\n\U0001f916 AI проверил — ответ ученика неверен.\n"
            text += f"Причина: {explanation}\n"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    async with httpx.AsyncClient() as client:
        for aid in admin_ids:
            try:
                await client.post(url, json={"chat_id": aid, "text": text})
            except Exception:
                pass  # notification is best-effort


@router.post("/practice/report")
async def practice_report(request: Request, body: ReportBody):
    session, student = await _get_current_student(request)
    try:
        problem = await session.get(Problem, body.problem_id)
        if not problem:
            raise HTTPException(status_code=404, detail="Задача не найдена")

        report = ProblemReport(
            student_id=student.id,
            problem_id=problem.id,
            node_id=problem.node_id,
            reason=body.reason,
            student_answer=body.student_answer or None,
            correct_answer=problem.answer,
            problem_text=problem.text_ru,
            comment="",
        )
        session.add(report)
        await session.flush()  # get report.id
        await session.commit()

        # AI auto-check: verify if student's answer is actually correct
        ai_verdict = None
        if body.student_answer:
            try:
                is_correct, explanation = await check_with_claude(
                    body.student_answer, problem.answer, problem.text_ru
                )
                if is_correct:
                    problem.answer = body.student_answer
                    report.status = "auto_fixed"
                    report.resolved_by = "AI (Claude)"
                    report.resolved_at = datetime.now(timezone.utc)
                    report.comment = f"AI: {explanation}"
                    await session.commit()
                    ai_verdict = ("fixed", explanation)
                    logger.info("Report #%d auto-fixed by AI: problem #%d answer -> '%s'",
                                report.id, problem.id, body.student_answer)
                else:
                    report.comment = f"AI: ответ ученика неверен. {explanation}"
                    await session.commit()
                    ai_verdict = ("rejected", explanation)
                    logger.info("Report #%d AI-rejected: %s", report.id, explanation)
            except Exception as exc:
                logger.warning("AI auto-check failed for report #%d: %s", report.id, exc)

        # Fire-and-forget Telegram notification
        asyncio.ensure_future(_notify_report(
            report.id, problem.text_ru, problem.answer,
            body.student_answer, body.reason, ai_verdict,
        ))

        return {"ok": True}
    finally:
        await session.close()


# ══════════════════════════════════════════════════════════════
#  TIMED EXAM (batch mode — all problems returned at once)
# ══════════════════════════════════════════════════════════════

@router.post("/practice/exam/start")
async def practice_exam_start(request: Request, body: ExamStartBody,
                              lang: str = Query("ru", pattern="^(ru|kz)$")):
    """Select N problems across diverse topics for a timed exam."""
    session, student = await _get_current_student(request)
    try:
        n = min(body.num_problems, 50)

        result = await session.execute(
            text("""
                WITH ranked AS (
                    SELECT p.id, p.node_id, p.text_ru, p.text_kz,
                           p.answer, p.answer_type, p.difficulty,
                           p.sub_difficulty, p.image_path, p.solution_ru,
                           n.name_ru AS node_name, n.name_kz AS node_name_kz,
                           ROW_NUMBER() OVER (PARTITION BY p.node_id ORDER BY RANDOM()) AS rn
                    FROM problems p
                    JOIN nodes n ON n.id = p.node_id
                    WHERE p.node_id NOT IN (
                        SELECT DISTINCT node_id FROM attempts
                        WHERE student_id = :sid AND is_correct = true
                        AND source = 'practice'
                    )
                )
                SELECT * FROM ranked WHERE rn = 1
                ORDER BY RANDOM()
                LIMIT :limit
            """),
            {"sid": student.id, "limit": n},
        )
        rows = result.all()

        if len(rows) < n:
            extra = await session.execute(
                text("""
                    SELECT p.id, p.node_id, p.text_ru, p.text_kz,
                           p.answer, p.answer_type, p.difficulty,
                           p.sub_difficulty, p.image_path, p.solution_ru,
                           n.name_ru AS node_name, n.name_kz AS node_name_kz
                    FROM problems p
                    JOIN nodes n ON n.id = p.node_id
                    WHERE p.id NOT IN :seen
                    ORDER BY RANDOM()
                    LIMIT :limit
                """),
                {
                    "seen": tuple(r[0] for r in rows) or (0,),
                    "limit": n - len(rows),
                },
            )
            rows = list(rows) + list(extra.all())

        problems = []
        for r in rows:
            text = r[3] if lang == "kz" and r[3] else r[2]
            node_name = r[11] if lang == "kz" and r[11] else r[10]
            problems.append({
                "problem_id": r[0],
                "node_id": r[1],
                "node_name": node_name,
                "text": text,
                "image_path": r[8],
                "answer_type": r[5],
                "difficulty": r[6],
                "sub_difficulty": r[7],
            })

        return {"problems": problems}
    finally:
        await session.close()


# ══════════════════════════════════════════════════════════════
#  DIAGNOSTIC ROUTES — session lifecycle
# ══════════════════════════════════════════════════════════════

_diagnostic_states: dict[int, object] = {}
_diagnostic_lock = asyncio.Lock()


async def _format_question(session: AsyncSession, problem: Problem, state, lang: str = "ru") -> dict:
    """Build the JSON question payload the Flutter client expects."""
    node = await session.get(Node, problem.node_id)
    node_name = (node.name_ru if lang == "ru" else (node.name_kz or node.name_ru)) if node else problem.node_id
    problem_text = problem.text_ru if lang == "ru" else (problem.text_kz or problem.text_ru)
    return {
        "finished": False,
        "problem_id": problem.id,
        "node_id": problem.node_id,
        "node_name": node_name,
        "text": problem_text,
        "image_path": problem.image_path,
        "answer_type": problem.answer_type,
        "difficulty": problem.difficulty,
        "sub_difficulty": problem.sub_difficulty,
        "questions_asked": state.questions_asked,
        "topics_tested": state.topics_tested,
        "max_topics": state.max_topics,
        "count": state.questions_asked,
    }


async def _get_next_problem(session: AsyncSession, state) -> Problem | None:
    """Get next problem from either exam or diagnostic state."""
    from core.exam import ExamState, exam_next_question
    from core.diagnostic import DiagnosticState, next_question

    if isinstance(state, ExamState):
        return await exam_next_question(session, state)
    elif isinstance(state, DiagnosticState):
        return await next_question(session, state)
    return None


def _state_mode(state) -> str:
    from core.exam import ExamState
    return "exam" if isinstance(state, ExamState) else "diagnostic"


async def _persist_state(session: AsyncSession, student: Student, state, mode: str):
    """Snapshot current state into student.paused_diagnostic JSONB."""
    blob = state.to_dict()
    blob["_mode"] = mode
    student.paused_diagnostic = blob
    await session.flush()


async def _restore_state(session: AsyncSession, student: Student):
    """Restore in-memory state from paused_diagnostic JSONB if missing."""
    from core.exam import ExamState
    from core.diagnostic import DiagnosticState

    async with _diagnostic_lock:
        if student.id in _diagnostic_states:
            return _diagnostic_states[student.id]

        blob = student.paused_diagnostic
        if not blob or not isinstance(blob, dict):
            return None

        mode = blob.get("_mode", blob.get("mode", ""))
        try:
            if mode == "exam" or blob.get("phase") == 4:
                state = ExamState.from_dict(blob)
            else:
                state = DiagnosticState.from_dict(blob)
            _diagnostic_states[student.id] = state
            return state
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("Failed to restore diagnostic state for %s: %s", student.id, exc)
            student.paused_diagnostic = None
            return None


@router.post("/diagnostic/start")
async def diagnostic_start(request: Request, body: DiagnosticStartBody, lang: str = Query("ru", regex="^(ru|kz)$")):
    session, student = await _get_current_student(request)
    try:
        mode = body.mode

        async with _diagnostic_lock:
            _diagnostic_states.pop(student.id, None)

        if mode in ("exam", "gaps"):
            from core.exam import init_exam
            state = await init_exam(session, student.id)
        elif mode == "phase1":
            from core.diagnostic import init_phase1
            state = await init_phase1(session, student.id)
        elif mode == "phase2":
            from core.diagnostic import init_phase2
            state = await init_phase2(session, student.id)
        elif mode == "phase3":
            from core.diagnostic import init_phase3
            state = await init_phase3(session, student.id)
        else:
            from core.exam import init_exam
            state = await init_exam(session, student.id)

        async with _diagnostic_lock:
            _diagnostic_states[student.id] = state
        await _persist_state(session, student, state, mode)
        await session.commit()

        problem = await _get_next_problem(session, state)
        if problem is None:
            return {"finished": True, "problem_id": None}

        return await _format_question(session, problem, state, lang)
    finally:
        await session.close()


@router.get("/diagnostic/question")
async def diagnostic_question(request: Request, lang: str = Query("ru", regex="^(ru|kz)$")):
    session, student = await _get_current_student(request)
    try:
        state = await _restore_state(session, student)
        if not state:
            raise HTTPException(status_code=400, detail="Нет активной сессии диагностики")

        problem = await _get_next_problem(session, state)
        if problem is None:
            return {"finished": True, "problem_id": None}

        return await _format_question(session, problem, state, lang)
    finally:
        await session.close()


@router.post("/diagnostic/answer")
async def diagnostic_answer(request: Request, body: DiagnosticAnswerBody, lang: str = Query("ru", regex="^(ru|kz)$")):
    session, student = await _get_current_student(request)
    try:
        state = await _restore_state(session, student)
        if not state:
            raise HTTPException(status_code=400, detail="Нет активной сессии диагностики")

        problem = await session.get(Problem, body.problem_id)
        if not problem:
            raise HTTPException(status_code=404, detail="Задача не найдена")

        is_correct = check_answer(body.answer, problem.answer, problem.answer_type)
        elapsed_ms = int(body.elapsed_sec * 1000)

        from core.exam import ExamState, exam_handle_answer
        from core.diagnostic import DiagnosticState, handle_correct, handle_incorrect

        if isinstance(state, ExamState):
            await exam_handle_answer(
                session, state, problem.node_id, is_correct,
                body.elapsed_sec, problem.sub_difficulty or 3,
            )
        elif isinstance(state, DiagnosticState):
            if is_correct:
                await handle_correct(session, state, problem.node_id, body.elapsed_sec)
            else:
                await handle_incorrect(session, state, problem.node_id, body.elapsed_sec)

        attempt = Attempt(
            student_id=student.id,
            problem_id=problem.id,
            node_id=problem.node_id,
            answer_given=body.answer,
            is_correct=is_correct,
            response_time_ms=elapsed_ms,
            source="exam" if isinstance(state, ExamState) else "diagnostic",
        )
        session.add(attempt)

        await _persist_state(session, student, state, _state_mode(state))
        await session.commit()

        has_next = False
        if isinstance(state, ExamState):
            has_next = bool(state.heads_queue or state.targets_queue)
        elif isinstance(state, DiagnosticState):
            has_next = bool(state.queue) or state.topics_tested < state.max_topics

        solution = problem.solution_ru if lang == "ru" else (problem.solution_kz or problem.solution_ru)

        return {
            "is_correct": is_correct,
            "correct_answer": problem.answer,
            "solution": solution,
            "questions_asked": state.questions_asked,
            "topics_tested": state.topics_tested,
            "max_topics": state.max_topics,
            "has_next": has_next,
        }
    finally:
        await session.close()


@router.post("/diagnostic/finish")
async def diagnostic_finish(request: Request):
    session, student = await _get_current_student(request)
    try:
        state = await _restore_state(session, student)
        if not state:
            return {"status": "no_session"}

        from core.exam import ExamState, finish_exam
        from core.diagnostic import (
            DiagnosticState, finish_phase1, finish_phase2, finish_phase3,
        )

        if isinstance(state, ExamState):
            await finish_exam(session, state)
        elif isinstance(state, DiagnosticState):
            if state.phase == 1:
                await finish_phase1(session, state)
            elif state.phase == 2:
                await finish_phase2(session, state)
            else:
                await finish_phase3(session, state)

        student.diagnostic_complete = True
        student.paused_diagnostic = None
        await session.commit()

        async with _diagnostic_lock:
            _diagnostic_states.pop(student.id, None)

        return {"status": "finished"}
    finally:
        await session.close()


@router.post("/diagnostic/cancel")
async def diagnostic_cancel(request: Request):
    """Explicitly abandon the current diagnostic/exam session."""
    session, student = await _get_current_student(request)
    try:
        async with _diagnostic_lock:
            _diagnostic_states.pop(student.id, None)
        student.paused_diagnostic = None
        await session.commit()
        return {"status": "cancelled"}
    finally:
        await session.close()


@router.get("/diagnostic/status")
async def diagnostic_status(request: Request):
    session, student = await _get_current_student(request)
    try:
        state = await _restore_state(session, student)
        has_active = state is not None
        paused = student.paused_diagnostic

        mode = ""
        questions_asked = 0
        topics_tested = 0
        max_topics = 0
        can_resume = False

        if state:
            mode = _state_mode(state)
            questions_asked = state.questions_asked
            topics_tested = state.topics_tested
            max_topics = state.max_topics
            can_resume = True
        elif paused and isinstance(paused, dict):
            mode = paused.get("_mode", paused.get("mode", ""))
            questions_asked = paused.get("questions_asked", 0)
            topics_tested = paused.get("topics_tested", 0)
            max_topics = paused.get("max_topics", 0)
            can_resume = True

        return {
            "active": has_active or can_resume,
            "can_resume": can_resume,
            "mode": mode,
            "diagnostic_complete": student.diagnostic_complete,
            "questions_asked": questions_asked,
            "topics_tested": topics_tested,
            "max_topics": max_topics,
        }
    finally:
        await session.close()
