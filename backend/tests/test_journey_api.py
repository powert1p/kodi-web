"""Production journey: adaptation -> diagnostic -> route -> photo/guided/transfer."""

from __future__ import annotations

import asyncio
import io
import json
import os
import warnings
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from core.journey import (
    DIAGNOSTIC_ANCHORS,
    DIAGNOSTIC_SKILLS,
    TOPIC_BLUEPRINTS,
    build_route,
    initial_diagnostic,
)
from core.learning import load_problem_bank


_TEST_URL = os.getenv("TEST_DATABASE_URL")
_DIAGNOSTIC_INDICES = (127, 121, 321, 320, 876, 448, 1144, 544, 1409, 804)
_LESSON_INDICES = tuple(
    dict.fromkeys(
        content_idx
        for blueprint in TOPIC_BLUEPRINTS.values()
        for content_idx in (
            blueprint["target_content_idx"],
            blueprint["transfer_content_idx"],
            *blueprint["reinforcement_content_indices"],
        )
    )
)
_ALL_INDICES = tuple(dict.fromkeys((*_DIAGNOSTIC_INDICES, *_LESSON_INDICES)))
_PHOTO = Path(__file__).parent / "fixtures" / "sample_work.jpg"


async def _render_workspace_case(monkeypatch, case: dict):
    import api.routers.journey as journey_module

    problem = SimpleNamespace(
        id=431,
        content_idx=case["content_idx"],
        node_id="PC06",
        text_ru="В растворе было 20% соли. Найди новую концентрацию.",
        answer="25%",
    )
    topic = {
        "id": "PC06",
        "title": "Смеси и концентрации",
        "strand": "Отношения и пропорции",
        "goal": "Сохранять количество вещества.",
        "reason": "Тренируем перенос.",
        "status": "next",
    }
    journey = SimpleNamespace(
        id=12,
        stage=case["stage"],
        revision=18,
        profile_data={},
        route={"topics": [topic], "index": 0},
        activity=dict(case.get("activity") or {}),
        feedback=dict(case.get("feedback") or {}),
        current_problem_id=problem.id,
        current_decomp_idx=case["content_idx"],
    )
    student = SimpleNamespace(
        id=98401,
        first_name="Аян",
        full_name="Аян",
        grade=6,
        photo_consent=True,
    )
    processing_attempt = case.get("processing_attempt")
    latest_attempt = case.get("latest_attempt")
    latest_attempt_mock = AsyncMock(return_value=latest_attempt)
    monkeypatch.setattr(
        journey_module,
        "_current_problem",
        AsyncMock(return_value=problem),
    )
    monkeypatch.setattr(
        journey_module,
        "_steps_for_problem",
        AsyncMock(
            return_value=[
                SimpleNamespace(
                    n=1,
                    instruction_ru="Запиши количество соли.",
                    expected_value="40 г",
                )
            ]
        ),
    )
    monkeypatch.setattr(
        journey_module,
        "_existing_attempt",
        AsyncMock(return_value=processing_attempt),
    )
    monkeypatch.setattr(
        journey_module,
        "_latest_photo_attempt",
        latest_attempt_mock,
    )

    payload = await journey_module._render(object(), student, journey)
    return payload, journey, student, latest_attempt_mock


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [
        pytest.param(
            {
                "stage": "independent_task",
                "content_idx": 1765,
                "next_type": "independent_task",
                "mode": "independent",
                "evidence_status": "empty",
                "evidence_label": None,
                "context_kind": "closed",
                "verdict": None,
                "recovery_reason": None,
                "help_available": True,
                "position": 1,
            },
            id="independent-task",
        ),
        pytest.param(
            {
                "stage": "independent_task",
                "content_idx": 1765,
                "next_type": "typed_processing",
                "mode": "independent",
                "activity": {
                    "typed_processing_client_attempt_id": "typed-live-reload-1"
                },
                "processing_attempt": SimpleNamespace(
                    journey_id=12,
                    problem_id=431,
                    stage="independent_task",
                    answer_given="2 5/6",
                    original_filename=None,
                ),
                "evidence_kind": "typed",
                "evidence_status": "processing",
                "evidence_label": "2 5/6",
                "context_kind": "processing",
                "verdict": None,
                "recovery_reason": None,
                "response_default_mode": "typed",
                "help_available": False,
                "position": 1,
            },
            id="typed-processing-after-reload",
        ),
        pytest.param(
            {
                "stage": "photo_recovery",
                "content_idx": 331,
                "next_type": "photo_processing",
                "mode": "transfer",
                "activity": {"processing_client_attempt_id": "photo-transfer-retry"},
                "feedback": {"return_stage": "transfer_task"},
                "processing_attempt": SimpleNamespace(
                    journey_id=12,
                    problem_id=431,
                    stage="transfer_task",
                    original_filename="transfer-retry.heic",
                ),
                "evidence_status": "processing",
                "evidence_label": "transfer-retry.heic",
                "context_kind": "processing",
                "verdict": None,
                "recovery_reason": None,
                "help_available": False,
                "position": 2,
            },
            id="photo-processing-transfer-retry",
        ),
        pytest.param(
            {
                "stage": "photo_feedback",
                "content_idx": 1765,
                "next_type": "photo_feedback",
                "mode": "independent",
                "feedback": {
                    "verdict": "incorrect",
                    "message": "Исправь первый шаг.",
                    "primary_action": "Исправить",
                },
                "latest_attempt": SimpleNamespace(original_filename="work.jpg"),
                "evidence_status": "checked",
                "evidence_label": "work.jpg",
                "context_kind": "feedback",
                "verdict": "needs_revision",
                "recovery_reason": None,
                "help_available": False,
                "position": 1,
            },
            id="photo-feedback",
        ),
        pytest.param(
            {
                "stage": "photo_recovery",
                "content_idx": 1765,
                "next_type": "photo_recovery",
                "mode": "independent",
                "feedback": {
                    "reason": "wrong_photo",
                    "return_stage": "independent_task",
                    "preserved_photo": {"name": "other.heic"},
                    "message": "Нужно фото этой задачи.",
                    "primary_action": "Заменить фото",
                },
                "evidence_status": "preserved",
                "evidence_label": "other.heic",
                "context_kind": "uncertain",
                "verdict": "uncertain",
                "recovery_reason": "wrong_photo",
                "help_available": False,
                "position": 1,
            },
            id="photo-recovery",
        ),
        pytest.param(
            {
                "stage": "guided_step",
                "content_idx": 1765,
                "next_type": "guided_step",
                "mode": "independent",
                "activity": {"guided_step": 1, "support_used": True},
                "evidence_status": "guided",
                "evidence_label": None,
                "context_kind": "guided",
                "verdict": None,
                "recovery_reason": None,
                "help_available": False,
                "position": 1,
                "support_used": True,
            },
            id="guided-step",
        ),
        pytest.param(
            {
                "stage": "transfer_task",
                "content_idx": 331,
                "next_type": "transfer_task",
                "mode": "transfer",
                "evidence_status": "empty",
                "evidence_label": None,
                "context_kind": "closed",
                "verdict": None,
                "recovery_reason": None,
                "help_available": False,
                "position": 2,
            },
            id="transfer-task",
        ),
        pytest.param(
            {
                "stage": "transfer_feedback",
                "content_idx": 331,
                "next_type": "transfer_feedback",
                "mode": "transfer",
                "feedback": {
                    "verdict": "correct",
                    "message": "Перенос подтверждён.",
                    "primary_action": "Продолжить",
                },
                "latest_attempt": SimpleNamespace(original_filename="transfer.jpg"),
                "evidence_status": "checked",
                "evidence_label": "transfer.jpg",
                "context_kind": "feedback",
                "verdict": "correct",
                "recovery_reason": None,
                "help_available": False,
                "position": 2,
            },
            id="transfer-feedback",
        ),
    ],
)
async def test_active_journey_states_share_workspace_envelope(monkeypatch, case) -> None:
    payload, _journey, _student, latest_attempt_mock = await _render_workspace_case(
        monkeypatch,
        case,
    )

    assert payload["workspace_version"] == 1
    assert payload["next_step"]["type"] == case["next_type"]
    assert payload["task"] == {
        "journey_id": 12,
        "problem_id": 431,
        "topic": {"id": "PC06", "title": "Смеси и концентрации"},
        "mode": case["mode"],
        "statement": "В растворе было 20% соли. Найди новую концентрацию.",
        "position": case["position"],
    }
    assert payload["next_step"]["problem"]["id"] == payload["task"]["problem_id"]
    assert payload["next_step"]["problem"]["statement"] == payload["task"]["statement"]
    assert payload["learner_evidence"] == {
        "kind": case.get("evidence_kind", "photo"),
        "status": case["evidence_status"],
        "label": case["evidence_label"],
    }
    assert payload["context_layer"] == {
        "kind": case["context_kind"],
        "verdict": case["verdict"],
        "recovery_reason": case["recovery_reason"],
    }
    assert payload["response"] == {
        "default_mode": case.get("response_default_mode", "photo"),
        "typed_available": case["next_type"] in {"independent_task", "transfer_task"},
        "help_available": case["help_available"],
    }
    if case["next_type"] == "typed_processing":
        assert payload["next_step"]["preserved_answer"] == {"value": "2 5/6"}
    assert payload["support"] == {
        "used": case.get("support_used", False),
        "highest_hint_rung": 0,
    }
    assert "photo_ref" not in json.dumps(payload, ensure_ascii=False)
    assert latest_attempt_mock.await_count == (
        1 if case["next_type"] in {"photo_feedback", "transfer_feedback"} else 0
    )


@pytest.mark.asyncio
async def test_stale_revision_keeps_current_active_workspace(monkeypatch) -> None:
    from fastapi import HTTPException
    from api.routers.journey import _require_revision

    case = {
        "stage": "independent_task",
        "content_idx": 1765,
        "next_type": "independent_task",
        "mode": "independent",
        "evidence_status": "empty",
        "evidence_label": None,
        "context_kind": "closed",
        "verdict": None,
        "recovery_reason": None,
        "help_available": True,
        "position": 1,
    }
    _payload, journey, student, _latest = await _render_workspace_case(monkeypatch, case)

    with pytest.raises(HTTPException) as error:
        await _require_revision(object(), student, journey, journey.revision - 1)

    assert error.value.status_code == 409
    detail = error.value.detail
    assert detail["code"] == "stale_revision"
    assert detail["current_revision"] == journey.revision
    assert detail["state"]["workspace_version"] == 1
    assert detail["state"]["task"]["problem_id"] == 431
    assert detail["state"]["next_step"]["problem"]["id"] == 431


@pytest.mark.asyncio
async def test_old_typed_lease_cannot_supersede_reacquired_attempt(monkeypatch) -> None:
    """Поздний provider-result не меняет attempt, уже принадлежащий новой lease."""
    from fastapi import HTTPException
    import api.routers.journey as journey_module

    db = SimpleNamespace(flush=AsyncMock(), commit=AsyncMock())
    student = SimpleNamespace(id=91)
    journey = SimpleNamespace(
        id=12,
        stage="independent_task",
        current_problem_id=431,
        activity={
            "typed_processing_client_attempt_id": "typed-lease-race-1",
            "typed_processing_lease_id": "new-lease",
        },
    )
    attempt = SimpleNamespace(
        status="processing",
        verdict=None,
        counts_for_mastery=False,
        journey_id=journey.id,
        stage=journey.stage,
        problem_id=journey.current_problem_id,
        client_attempt_id="typed-lease-race-1",
        response_payload=None,
    )

    async def conflict(*_args, **kwargs):
        raise HTTPException(
            status_code=409,
            detail={"code": kwargs["code"]},
        )

    monkeypatch.setattr(journey_module, "_state_conflict", conflict)
    monkeypatch.setattr(journey_module, "_render", AsyncMock(return_value={}))

    with pytest.raises(HTTPException) as error:
        await journey_module._require_typed_lease(
            db,
            student=student,
            journey=journey,
            attempt=attempt,
            source_stage="independent_task",
            source_problem_id=431,
            expected_lease_id="old-lease",
        )

    assert error.value.detail["code"] == "typed_invocation_superseded"
    assert attempt.status == "processing"
    assert attempt.verdict is None
    db.flush.assert_not_awaited()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_inactive_and_legacy_states_remain_compatible_without_envelope() -> None:
    from api.routers.journey import _render

    journey = SimpleNamespace(
        id=12,
        stage="profile",
        revision=0,
        profile_data={},
        route={},
        activity={},
        feedback={},
    )
    student = SimpleNamespace(
        id=98401,
        first_name="Аян",
        full_name="Аян",
        grade=6,
        photo_consent=True,
    )

    payload = await _render(object(), student, journey)

    assert payload["next_step"]["type"] == "profile"
    assert "workspace_version" not in payload
    assert "task" not in payload


