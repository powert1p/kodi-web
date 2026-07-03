from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Node(Base):
    """Knowledge-graph node (skill)."""

    __tablename__ = "nodes"

    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    name_ru: Mapped[str] = mapped_column(Text, nullable=False)
    name_kz: Mapped[str] = mapped_column(Text, nullable=False)
    tag: Mapped[str | None] = mapped_column(String(30))
    topic_id: Mapped[str | None] = mapped_column(String(20))  # FK на topics.id; на existing-БД без констрейнта (ALTER)
    difficulty: Mapped[int | None] = mapped_column(SmallInteger)
    description: Mapped[str | None] = mapped_column(Text)
    bkt_p_t: Mapped[float] = mapped_column(Float, default=0.3)
    bkt_p_g: Mapped[float] = mapped_column(Float, default=0.05)
    bkt_p_s: Mapped[float] = mapped_column(Float, default=0.1)


class Edge(Base):
    """Prerequisite edge between two nodes."""

    __tablename__ = "edges"

    from_node: Mapped[str] = mapped_column(
        String(10), ForeignKey("nodes.id"), primary_key=True
    )
    to_node: Mapped[str] = mapped_column(
        String(10), ForeignKey("nodes.id"), primary_key=True
    )
    encompassing_weight: Mapped[float] = mapped_column(Float, default=0.5)


class Problem(Base):
    """Problem bank entry linked to a node."""

    __tablename__ = "problems"
    __table_args__ = (
        Index("ix_problems_node_id", "node_id"),
        Index("ix_problems_raw_score", "raw_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(String(10), ForeignKey("nodes.id"))
    text_ru: Mapped[str] = mapped_column(Text, nullable=False)
    text_kz: Mapped[str | None] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    answer_type: Mapped[str | None] = mapped_column(String(20))
    difficulty: Mapped[int | None] = mapped_column(SmallInteger)
    sub_difficulty: Mapped[int | None] = mapped_column(SmallInteger)  # 1=easy, 2=medium, 3=hard, 4=advanced within node
    raw_score: Mapped[float | None] = mapped_column(Float)
    image_path: Mapped[str | None] = mapped_column(String(200))
    image_path_kz: Mapped[str | None] = mapped_column(String(200))
    source: Mapped[str | None] = mapped_column(String(100))
    solution_ru: Mapped[str | None] = mapped_column(Text)
    solution_kz: Mapped[str | None] = mapped_column(Text)


class Student(Base):
    """Telegram user profile."""

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # tg user_id
    first_name: Mapped[str | None] = mapped_column(Text)
    last_name: Mapped[str | None] = mapped_column(Text)
    username: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(20))
    phone_pin: Mapped[str | None] = mapped_column(String(4))
    full_name: Mapped[str | None] = mapped_column(Text)  # ФИО (ввод вручную)
    grade: Mapped[int | None] = mapped_column(SmallInteger)
    lang: Mapped[str] = mapped_column(String(2), default="ru")
    registered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    last_reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_streak: Mapped[int | None] = mapped_column(Integer, default=0, server_default="0")
    longest_streak: Mapped[int | None] = mapped_column(Integer, default=0, server_default="0")
    last_active_date: Mapped[str | None] = mapped_column(String(10))  # YYYY-MM-DD
    diagnostic_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    practice_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    current_practice_node: Mapped[str | None] = mapped_column(String(10), nullable=True)
    problems_on_current_node: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    pin_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    paused_diagnostic: Mapped[dict | None] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"), nullable=True
    )
    # Согласие родителя на использование фото работ ребёнка (Блок 1.0).
    # NULL = не спрашивали (мягкая карточка на hub); true/false = ответ дан.
    photo_consent: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    photo_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Mastery(Base):
    """BKT mastery probability per student x node."""

    __tablename__ = "mastery"

    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("students.id", ondelete="CASCADE"), primary_key=True
    )
    node_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("nodes.id", ondelete="RESTRICT"), primary_key=True
    )
    p_mastery: Mapped[float] = mapped_column(Float, default=0.0)
    attempts_total: Mapped[int] = mapped_column(Integer, default=0)
    attempts_correct: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fsrs_stability: Mapped[float | None] = mapped_column(Float)
    fsrs_difficulty: Mapped[float | None] = mapped_column(Float)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Attempt(Base):
    """Single answer attempt."""

    __tablename__ = "attempts"
    __table_args__ = (
        Index("ix_attempts_student_node", "student_id", "node_id"),
        Index("ix_attempts_student_source", "student_id", "source"),
        Index("ix_attempts_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("students.id", ondelete="CASCADE"))
    problem_id: Mapped[int] = mapped_column(Integer, ForeignKey("problems.id", ondelete="RESTRICT"))
    node_id: Mapped[str] = mapped_column(String(10), ForeignKey("nodes.id", ondelete="RESTRICT"))
    answer_given: Mapped[str | None] = mapped_column(Text)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    source: Mapped[str | None] = mapped_column(String(20))  # "diagnostic" / "practice"
    response_time_ms: Mapped[int | None] = mapped_column(Integer)
    p_mastery_after: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())


class ProblemReport(Base):
    """Student report about a broken or disputed problem."""

    __tablename__ = "problem_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("students.id", ondelete="CASCADE"))
    problem_id: Mapped[int] = mapped_column(Integer, ForeignKey("problems.id", ondelete="CASCADE"))
    node_id: Mapped[str] = mapped_column(String(10))
    reason: Mapped[str] = mapped_column(String(30))
    student_answer: Mapped[str | None] = mapped_column(Text)
    correct_answer: Mapped[str] = mapped_column(Text)
    problem_text: Mapped[str] = mapped_column(Text)
    comment: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="open")  # open/fixed/auto_fixed/invalid
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())


