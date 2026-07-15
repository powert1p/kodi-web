"""Versioned learning-path content contract and student-safe serialization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_MANIFEST_PATH = Path(__file__).resolve().parent.parent / "data" / "learning_paths_v1.json"
_PROBLEMS_PATH = Path(__file__).resolve().parent.parent / "data" / "problems_v10.json"


def load_learning_manifest(path: Path | None = None) -> dict[str, Any]:
    """Load the immutable, versioned lesson manifest."""
    return json.loads((path or _MANIFEST_PATH).read_text(encoding="utf-8"))


def load_problem_bank() -> list[dict[str, Any]]:
    """Load canonical problems indexed by ``content_idx``."""
    return json.loads(_PROBLEMS_PATH.read_text(encoding="utf-8"))["problems"]


def get_lesson(lesson_id: str) -> dict[str, Any] | None:
    """Return a lesson by stable id from the current manifest version."""
    manifest = load_learning_manifest()
    return next(
        (lesson for lesson in manifest["lessons"] if lesson["id"] == lesson_id),
        None,
    )


def validate_learning_manifest(
    manifest: dict[str, Any],
    *,
    problems: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Return deterministic content-contract violations without mutating content."""
    errors: list[str] = []
    path = manifest.get("path")
    lessons = manifest.get("lessons")
    if not manifest.get("version"):
        errors.append("manifest.version is required")
    if not isinstance(path, dict):
        errors.append("manifest.path is required")
    else:
        for field in ("id", "title", "current_block_id", "current_block_title"):
            if not path.get(field):
                errors.append(f"manifest.path.{field} is required")
    if not isinstance(lessons, list) or not lessons:
        return [*errors, "manifest.lessons must be non-empty"]

    lesson_ids = [lesson.get("id") for lesson in lessons]
    if any(not lesson_id for lesson_id in lesson_ids) or len(set(lesson_ids)) != len(
        lesson_ids
    ):
        errors.append("manifest lesson ids must be unique and non-empty")

    for lesson in lessons:
        prefix = f"lesson {lesson.get('id', '<missing>')}"
        for field in (
            "id",
            "title",
            "lesson_title",
            "goal",
            "result_label",
            "duration_minutes",
            "node_id",
        ):
            if not lesson.get(field):
                errors.append(f"{prefix}: {field} is required")
        if isinstance(path, dict) and lesson.get("node_id") != path.get("current_block_id"):
            errors.append(f"{prefix}: lesson must belong to current path block")
        if not lesson.get("prerequisite"):
            errors.append(f"{prefix}: prerequisite is required")
        if not lesson.get("structural_cases"):
            errors.append(f"{prefix}: structural_cases are required")
        if len(lesson.get("misconceptions", [])) < 3:
            errors.append(f"{prefix}: at least three misconceptions are required")

        activities = lesson.get("activities", [])
        roles = [activity.get("role") for activity in activities]
        if not roles or roles[0] != "worked":
            errors.append(f"{prefix}: route must begin with worked example")
        if roles[-2:] != ["independent", "transfer"]:
            errors.append(f"{prefix}: route must end with independent + transfer")

        support_counts = [
            int(activity.get("embedded_support_count", -1))
            for activity in activities[1:]
        ]
        if any(count < 0 or count > 2 for count in support_counts):
            errors.append(f"{prefix}: embedded support count must be between 0 and 2")
        if support_counts != sorted(support_counts, reverse=True):
            errors.append(f"{prefix}: embedded supports must fade monotonically")
        if activities:
            transfer = activities[-1]
            if not transfer.get("hardest_case"):
                errors.append(f"{prefix}: transfer must be the hardest case")
            if not transfer.get("discriminates_misconception"):
                errors.append(f"{prefix}: transfer must discriminate a misconception")

        ids: set[str] = set()
        for activity in activities:
            activity_id = activity.get("id")
            if not activity_id or activity_id in ids:
                errors.append(f"{prefix}: activity ids must be unique and non-empty")
            ids.add(activity_id)
            if "expected_answer" not in activity:
                errors.append(f"{prefix}/{activity_id}: expected_answer is required")
            if len(activity.get("hint_levels", [])) > 2:
                errors.append(f"{prefix}/{activity_id}: at most two hint levels")

            if problems is None:
                continue
            content_idx = activity.get("content_idx")
            if not isinstance(content_idx, int) or not 0 <= content_idx < len(problems):
                errors.append(f"{prefix}/{activity_id}: invalid content_idx")
                continue
            problem = problems[content_idx]
            if problem["node_id"] != lesson.get("node_id"):
                errors.append(f"{prefix}/{activity_id}: problem belongs to another node")
            if (
                activity.get("answer_source") == "problem"
                and str(activity.get("expected_answer")) != str(problem["answer"])
            ):
                errors.append(f"{prefix}/{activity_id}: expected answer drifts from problem bank")

    return errors


def student_activity_payload(
    activity: dict[str, Any],
    *,
    statement: str,
    answer_type: str | None,
    support_level: int,
    last_answer: str | None,
) -> dict[str, Any]:
    """Serialize only student-facing fields; answers and future hints stay server-side."""
    hints = activity.get("hint_levels", [])
    support = hints[min(support_level, len(hints)) - 1] if support_level > 0 and hints else None
    return {
        "id": activity["id"],
        "role": activity["role"],
        "phase_label": activity["phase_label"],
        "title": activity["title"],
        "prompt": activity["prompt"],
        "content_idx": activity["content_idx"],
        "statement": statement,
        "answer_type": activity.get("answer_type") or answer_type,
        "input_suffix": activity.get("input_suffix"),
        "embedded_supports": activity.get("embedded_supports", []),
        "worked_steps": activity.get("worked_steps", []) if activity["role"] == "worked" else [],
        "support_level": support_level,
        "support": support,
        "last_answer": last_answer,
    }