@pytest.mark.parametrize(
    ("content_idx", "mode", "expected"),
    [
        (1765, "independent", 1),
        (331, "transfer", 2),
        (332, "transfer", 3),
        (999_999, "independent", 1),
        (999_999, "transfer", 2),
    ],
)
def test_workspace_position_uses_blueprint_order_and_safe_fallback(
    content_idx,
    mode,
    expected,
) -> None:
    from api.routers.journey import _workspace_position

    journey = SimpleNamespace(current_decomp_idx=content_idx)

    assert _workspace_position(
        journey,
        {"id": "PC06", "title": "Смеси и концентрации"},
        mode,
    ) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("correct", ("correct", None)),
        ("incorrect", ("needs_revision", None)),
        ("unreadable", ("uncertain", "unreadable")),
        ("provider_error", ("uncertain", "provider_error")),
        ("broken-value", ("uncertain", "unknown")),
        ({"malformed": True}, ("uncertain", "unknown")),
        (None, ("uncertain", "unknown")),
    ],
)
def test_workspace_verdict_mapping_fails_closed(raw, expected) -> None:
    from api.routers.journey import _normalise_workspace_verdict

    assert _normalise_workspace_verdict(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            {"verdict": "correct", "error_focus": "none"},
            {
                "verdict": "correct",
                "message": "Ответ подтверждён. Открываем следующую задачу.",
                "error_focus": "none",
                "counts_for_mastery": False,
            },
        ),
        (
            {"verdict": "correct", "error_focus": "format"},
            {
                "verdict": "correct",
                "message": "Ответ по смыслу верный. Открываем следующую задачу.",
                "error_focus": "format",
                "counts_for_mastery": False,
            },
        ),
        (
            {"verdict": "incorrect", "error_focus": "calculation"},
            {
                "verdict": "incorrect",
                "message": "Проверь вычисления и попробуй ещё раз.",
                "error_focus": "calculation",
                "counts_for_mastery": False,
            },
        ),
        (
            {
                "verdict": "incorrect",
                "error_focus": "calculation",
                "counts_for_mastery": True,
            },
            {
                "verdict": "incorrect",
                "message": "Проверь вычисления и попробуй ещё раз.",
                "error_focus": "calculation",
                "counts_for_mastery": True,
            },
        ),
        (
            {
                "verdict": "unsure",
                "error_focus": "unknown",
                "reason": "provider_error",
            },
            {
                "verdict": "unsure",
                "message": "Проверка временно недоступна. Повтори проверку или отправь фото.",
                "error_focus": "unknown",
                "counts_for_mastery": False,
            },
        ),
        (
            {"verdict": "free prose", "error_focus": "unsafe"},
            {
                "verdict": "unsure",
                "message": "Не удалось надёжно проверить ответ. Попробуй ещё раз или отправь фото.",
                "error_focus": "unknown",
                "counts_for_mastery": False,
            },
        ),
    ],
)
def test_typed_feedback_payload_is_closed_and_server_owned(raw, expected) -> None:
    """Клиент получает только enum-based feedback, без provider prose."""
    from api.routers.journey import _typed_feedback_payload

    assert _typed_feedback_payload(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  １\n", "1"),
        ("\tответ   42\r\n", "ответ 42"),
        ("   ", None),
        ("ответ\x00", None),
        ("x" * 501, None),
        (" " * 501 + "42", "42"),
    ],
)
def test_typed_answer_normalisation_is_bounded_and_control_safe(raw, expected) -> None:
    """Idempotency использует один NFKC + whitespace-normalized ответ."""
    from api.routers.journey import _normalise_typed_answer

    assert _normalise_typed_answer(raw) == expected


def test_typed_result_preserves_format_note_for_equivalent_answer() -> None:
    """AI может принять эквивалентное значение и отдельно отметить форму записи."""
    from api.routers.journey import _normalise_typed_result
    from core.llm_openai import TypedAnswerResult

    result = TypedAnswerResult(
        verdict="correct",
        error_focus="format",
        confidence=1.0,
        provider="gemini",
        model="gemini-test",
        evidence_verified=True,
        answer_echo="2 5/6",
        check_summary="Значение эквивалентно эталону, отличается только форма записи.",
    )

    assert _normalise_typed_result(result, answer="2 5/6") == ("correct", "format")


def test_stage_transition_clears_typed_feedback() -> None:
    """Любой переход не переносит formative typed-feedback на следующий экран."""
    from api.routers.journey import _set_stage

    journey = SimpleNamespace(
        stage="independent_task",
        activity={
            "mode": "independent",
            "typed_feedback": {"verdict": "correct", "error_focus": "none"},
        },
    )

    _set_stage(journey, "photo_feedback")

    assert journey.stage == "photo_feedback"
    assert "typed_feedback" not in journey.activity


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        pytest.param(
            SimpleNamespace(
                verdict="correct",
                error_focus="none",
                confidence=0.99,
                evidence_verified=True,
                answer_echo="42",
                check_summary="Ответ проверен по эталону.",
            ),
            ("correct", "none"),
            id="verified-correct",
        ),
        pytest.param(
            SimpleNamespace(
                verdict="incorrect",
                error_focus="calculation",
                confidence=0.65,
                evidence_verified=True,
                answer_echo="42",
                check_summary="Ответ проверен по эталону.",
            ),
            ("incorrect", "calculation"),
            id="threshold-incorrect",
        ),
        pytest.param(
            SimpleNamespace(
                verdict="correct",
                error_focus="none",
                confidence=0.99,
                evidence_verified=False,
                answer_echo="42",
                check_summary="Ответ проверен по эталону.",
            ),
            ("unsure", "unknown"),
            id="unverified",
        ),
        pytest.param(
            SimpleNamespace(
                verdict="correct",
                error_focus="none",
                confidence=float("nan"),
                evidence_verified=True,
                answer_echo="42",
                check_summary="Ответ проверен по эталону.",
            ),
            ("unsure", "unknown"),
            id="non-finite-confidence",
        ),
        pytest.param(
            SimpleNamespace(
                verdict="incorrect",
                error_focus="calculation",
                confidence=0.99,
                evidence_verified=True,
                answer_echo="43",
                check_summary="Ответ проверен по эталону.",
            ),
            ("unsure", "unknown"),
            id="echo-mismatch",
        ),
        pytest.param(
            SimpleNamespace(
                verdict="correct",
                error_focus="none",
                confidence=0.99,
                evidence_verified=True,
                answer_echo="42",
                check_summary="\x00",
            ),
            ("unsure", "unknown"),
            id="unsafe-summary",
        ),
    ],
)
def test_typed_result_is_fail_closed_before_durable_state(result, expected) -> None:
    """Даже объект, подменённый после parser, не становится binary-feedback без evidence."""
    from api.routers.journey import _normalise_typed_result

    assert _normalise_typed_result(result, answer="42") == expected


def test_photo_validator_rejects_pillow_decompression_warning(monkeypatch) -> None:
    """Даже warning Pillow не должен пропускать потенциальную image bomb."""
    from PIL import Image

    from api.routers.journey import _valid_image

    image_bytes = _PHOTO.read_bytes()
    with Image.open(_PHOTO) as image:
        pixel_count = image.width * image.height
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", max(1, pixel_count - 1))

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", Image.DecompressionBombWarning)
        assert _valid_image(image_bytes, "image/jpeg") is False


def test_photo_validator_enforces_explicit_pixel_cap(monkeypatch) -> None:
    """Свой cap действует, даже если глобальный Pillow guard отключён."""
    from PIL import Image

    from api.routers.journey import _valid_image

    source = io.BytesIO()
    Image.new("RGB", (2, 1), "white").save(source, format="PNG")
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", None)
    monkeypatch.setattr("api.routers.journey._MAX_PHOTO_PIXELS", 1)

    assert _valid_image(source.getvalue(), "image/png") is False


def test_photo_validator_accepts_image_at_explicit_pixel_cap(monkeypatch) -> None:
    """Безопасное изображение ровно на границе cap принимается."""
    from PIL import Image

    from api.routers.journey import _valid_image

    source = io.BytesIO()
    Image.new("RGB", (2, 1), "white").save(source, format="PNG")
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", None)
    monkeypatch.setattr("api.routers.journey._MAX_PHOTO_PIXELS", 2)

    assert _valid_image(source.getvalue(), "image/png") is True


def test_photo_verdict_requires_explicit_ai_verified_evidence() -> None:
    """Невалидированный provider verdict не может стать mastery evidence."""
    from api.routers.journey import _normalise_photo_verdict
    from core.llm_openai import SolutionPhotoResult

    forged = SolutionPhotoResult(
        verdict="correct",
        failed_step=None,
        confidence=0.99,
        provider="gemini",
        model="gemini-test",
    )

    assert _normalise_photo_verdict(forged, {1, 2}) == ("unsure", None)


def _decompositions() -> dict[int, dict]:
    payload = json.loads(
        (Path(__file__).parents[1] / "data" / "full_decomposition_v1.json").read_text(
            encoding="utf-8"
        )
    )
    return {int(item["idx"]): item for item in payload["problems"]}


def test_every_journey_problem_has_machine_checkable_steps() -> None:
    """Маршрут не может выдать задачу, которую photo/guided checker не понимает."""
    from core.grading import is_step_reference_supported

    decompositions = _decompositions()
    unsupported: list[tuple[int, int, str]] = []
    for content_idx in _LESSON_INDICES:
        for step in decompositions[content_idx]["steps"]:
            expected = str(step["expected_value"])
            if not is_step_reference_supported(expected):
                unsupported.append((content_idx, int(step["n"]), expected))

    assert unsupported == []


def test_every_journey_problem_is_verified_evidence_for_its_topic() -> None:
    """Маршрут не использует спорный эталон или задачу из чужого навыка."""
    allowed_primary_skills = {
        "PC06": {
            "mixture_concentration",
            "concentration_after_evaporation",
            "mixture_alligation_solve",
        },
        "EQ04": {
            "translate_words_to_equation",
            "solve_linear",
            "solve_system_substitution",
            "solve_linear_word",
            "inclusion_exclusion_three",
        },
        "FR05": {"compare_frac"},
        "GE04": {
            "angle_ratio_split",
            "angle_ratio_triangle",
            "angle_partition_ratio",
        },
        "DA02": {
            "read_chart_combine",
            "read_graph_value",
            "rate_of_change",
            "average_speed",
            "linear_extrapolation",
            "linear_from_two_points",
            "linear_equation_from_points",
            "closing_speed",
        },
    }
    decompositions = _decompositions()
    defects: list[tuple[str, int, str]] = []

    for topic_id, blueprint in TOPIC_BLUEPRINTS.items():
        content_indices = (
            int(blueprint["target_content_idx"]),
            int(blueprint["transfer_content_idx"]),
            *(int(value) for value in blueprint["reinforcement_content_indices"]),
        )
        for content_idx in content_indices:
            decomposition = decompositions[content_idx]
            if decomposition.get("needs_review"):
                defects.append((topic_id, content_idx, "needs_review"))
            if decomposition.get("node_id") != topic_id:
                defects.append((topic_id, content_idx, "wrong_node"))
            if decomposition.get("primary_micro_skill") not in allowed_primary_skills[topic_id]:
                defects.append((topic_id, content_idx, "wrong_primary_skill"))

    assert defects == []


async def _seed_journey_content(db_session, *, student_id: int) -> None:
    bank = load_problem_bank()
    rows = {idx: bank[idx] for idx in _ALL_INDICES}
    node_names = {
        "FR05": "Сравнение дробей",
        "PC05": "Последовательные проценты",
        "PC06": "Смеси и концентрации",
        "EQ04": "Текстовые уравнения",
        "GE04": "Угловые отношения",
        "DA02": "Графики и данные",
    }
    for node_id in {str(row["node_id"]) for row in rows.values()}:
        await db_session.execute(
            text(
                "INSERT INTO nodes "
                "(id, name_ru, name_kz, difficulty, bkt_p_t, bkt_p_g, bkt_p_s) "
                "VALUES (:id, :name, :name, 3, 0.3, 0.05, 0.1)"
            ),
            {"id": node_id, "name": node_names[node_id]},
        )

    problem_ids: dict[int, int] = {}
    for content_idx, problem in rows.items():
        problem_ids[content_idx] = (
            await db_session.execute(
                text(
                    "INSERT INTO problems "
                    "(content_idx, node_id, text_ru, answer, answer_type, difficulty, raw_score) "
                    "VALUES (:idx, :node, :statement, :answer, :answer_type, :difficulty, :score) "
                    "RETURNING id"
                ),
                {
                    "idx": content_idx,
                    "node": problem["node_id"],
                    "statement": problem["text_ru"],
                    "answer": str(problem["answer"]),
                    "answer_type": problem.get("answer_type"),
                    "difficulty": problem.get("difficulty"),
                    "score": problem.get("raw_score"),
                },
            )
        ).scalar_one()

    decomposition_by_idx = _decompositions()
    micro_skills: set[str] = set()
    for content_idx in _LESSON_INDICES:
        decomposition = decomposition_by_idx[content_idx]
        micro_skills.update(str(step["micro_skill"]) for step in decomposition["steps"])
    for code in micro_skills:
        await db_session.execute(
            text(
                "INSERT INTO micro_skills (code, label_ru, domain, freq) "
                "VALUES (:code, :label, 'journey-test', 1)"
            ),
            {"code": code, "label": code},
        )
    for content_idx in _LESSON_INDICES:
        decomposition = decomposition_by_idx[content_idx]
        await db_session.execute(
            text(
                "INSERT INTO decomposition_problems "
                "(idx, node_id, answer, primary_micro_skill, all_steps_verified, "
                "needs_review, problems_db_id) "
                "VALUES (:idx, :node, :answer, :skill, true, false, :problem_id)"
            ),
            {
                "idx": content_idx,
                "node": decomposition["node_id"],
                "answer": str(decomposition["answer"]),
                "skill": decomposition.get("primary_micro_skill"),
                "problem_id": problem_ids[content_idx],
            },
        )
        for step in decomposition["steps"]:
            await db_session.execute(
                text(
                    "INSERT INTO problem_steps "
                    "(decomp_idx, n, instruction_ru, micro_skill, expected_value, verified) "
                    "VALUES (:idx, :n, :instruction, :skill, :expected, :verified)"
                ),
                {
                    "idx": content_idx,
                    "n": step["n"],
                    "instruction": step["instruction_ru"],
                    "skill": step["micro_skill"],
                    "expected": str(step["expected_value"]),
                    "verified": step.get("verified"),
                },
            )

    await db_session.execute(
        text(
            "INSERT INTO students "
            "(id, first_name, full_name, registered, lang, grade, created_at, "
            "diagnostic_complete, photo_consent, photo_consent_at) "
            "VALUES (:id, 'Аян', 'Аян', true, 'ru', 6, NOW(), false, true, NOW())"
        ),
        {"id": student_id},
    )
    await db_session.commit()