class Setting(Base):
    """Key-value store for system settings (algo version, etc.)."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(Text)


class Topic(Base):
    """Тема графа (CC-кластер или НИШ-группа) — слой над узлами."""

    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # "6.RP.A" / "NIS.COMB"
    strand: Mapped[str] = mapped_column(String(10), nullable=False)  # домен: RP/EE/.../NIS
    grade: Mapped[int | None] = mapped_column(SmallInteger)
    order_idx: Mapped[int] = mapped_column(Integer, default=0)
    name_ru: Mapped[str] = mapped_column(Text, nullable=False)
    name_kz: Mapped[str] = mapped_column(Text, nullable=False)


class TopicEdge(Base):
    """Ребро-пререквизит между темами (CC coherence map)."""

    __tablename__ = "topic_edges"

    from_topic: Mapped[str] = mapped_column(String(20), ForeignKey("topics.id"), primary_key=True)
    to_topic: Mapped[str] = mapped_column(String(20), ForeignKey("topics.id"), primary_key=True)


# ─────────────────────────────────────────────────────────────
# Тренажёр ошибок: банк декомпозиций + захват/накопление ошибок
# ─────────────────────────────────────────────────────────────


class MicroSkill(Base):
    """Каталог микро-умений (атомарных шагов решения задачи)."""

    __tablename__ = "micro_skills"

    code: Mapped[str] = mapped_column(String(50), primary_key=True)          # уникальный код умения
    label_ru: Mapped[str] = mapped_column(Text, nullable=False)              # русское название
    domain: Mapped[str | None] = mapped_column(String(50))                  # раздел математики
    freq: Mapped[int | None] = mapped_column(Integer)                       # частота встречаемости в банке


class DecompositionProblem(Base):
    """Задача из банка декомпозиций (полностью автономный банк, 0..2524).

    idx — явный PK из JSON (0-based), НЕ автоинкремент.
    problems_db_id — ссылка на БД-задачу там, где совпадает (node_id, answer); ~42%.
    """

    __tablename__ = "decomposition_problems"
    __table_args__ = (
        # Индекс по узлу — быстрый выбор задач по теме
        Index("idx_decomp_node", "node_id"),
        # Индекс по связанной БД-задаче — быстрый join
        Index("idx_decomp_dbid", "problems_db_id"),
    )

    idx: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)  # JSON-индекс
    node_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("nodes.id", ondelete="RESTRICT"), nullable=False
    )
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    primary_micro_skill: Mapped[str | None] = mapped_column(String(50))     # основное умение задачи
    all_steps_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # FK на problems.id, только там где (node_id, answer) однозначно совпадают (~42%)
    problems_db_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("problems.id", ondelete="SET NULL"), nullable=True
    )


class ProblemStep(Base):
    """Шаг решения задачи (один из N шагов декомпозиции)."""

    __tablename__ = "problem_steps"
    __table_args__ = (
        Index("idx_problem_steps_decomp", "decomp_idx"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decomp_idx: Mapped[int] = mapped_column(
        Integer, ForeignKey("decomposition_problems.idx", ondelete="CASCADE"), nullable=False
    )
    n: Mapped[int] = mapped_column(Integer, nullable=False)                 # порядковый номер шага
    instruction_ru: Mapped[str] = mapped_column(Text, nullable=False)       # текст инструкции на русском
    micro_skill: Mapped[str] = mapped_column(String(50), nullable=False)    # код микро-умения
    expected_value: Mapped[str] = mapped_column(Text, nullable=False)       # ожидаемый результат шага
    verified: Mapped[str | None] = mapped_column(String(20))               # статус верификации шага


class ProblemFingerprint(Base):
    """Отпечаток типичной ошибки на задаче (micro_skill + wrong_answer → описание)."""

    __tablename__ = "problem_fingerprints"
    __table_args__ = (
        Index("idx_problem_fingerprints_decomp", "decomp_idx"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decomp_idx: Mapped[int] = mapped_column(
        Integer, ForeignKey("decomposition_problems.idx", ondelete="CASCADE"), nullable=False
    )
    micro_skill: Mapped[str] = mapped_column(String(50), nullable=False)    # код умения, где ошибка
    wrong_answer: Mapped[str] = mapped_column(Text, nullable=False)         # неверный ответ
    mistake_ru: Mapped[str] = mapped_column(Text, nullable=False)           # описание ошибки на русском


class ErrorCapture(Base):
    """Один захваченный факт ошибки студента на задаче (результат AI-анализа среза)."""

    __tablename__ = "error_captures"
    __table_args__ = (
        Index("idx_error_captures_student_node", "student_id", "node_id"),
        Index("idx_error_captures_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    # attempt_id — опционально: ссылка на попытку (если захват произошёл в контексте attempt)
    attempt_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("attempts.id", ondelete="SET NULL"), nullable=True
    )
    problem_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("problems.id", ondelete="RESTRICT"), nullable=False
    )
    node_id: Mapped[str] = mapped_column(String(10), nullable=False)        # дублируется для быстрого фильтра
    image_ref: Mapped[str] = mapped_column(Text, nullable=False)            # ссылка на изображение среза
    transcription: Mapped[str | None] = mapped_column(Text)                 # OCR-текст из среза
    failed_step: Mapped[int | None] = mapped_column(Integer)               # номер шага, где ошибка
    failed_micro_skill: Mapped[str | None] = mapped_column(String(50))     # код умения, где ошибка
    cause_text: Mapped[str | None] = mapped_column(Text)                   # AI-объяснение причины
    level: Mapped[int | None] = mapped_column(SmallInteger)                # уровень сложности задачи
    model: Mapped[str | None] = mapped_column(String(50))                  # AI-модель, сделавшая анализ
    confidence: Mapped[float | None] = mapped_column(Float)                # уверенность модели (0..1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False
    )


class RecurringError(Base):
    """Накопленная статистика повторяющихся ошибок студента по умению.

    Составной PK (student_id, micro_skill) — аналогично Mastery (student_id, node_id).
    """

    __tablename__ = "recurring_errors"
    __table_args__ = (
        Index("idx_recurring_errors_micro_skill", "micro_skill"),
    )

    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("students.id", ondelete="CASCADE"), primary_key=True
    )
    micro_skill: Mapped[str] = mapped_column(String(50), primary_key=True)  # код умения
    node_id: Mapped[str | None] = mapped_column(String(10))                 # последний узел, где встретилась ошибка
    error_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_cause_text: Mapped[str | None] = mapped_column(Text)              # последнее AI-объяснение
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False
    )


class TutorSession(Base):
    """Сессия чата с ИИ-тьютором: одна на (студент, задача)."""

    __tablename__ = "tutor_sessions"
    __table_args__ = (
        # UNIQUE (не просто индекс) — защита от гонки SELECT-then-INSERT в эндпоинте:
        # ON CONFLICT DO NOTHING опирается именно на этот констрейнт.
        UniqueConstraint("student_id", "problem_id", name="uq_tutor_sessions_student_problem"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    problem_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )
    node_id: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False
    )


class TutorMessage(Base):
    """Одна реплика чата тьютора (user/assistant)."""

    __tablename__ = "tutor_messages"
    __table_args__ = (
        Index("idx_tutor_messages_session", "session_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tutor_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # 'user' | 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False
    )


class Event(Base):
    """Сырое событие телеметрии UX (Блок 1.0, пилот-аналитика)."""

    __tablename__ = "events"
    __table_args__ = (
        Index("idx_events_student_created", "student_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)  # произвольная строка, не enum
    payload: Mapped[dict | None] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False
    )


class StepSubmission(Base):
    """Одна сдача фото шага лесенки (Блок 1.2). Датасет фото+шаг+вердикт."""

    __tablename__ = "step_submissions"
    __table_args__ = (
        Index("idx_step_submissions_student_created", "student_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    decomp_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    step_n: Mapped[int] = mapped_column(Integer, nullable=False)
    problem_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("problems.id", ondelete="SET NULL"), nullable=True
    )
    verdict: Mapped[str] = mapped_column(String(16), nullable=False)  # match|mismatch|unsure
    confidence: Mapped[float | None] = mapped_column(Float)
    matched_micro_skill: Mapped[str | None] = mapped_column(String(50))
    photo_path: Mapped[str] = mapped_column(Text, nullable=False)     # относительно photo_dir
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False
    )
