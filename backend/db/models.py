from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
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
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    last_reminded_at: Mapped[datetime | None] = mapped_column(nullable=True)
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
    last_attempt_at: Mapped[datetime | None] = mapped_column()
    fsrs_stability: Mapped[float | None] = mapped_column(Float)
    fsrs_difficulty: Mapped[float | None] = mapped_column(Float)
    next_review_at: Mapped[datetime | None] = mapped_column()


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
    created_at: Mapped[datetime] = mapped_column(default=func.now())


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
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True, default=None)
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(default=func.now())


class Setting(Base):
    """Key-value store for system settings (algo version, etc.)."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