@pytest_asyncio.fixture
async def journey_client(db_session, monkeypatch):
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан")

    student_id = 98401
    await _seed_journey_content(db_session, student_id=student_id)

    from api.routes import _create_token
    import api.routes as routes_module
    import db.base as db_base
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_TEST_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    original_base_session = db_base.async_session
    original_routes_session = routes_module.async_session
    db_base.async_session = factory
    routes_module.async_session = factory

    from core.llm_openai import GuidedAnswerResult
    import api.routers.journey as journey_module

    async def guided_answer_ai(**kwargs):
        submitted = " ".join(kwargs["submitted_answer"].split())
        expected = " ".join(kwargs["expected_value"].split())
        correct = submitted.casefold() == expected.casefold()
        return GuidedAnswerResult(
            verdict="correct" if correct else "incorrect",
            confidence=0.99,
            provider="test-ai",
            model="guided-test",
            evidence_verified=True,
            answer_echo=submitted,
            feedback=(
                "Текущий переход верный."
                if correct
                else "Проверь действие только на этом шаге."
            ),
        )

    monkeypatch.setattr(journey_module, "evaluate_guided_answer", guided_answer_ai)

    from web import app

    # SlowAPI хранит buckets на уровне процесса; integration-cases изолированы.
    routes_module.limiter.reset()
    app.state.limiter.reset()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client, _create_token(student_id), student_id

    db_base.async_session = original_base_session
    routes_module.async_session = original_routes_session
    await engine.dispose()


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _assert_safe(payload: dict) -> None:
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "correct_answer" not in serialized
    assert "expected_value" not in serialized


def test_build_route_uses_fallback_evidence_and_routes_all_five_skills():
    diagnostic = {
        "answers": [
            {"question_id": 127, "correct": True},
            {"question_id": 321, "correct": False},
            {"question_id": 320, "correct": True},
            {"question_id": 876, "correct": False},
            {"question_id": 448, "correct": False},
            {"question_id": 1144, "correct": False},
            {"question_id": 544, "correct": True},
            {"question_id": 1409, "correct": False},
            {"question_id": 804, "correct": False},
        ]
    }

    route = build_route(diagnostic)

    assert [topic["id"] for topic in route["topics"]] == [
        "EQ04",
        "DA02",
        "PC06",
        "GE04",
        "FR05",
    ]
    assert [topic["diagnostic_level"] for topic in route["topics"]] == [
        "foundation",
        "foundation",
        "developing",
        "developing",
        "secure",
    ]
    profile = {skill["id"]: skill for skill in route["skill_profile"]}
    assert set(profile) == {"FR05", "PC05", "EQ04", "GE04", "DA02"}
    assert profile["FR05"]["level"] == "secure"
    assert profile["PC05"]["level"] == "developing"
    assert profile["GE04"]["level"] == "developing"
    assert profile["DA02"]["level"] == "foundation"
    assert len(route["topics"]) == len(DIAGNOSTIC_SKILLS)
    assert all(skill["route_topic_id"] for skill in route["skill_profile"])
    assert {skill["route_topic_id"] for skill in route["skill_profile"]} == set(
        TOPIC_BLUEPRINTS
    )


@pytest.mark.asyncio
async def test_profile_draft_and_substep_survive_reload(journey_client) -> None:
    client, token, _student_id = journey_client
    current = await client.get("/api/journey/current", headers=_headers(token))
    state = current.json()

    response = await client.post(
        "/api/journey/profile/draft",
        headers=_headers(token),
        json={
            "revision": state["revision"],
            "screen": 1,
            "substep": 2,
            "target": "nis-grade-7",
            "weekly_goal": 5,
            "session_minutes": 45,
            "target_window": "later",
            "prep_experience": "teacher",
            "weak_topics": ["GE04"],
            "strong_topics": ["FR05"],
            "mock_math_band": "21-30",
            "language": "ru",
        },
    )

    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["next_step"]["type"] == "profile"
    assert saved["next_step"]["screen"] == 1
    assert saved["next_step"]["substep"] == 2
    assert saved["next_step"]["draft"]["weekly_goal"] == 5

    resumed = await client.get("/api/journey/current", headers=_headers(token))
    assert resumed.status_code == 200
    assert resumed.json()["next_step"] == saved["next_step"]


@pytest.mark.asyncio
async def test_stale_revision_returns_fresh_safe_state(journey_client) -> None:
    """409 сразу несёт authoritative state без ручной перезагрузки экрана."""
    client, token, _student_id = journey_client
    current = (await client.get("/api/journey/current", headers=_headers(token))).json()
    payload = {
        "revision": current["revision"],
        "screen": 1,
        "substep": 1,
        "target": "nis-grade-7",
        "weekly_goal": 4,
        "session_minutes": 30,
        "target_window": "spring-2027",
        "prep_experience": "new",
        "weak_topics": [],
        "strong_topics": [],
        "mock_math_band": "not-taken",
        "language": "ru",
    }
    saved = await client.post(
        "/api/journey/profile/draft",
        headers=_headers(token),
        json=payload,
    )
    assert saved.status_code == 200, saved.text

    stale = await client.post(
        "/api/journey/profile/draft",
        headers=_headers(token),
        json={**payload, "screen": 2},
    )

    assert stale.status_code == 409
    detail = stale.json()["detail"]
    assert detail["code"] == "stale_revision"
    assert detail["current_revision"] == saved.json()["revision"]
    assert detail["state"] == saved.json()
    _assert_safe(detail["state"])


def test_initial_diagnostic_uses_self_report_only_to_order_verified_anchors():
    """Самооценка меняет порядок проверки, но не подменяет evidence диагностики."""

    diagnostic = initial_diagnostic(
        {
            "weak_topics": ["PC05", "DA02"],
            "strong_topics": ["EQ04"],
        }
    )

    assert diagnostic["queue"][:2] == [321, 1409]
    assert diagnostic["queue"][-1] == 876
    assert set(diagnostic["queue"]) == set(DIAGNOSTIC_ANCHORS)
    assert len(diagnostic["queue"]) == len(DIAGNOSTIC_ANCHORS)


@pytest.mark.asyncio
async def test_diagnostic_mastery_seed_distinguishes_developing_from_foundation(
    journey_client,
    db_session,
):
    _, _, student_id = journey_client
    from api.routers.journey import _seed_diagnostic_mastery

    diagnostic = {
        "answers": [
            {"question_id": 127, "correct": True},
            {"question_id": 321, "correct": False},
            {"question_id": 320, "correct": True},
            {"question_id": 876, "correct": False},
            {"question_id": 448, "correct": False},
            {"question_id": 1409, "correct": False},
            {"question_id": 804, "correct": True},
        ]
    }
    await _seed_diagnostic_mastery(db_session, student_id, diagnostic)
    await db_session.commit()

    rows = (
        await db_session.execute(
            text(
                "SELECT node_id, p_mastery FROM mastery "
                "WHERE student_id = :student_id ORDER BY node_id"
            ),
            {"student_id": student_id},
        )
    ).all()
    mastery = {row.node_id: float(row.p_mastery) for row in rows}
    assert mastery["FR05"] == pytest.approx(0.55)
    assert mastery["PC06"] == pytest.approx(0.35)
    assert mastery["EQ04"] == pytest.approx(0.2)
    assert mastery["GE04"] == pytest.approx(0.1)
    assert mastery["DA02"] == pytest.approx(0.35)


def test_image_validator_rejects_decompression_bomb(monkeypatch):
    from PIL import Image
    from api.routers.journey import _valid_image

    monkeypatch.setattr(
        Image,
        "open",
        MagicMock(side_effect=Image.DecompressionBombError("too many pixels")),
    )

    assert _valid_image(_PHOTO.read_bytes(), "image/jpeg") is False


