"""Product/content contract первого server-owned learning path."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path


_BACKEND = Path(__file__).resolve().parents[1]


def test_mixtures_manifest_passes_content_quality_gate():
    from core.learning import load_learning_manifest, validate_learning_manifest

    manifest = load_learning_manifest()

    assert validate_learning_manifest(manifest) == []
    assert manifest["path"] == {
        "id": "nish-preparation",
        "title": "Подготовка к НИШ",
        "current_block_id": "PC06",
        "current_block_title": "Смеси и концентрации",
    }
    lesson = manifest["lessons"][0]
    assert lesson["id"] == "mixtures-1"
    assert lesson["prerequisite"]
    assert lesson["structural_cases"]
    assert len(lesson["misconceptions"]) >= 3
    assert [activity["role"] for activity in lesson["activities"]] == [
        "worked",
        "guided",
        "guided",
        "guided",
        "independent",
        "transfer",
    ]
    assert [
        activity["embedded_support_count"]
        for activity in lesson["activities"][1:]
    ] == [2, 1, 0, 0, 0]
    assert lesson["activities"][-1]["hardest_case"] is True
    assert lesson["activities"][-1]["discriminates_misconception"]


def test_manifest_content_indices_match_canonical_problem_bank():
    from core.learning import load_learning_manifest, validate_learning_manifest

    manifest = load_learning_manifest()
    problems = json.loads(
        (_BACKEND / "data" / "problems_v10.json").read_text(encoding="utf-8")
    )["problems"]

    assert validate_learning_manifest(manifest, problems=problems) == []
    for activity in manifest["lessons"][0]["activities"]:
        content_idx = activity["content_idx"]
        problem = problems[content_idx]
        assert problem["node_id"] == "PC06"


def test_student_activity_payload_never_contains_expected_answer_or_private_hints():
    from core.learning import load_learning_manifest, student_activity_payload

    activity = load_learning_manifest()["lessons"][0]["activities"][1]

    payload = student_activity_payload(
        activity,
        statement="К 200 г 10%-го раствора добавили 50 г воды.",
        answer_type="number",
        support_level=0,
        last_answer=None,
    )

    assert "expected_answer" not in payload
    assert "hint_levels" not in payload
    assert payload["support"] is None


def test_manifest_rejects_duplicate_lesson_ids_and_incomplete_public_summary():
    from core.learning import load_learning_manifest, validate_learning_manifest

    manifest = load_learning_manifest()
    duplicate = deepcopy(manifest["lessons"][0])
    duplicate.pop("lesson_title")
    manifest["lessons"].append(duplicate)

    errors = validate_learning_manifest(manifest)

    assert "manifest lesson ids must be unique and non-empty" in errors
    assert "lesson mixtures-1: lesson_title is required" in errors