async def _continue(client, token: str, state: dict, action: str) -> dict:
    response = await client.post(
        "/api/journey/continue",
        headers=_headers(token),
        json={"revision": state["revision"], "action": action},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _open_diagnostic(client, token: str) -> dict:
    current = await client.get("/api/journey/current", headers=_headers(token))
    assert current.status_code == 200
    state = current.json()
    assert state["next_step"]["type"] == "profile"

    profile = await client.post(
        "/api/journey/profile",
        headers=_headers(token),
        json={
            "revision": state["revision"],
            "target": "nis-grade-7",
            "weekly_goal": 4,
        },
    )
    assert profile.status_code == 200, profile.text
    state = profile.json()
    assert state["next_step"]["type"] == "exam_map"
    state = await _continue(client, token, state, "open_diagnostic_intro")
    assert state["next_step"]["type"] == "diagnostic_intro"
    state = await _continue(client, token, state, "start_diagnostic")
    assert state["next_step"]["type"] == "diagnostic_question"
    return state


@pytest.mark.asyncio
async def test_profile_persists_real_adaptation_and_drives_diagnostic_order(
    journey_client,
    db_session,
) -> None:
    client, token, student_id = journey_client
    current = await client.get("/api/journey/current", headers=_headers(token))
    state = current.json()

    response = await client.post(
        "/api/journey/profile",
        headers=_headers(token),
        json={
            "revision": state["revision"],
            "target": "nis-grade-7",
            "weekly_goal": 3,
            "session_minutes": 30,
            "target_window": "spring-2027",
            "prep_experience": "self",
            "weak_topics": ["PC05", "DA02"],
            "strong_topics": ["EQ04"],
            "mock_math_band": "21-30",
            "language": "ru",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["context"]["profile"] == {
        "target": "nis-grade-7",
        "weekly_goal": 3,
        "session_minutes": 30,
        "target_window": "spring-2027",
        "prep_experience": "self",
        "weak_topics": ["PC05", "DA02"],
        "strong_topics": ["EQ04"],
        "mock_math_band": "21-30",
        "language": "ru",
    }

    payload = await _continue(client, token, payload, "open_diagnostic_intro")
    payload = await _continue(client, token, payload, "start_diagnostic")
    assert payload["next_step"]["question"]["id"] == 321

    stored = (
        await db_session.execute(
            text("SELECT profile_data FROM student_journeys WHERE student_id = :student_id"),
            {"student_id": student_id},
        )
    ).scalar_one()
    assert stored["session_minutes"] == 30
    assert stored["weak_topics"] == ["PC05", "DA02"]


@pytest.mark.asyncio
async def test_profile_rejects_conflicting_self_report(journey_client) -> None:
    client, token, _student_id = journey_client
    current = await client.get("/api/journey/current", headers=_headers(token))
    state = current.json()

    response = await client.post(
        "/api/journey/profile",
        headers=_headers(token),
        json={
            "revision": state["revision"],
            "target": "nis-grade-7",
            "weekly_goal": 4,
            "session_minutes": 30,
            "target_window": "spring-2027",
            "prep_experience": "new",
            "weak_topics": ["FR05"],
            "strong_topics": ["FR05"],
            "mock_math_band": "not-taken",
            "language": "ru",
        },
    )

    assert response.status_code == 422


async def _finish_diagnostic(
    client,
    token: str,
    *,
    wrong_answers: dict[int, str] | None = None,
) -> dict:
    wrong_answers = wrong_answers or {}
    bank = load_problem_bank()
    state = await _open_diagnostic(client, token)
    while state["next_step"]["type"] == "diagnostic_question":
        question = state["next_step"]["question"]
        question_id = int(question["id"])
        response = await client.post(
            "/api/journey/diagnostic/answer",
            headers=_headers(token),
            json={
                "revision": state["revision"],
                "question_id": question_id,
                "answer": wrong_answers.get(question_id, str(bank[question_id]["answer"])),
                "client_attempt_id": f"diagnostic-{question_id}",
            },
        )
        assert response.status_code == 200, response.text
        state = response.json()
        _assert_safe(state)
    assert state["next_step"]["type"] == "diagnostic_result"
    return state


async def _open_first_task(
    client,
    token: str,
    *,
    wrong_answers: dict[int, str] | None = None,
) -> tuple[dict, dict]:
    result = await _finish_diagnostic(client, token, wrong_answers=wrong_answers)
    route = await _continue(client, token, result, "show_route")
    assert route["next_step"]["type"] == "route_ready"
    intro = await _continue(client, token, route, "start_lesson")
    assert intro["next_step"]["type"] == "lesson_intro"
    task = await _continue(client, token, intro, "start_task")
    assert task["next_step"]["type"] == "independent_task"
    return route, task


@pytest.mark.asyncio
async def test_typed_incorrect_stays_on_task_records_once_and_replays_exact_response(
    journey_client,
    db_session,
    monkeypatch,
):
    """AI-confirmed incorrect сохраняет задачу и учитывает outcome ровно один раз."""

    client, token, student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]
    calls: list[dict] = []

    from core.llm_openai import TypedAnswerResult

    async def typed_answer(**kwargs):
        calls.append(kwargs)
        return TypedAnswerResult(
            verdict="incorrect",
            error_focus="calculation",
            confidence=0.97,
            provider="gemini",
            model="gemini-test",
            evidence_verified=True,
            answer_echo="42",
            check_summary="provider prose must not reach the learner",
        )

    monkeypatch.setattr("api.routers.journey.evaluate_typed_answer", typed_answer)
    payload = {
        "revision": task["revision"],
        "problem_id": problem_id,
        "answer": "  ４２\n",
        "client_attempt_id": "typed-formative-replay-1",
    }
    response = await client.post(
        "/api/journey/answer",
        headers=_headers(token),
        json=payload,
    )

    assert response.status_code == 200, response.text
    checked = response.json()
    assert checked["revision"] == task["revision"] + 1
    assert checked["next_step"]["type"] == "independent_task"
    assert checked["next_step"]["problem"]["id"] == problem_id
    assert checked["next_step"]["typed_feedback"] == {
        "verdict": "incorrect",
        "message": "Проверь вычисления и попробуй ещё раз.",
        "error_focus": "calculation",
        "counts_for_mastery": True,
    }
    assert checked["response"]["typed_available"] is True
    assert calls[0]["submitted_answer"] == "42"
    assert calls[0]["trusted_context"]["journey"]["revision"] == task["revision"]
    assert calls[0]["trusted_context"]["stage"] == "independent_task"
    assert calls[0]["trusted_context"]["problem"]["id"] == problem_id
    assert calls[0]["trusted_context"]["support"]["used"] is False
    assert calls[0]["untrusted_history"] == []
    assert "provider prose" not in json.dumps(checked, ensure_ascii=False)
    _assert_safe(checked)

    replay = await client.post(
        "/api/journey/answer",
        headers=_headers(token),
        json=payload,
    )
    assert replay.status_code == 200, replay.text
    assert replay.json() == checked
    assert len(calls) == 1
    assert (
        await db_session.execute(
            text("SELECT count(*) FROM attempts WHERE student_id = :student_id"),
            {"student_id": student_id},
        )
    ).scalar_one() == 1
    attempt = (
        await db_session.execute(
            text(
                "SELECT kind, answer_given, verdict, counts_for_mastery "
                "FROM journey_attempts WHERE client_attempt_id = 'typed-formative-replay-1'"
            )
        )
    ).one()
    assert attempt.kind == "independent_typed"
    assert attempt.answer_given == "42"
    assert attempt.verdict == "incorrect"
    assert attempt.counts_for_mastery is True


@pytest.mark.asyncio
async def test_typed_correct_advances_to_transfer_and_replays_exact_response(
    journey_client,
    db_session,
    monkeypatch,
):
    """AI-confirmed correct сразу открывает transfer-задачу без обязательного фото."""

    client, token, student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]

    from core.llm_openai import TypedAnswerResult

    async def equivalent(**kwargs):
        assert kwargs["submitted_answer"] == "2 5/6"
        return TypedAnswerResult(
            verdict="correct",
            error_focus="format",
            confidence=1.0,
            provider="gemini",
            model="gemini-test",
            evidence_verified=True,
            answer_echo="2 5/6",
            check_summary="Эквивалентное значение, отличается только форма записи.",
        )

    monkeypatch.setattr("api.routers.journey.evaluate_typed_answer", equivalent)
    response = await client.post(
        "/api/journey/answer",
        headers=_headers(token),
        json={
            "revision": task["revision"],
            "problem_id": problem_id,
            "answer": "2 5/6",
            "client_attempt_id": "typed-equivalent-format-1",
        },
    )

    assert response.status_code == 200, response.text
    checked = response.json()
    assert checked["revision"] == task["revision"] + 1
    assert checked["next_step"]["type"] == "transfer_task"
    assert checked["next_step"]["problem"]["id"] != problem_id
    assert "typed_feedback" not in checked["next_step"]
    assert checked["response"]["typed_available"] is True
    assert (
        await db_session.execute(
            text("SELECT count(*) FROM attempts WHERE student_id = :student_id"),
            {"student_id": student_id},
        )
    ).scalar_one() == 1
    attempt = (
        await db_session.execute(
            text(
                "SELECT verdict, counts_for_mastery FROM journey_attempts "
                "WHERE client_attempt_id = 'typed-equivalent-format-1'"
            )
        )
    ).one()
    assert attempt.verdict == "correct"
    assert attempt.counts_for_mastery is True

    replay = await client.post(
        "/api/journey/answer",
        headers=_headers(token),
        json={
            "revision": task["revision"],
            "problem_id": problem_id,
            "answer": "2 5/6",
            "client_attempt_id": "typed-equivalent-format-1",
        },
    )
    assert replay.status_code == 200, replay.text
    assert replay.json() == checked

    stale = await client.post(
        "/api/journey/answer",
        headers=_headers(token),
        json={
            "revision": task["revision"],
            "problem_id": problem_id,
            "answer": "2 5/6",
            "client_attempt_id": "typed-stale-after-advance-1",
        },
    )
    assert stale.status_code == 409
    stale_detail = stale.json()["detail"]
    assert stale_detail["code"] == "stale_revision"
    assert stale_detail["state"] == checked


@pytest.mark.asyncio
async def test_typed_answer_provider_error_is_retryable_without_revision_bump(
    journey_client,
    db_session,
    monkeypatch,
):
    """Тот же canonical attempt повторно проверяется и затем terminal-replay'ится."""

    client, token, student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]
    calls = 0

    from core.llm_openai import LlmUnavailable, TypedAnswerResult

    async def unavailable_then_incorrect(**_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise LlmUnavailable("temporary provider failure")
        return TypedAnswerResult(
            verdict="incorrect",
            error_focus="calculation",
            confidence=0.97,
            provider="gemini",
            model="gemini-retry",
            evidence_verified=True,
            answer_echo="42",
            check_summary="Проверка после повторного вызова.",
        )

    monkeypatch.setattr(
        "api.routers.journey.evaluate_typed_answer",
        unavailable_then_incorrect,
    )
    payload = {
        "revision": task["revision"],
        "problem_id": problem_id,
        "answer": "42",
        "client_attempt_id": "typed-provider-error-1",
    }
    response = await client.post(
        "/api/journey/answer",
        headers=_headers(token),
        json=payload,
    )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["code"] == "ai_unavailable"
    assert detail["state"]["revision"] == task["revision"]
    assert detail["state"]["next_step"]["typed_feedback"] == {
        "verdict": "unsure",
        "message": "Проверка временно недоступна. Повтори проверку или отправь фото.",
        "error_focus": "unknown",
        "counts_for_mastery": False,
    }
    assert calls == 1

    retry = await client.post(
        "/api/journey/answer",
        headers=_headers(token),
        json=payload,
    )
    assert retry.status_code == 200, retry.text
    checked = retry.json()
    assert checked["revision"] == task["revision"] + 1
    assert checked["next_step"]["typed_feedback"]["verdict"] == "incorrect"
    assert calls == 2

    replay = await client.post(
        "/api/journey/answer",
        headers=_headers(token),
        json=payload,
    )
    assert replay.status_code == 200, replay.text
    assert replay.json() == checked
    assert calls == 2
    attempt = (
        await db_session.execute(
            text(
                "SELECT status, verdict, counts_for_mastery FROM journey_attempts "
                "WHERE client_attempt_id = 'typed-provider-error-1'"
            )
        )
    ).one()
    assert attempt.status == "accepted"
    assert attempt.verdict == "incorrect"
    assert attempt.counts_for_mastery is True
    assert (
        await db_session.execute(
            text(
                "SELECT count(*) FROM journey_attempts "
                "WHERE student_id = :student_id "
                "AND client_attempt_id = 'typed-provider-error-1'"
            ),
            {"student_id": student_id},
        )
    ).scalar_one() == 1


@pytest.mark.asyncio
async def test_typed_provider_error_retry_has_one_live_provider_call_for_same_attempt(
    journey_client,
    db_session,
    monkeypatch,
):
    """Параллельный replay видит processing lease и не дублирует provider вызов."""

    client, token, student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]
    provider_started = asyncio.Event()
    release_provider = asyncio.Event()
    calls = 0

    from core.llm_openai import LlmUnavailable, TypedAnswerResult

    async def unavailable_then_delayed_result(**_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise LlmUnavailable("temporary provider failure")
        provider_started.set()
        await release_provider.wait()
        return TypedAnswerResult(
            verdict="incorrect",
            error_focus="calculation",
            confidence=0.97,
            provider="gemini",
            model="gemini-retry",
            evidence_verified=True,
            answer_echo="42",
            check_summary="Повторная проверка завершена.",
        )

    monkeypatch.setattr(
        "api.routers.journey.evaluate_typed_answer",
        unavailable_then_delayed_result,
    )
    payload = {
        "revision": task["revision"],
        "problem_id": problem_id,
        "answer": "42",
        "client_attempt_id": "typed-provider-race-1",
    }

    first = await client.post(
        "/api/journey/answer",
        headers=_headers(token),
        json=payload,
    )
    assert first.status_code == 503, first.text

    retry = asyncio.create_task(
        client.post(
            "/api/journey/answer",
            headers=_headers(token),
            json=payload,
        )
    )
    await asyncio.wait_for(provider_started.wait(), timeout=2)
    try:
        overlap = await client.post(
            "/api/journey/answer",
            headers=_headers(token),
            json=payload,
        )
        assert overlap.status_code == 409, overlap.text
        assert overlap.json()["detail"]["code"] == "typed_processing"
        assert calls == 2
    finally:
        release_provider.set()

    completed = await retry
    assert completed.status_code == 200, completed.text
    checked = completed.json()
    assert checked["next_step"]["typed_feedback"]["verdict"] == "incorrect"
    assert calls == 2

    replay = await client.post(
        "/api/journey/answer",
        headers=_headers(token),
        json=payload,
    )
    assert replay.status_code == 200, replay.text
    assert replay.json() == checked
    assert calls == 2
    assert (
        await db_session.execute(
            text(
                "SELECT count(*) FROM journey_attempts "
                "WHERE student_id = :student_id "
                "AND client_attempt_id = 'typed-provider-race-1'"
            ),
            {"student_id": student_id},
        )
    ).scalar_one() == 1


@pytest.mark.asyncio
async def test_live_typed_processing_survives_reload_and_blocks_photo_race(
    journey_client,
    db_session,
    monkeypatch,
):
    """Reload видит pending answer, а фото не может отменить поздний correct."""

    client, token, student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]
    provider_started = asyncio.Event()
    release_provider = asyncio.Event()

    from core.llm_openai import TypedAnswerResult

    async def delayed_correct(**kwargs):
        assert kwargs["submitted_answer"] == "2 5/6"
        provider_started.set()
        await release_provider.wait()
        return TypedAnswerResult(
            verdict="correct",
            error_focus="none",
            confidence=1.0,
            provider="gemini",
            model="gemini-race",
            evidence_verified=True,
            answer_echo="2 5/6",
            check_summary="Ответ эквивалентен эталону.",
        )

    monkeypatch.setattr("api.routers.journey.evaluate_typed_answer", delayed_correct)
    typed = asyncio.create_task(
        client.post(
            "/api/journey/answer",
            headers=_headers(token),
            json={
                "revision": task["revision"],
                "problem_id": problem_id,
                "answer": "2 5/6",
                "client_attempt_id": "typed-photo-mutual-lock-1",
            },
        )
    )
    await asyncio.wait_for(provider_started.wait(), timeout=2)
    try:
        reloaded = await client.get("/api/journey/current", headers=_headers(token))
        assert reloaded.status_code == 200, reloaded.text
        pending = reloaded.json()
        assert pending["next_step"]["type"] == "typed_processing"
        assert pending["next_step"]["preserved_answer"] == {"value": "2 5/6"}
        assert pending["learner_evidence"] == {
            "kind": "typed",
            "status": "processing",
            "label": "2 5/6",
        }

        photo = await client.post(
            "/api/journey/photo",
            headers=_headers(token),
            data={
                "revision": str(task["revision"]),
                "problem_id": str(problem_id),
                "client_attempt_id": "photo-during-typed-lock-1",
            },
            files={"photo": ("solution.jpg", _PHOTO.read_bytes(), "image/jpeg")},
        )
        assert photo.status_code == 409, photo.text
        assert photo.json()["detail"]["code"] == "typed_processing"
        assert photo.json()["detail"]["state"]["next_step"]["type"] == "typed_processing"
    finally:
        release_provider.set()

    completed = await typed
    assert completed.status_code == 200, completed.text
    advanced = completed.json()
    assert advanced["next_step"]["type"] == "transfer_task"
    assert advanced["next_step"]["problem"]["id"] != problem_id
    assert (
        await db_session.execute(
            text(
                "SELECT count(*) FROM journey_attempts "
                "WHERE student_id = :student_id "
                "AND client_attempt_id = 'photo-during-typed-lock-1'"
            ),
            {"student_id": student_id},
        )
    ).scalar_one() == 0


@pytest.mark.asyncio
async def test_typed_result_is_persisted_after_request_disconnect(
    journey_client,
    db_session,
    monkeypatch,
):
    """Закрытие страницы не отменяет уже начатую AI-проверку."""

    client, token, student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]
    provider_started = asyncio.Event()
    release_provider = asyncio.Event()

    from core.llm_openai import TypedAnswerResult

    async def delayed_correct(**kwargs):
        assert kwargs["submitted_answer"] == "2 5/6"
        provider_started.set()
        await release_provider.wait()
        return TypedAnswerResult(
            verdict="correct",
            error_focus="none",
            confidence=1.0,
            provider="gemini",
            model="gemini-disconnect",
            evidence_verified=True,
            answer_echo="2 5/6",
            check_summary="Ответ эквивалентен эталону.",
        )

    monkeypatch.setattr("api.routers.journey.evaluate_typed_answer", delayed_correct)
    submitted = asyncio.create_task(
        client.post(
            "/api/journey/answer",
            headers=_headers(token),
            json={
                "revision": task["revision"],
                "problem_id": problem_id,
                "answer": "2 5/6",
                "client_attempt_id": "typed-disconnect-1",
            },
        )
    )
    await asyncio.wait_for(provider_started.wait(), timeout=2)
    submitted.cancel()
    with pytest.raises(asyncio.CancelledError):
        await submitted
    release_provider.set()

    async def wait_for_advanced_state() -> dict:
        for _ in range(100):
            current = await client.get(
                "/api/journey/current",
                headers=_headers(token),
            )
            assert current.status_code == 200, current.text
            state = current.json()
            if state["next_step"]["type"] != "typed_processing":
                return state
            await asyncio.sleep(0.02)
        raise AssertionError("AI-результат не сохранился после disconnect")

    advanced = await wait_for_advanced_state()
    assert advanced["next_step"]["type"] == "transfer_task"
    assert advanced["next_step"]["problem"]["id"] != problem_id
    persisted = (
        await db_session.execute(
            text(
                "SELECT status, verdict, model FROM journey_attempts "
                "WHERE student_id = :student_id "
                "AND client_attempt_id = 'typed-disconnect-1'"
            ),
            {"student_id": student_id},
        )
    ).one()
    assert tuple(persisted) == ("accepted", "correct", "gemini-disconnect")


@pytest.mark.asyncio
async def test_typed_incorrect_feedback_persists_after_request_disconnect(
    journey_client,
    monkeypatch,
):
    """Reload после disconnect получает durable feedback, а не пустую форму."""

    client, token, _student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]
    provider_started = asyncio.Event()
    release_provider = asyncio.Event()

    from core.llm_openai import TypedAnswerResult

    async def delayed_incorrect(**kwargs):
        assert kwargs["submitted_answer"] == "0"
        provider_started.set()
        await release_provider.wait()
        return TypedAnswerResult(
            verdict="incorrect",
            error_focus="calculation",
            confidence=0.99,
            provider="gemini",
            model="gemini-disconnect-incorrect",
            evidence_verified=True,
            answer_echo="0",
            check_summary="Ответ не согласуется с условием.",
        )

    monkeypatch.setattr("api.routers.journey.evaluate_typed_answer", delayed_incorrect)
    submitted = asyncio.create_task(
        client.post(
            "/api/journey/answer",
            headers=_headers(token),
            json={
                "revision": task["revision"],
                "problem_id": problem_id,
                "answer": "0",
                "client_attempt_id": "typed-disconnect-incorrect-1",
            },
        )
    )
    await asyncio.wait_for(provider_started.wait(), timeout=2)
    submitted.cancel()
    with pytest.raises(asyncio.CancelledError):
        await submitted
    release_provider.set()

    for _ in range(100):
        current = await client.get("/api/journey/current", headers=_headers(token))
        assert current.status_code == 200, current.text
        state = current.json()
        if state["next_step"]["type"] != "typed_processing":
            break
        await asyncio.sleep(0.02)
    else:
        raise AssertionError("Incorrect AI-результат не сохранился после disconnect")

    assert state["next_step"]["type"] == "independent_task"
    assert state["next_step"]["typed_feedback"] == {
        "verdict": "incorrect",
        "error_focus": "calculation",
        "message": "Проверь вычисления и попробуй ещё раз.",
        "counts_for_mastery": True,
    }
    assert state["next_step"]["preserved_answer"] == {"value": "0"}


@pytest.mark.asyncio
async def test_typed_answer_fails_closed_when_mocked_result_lacks_evidence(
    journey_client,
    db_session,
    monkeypatch,
):
    """Даже forged result минует mastery и возвращает только safe unsure feedback."""

    client, token, student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]

    from core.llm_openai import TypedAnswerResult

    async def forged(**_kwargs):
        return TypedAnswerResult(
            verdict="correct",
            error_focus="none",
            confidence=0.99,
            provider="gemini",
            model="gemini-test",
            evidence_verified=False,
            answer_echo="42",
            check_summary="untrusted summary",
        )

    monkeypatch.setattr("api.routers.journey.evaluate_typed_answer", forged)
    response = await client.post(
        "/api/journey/answer",
        headers=_headers(token),
        json={
            "revision": task["revision"],
            "problem_id": problem_id,
            "answer": "42",
            "client_attempt_id": "typed-forged-result-1",
        },
    )

    assert response.status_code == 200, response.text
    checked = response.json()
    assert checked["next_step"]["typed_feedback"]["verdict"] == "unsure"
    assert checked["next_step"]["typed_feedback"]["counts_for_mastery"] is False
    assert (
        await db_session.execute(
            text("SELECT count(*) FROM attempts WHERE student_id = :student_id"),
            {"student_id": student_id},
        )
    ).scalar_one() == 0


@pytest.mark.asyncio
async def test_new_student_is_adapted_before_any_task(journey_client):
    client, token, _ = journey_client

    current = await client.get("/api/journey/current", headers=_headers(token))

    assert current.status_code == 200
    state = current.json()
    assert state["next_step"]["type"] == "profile"
    assert state["next_step"]["student"] == {"name": "Аян", "grade": 6}
    assert state["next_step"]["primary_action"] == "Настроить подготовку"
    assert "problem" not in state["next_step"]
    _assert_safe(state)

    diagnostic = await _open_diagnostic(client, token)
    exam_map = diagnostic["context"]["exam_map"]
    assert exam_map["day_one"] == [
        {"name": "Математика", "questions": 40, "minutes": 60, "covered": True},
        {
            "name": "Количественные характеристики",
            "questions": 60,
            "minutes": 30,
            "covered": True,
        },
        {"name": "Естествознание", "questions": 20, "minutes": 30, "covered": False},
    ]


@pytest.mark.asyncio
async def test_diagnostic_persists_issued_question_and_adaptive_branch(
    journey_client,
    db_session,
):
    client, token, student_id = journey_client
    state = await _open_diagnostic(client, token)

    while int(state["next_step"]["question"]["id"]) != 321:
        question_id = int(state["next_step"]["question"]["id"])
        response = await client.post(
            "/api/journey/diagnostic/answer",
            headers=_headers(token),
            json={
                "revision": state["revision"],
                "question_id": question_id,
                "answer": str(load_problem_bank()[question_id]["answer"]),
                "client_attempt_id": f"before-pc-{question_id}",
            },
        )
        state = response.json()

    wrong = await client.post(
        "/api/journey/diagnostic/answer",
        headers=_headers(token),
        json={
            "revision": state["revision"],
            "question_id": 321,
            "answer": "1200",
            "client_attempt_id": "pc-anchor-wrong",
        },
    )
    assert wrong.status_code == 200, wrong.text
    branched = wrong.json()
    assert branched["next_step"]["type"] == "diagnostic_question"
    assert branched["next_step"]["question"]["id"] == 320

    resumed = await client.get("/api/journey/current", headers=_headers(token))
    assert resumed.json()["next_step"]["question"]["id"] == 320

    stored = (
        await db_session.execute(
            text(
                "SELECT diagnostic FROM student_journeys WHERE student_id = :student_id"
            ),
            {"student_id": student_id},
        )
    ).scalar_one()
    assert stored["queue"][stored["position"]] == 320
    assert stored["answers"][-1]["question_id"] == 321
    assert stored["answers"][-1]["correct"] is False
    assert (
        await db_session.execute(
            text(
                "SELECT count(*) FROM journey_attempts "
                "WHERE student_id = :student_id AND client_attempt_id = 'pc-anchor-wrong'"
            ),
            {"student_id": student_id},
        )
    ).scalar_one() == 1

@pytest.mark.asyncio
async def test_diagnostic_evidence_changes_route_order(journey_client):
    client, token, _ = journey_client

    pc_result = await _finish_diagnostic(client, token, wrong_answers={321: "1200"})
    pc_route = await _continue(client, token, pc_result, "show_route")
    assert [topic["id"] for topic in pc_route["next_step"]["topics"][:2]] == ["PC06", "EQ04"]
    assert "процент" in pc_route["next_step"]["topics"][0]["reason"].lower()


@pytest.mark.asyncio
async def test_explicit_help_keeps_same_task_and_never_counts_as_mastery(
    journey_client,
    db_session,
):
    client, token, student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]

    help_response = await client.post(
        "/api/journey/help",
        headers=_headers(token),
        json={"revision": task["revision"], "problem_id": problem_id},
    )
    assert help_response.status_code == 200, help_response.text
    guided = help_response.json()
    assert guided["next_step"]["type"] == "guided_step"
    assert guided["next_step"]["problem"]["id"] == problem_id
    assert guided["next_step"]["photo_required"] is False
    assert "не повышает уровень" in guided["next_step"]["mastery_note"]

    step_answers = ["75", "500", "15"]
    for index, answer in enumerate(step_answers, start=1):
        response = await client.post(
            "/api/journey/guided/answer",
            headers=_headers(token),
            json={
                "revision": guided["revision"],
                "problem_id": problem_id,
                "step_n": index,
                "answer": answer,
                "client_attempt_id": f"guided-{index}",
            },
        )
        assert response.status_code == 200, response.text
        guided = response.json()

    assert guided["next_step"]["type"] == "transfer_task"
    assert guided["next_step"]["problem"]["id"] != problem_id
    assert guided["next_step"]["photo_required"] is False
    assert (
        await db_session.execute(
            text(
                "SELECT count(*) FROM attempts WHERE student_id = :student_id"
            ),
            {"student_id": student_id},
        )
    ).scalar_one() == 0
    assert (
        await db_session.execute(
            text(
                "SELECT count(*) FROM journey_attempts "
                "WHERE student_id = :student_id AND kind = 'guided' "
                "AND counts_for_mastery = false"
            ),
            {"student_id": student_id},
        )
    ).scalar_one() == 3


@pytest.mark.asyncio
async def test_guided_stage_does_not_accept_a_later_equivalent_equation(
    journey_client,
    db_session,
):
    client, token, _student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]

    help_response = await client.post(
        "/api/journey/help",
        headers=_headers(token),
        json={"revision": task["revision"], "problem_id": problem_id},
    )
    guided = help_response.json()
    step_n = guided["next_step"]["step"]["number"]

    await db_session.execute(
        text(
            "UPDATE problem_steps SET expected_value = '0.05x+(500-x)*0.15=40' "
            "WHERE decomp_idx = ("
            "  SELECT idx FROM decomposition_problems WHERE problems_db_id = :problem_id"
            ") AND n = :step_n"
        ),
        {"problem_id": problem_id, "step_n": step_n},
    )
    await db_session.commit()

    response = await client.post(
        "/api/journey/guided/answer",
        headers=_headers(token),
        json={
            "revision": guided["revision"],
            "problem_id": problem_id,
            "step_n": step_n,
            "answer": "x=350",
            "client_attempt_id": "guided-stage-collapse-regression",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["next_step"]["type"] == "guided_step"
    assert payload["next_step"]["step"]["number"] == step_n
    assert payload["next_step"]["feedback"]["verdict"] == "incorrect"
    assert (
        await db_session.execute(
            text(
                "SELECT verdict FROM journey_attempts "
                "WHERE client_attempt_id = 'guided-stage-collapse-regression'"
            ),
        )
    ).scalar_one() == "incorrect"


@pytest.mark.asyncio
async def test_guided_step_uses_ai_verdict_not_backend_string_match(
    journey_client,
    db_session,
    monkeypatch,
):
    client, token, _student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]
    guided = (
        await client.post(
            "/api/journey/help",
            headers=_headers(token),
            json={"revision": task["revision"], "problem_id": problem_id},
        )
    ).json()
    step_n = guided["next_step"]["step"]["number"]
    expected = (
        await db_session.execute(
            text(
                "SELECT expected_value FROM problem_steps "
                "WHERE decomp_idx = :idx AND n = :step_n"
            ),
            {
                "idx": guided["next_step"]["problem"]["content_idx"],
                "step_n": step_n,
            },
        )
    ).scalar_one()

    from core.llm_openai import GuidedAnswerResult

    async def ai_incorrect(**kwargs):
        return GuidedAnswerResult(
            verdict="incorrect",
            confidence=0.98,
            provider="test-ai",
            model="guided-test",
            evidence_verified=True,
            answer_echo=kwargs["submitted_answer"],
            feedback="В этой записи не сходится текущий переход.",
        )

    monkeypatch.setattr("api.routers.journey.evaluate_guided_answer", ai_incorrect)
    rejected = await client.post(
        "/api/journey/guided/answer",
        headers=_headers(token),
        json={
            "revision": guided["revision"],
            "problem_id": problem_id,
            "step_n": step_n,
            "answer": expected,
            "client_attempt_id": "guided-ai-overrules-string-match",
        },
    )
    assert rejected.status_code == 200, rejected.text
    rejected_state = rejected.json()
    assert rejected_state["next_step"]["step"]["number"] == step_n
    assert rejected_state["next_step"]["feedback"]["verdict"] == "incorrect"

    async def ai_correct(**kwargs):
        return GuidedAnswerResult(
            verdict="correct",
            confidence=0.98,
            provider="test-ai",
            model="guided-test",
            evidence_verified=True,
            answer_echo=kwargs["submitted_answer"],
            feedback="Смысл перехода верный.",
        )

    monkeypatch.setattr("api.routers.journey.evaluate_guided_answer", ai_correct)
    accepted = await client.post(
        "/api/journey/guided/answer",
        headers=_headers(token),
        json={
            "revision": rejected_state["revision"],
            "problem_id": problem_id,
            "step_n": step_n,
            "answer": "другая запись, которую backend не сравнивает",
            "client_attempt_id": "guided-ai-owns-correct-verdict",
        },
    )
    assert accepted.status_code == 200, accepted.text
    accepted_state = accepted.json()
    assert accepted_state["next_step"]["type"] == "guided_step"
    assert accepted_state["next_step"]["step"]["number"] > step_n


@pytest.mark.parametrize(
    ("protected", "feedback"),
    [
        ("1/2", "Получается 0,5. Что проверишь?"),
        ("1/2", "Это одна вторая. Как проверишь?"),
        ("0,5 кг", "Получается 500 г. Что проверишь?"),
    ],
)
def test_guided_feedback_blocks_semantic_protected_value(protected, feedback):
    """AI не может раскрыть ожидаемое значение в эквивалентной форме."""
    from api.routers.journey import _normalise_guided_result
    from core.llm_openai import GuidedAnswerResult

    verdict, message = _normalise_guided_result(
        GuidedAnswerResult(
            verdict="incorrect",
            confidence=0.98,
            provider="test-ai",
            model="guided-test",
            evidence_verified=True,
            answer_echo="черновик",
            feedback=feedback,
        ),
        answer="черновик",
        protected_values=[protected],
    )

    assert verdict == "incorrect"
    assert message == "Проверь действие в этом шаге и попробуй ещё раз."


@pytest.mark.asyncio
async def test_unreadable_photo_is_recoverable_and_not_a_math_error(
    journey_client,
    db_session,
    monkeypatch,
):
    client, token, student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]

    from core.llm_openai import SolutionPhotoResult

    async def unreadable(**_kwargs):
        return SolutionPhotoResult(
            verdict="unreadable",
            failed_step=None,
            confidence=0.96,
            provider="gemini",
            model="gemini-test",
        )

    monkeypatch.setattr("api.routers.journey.evaluate_solution_photo", unreadable)
    response = await client.post(
        "/api/journey/photo",
        headers=_headers(token),
        data={
            "revision": str(task["revision"]),
            "problem_id": str(problem_id),
            "client_attempt_id": "unreadable-photo-1",
        },
        files={"photo": ("solution.jpg", _PHOTO.read_bytes(), "image/jpeg")},
    )
    assert response.status_code == 200, response.text
    recovery = response.json()
    assert recovery["next_step"]["type"] == "photo_recovery"
    assert recovery["next_step"]["reason"] == "unreadable"
    assert recovery["next_step"]["preserved_photo"]["name"] == "solution.jpg"
    assert recovery["next_step"]["primary_action"] == "Переснять фото"
    assert recovery["next_step"]["problem"]["id"] == problem_id

    assert (
        await db_session.execute(
            text(
                "SELECT count(*) FROM attempts WHERE student_id = :student_id"
            ),
            {"student_id": student_id},
        )
    ).scalar_one() == 0
    attempt = (
        await db_session.execute(
            text(
                "SELECT verdict, counts_for_mastery, photo_ref FROM journey_attempts "
                "WHERE student_id = :student_id AND client_attempt_id = 'unreadable-photo-1'"
            ),
            {"student_id": student_id},
        )
    ).one()
    assert attempt.verdict == "unreadable"
    assert attempt.counts_for_mastery is False
    assert attempt.photo_ref

    retry = await _continue(client, token, recovery, "retry_photo")
    assert retry["next_step"]["type"] == "independent_task"
    assert retry["next_step"]["problem"]["id"] == problem_id


@pytest.mark.asyncio
async def test_photo_problem_mismatch_returns_current_safe_state(journey_client) -> None:
    """Фото для старой задачи не меняет маршрут и сразу возвращает текущий экран."""
    client, token, _student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]

    response = await client.post(
        "/api/journey/photo",
        headers=_headers(token),
        data={
            "revision": str(task["revision"]),
            "problem_id": str(problem_id + 999_999),
            "client_attempt_id": "mismatched-photo-1",
        },
        files={"photo": ("solution.jpg", _PHOTO.read_bytes(), "image/jpeg")},
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "problem_mismatch"
    assert detail["state"] == task
    _assert_safe(detail["state"])


@pytest.mark.asyncio
async def test_photo_consent_is_explicit_and_required_before_upload(
    journey_client,
    db_session,
):
    client, token, student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]

    await db_session.execute(
        text(
            "UPDATE students SET photo_consent = NULL, photo_consent_at = NULL "
            "WHERE id = :student_id"
        ),
        {"student_id": student_id},
    )
    await db_session.commit()

    resumed = await client.get("/api/journey/current", headers=_headers(token))
    assert resumed.status_code == 200
    state = resumed.json()
    assert state["next_step"]["photo_consent_required"] is True

    blocked = await client.post(
        "/api/journey/photo",
        headers=_headers(token),
        data={
            "revision": str(state["revision"]),
            "problem_id": str(problem_id),
            "client_attempt_id": "photo-without-consent",
        },
        files={"photo": ("solution.jpg", _PHOTO.read_bytes(), "image/jpeg")},
    )
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "consent_required"

    consent = await client.post(
        "/api/trainer/consent",
        headers=_headers(token),
        json={"photo_consent": True},
    )
    assert consent.status_code == 200
    refreshed = await client.get("/api/journey/current", headers=_headers(token))
    assert refreshed.json()["next_step"]["photo_consent_required"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider_verdict", "confidence", "failed_step", "expected_reason"),
    [
        ("wrong_photo", 0.97, None, "wrong_photo"),
        ("unsure", 0.91, None, "unsure"),
        ("correct", 0.40, None, "unsure"),
        ("incorrect", 0.96, 999, "unsure"),
    ],
)
async def test_non_math_photo_verdicts_never_change_mastery(
    journey_client,
    db_session,
    monkeypatch,
    provider_verdict,
    confidence,
    failed_step,
    expected_reason,
):
    client, token, student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]

    from core.llm_openai import SolutionPhotoResult

    async def verdict(**_kwargs):
        return SolutionPhotoResult(
            verdict=provider_verdict,
            failed_step=failed_step,
            confidence=confidence,
            provider="gemini",
            model="gemini-test",
            evidence_verified=provider_verdict in {"correct", "incorrect"},
        )

    monkeypatch.setattr("api.routers.journey.evaluate_solution_photo", verdict)
    response = await client.post(
        "/api/journey/photo",
        headers=_headers(token),
        data={
            "revision": str(task["revision"]),
            "problem_id": str(problem_id),
            "client_attempt_id": f"recovery-{provider_verdict}-{failed_step}",
        },
        files={"photo": ("solution.jpg", _PHOTO.read_bytes(), "image/jpeg")},
    )
    assert response.status_code == 200, response.text
    recovery = response.json()
    assert recovery["next_step"]["type"] == "photo_recovery"
    assert recovery["next_step"]["reason"] == expected_reason
    assert (
        await db_session.execute(
            text("SELECT count(*) FROM attempts WHERE student_id = :student_id"),
            {"student_id": student_id},
        )
    ).scalar_one() == 0


@pytest.mark.asyncio
async def test_unverified_correct_photo_never_changes_mastery(
    journey_client,
    db_session,
    monkeypatch,
):
    """Даже уверенный forged correct без code evidence остаётся recovery."""
    client, token, student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]
    mastery_before = (
        await db_session.execute(
            text(
                "SELECT p_mastery FROM mastery "
                "WHERE student_id = :student_id AND node_id = 'PC06'"
            ),
            {"student_id": student_id},
        )
    ).scalar_one()

    from core.llm_openai import SolutionPhotoResult

    async def forged_correct(**_kwargs):
        return SolutionPhotoResult(
            verdict="correct",
            failed_step=None,
            confidence=0.99,
            provider="gemini",
            model="gemini-test",
            evidence_verified=False,
        )

    monkeypatch.setattr("api.routers.journey.evaluate_solution_photo", forged_correct)
    response = await client.post(
        "/api/journey/photo",
        headers=_headers(token),
        data={
            "revision": str(task["revision"]),
            "problem_id": str(problem_id),
            "client_attempt_id": "forged-unverified-correct",
        },
        files={"photo": ("solution.jpg", _PHOTO.read_bytes(), "image/jpeg")},
    )

    assert response.status_code == 200, response.text
    recovery = response.json()
    assert recovery["next_step"]["type"] == "photo_recovery"
    assert recovery["next_step"]["reason"] == "unsure"
    assert (
        await db_session.execute(
            text("SELECT count(*) FROM attempts WHERE student_id = :student_id"),
            {"student_id": student_id},
        )
    ).scalar_one() == 0
    attempt = (
        await db_session.execute(
            text(
                "SELECT verdict, counts_for_mastery FROM journey_attempts "
                "WHERE student_id = :student_id "
                "AND client_attempt_id = 'forged-unverified-correct'"
            ),
            {"student_id": student_id},
        )
    ).one()
    assert attempt.verdict == "unsure"
    assert attempt.counts_for_mastery is False
    mastery_after = (
        await db_session.execute(
            text(
                "SELECT p_mastery FROM mastery "
                "WHERE student_id = :student_id AND node_id = 'PC06'"
            ),
            {"student_id": student_id},
        )
    ).scalar_one()
    assert mastery_after == pytest.approx(mastery_before)


@pytest.mark.asyncio
async def test_confirmed_incorrect_then_corrected_photo_records_both_outcomes(
    journey_client,
    db_session,
    monkeypatch,
):
    client, token, student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]

    from core.llm_openai import SolutionPhotoResult

    async def incorrect(**_kwargs):
        return SolutionPhotoResult(
            verdict="incorrect",
            failed_step=2,
            confidence=0.96,
            provider="gemini",
            model="gemini-test",
            evidence_verified=True,
        )

    monkeypatch.setattr("api.routers.journey.evaluate_solution_photo", incorrect)
    response = await client.post(
        "/api/journey/photo",
        headers=_headers(token),
        data={
            "revision": str(task["revision"]),
            "problem_id": str(problem_id),
            "client_attempt_id": "incorrect-photo-1",
        },
        files={"photo": ("solution.jpg", _PHOTO.read_bytes(), "image/jpeg")},
    )
    assert response.status_code == 200, response.text
    feedback = response.json()
    assert feedback["next_step"]["type"] == "photo_feedback"
    assert feedback["next_step"]["verdict"] == "incorrect"
    assert feedback["next_step"]["failed_step"] == 2
    assert [item["number"] for item in feedback["next_step"]["confirmed_steps"]] == [1]
    assert feedback["next_step"]["confirmed_steps"][0]["label"]
    assert feedback["next_step"]["correction"]
    assert feedback["next_step"]["help_available"] is True

    evidence = (
        await db_session.execute(
            text(
                "SELECT is_correct, source FROM attempts "
                "WHERE student_id = :student_id"
            ),
            {"student_id": student_id},
        )
    ).one()
    assert evidence.is_correct is False
    assert evidence.source == "journey_independent"
    assert (
        await db_session.execute(
            text(
                "SELECT counts_for_mastery FROM journey_attempts "
                "WHERE student_id = :student_id "
                "AND client_attempt_id = 'incorrect-photo-1'"
            ),
            {"student_id": student_id},
        )
    ).scalar_one() is True

    retry = await _continue(client, token, feedback, "retry_task")
    assert retry["next_step"]["type"] == "independent_task"
    assert retry["next_step"]["problem"]["id"] == problem_id

    mastery_after_incorrect = (
        await db_session.execute(
            text(
                "SELECT p_mastery FROM mastery "
                "WHERE student_id = :student_id AND node_id = 'PC06'"
            ),
            {"student_id": student_id},
        )
    ).scalar_one()

    async def corrected(**_kwargs):
        return SolutionPhotoResult(
            verdict="correct",
            failed_step=None,
            confidence=0.96,
            provider="gemini",
            model="gemini-test",
            evidence_verified=True,
        )

    monkeypatch.setattr("api.routers.journey.evaluate_solution_photo", corrected)
    corrected_response = await client.post(
        "/api/journey/photo",
        headers=_headers(token),
        data={
            "revision": str(retry["revision"]),
            "problem_id": str(problem_id),
            "client_attempt_id": "corrected-same-photo-problem",
        },
        files={"photo": ("corrected.jpg", _PHOTO.read_bytes(), "image/jpeg")},
    )
    assert corrected_response.status_code == 200, corrected_response.text
    assert corrected_response.json()["next_step"]["verdict"] == "correct"
    assert (
        await db_session.execute(
            text(
                "SELECT count(*) FROM attempts "
                "WHERE student_id = :student_id AND source = 'journey_independent'"
            ),
            {"student_id": student_id},
        )
    ).scalar_one() == 2
    mastery_after_correction = (
        await db_session.execute(
            text(
                "SELECT p_mastery FROM mastery "
                "WHERE student_id = :student_id AND node_id = 'PC06'"
            ),
            {"student_id": student_id},
        )
    ).scalar_one()
    assert mastery_after_correction > mastery_after_incorrect
    assert (
        await db_session.execute(
            text(
                "SELECT counts_for_mastery FROM journey_attempts "
                "WHERE student_id = :student_id "
                "AND client_attempt_id = 'corrected-same-photo-problem'"
            ),
            {"student_id": student_id},
        )
    ).scalar_one() is True


@pytest.mark.asyncio
async def test_incorrect_photo_can_open_guided_review(
    journey_client,
    monkeypatch,
):
    client, token, _ = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})

    from core.llm_openai import SolutionPhotoResult

    async def incorrect(**_kwargs):
        return SolutionPhotoResult(
            verdict="incorrect",
            failed_step=2,
            confidence=0.96,
            provider="gemini",
            model="gemini-test",
            evidence_verified=True,
        )

    monkeypatch.setattr("api.routers.journey.evaluate_solution_photo", incorrect)
    response = await client.post(
        "/api/journey/photo",
        headers=_headers(token),
        data={
            "revision": str(task["revision"]),
            "problem_id": str(task["next_step"]["problem"]["id"]),
            "client_attempt_id": "incorrect-photo-guided-review",
        },
        files={"photo": ("solution.jpg", _PHOTO.read_bytes(), "image/jpeg")},
    )
    feedback = response.json()

    guided = await client.post(
        "/api/journey/continue",
        headers=_headers(token),
        json={"revision": feedback["revision"], "action": "review_with_help"},
    )
    assert guided.status_code == 200, guided.text
    assert guided.json()["next_step"]["type"] == "guided_step"
    assert guided.json()["next_step"]["step"]["number"] == 1


@pytest.mark.asyncio
async def test_live_photo_processing_is_pollable_and_durable(
    journey_client,
    monkeypatch,
):
    client, token, _ = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]
    evaluator_started = asyncio.Event()
    release_evaluator = asyncio.Event()

    from core.llm_openai import SolutionPhotoResult

    async def delayed_correct(**_kwargs):
        evaluator_started.set()
        await release_evaluator.wait()
        return SolutionPhotoResult(
            verdict="correct",
            failed_step=None,
            confidence=0.96,
            provider="gemini",
            model="gemini-test",
            evidence_verified=True,
        )

    monkeypatch.setattr("api.routers.journey.evaluate_solution_photo", delayed_correct)
    upload = asyncio.create_task(
        client.post(
            "/api/journey/photo",
            headers=_headers(token),
            data={
                "revision": str(task["revision"]),
                "problem_id": str(problem_id),
                "client_attempt_id": "live-processing-photo",
            },
            files={"photo": ("processing.jpg", _PHOTO.read_bytes(), "image/jpeg")},
        )
    )
    await asyncio.wait_for(evaluator_started.wait(), timeout=2)
    try:
        current = await client.get("/api/journey/current", headers=_headers(token))
        assert current.status_code == 200
        processing = current.json()
        assert processing["next_step"]["type"] == "photo_processing"
        assert processing["next_step"]["preserved_photo"]["name"] == "processing.jpg"
    finally:
        release_evaluator.set()
    completed = await upload
    assert completed.status_code == 200, completed.text
    assert completed.json()["next_step"]["type"] == "photo_feedback"


@pytest.mark.asyncio
async def test_superseded_photo_result_cannot_overwrite_retry(
    journey_client,
    db_session,
    monkeypatch,
    tmp_path,
):
    client, token, student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]

    from core.config import settings as app_settings
    from core.llm_openai import SolutionPhotoResult

    monkeypatch.setattr(app_settings, "photo_dir", str(tmp_path))
    first_started = asyncio.Event()
    release_first = asyncio.Event()
    calls = 0

    async def overlapping_result(**_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            first_started.set()
            await release_first.wait()
            return SolutionPhotoResult(
                verdict="incorrect",
                failed_step=1,
                confidence=0.96,
                provider="gemini",
                model="gemini-old",
                evidence_verified=True,
            )
        return SolutionPhotoResult(
            verdict="correct",
            failed_step=None,
            confidence=0.97,
            provider="gemini",
            model="gemini-retry",
            evidence_verified=True,
        )

    monkeypatch.setattr("api.routers.journey.evaluate_solution_photo", overlapping_result)
    original = asyncio.create_task(
        client.post(
            "/api/journey/photo",
            headers=_headers(token),
            data={
                "revision": str(task["revision"]),
                "problem_id": str(problem_id),
                "client_attempt_id": "photo-overlap-result",
            },
            files={"photo": ("overlap.jpg", _PHOTO.read_bytes(), "image/jpeg")},
        )
    )
    await asyncio.wait_for(first_started.wait(), timeout=2)
    monkeypatch.setattr("api.routers.journey._PHOTO_PROCESSING_TIMEOUT", timedelta(0))
    recovery = await client.get("/api/journey/current", headers=_headers(token))
    assert recovery.status_code == 200
    recovery_state = recovery.json()
    assert recovery_state["next_step"]["reason"] == "provider_error"

    retry = await client.post(
        "/api/journey/photo/retry",
        headers=_headers(token),
        json={"revision": recovery_state["revision"]},
    )
    assert retry.status_code == 200, retry.text
    retry_state = retry.json()
    assert retry_state["next_step"]["verdict"] == "correct"

    release_first.set()
    stale = await original
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "photo_invocation_superseded"
    assert stale.json()["detail"]["state"] == retry_state

    stored = (
        await db_session.execute(
            text(
                "SELECT status, verdict, model, counts_for_mastery "
                "FROM journey_attempts WHERE student_id = :student_id "
                "AND client_attempt_id = 'photo-overlap-result'"
            ),
            {"student_id": student_id},
        )
    ).one()
    assert tuple(stored) == ("accepted", "correct", "gemini-retry", True)


@pytest.mark.asyncio
async def test_superseded_provider_error_cannot_cancel_live_retry(
    journey_client,
    monkeypatch,
    tmp_path,
):
    client, token, _student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]

    from core.config import settings as app_settings
    from core.llm_openai import LlmUnavailable, SolutionPhotoResult

    monkeypatch.setattr(app_settings, "photo_dir", str(tmp_path))
    first_started = asyncio.Event()
    second_started = asyncio.Event()
    release_first = asyncio.Event()
    release_second = asyncio.Event()
    calls = 0

    async def overlapping_error(**_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            first_started.set()
            await release_first.wait()
            raise LlmUnavailable("stale provider failure")
        second_started.set()
        await release_second.wait()
        return SolutionPhotoResult(
            verdict="correct",
            failed_step=None,
            confidence=0.97,
            provider="gemini",
            model="gemini-retry",
            evidence_verified=True,
        )

    monkeypatch.setattr("api.routers.journey.evaluate_solution_photo", overlapping_error)
    original = asyncio.create_task(
        client.post(
            "/api/journey/photo",
            headers=_headers(token),
            data={
                "revision": str(task["revision"]),
                "problem_id": str(problem_id),
                "client_attempt_id": "photo-overlap-error",
            },
            files={"photo": ("overlap.jpg", _PHOTO.read_bytes(), "image/jpeg")},
        )
    )
    await asyncio.wait_for(first_started.wait(), timeout=2)
    monkeypatch.setattr("api.routers.journey._PHOTO_PROCESSING_TIMEOUT", timedelta(0))
    recovery_state = (
        await client.get("/api/journey/current", headers=_headers(token))
    ).json()
    retry = asyncio.create_task(
        client.post(
            "/api/journey/photo/retry",
            headers=_headers(token),
            json={"revision": recovery_state["revision"]},
        )
    )
    await asyncio.wait_for(second_started.wait(), timeout=2)
    monkeypatch.setattr(
        "api.routers.journey._PHOTO_PROCESSING_TIMEOUT",
        timedelta(minutes=2),
    )

    release_first.set()
    stale = await original
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "photo_invocation_superseded"
    processing = await client.get("/api/journey/current", headers=_headers(token))
    assert processing.status_code == 200
    assert processing.json()["next_step"]["type"] == "photo_processing"

    release_second.set()
    completed = await retry
    assert completed.status_code == 200, completed.text
    assert completed.json()["next_step"]["verdict"] == "correct"


@pytest.mark.asyncio
async def test_provider_error_retries_saved_photo_after_reload(
    journey_client,
    db_session,
    monkeypatch,
    tmp_path,
):
    client, token, student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]

    from core.config import settings as app_settings
    from core.llm_openai import LlmUnavailable, SolutionPhotoResult

    monkeypatch.setattr(app_settings, "photo_dir", str(tmp_path))

    async def unavailable(**_kwargs):
        raise LlmUnavailable("temporary provider failure")

    monkeypatch.setattr("api.routers.journey.evaluate_solution_photo", unavailable)
    first = await client.post(
        "/api/journey/photo",
        headers=_headers(token),
        data={
            "revision": str(task["revision"]),
            "problem_id": str(problem_id),
            "client_attempt_id": "provider-photo-1",
        },
        files={"photo": ("saved-solution.jpg", _PHOTO.read_bytes(), "image/jpeg")},
    )
    assert first.status_code == 503, first.text
    recovery = first.json()["detail"]["state"]
    assert recovery["next_step"]["type"] == "photo_recovery"
    assert recovery["next_step"]["reason"] == "provider_error"

    resumed = await client.get("/api/journey/current", headers=_headers(token))
    assert resumed.status_code == 200
    assert resumed.json() == recovery

    bypass = await client.post(
        "/api/journey/continue",
        headers=_headers(token),
        json={"revision": recovery["revision"], "action": "retry_photo"},
    )
    assert bypass.status_code == 409
    still_recovering = await client.get("/api/journey/current", headers=_headers(token))
    assert still_recovering.json()["next_step"]["reason"] == "provider_error"

    seen_bytes: list[bytes] = []

    async def correct(**kwargs):
        seen_bytes.append(kwargs["image_bytes"])
        return SolutionPhotoResult(
            verdict="correct",
            failed_step=None,
            confidence=0.94,
            provider="gemini",
            model="gemini-test",
            evidence_verified=True,
        )

    monkeypatch.setattr("api.routers.journey.evaluate_solution_photo", correct)
    retry = await client.post(
        "/api/journey/photo/retry",
        headers=_headers(token),
        json={"revision": recovery["revision"]},
    )
    assert retry.status_code == 200, retry.text
    feedback = retry.json()
    assert feedback["next_step"]["type"] == "photo_feedback"
    assert feedback["next_step"]["verdict"] == "correct"
    assert seen_bytes == [_PHOTO.read_bytes()]

    attempt = (
        await db_session.execute(
            text(
                "SELECT status, verdict, counts_for_mastery, photo_ref "
                "FROM journey_attempts WHERE student_id = :student_id "
                "AND client_attempt_id = 'provider-photo-1'"
            ),
            {"student_id": student_id},
        )
    ).one()
    assert attempt.status == "accepted"
    assert attempt.verdict == "correct"
    assert attempt.counts_for_mastery is True
    assert (tmp_path / attempt.photo_ref).is_file()


@pytest.mark.asyncio
async def test_retry_rejects_replaced_saved_photo_without_mastery(
    journey_client,
    db_session,
    monkeypatch,
    tmp_path,
):
    client, token, student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]

    from PIL import Image
    from core.config import settings as app_settings
    from core.llm_openai import LlmUnavailable

    monkeypatch.setattr(app_settings, "photo_dir", str(tmp_path))

    async def unavailable(**_kwargs):
        raise LlmUnavailable("temporary provider failure")

    monkeypatch.setattr("api.routers.journey.evaluate_solution_photo", unavailable)
    first = await client.post(
        "/api/journey/photo",
        headers=_headers(token),
        data={
            "revision": str(task["revision"]),
            "problem_id": str(problem_id),
            "client_attempt_id": "provider-photo-replaced",
        },
        files={"photo": ("saved-solution.jpg", _PHOTO.read_bytes(), "image/jpeg")},
    )
    assert first.status_code == 503, first.text
    recovery = first.json()["detail"]["state"]

    photo_ref = (
        await db_session.execute(
            text(
                "SELECT photo_ref FROM journey_attempts "
                "WHERE student_id = :student_id "
                "AND client_attempt_id = 'provider-photo-replaced'"
            ),
            {"student_id": student_id},
        )
    ).scalar_one()
    replacement = io.BytesIO()
    Image.new("RGB", (32, 32), "black").save(replacement, format="JPEG")
    (tmp_path / photo_ref).write_bytes(replacement.getvalue())

    async def must_not_regrade(**_kwargs):
        raise AssertionError("подменённое фото не должно уходить провайдеру")

    monkeypatch.setattr("api.routers.journey.evaluate_solution_photo", must_not_regrade)
    retry = await client.post(
        "/api/journey/photo/retry",
        headers=_headers(token),
        json={"revision": recovery["revision"]},
    )
    assert retry.status_code == 200, retry.text
    state = retry.json()
    assert state["next_step"]["type"] == "independent_task"
    assert state["next_step"]["problem"]["id"] == problem_id

    stored = (
        await db_session.execute(
            text(
                "SELECT status, verdict, counts_for_mastery FROM journey_attempts "
                "WHERE student_id = :student_id "
                "AND client_attempt_id = 'provider-photo-replaced'"
            ),
            {"student_id": student_id},
        )
    ).one()
    assert tuple(stored) == ("photo_missing", "provider_error", False)
    assert (
        await db_session.execute(
            text(
                "SELECT count(*) FROM attempts WHERE student_id = :student_id "
                "AND problem_id = :problem_id"
            ),
            {"student_id": student_id, "problem_id": problem_id},
        )
    ).scalar_one() == 0


@pytest.mark.asyncio
async def test_stale_processing_recovers_to_saved_photo_retry(
    journey_client,
    db_session,
):
    client, token, student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]
    journey_id = task["journey_id"]

    await db_session.execute(
        text(
            "INSERT INTO journey_attempts "
            "(journey_id, student_id, client_attempt_id, kind, stage, topic_id, "
            "problem_id, payload_hash, photo_ref, original_filename, status, "
            "counts_for_mastery, created_at, updated_at) "
            "VALUES (:journey_id, :student_id, 'stale-photo-1', 'independent_photo', "
            "'independent_task', 'PC06', :problem_id, :payload_hash, "
            "'journey/stale.jpg', 'stale-solution.jpg', 'processing', false, "
            "NOW() - INTERVAL '10 minutes', NOW() - INTERVAL '10 minutes')"
        ),
        {
            "journey_id": journey_id,
            "student_id": student_id,
            "problem_id": problem_id,
            "payload_hash": "0" * 64,
        },
    )
    await db_session.execute(
        text(
            "UPDATE student_journeys SET "
            "activity = jsonb_build_object('processing_client_attempt_id', 'stale-photo-1') "
            "WHERE id = :journey_id"
        ),
        {"journey_id": journey_id},
    )
    await db_session.commit()

    resumed = await client.get("/api/journey/current", headers=_headers(token))
    assert resumed.status_code == 200, resumed.text
    recovery = resumed.json()
    assert recovery["next_step"]["type"] == "photo_recovery"
    assert recovery["next_step"]["reason"] == "provider_error"
    assert recovery["next_step"]["preserved_photo"]["name"] == "stale-solution.jpg"

    stored = (
        await db_session.execute(
            text(
                "SELECT status FROM journey_attempts WHERE student_id = :student_id "
                "AND client_attempt_id = 'stale-photo-1'"
            ),
            {"student_id": student_id},
        )
    ).scalar_one()
    assert stored == "provider_error"


@pytest.mark.asyncio
async def test_stale_guided_processing_recovers_on_current_and_can_retry(
    journey_client,
    db_session,
):
    client, token, student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]
    guided = (
        await client.post(
            "/api/journey/help",
            headers=_headers(token),
            json={"revision": task["revision"], "problem_id": problem_id},
        )
    ).json()
    step_n = guided["next_step"]["step"]["number"]
    answer = (
        await db_session.execute(
            text(
                "SELECT expected_value FROM problem_steps "
                "WHERE decomp_idx = :idx AND n = :step_n"
            ),
            {
                "idx": guided["next_step"]["problem"]["content_idx"],
                "step_n": step_n,
            },
        )
    ).scalar_one()
    from api.routers.journey import _hash_parts

    await db_session.execute(
        text(
            "INSERT INTO journey_attempts "
            "(journey_id, student_id, client_attempt_id, kind, stage, topic_id, "
            "problem_id, step_n, payload_hash, answer_given, status, counts_for_mastery, "
            "created_at, updated_at) "
            "VALUES (:journey_id, :student_id, 'stale-guided-1', 'guided', "
            "'guided_step', 'PC06', :problem_id, :step_n, :payload_hash, :answer, "
            "'processing', false, NOW() - INTERVAL '10 minutes', "
            "NOW() - INTERVAL '10 minutes')"
        ),
        {
            "journey_id": guided["journey_id"],
            "student_id": student_id,
            "problem_id": problem_id,
            "step_n": step_n,
            "payload_hash": _hash_parts(str(problem_id), str(step_n), answer),
            "answer": answer,
        },
    )
    await db_session.execute(
        text(
            "UPDATE student_journeys SET activity = activity || "
            "jsonb_build_object(" 
            "'guided_processing_client_attempt_id', 'stale-guided-1', "
            "'guided_processing_lease_id', 'abandoned-lease') "
            "WHERE id = :journey_id"
        ),
        {"journey_id": guided["journey_id"]},
    )
    await db_session.commit()

    resumed = await client.get("/api/journey/current", headers=_headers(token))
    assert resumed.status_code == 200, resumed.text
    recovery = resumed.json()
    assert recovery["next_step"]["type"] == "guided_step"
    assert recovery["next_step"]["feedback"] == {
        "verdict": "unsure",
        "message": "AI временно не ответил. Твоя запись сохранена — попробуй ещё раз.",
        "answer": answer,
        "reason": "provider_error",
    }

    stored = (
        await db_session.execute(
            text(
                "SELECT status, response_payload IS NOT NULL FROM journey_attempts "
                "WHERE student_id = :student_id AND client_attempt_id = 'stale-guided-1'"
            ),
            {"student_id": student_id},
        )
    ).one()
    assert tuple(stored) == ("provider_error", True)

    retry = await client.post(
        "/api/journey/guided/answer",
        headers=_headers(token),
        json={
            "revision": recovery["revision"],
            "problem_id": problem_id,
            "step_n": step_n,
            "answer": answer,
            "client_attempt_id": "stale-guided-1",
        },
    )
    assert retry.status_code == 200, retry.text
    assert (
        await db_session.execute(
            text(
                "SELECT status FROM journey_attempts "
                "WHERE student_id = :student_id AND client_attempt_id = 'stale-guided-1'"
            ),
            {"student_id": student_id},
        )
    ).scalar_one() == "accepted"


@pytest.mark.asyncio
async def test_diagnostic_replay_never_rolls_back_a_newer_question(journey_client):
    client, token, _student_id = journey_client
    state = await _open_diagnostic(client, token)
    bank = load_problem_bank()
    question_id = int(state["next_step"]["question"]["id"])
    request = {
        "revision": state["revision"],
        "question_id": question_id,
        "answer": str(bank[question_id]["answer"]),
        "client_attempt_id": "diagnostic-replay-first",
    }

    first = await client.post(
        "/api/journey/diagnostic/answer",
        headers=_headers(token),
        json=request,
    )
    assert first.status_code == 200, first.text
    first_state = first.json()

    immediate = await client.post(
        "/api/journey/diagnostic/answer",
        headers=_headers(token),
        json=request,
    )
    assert immediate.status_code == 200
    assert immediate.json() == first_state

    next_question_id = int(first_state["next_step"]["question"]["id"])
    advanced = await client.post(
        "/api/journey/diagnostic/answer",
        headers=_headers(token),
        json={
            "revision": first_state["revision"],
            "question_id": next_question_id,
            "answer": str(bank[next_question_id]["answer"]),
            "client_attempt_id": "diagnostic-replay-second",
        },
    )
    assert advanced.status_code == 200, advanced.text

    stale = await client.post(
        "/api/journey/diagnostic/answer",
        headers=_headers(token),
        json=request,
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "stale_revision"
    assert stale.json()["detail"]["state"] == advanced.json()


@pytest.mark.asyncio
async def test_guided_replay_never_rolls_back_a_newer_step(journey_client):
    client, token, _student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    problem_id = task["next_step"]["problem"]["id"]
    guided = (
        await client.post(
            "/api/journey/help",
            headers=_headers(token),
            json={"revision": task["revision"], "problem_id": problem_id},
        )
    ).json()
    first_request = {
        "revision": guided["revision"],
        "problem_id": problem_id,
        "step_n": 1,
        "answer": "75",
        "client_attempt_id": "guided-replay-first",
    }
    first = await client.post(
        "/api/journey/guided/answer",
        headers=_headers(token),
        json=first_request,
    )
    assert first.status_code == 200, first.text
    first_state = first.json()

    immediate = await client.post(
        "/api/journey/guided/answer",
        headers=_headers(token),
        json=first_request,
    )
    assert immediate.status_code == 200
    assert immediate.json() == first_state

    advanced = await client.post(
        "/api/journey/guided/answer",
        headers=_headers(token),
        json={
            "revision": first_state["revision"],
            "problem_id": problem_id,
            "step_n": 2,
            "answer": "500",
            "client_attempt_id": "guided-replay-second",
        },
    )
    assert advanced.status_code == 200, advanced.text

    stale = await client.post(
        "/api/journey/guided/answer",
        headers=_headers(token),
        json=first_request,
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "stale_revision"
    assert stale.json()["detail"]["state"] == advanced.json()


@pytest.mark.asyncio
async def test_guided_transfer_photo_is_the_only_mastery_evidence_and_is_idempotent(
    journey_client,
    db_session,
    monkeypatch,
):
    client, token, student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    original_problem_id = task["next_step"]["problem"]["id"]
    guided_response = await client.post(
        "/api/journey/help",
        headers=_headers(token),
        json={"revision": task["revision"], "problem_id": original_problem_id},
    )
    guided = guided_response.json()
    for index, answer in enumerate(("75", "500", "15"), start=1):
        guided = (
            await client.post(
                "/api/journey/guided/answer",
                headers=_headers(token),
                json={
                    "revision": guided["revision"],
                    "problem_id": original_problem_id,
                    "step_n": index,
                    "answer": answer,
                    "client_attempt_id": f"transfer-guided-{index}",
                },
            )
        ).json()
    transfer_problem_id = guided["next_step"]["problem"]["id"]
    mastery_before = (
        await db_session.execute(
            text(
                "SELECT p_mastery FROM mastery "
                "WHERE student_id = :student_id AND node_id = 'PC06'"
            ),
            {"student_id": student_id},
        )
    ).scalar_one()

    from core.llm_openai import SolutionPhotoResult

    async def correct(**_kwargs):
        return SolutionPhotoResult(
            verdict="correct",
            failed_step=None,
            confidence=0.94,
            provider="gemini",
            model="gemini-test",
            evidence_verified=True,
        )

    monkeypatch.setattr("api.routers.journey.evaluate_solution_photo", correct)
    request = {
        "revision": str(guided["revision"]),
        "problem_id": str(transfer_problem_id),
        "client_attempt_id": "transfer-photo-correct",
    }
    first = await client.post(
        "/api/journey/photo",
        headers=_headers(token),
        data=request,
        files={"photo": ("transfer.jpg", _PHOTO.read_bytes(), "image/jpeg")},
    )
    assert first.status_code == 200, first.text
    feedback = first.json()
    assert feedback["next_step"]["type"] == "transfer_feedback"
    assert feedback["next_step"]["verdict"] == "correct"
    assert feedback["next_step"]["mastery"]["value"] > mastery_before

    duplicate = await client.post(
        "/api/journey/photo",
        headers=_headers(token),
        data=request,
        files={"photo": ("transfer.jpg", _PHOTO.read_bytes(), "image/jpeg")},
    )
    assert duplicate.status_code == 200
    assert duplicate.json() == feedback

    assert (
        await db_session.execute(
            text(
                "SELECT count(*) FROM attempts "
                "WHERE student_id = :student_id AND source = 'journey_transfer'"
            ),
            {"student_id": student_id},
        )
    ).scalar_one() == 1
    mastery = (
        await db_session.execute(
            text(
                "SELECT p_mastery FROM mastery "
                "WHERE student_id = :student_id AND node_id = 'PC06'"
            ),
            {"student_id": student_id},
        )
    ).scalar_one()
    assert mastery == pytest.approx(feedback["next_step"]["mastery"]["value"], abs=0.001)
    assert (
        await db_session.execute(
            text(
                "SELECT count(*) FROM journey_attempts "
                "WHERE student_id = :student_id "
                "AND client_attempt_id = 'transfer-photo-correct'"
            ),
            {"student_id": student_id},
        )
    ).scalar_one() == 1

    advanced = await _continue(client, token, feedback, "continue_transfer")
    stale = await client.post(
        "/api/journey/photo",
        headers=_headers(token),
        data=request,
        files={"photo": ("transfer.jpg", _PHOTO.read_bytes(), "image/jpeg")},
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "stale_revision"
    assert stale.json()["detail"]["state"] == advanced


@pytest.mark.asyncio
async def test_topic_cannot_finish_below_mastery_and_gets_a_new_transfer_problem(
    journey_client,
    db_session,
    monkeypatch,
):
    client, token, student_id = journey_client
    _, task = await _open_first_task(client, token, wrong_answers={321: "1200"})
    original_problem_id = task["next_step"]["problem"]["id"]
    guided = (
        await client.post(
            "/api/journey/help",
            headers=_headers(token),
            json={"revision": task["revision"], "problem_id": original_problem_id},
        )
    ).json()
    for index, answer in enumerate(("75", "500", "15"), start=1):
        guided = (
            await client.post(
                "/api/journey/guided/answer",
                headers=_headers(token),
                json={
                    "revision": guided["revision"],
                    "problem_id": original_problem_id,
                    "step_n": index,
                    "answer": answer,
                    "client_attempt_id": f"low-mastery-guided-{index}",
                },
            )
        ).json()
    first_transfer_id = guided["next_step"]["problem"]["id"]
    await db_session.execute(
        text(
            "UPDATE mastery SET p_mastery = 0.001 "
            "WHERE student_id = :student_id AND node_id = 'PC06'"
        ),
        {"student_id": student_id},
    )
    await db_session.commit()

    from core.llm_openai import SolutionPhotoResult

    async def correct(**_kwargs):
        return SolutionPhotoResult(
            verdict="correct",
            failed_step=None,
            confidence=0.95,
            provider="gemini",
            model="gemini-test",
            evidence_verified=True,
        )

    monkeypatch.setattr("api.routers.journey.evaluate_solution_photo", correct)
    response = await client.post(
        "/api/journey/photo",
        headers=_headers(token),
        data={
            "revision": str(guided["revision"]),
            "problem_id": str(first_transfer_id),
            "client_attempt_id": "low-mastery-transfer-1",
        },
        files={"photo": ("transfer.jpg", _PHOTO.read_bytes(), "image/jpeg")},
    )
    assert response.status_code == 200, response.text
    feedback = response.json()
    assert feedback["next_step"]["type"] == "transfer_feedback"
    assert feedback["next_step"]["mastery"]["reached"] is False
    evidence = feedback["next_step"]["mastery"]["evidence"]
    assert evidence == {
        "correct": 1,
        "required_correct": 3,
        "remaining_correct": 2,
        "total": 1,
        "accuracy": 1.0,
        "minimum_accuracy": 0.5,
        "probability_reached": False,
        "correct_reached": False,
        "accuracy_reached": True,
    }
    assert feedback["next_step"]["primary_action"] == "Решить ещё одну задачу"

    blocked = await client.post(
        "/api/journey/continue",
        headers=_headers(token),
        json={"revision": feedback["revision"], "action": "finish_topic"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "mastery_not_reached"

    forged_retry = await client.post(
        "/api/journey/continue",
        headers=_headers(token),
        json={"revision": feedback["revision"], "action": "retry_task"},
    )
    assert forged_retry.status_code == 409

    next_transfer = await _continue(client, token, feedback, "continue_transfer")
    assert next_transfer["next_step"]["type"] == "transfer_task"
    assert next_transfer["next_step"]["problem"]["id"] != first_transfer_id
