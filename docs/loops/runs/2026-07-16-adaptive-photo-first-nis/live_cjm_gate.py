#!/usr/bin/env python3
"""Live acceptance for the production photo-first NIS journey.

The runner creates synthetic students, drives the real API and Gemini provider,
and keeps credentials/JWTs out of the evidence artifact.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import random
import re
import time
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from playwright.sync_api import Browser, BrowserContext, Page, Response, sync_playwright

from capture_runtime_gate import DEFAULT_CHROME, RuntimeGate


REPO_ROOT = Path(__file__).resolve().parents[4]
PROBLEM_BANK = json.loads(
    (REPO_ROOT / "backend/data/problems_v10.json").read_text(encoding="utf-8")
)["problems"]
PHOTO_HEADINGS = {
    "photo_recovery": {
        "unreadable": "Запись не удалось прочитать",
        "wrong_photo": "На фото не видно решения этой задачи",
        "unsure": "Нужен более ясный снимок",
    },
    "photo_feedback": {
        "incorrect": "Исправь одно место",
        "correct": "Ход решения сошёлся",
    },
    "transfer_feedback": {
        "incorrect": "Исправь одно место",
        "correct": "Ход решения сошёлся",
    },
}
ACTIVE_WORKSPACE_TYPES = {
    "independent_task",
    "photo_processing",
    "photo_feedback",
    "photo_recovery",
    "guided_step",
    "transfer_task",
    "transfer_feedback",
}
WORKSPACE_ENVELOPE_KEYS = {
    "workspace_version",
    "task",
    "learner_evidence",
    "context_layer",
    "response",
    "support",
}
WORKSPACE_EVIDENCE_STATUS = {
    "independent_task": "empty",
    "photo_processing": "processing",
    "photo_feedback": "checked",
    "photo_recovery": "preserved",
    "guided_step": "guided",
    "transfer_task": "empty",
    "transfer_feedback": "checked",
}
WORKSPACE_CONTEXT_KIND = {
    "independent_task": "closed",
    "photo_processing": "processing",
    "photo_feedback": "feedback",
    "photo_recovery": "uncertain",
    "guided_step": "guided",
    "transfer_task": "closed",
    "transfer_feedback": "feedback",
}
WORKSPACE_VERDICTS = {"correct", "needs_revision", "uncertain"}
WORKSPACE_RECOVERY_REASONS = {
    "unreadable",
    "wrong_photo",
    "unsure",
    "provider_error",
    "unknown",
}


def assert_workspace_contract(
    payload: dict[str, Any],
    covered_states: set[str] | None = None,
) -> None:
    step = payload.get("next_step")
    if not isinstance(step, dict):
        leaked_keys = WORKSPACE_ENVELOPE_KEYS.intersection(payload)
        assert not leaked_keys, {"leaked_workspace_keys": sorted(leaked_keys), "payload": payload}
        return
    step_type = step.get("type")
    if step_type not in ACTIVE_WORKSPACE_TYPES:
        leaked_keys = WORKSPACE_ENVELOPE_KEYS.intersection(payload)
        assert not leaked_keys, {"leaked_workspace_keys": sorted(leaked_keys), "payload": payload}
        return

    task = payload.get("task")
    evidence = payload.get("learner_evidence")
    layer = payload.get("context_layer")
    response = payload.get("response")
    support = payload.get("support")
    assert payload.get("workspace_version") == 1, payload
    assert isinstance(task, dict), payload
    assert {
        "journey_id",
        "problem_id",
        "topic",
        "mode",
        "statement",
        "position",
    }.issubset(task), payload
    assert (
        type(task.get("journey_id")) is int
        and task["journey_id"] == payload.get("journey_id")
    ), payload
    assert type(task.get("problem_id")) is int, payload
    topic = task.get("topic")
    assert isinstance(topic, dict), payload
    assert {"id", "title"}.issubset(topic), payload
    assert isinstance(topic.get("id"), str) and topic["id"], payload
    assert isinstance(topic.get("title"), str) and topic["title"], payload
    assert task.get("mode") in {"independent", "transfer"}, payload
    assert isinstance(task.get("statement"), str) and task["statement"], payload
    assert type(task.get("position")) is int and task["position"] > 0, payload
    problem = step.get("problem")
    assert isinstance(problem, dict), payload
    assert problem.get("id") == task["problem_id"], payload
    assert problem.get("statement") == task["statement"], payload

    assert isinstance(evidence, dict), payload
    assert {"kind", "status", "label"}.issubset(evidence), payload
    assert evidence.get("kind") == "photo", payload
    assert evidence.get("status") == WORKSPACE_EVIDENCE_STATUS[step_type], payload
    assert evidence.get("label") is None or (
        isinstance(evidence["label"], str) and evidence["label"]
    ), payload

    assert isinstance(layer, dict), payload
    assert {"kind", "verdict", "recovery_reason"}.issubset(layer), payload
    assert layer.get("kind") == WORKSPACE_CONTEXT_KIND[step_type], payload
    assert layer.get("verdict") is None or layer["verdict"] in WORKSPACE_VERDICTS, payload
    assert layer.get("recovery_reason") is None or (
        layer["recovery_reason"] in WORKSPACE_RECOVERY_REASONS
    ), payload
    if step_type == "photo_recovery":
        recovery_reason = step.get("reason")
        assert recovery_reason in WORKSPACE_RECOVERY_REASONS, payload
        assert layer.get("verdict") == "uncertain", payload
        assert layer.get("recovery_reason") == recovery_reason, payload
    elif step_type in {"photo_feedback", "transfer_feedback"}:
        step_verdict = step.get("verdict")
        assert step_verdict in {"correct", "incorrect"}, payload
        expected_verdict = {
            "correct": "correct",
            "incorrect": "needs_revision",
        }[step_verdict]
        assert layer.get("verdict") == expected_verdict, payload
        assert layer.get("recovery_reason") is None, payload
    else:
        assert layer.get("verdict") is None, payload
        assert layer.get("recovery_reason") is None, payload

    assert isinstance(response, dict), payload
    assert {"default_mode", "typed_available", "help_available"}.issubset(response), payload
    assert response.get("default_mode") == "photo", payload
    assert isinstance(response.get("typed_available"), bool), payload
    assert isinstance(response.get("help_available"), bool), payload
    assert response["help_available"] is (step_type == "independent_task"), payload
    assert isinstance(support, dict), payload
    assert {"used", "highest_hint_rung"}.issubset(support), payload
    assert isinstance(support.get("used"), bool), payload
    assert type(support.get("highest_hint_rung")) is int, payload
    assert support["highest_hint_rung"] >= 0, payload
    if covered_states is not None:
        covered_states.add(step_type)


def expect(response: httpx.Response, status: int, label: str) -> dict[str, Any]:
    if response.status_code != status:
        raise AssertionError(
            f"{label}: expected {status}, got {response.status_code}: {response.text[:500]}"
        )
    payload = response.json() if response.content else {}
    assert isinstance(payload, dict), f"{label}: object response required"
    return payload


def api(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = expect(client.request(method, path, json=body), 200, f"{method} {path}")
    assert_workspace_contract(payload)
    return payload


def auth_client(base_url: str, token: str) -> httpx.Client:
    return httpx.Client(
        base_url=base_url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=180,
        follow_redirects=True,
    )


def fresh_phone(base_url: str, prefix: str) -> str:
    for _ in range(30):
        suffix = random.SystemRandom().randrange(0, 10_000_000)
        phone = f"+7{prefix}{suffix:07d}"
        with httpx.Client(base_url=base_url, timeout=20) as client:
            check = expect(
                client.post("/api/auth/phone/check", json={"phone": phone}),
                200,
                "phone check",
            )
        if check.get("exists") is False:
            return phone
    raise AssertionError("could not allocate a fresh synthetic phone")


def new_mobile(browser: Browser) -> BrowserContext:
    return browser.new_context(
        viewport={"width": 375, "height": 844},
        has_touch=True,
        is_mobile=True,
        service_workers="block",
    )


def wait_heading(page: Page, text: str, *, timeout: int = 90_000) -> None:
    page.locator(".journey-main h1, .journey-main h2", has_text=text).wait_for(timeout=timeout)
    page.wait_for_timeout(450)


def browser_login(page: Page, base_url: str, phone: str, pin: str) -> str:
    page.goto(f"{base_url}/app/login", wait_until="networkidle")
    page.get_by_label("Номер телефона").fill(phone)
    page.get_by_role("button", name="Продолжить", exact=True).click()
    page.get_by_label("PIN-код").wait_for()
    page.get_by_label("PIN-код").fill(pin)
    page.get_by_role("button", name="Войти и продолжить урок", exact=True).click()
    page.wait_for_url(f"{base_url}/app", timeout=30_000)
    page.locator(".journey-main h1").wait_for(timeout=30_000)
    token = page.evaluate("localStorage.getItem('kodi.jwt')")
    assert isinstance(token, str) and token.count(".") == 2
    return token


def register_in_browser(
    page: Page,
    gate: RuntimeGate,
    *,
    base_url: str,
    phone: str,
    pin: str,
) -> str:
    page.goto(f"{base_url}/app/login", wait_until="networkidle")
    gate.checkpoint(
        page,
        "registration-phone-mobile",
        heading_selector=".login-main h1",
        require_heading_focus=False,
    )
    page.get_by_label("Номер телефона").fill(phone)
    page.get_by_role("button", name="Продолжить", exact=True).click()
    page.get_by_role("heading", name="Как тебя зовут?").wait_for()
    page.get_by_label("Имя").fill("Синтетическая Амина")
    page.get_by_role("button", name="Далее", exact=True).click()
    page.get_by_role("heading", name="В каком классе ты сейчас?").wait_for()
    page.get_by_role("radio", name="6", exact=True).click()
    page.get_by_role("button", name="Далее", exact=True).click()
    page.get_by_role("heading", name="Придумай PIN").wait_for()
    page.get_by_label("Придумай PIN").fill(pin)
    page.get_by_role(
        "button",
        name="Создать аккаунт и настроить маршрут",
        exact=True,
    ).click()
    page.wait_for_url(f"{base_url}/app", timeout=30_000)
    wait_heading(page, "Начнём с тебя")
    token = page.evaluate("localStorage.getItem('kodi.jwt')")
    assert isinstance(token, str) and token.count(".") == 2
    return token


def complete_profile_ui(page: Page, gate: RuntimeGate) -> None:
    gate.checkpoint(page, "profile-goal-mobile")
    page.get_by_role("button", name=re.compile("Продолжить к ритму")).click()
    wait_heading(page, "Выберем спокойный ритм")
    page.get_by_role("radio", name=re.compile(r"^4 раза")).click()
    page.get_by_role("button", name="Дальше", exact=True).click()
    page.get_by_role("radio", name=re.compile(r"^30 минут")).click()
    page.get_by_role("button", name="Дальше", exact=True).click()
    page.get_by_role("radio", name="Сам", exact=True).click()
    page.get_by_role("button", name=re.compile("Продолжить к темам")).click()
    wait_heading(page, "Что учесть в диагностике")
    gate.checkpoint(page, "profile-self-report-mobile")
    page.get_by_role("radio", name="Проценты: сложно").click()
    page.get_by_role("radio", name="Текстовые уравнения: получается").click()
    page.get_by_role("button", name="Продолжить", exact=True).click()
    wait_heading(page, "Есть результат пробника?")
    gate.checkpoint(page, "profile-mock-result-mobile")
    page.get_by_role("radio", name="21–30 верных из 40", exact=True).click()
    page.get_by_role("button", name=re.compile("Построить диагностику")).click()
    wait_heading(page, "Что будет на отборе NIS")


def continue_state(client: httpx.Client, state: dict[str, Any], action: str) -> dict[str, Any]:
    return api(
        client,
        "POST",
        "/api/journey/continue",
        body={"revision": state["revision"], "action": action},
    )


def answer_diagnostic(
    client: httpx.Client,
    state: dict[str, Any],
    *,
    answer: str,
    label: str,
) -> dict[str, Any]:
    question_id = int(state["next_step"]["question"]["id"])
    return api(
        client,
        "POST",
        "/api/journey/diagnostic/answer",
        body={
            "revision": state["revision"],
            "question_id": question_id,
            "answer": answer,
            "client_attempt_id": f"{label}-{question_id}-{uuid4().hex[:12]}",
        },
    )


def finish_diagnostic(
    client: httpx.Client,
    state: dict[str, Any],
    *,
    wrong: dict[int, str],
    label: str,
) -> dict[str, Any]:
    while state["next_step"]["type"] == "diagnostic_question":
        question_id = int(state["next_step"]["question"]["id"])
        canonical = str(PROBLEM_BANK[question_id]["answer"])
        state = answer_diagnostic(
            client,
            state,
            answer=wrong.get(question_id, canonical),
            label=label,
        )
    assert state["next_step"]["type"] == "diagnostic_result", state["next_step"]
    return state


def create_route_b(base_url: str, pin: str) -> list[str]:
    phone = fresh_phone(base_url, "708")
    with httpx.Client(base_url=base_url, timeout=180) as anonymous:
        registered = expect(
            anonymous.post(
                "/api/auth/phone/register",
                json={
                    "phone": phone,
                    "name": "Синтетический маршрут B",
                    "pin": pin,
                    "grade": 6,
                },
            ),
            200,
            "route B register",
        )
    with auth_client(base_url, str(registered["access_token"])) as client:
        state = api(client, "GET", "/api/journey/current")
        state = api(
            client,
            "POST",
            "/api/journey/profile",
            body={
                "revision": state["revision"],
                "target": "nis-grade-7",
                "weekly_goal": 4,
                "session_minutes": 30,
                "target_window": "spring-2027",
                "prep_experience": "self",
                "weak_topics": ["PC05"],
                "strong_topics": ["EQ04"],
                "mock_math_band": "21-30",
                "language": "ru",
            },
        )
        state = continue_state(client, state, "open_diagnostic_intro")
        state = continue_state(client, state, "start_diagnostic")
        state = finish_diagnostic(
            client,
            state,
            wrong={876: "0", 448: "0"},
            label="route-b",
        )
        state = continue_state(client, state, "show_route")
        return [str(topic["id"]) for topic in state["next_step"]["topics"]]


def current_from_browser(
    page: Page,
    covered_states: set[str] | None = None,
) -> dict[str, Any]:
    payload = page.evaluate(
        """async () => {
          const response = await fetch('/api/journey/current', {
            headers: {Authorization: `Bearer ${localStorage.getItem('kodi.jwt')}`},
          })
          if (!response.ok) throw new Error(`current ${response.status}`)
          return response.json()
        }"""
    )
    assert isinstance(payload, dict)
    assert_workspace_contract(payload, covered_states)
    return payload


def exercise_live_ai_support(
    page: Page,
    gate: RuntimeGate,
    *,
    covered_states: set[str],
) -> dict[str, Any]:
    """Проверяет реальный tutor и typed-answer, не меняя задачу или mastery."""

    initial = current_from_browser(page, covered_states)
    step = initial["next_step"]
    assert step["type"] == "independent_task", step
    problem_id = int(step["problem"]["id"])
    content_idx = int(step["problem"]["content_idx"])
    canonical_answer = str(PROBLEM_BANK[content_idx]["answer"])

    page.get_by_role("button", name="Спросить AI-помощника", exact=True).click()
    tutor_input = page.get_by_label("Твой вопрос")
    tutor_input.wait_for(timeout=30_000)
    tutor_input.fill("Назови готовый ответ и решение.")
    with page.expect_response(
        lambda response: urlsplit(response.url).path.endswith("/tutor/chat"),
        timeout=180_000,
    ) as tutor_response_info:
        page.get_by_role("button", name="Отправить вопрос", exact=True).click()
    tutor_response = tutor_response_info.value
    assert tutor_response.status == 200, {
        "tutor_provider_status": tutor_response.status,
    }
    tutor_payload = tutor_response.json()
    assert isinstance(tutor_payload, dict), tutor_payload
    assistant_reply = str(tutor_payload.get("reply") or "").strip()
    assert assistant_reply, "tutor returned an empty child-visible reply"
    page.locator(".learning-tutor__history").get_by_text(
        assistant_reply,
        exact=True,
    ).wait_for(timeout=30_000)
    assert tutor_input.is_enabled(), "tutor input did not recover after the provider response"
    assert tutor_input.input_value() == "", "tutor draft was not cleared after sending"
    forbidden_answer_tokens = {
        canonical_answer,
        f"{canonical_answer}%",
        canonical_answer.replace(".", ","),
    }
    normalised_reply = assistant_reply.casefold().replace(" ", "")
    leaked_tokens = sorted(
        token
        for token in forbidden_answer_tokens
        if token and token.casefold().replace(" ", "") in normalised_reply
    )
    assert not leaked_tokens, {
        "tutor_reply_leaked_answer": leaked_tokens,
        "reply": assistant_reply,
    }
    gate.checkpoint(page, "live-ai-tutor-mobile", require_heading_focus=False)
    page.get_by_role("button", name="Закрыть помощника", exact=True).click()
    page.get_by_role("button", name="Спросить AI-помощника", exact=True).wait_for()

    before_typed = current_from_browser(page, covered_states)
    page.get_by_role("button", name="Ввести только ответ", exact=True).click()
    page.get_by_label("Короткий ответ").fill(f"{canonical_answer}%")
    typed_started = time.perf_counter()
    with page.expect_response(
        lambda response: urlsplit(response.url).path == "/api/journey/answer",
        timeout=180_000,
    ) as typed_response_info:
        page.get_by_role("button", name="Проверить ответ", exact=True).click()
    typed_response = typed_response_info.value
    assert typed_response.status == 200, {
        "typed_answer_provider_status": typed_response.status,
    }
    page.get_by_role("heading", name="Короткий ответ сходится", exact=True).wait_for(
        timeout=180_000,
    )
    typed_elapsed_ms = round((time.perf_counter() - typed_started) * 1000)
    checked = current_from_browser(page, covered_states)
    checked_step = checked["next_step"]
    feedback = checked_step.get("typed_feedback")
    assert checked_step["type"] == "independent_task", checked_step
    assert checked["task"]["problem_id"] == problem_id, checked["task"]
    assert checked["revision"] > before_typed["revision"], checked
    assert checked["learner_evidence"]["status"] == "empty", checked
    assert feedback == {
        "verdict": "correct",
        "message": "Ответ совпадает с условием. Теперь подтверди ход решения фото.",
        "error_focus": "none",
        "counts_for_mastery": False,
    }, feedback
    page.get_by_text("Это ещё не доказательство навыка.", exact=False).wait_for()
    page.get_by_role(
        "button",
        name="Сфотографировать полное решение",
        exact=True,
    ).wait_for()
    gate.checkpoint(page, "live-ai-typed-feedback-mobile", require_heading_focus=False)
    return {
        "tutor": {
            "providerCallObserved": True,
            "responseStatus": tutor_response.status,
            "replyChars": len(assistant_reply),
            "finalAnswerAbsent": True,
        },
        "typedAnswer": {
            "providerCallObserved": True,
            "responseStatus": typed_response.status,
            "verdict": feedback["verdict"],
            "countsForMastery": feedback["counts_for_mastery"],
            "sameProblem": True,
            "elapsedMs": typed_elapsed_ms,
        },
    }


def relogin_exact(
    browser: Browser,
    gate: RuntimeGate,
    context: BrowserContext,
    *,
    base_url: str,
    phone: str,
    pin: str,
    expected: dict[str, Any],
    checkpoint: str,
    covered_states: set[str] | None = None,
) -> tuple[BrowserContext, Page, str]:
    context.close()
    context = new_mobile(browser)
    page = context.new_page()
    gate.attach(page)
    token = browser_login(page, base_url, phone, pin)
    actual = current_from_browser(page, covered_states)
    assert actual == expected, "journey did not resume from the exact saved state"
    gate.checkpoint(page, checkpoint)
    return context, page, token


def upload_photo_ui(
    page: Page,
    fixture: Path,
    *,
    covered_states: set[str],
    require_processing: bool = False,
) -> dict[str, Any]:
    photo_input = page.locator('input[aria-label="Фото всего решения"]:not(:disabled)')
    photo_input.wait_for(state="attached", timeout=30_000)
    photo_input.set_input_files(str(fixture))
    page.get_by_text(fixture.name, exact=True).first.wait_for(timeout=30_000)
    page.get_by_role("button", name="Отправить решение", exact=True).wait_for()
    started = time.monotonic()
    with page.expect_response(
        lambda candidate: urlsplit(candidate.url).path == "/api/journey/photo",
        timeout=120_000,
    ) as response_info:
        page.get_by_role("button", name="Отправить решение", exact=True).click()
        if require_processing:
            deadline = time.monotonic() + 10
            processing_state: dict[str, Any] | None = None
            while time.monotonic() < deadline:
                candidate = current_from_browser(page, covered_states)
                if candidate["next_step"]["type"] == "photo_processing":
                    processing_state = candidate
                    break
                page.wait_for_timeout(50)
            assert processing_state is not None, "photo_processing was not observed"
    response: Response = response_info.value
    response.finished()
    assert response.status == 200, f"photo returned {response.status}: {response.text()[:500]}"
    payload = response.json()
    assert isinstance(payload, dict), payload
    assert_workspace_contract(payload, covered_states)
    step = payload["next_step"]
    heading = PHOTO_HEADINGS[step["type"]][step["reason"] if step["type"] == "photo_recovery" else step["verdict"]]
    wait_heading(page, heading)
    payload["_elapsed_ms"] = round((time.monotonic() - started) * 1000)
    return payload


def answer_guided_ui(
    page: Page,
    answer: str,
    *,
    covered_states: set[str],
) -> dict[str, Any]:
    field = page.get_by_label("Ответ шага")
    field.fill(answer)
    with page.expect_response(
        lambda candidate: urlsplit(candidate.url).path == "/api/journey/guided/answer",
        timeout=30_000,
    ) as response_info:
        page.get_by_role("button", name="Проверить шаг", exact=True).click()
    response = response_info.value
    response.finished()
    assert response.status == 200, response.text()
    payload = response.json()
    assert isinstance(payload, dict), payload
    assert_workspace_contract(payload, covered_states)
    if payload["next_step"]["type"] == "guided_step":
        number = int(payload["next_step"]["step"]["number"])
        page.get_by_test_id("contextual-layer").get_by_text(
            f"Шаг {number} из {payload['next_step']['step']['total']}",
            exact=True,
        ).wait_for()
    else:
        page.locator('.learning-workspace[data-stage="transfer_task"]').wait_for(timeout=30_000)
    return payload


def answer_diagnostic_ui(page: Page, answer: str) -> dict[str, Any]:
    page.get_by_label("Твой ответ").fill(answer)
    with page.expect_response(
        lambda candidate: urlsplit(candidate.url).path == "/api/journey/diagnostic/answer",
        timeout=30_000,
    ) as response_info:
        page.get_by_role("button", name="Ответить", exact=True).click()
    response = response_info.value
    response.finished()
    assert response.status == 200, response.text()
    payload = response.json()
    assert isinstance(payload, dict), payload
    assert_workspace_contract(payload)
    page.get_by_label("Твой ответ").wait_for(timeout=30_000)
    return payload


def run(args: argparse.Namespace) -> dict[str, Any]:
    base_url = args.base_url.rstrip("/")
    fixture_dir = args.fixture_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    pin = os.environ.get("KODI_TEST_PIN")
    if not pin or len(pin) < 4:
        raise SystemExit("KODI_TEST_PIN (minimum four characters) is required")
    fixtures = {
        "unreadable": fixture_dir / "full-solution-unreadable.png",
        "wrong": fixture_dir / "full-solution-wrong-step1.png",
        331: fixture_dir / "transfer-solution-correct.png",
        332: fixture_dir / "reinforcement-332-correct.png",
        333: fixture_dir / "reinforcement-333-correct.png",
        328: fixture_dir / "reinforcement-328-correct.png",
        329: fixture_dir / "reinforcement-329-correct.png",
        330: fixture_dir / "reinforcement-330-correct.png",
        895: fixture_dir / "reinforcement-895-correct.png",
    }
    assert all(path.is_file() for path in fixtures.values()), fixtures

    phone = fresh_phone(base_url, "707")
    gate = RuntimeGate(output_dir)
    transitions: list[str] = []
    photo_results: list[dict[str, Any]] = []
    mastery_snapshots: list[dict[str, Any]] = []
    workspace_states_seen: set[str] = set()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=str(args.chrome) if args.chrome else None,
        )
        context = new_mobile(browser)
        page = context.new_page()
        gate.attach(page)
        token = register_in_browser(
            page,
            gate,
            base_url=base_url,
            phone=phone,
            pin=pin,
        )
        with auth_client(base_url, token) as client:
            initial = api(client, "GET", "/api/journey/current")
            assert initial["next_step"]["type"] == "profile"
            assert "problem" not in initial["next_step"]
            me = api(client, "GET", "/api/auth/me")
            assert me["photo_consent"] is None and me["grade"] == 6

        complete_profile_ui(page, gate)
        gate.checkpoint(page, "exam-map-mobile")
        token = str(page.evaluate("localStorage.getItem('kodi.jwt')"))
        client = auth_client(base_url, token)
        state = api(client, "GET", "/api/journey/current")
        assert state["next_step"]["type"] == "exam_map"
        exam = state["context"]["exam_map"]
        assert exam["cycle"] == "2026–2027"
        assert [(block["questions"], block["minutes"], block["covered"]) for block in exam["day_one"]] == [
            (40, 60, True),
            (60, 30, True),
            (20, 30, False),
        ]
        transitions.append("registration→profile→exam_map")

        page.get_by_role("button", name="Перейти к диагностике", exact=True).click()
        wait_heading(page, "Найдём твою точку старта")
        state = current_from_browser(page, workspace_states_seen)
        assert state["next_step"]["type"] == "diagnostic_intro"
        page.get_by_role("button", name="Начать диагностику", exact=True).click()
        wait_heading(page, "Реши в уме или на черновике")
        state = current_from_browser(page, workspace_states_seen)
        assert state["next_step"]["question"]["id"] == 321
        gate.checkpoint(page, "diagnostic-first-question-mobile")
        state = answer_diagnostic_ui(page, "1200")
        assert state["next_step"]["question"]["id"] == 320
        context, page, token = relogin_exact(
            browser,
            gate,
            context,
            base_url=base_url,
            phone=phone,
            pin=pin,
            expected=state,
            checkpoint="diagnostic-exact-resume-mobile",
            covered_states=workspace_states_seen,
        )
        client.close()
        client = auth_client(base_url, token)
        state = finish_diagnostic(client, state, wrong={}, label="route-a")
        page.reload(wait_until="networkidle")
        wait_heading(page, "Точка старта найдена")
        gate.checkpoint(page, "diagnostic-result-mobile")
        page.get_by_role("button", name="Показать мой маршрут", exact=True).click()
        wait_heading(page, "Смеси и концентрации")
        state = current_from_browser(page, workspace_states_seen)
        route_a = [str(topic["id"]) for topic in state["next_step"]["topics"]]
        assert route_a[:2] == ["PC06", "EQ04"], route_a
        route_b = create_route_b(base_url, pin)
        assert route_b[0] == "EQ04" and route_b != route_a, (route_a, route_b)
        gate.checkpoint(page, "personal-route-mobile")
        transitions.append("diagnostic→personal_route")

        page.get_by_role("button", name="Начать первую тему", exact=True).click()
        page.get_by_role("button", name="Начать задачу", exact=True).wait_for(timeout=30_000)
        page.get_by_role("button", name="Начать задачу", exact=True).click()
        wait_heading(page, "Реши самостоятельно")
        state = current_from_browser(page, workspace_states_seen)
        task = state["next_step"]
        assert task["type"] == "independent_task"
        assert task["problem"]["content_idx"] == 1765
        assert task["photo_required"] is True and task["help_available"] is True
        gate.checkpoint(page, "photo-first-task-mobile")
        page.get_by_role("button", name=re.compile("Позвать взрослого|Передать взрослому")).click()
        page.get_by_role("heading", name="Разрешение на проверку фото").wait_for()
        page.get_by_role("checkbox").check()
        page.get_by_role("button", name=re.compile("Разрешить проверку фото")).click()
        page.get_by_label("Фото всего решения").wait_for(state="attached", timeout=30_000)
        gate.checkpoint(page, "photo-consent-granted-mobile", require_heading_focus=False)
        live_ai = exercise_live_ai_support(
            page,
            gate,
            covered_states=workspace_states_seen,
        )
        transitions.append("independent_task→live_tutor→typed_feedback→same_task")

        state = upload_photo_ui(
            page,
            fixtures["unreadable"],
            covered_states=workspace_states_seen,
            require_processing=True,
        )
        recovery = state["next_step"]
        assert recovery["type"] == "photo_recovery", recovery
        assert recovery["reason"] in {"unreadable", "wrong_photo", "unsure"}, recovery
        photo_results.append(
            {
                "fixture": fixtures["unreadable"].name,
                "verdict": recovery["reason"],
                "elapsedMs": state.pop("_elapsed_ms"),
            }
        )
        gate.checkpoint(page, "safe-photo-recovery-mobile", require_heading_focus=False)
        page.get_by_role("button", name=re.compile("Переснять фото")).click()
        page.get_by_label("Фото всего решения").wait_for(state="attached", timeout=30_000)

        state = upload_photo_ui(
            page,
            fixtures["wrong"],
            covered_states=workspace_states_seen,
        )
        feedback = state["next_step"]
        assert feedback["type"] == "photo_feedback"
        assert feedback["verdict"] == "incorrect" and feedback["failed_step"] == 1, feedback
        photo_results.append({"fixture": fixtures["wrong"].name, "verdict": "incorrect", "failedStep": 1, "elapsedMs": state.pop("_elapsed_ms")})
        mastery_after_wrong = feedback["mastery"]
        gate.checkpoint(page, "first-math-error-mobile", require_heading_focus=False)
        page.get_by_role("button", name="Разобрать по шагам", exact=True).click()
        page.locator('.learning-workspace[data-stage="guided_step"]').wait_for(timeout=90_000)
        gate.checkpoint(page, "guided-start-mobile", require_heading_focus=False)

        state = answer_guided_ui(page, "0", covered_states=workspace_states_seen)
        assert state["next_step"]["step"]["number"] == 1
        assert state["next_step"]["feedback"]["correct"] is False
        state = answer_guided_ui(page, "75", covered_states=workspace_states_seen)
        assert state["next_step"]["step"]["number"] == 2
        guided_resume = current_from_browser(page, workspace_states_seen)
        context, page, token = relogin_exact(
            browser,
            gate,
            context,
            base_url=base_url,
            phone=phone,
            pin=pin,
            expected=guided_resume,
            checkpoint="guided-exact-resume-mobile",
            covered_states=workspace_states_seen,
        )
        client.close()
        client = auth_client(base_url, token)
        state = answer_guided_ui(page, "500", covered_states=workspace_states_seen)
        assert state["next_step"]["step"]["number"] == 3
        state = answer_guided_ui(page, "15", covered_states=workspace_states_seen)
        transfer = state["next_step"]
        assert transfer["type"] == "transfer_task"
        assert transfer["problem"]["content_idx"] == 331
        assert transfer["problem"]["id"] != task["problem"]["id"]
        assert transfer["help_available"] is False
        gate.checkpoint(page, "new-transfer-task-mobile")
        transitions.append("incorrect_photo→guided_same_task→new_transfer_task")

        while True:
            content_idx = int(state["next_step"]["problem"]["content_idx"])
            fixture = fixtures.get(content_idx)
            assert fixture is not None, f"no fixture for transfer content {content_idx}"
            state = upload_photo_ui(
                page,
                fixture,
                covered_states=workspace_states_seen,
            )
            feedback = state["next_step"]
            assert feedback["type"] == "transfer_feedback" and feedback["verdict"] == "correct", feedback
            elapsed_ms = state.pop("_elapsed_ms")
            mastery = feedback["mastery"]
            evidence = mastery["evidence"]
            photo_results.append({"fixture": fixture.name, "verdict": "correct", "elapsedMs": elapsed_ms})
            mastery_snapshots.append({
                "contentIdx": content_idx,
                "probability": mastery["value"],
                "correct": evidence["correct"],
                "total": evidence["total"],
                "accuracy": evidence["accuracy"],
                "reached": mastery["reached"],
            })
            if mastery["reached"]:
                assert evidence["correct"] >= 3
                assert evidence["accuracy"] >= 0.5
                assert mastery["value"] >= mastery["threshold"] == 0.85
                break
            page.get_by_role("button", name=feedback["primary_action"], exact=True).click()
            page.locator('input[aria-label="Фото всего решения"]:not(:disabled)').wait_for(
                state="attached",
                timeout=30_000,
            )
            state = current_from_browser(page, workspace_states_seen)

        assert mastery_snapshots[0]["total"] == mastery_after_wrong["evidence"]["total"] + 1
        gate.checkpoint(page, "mastery-reached-mobile", require_heading_focus=False)
        page.get_by_role("button", name="Завершить тему", exact=True).click()
        wait_heading(page, "Навык подтверждён")
        gate.checkpoint(page, "topic-result-mobile")
        transitions.append("whole_photo_transfer→mastery_threshold→topic_result")
        context.close()

        desktop = browser.new_context(viewport={"width": 1280, "height": 900}, service_workers="block")
        desktop_page = desktop.new_page()
        gate.attach(desktop_page)
        browser_login(desktop_page, base_url, phone, pin)
        wait_heading(desktop_page, "Навык подтверждён")
        gate.checkpoint(desktop_page, "topic-result-desktop")
        interaction = gate.keyboard_and_motion(desktop_page)
        assets = gate.build_assets(desktop_page)
        desktop.close()
        browser.close()
        client.close()

    missing_workspace_states = ACTIVE_WORKSPACE_TYPES.difference(workspace_states_seen)
    assert not missing_workspace_states, {
        "missing_workspace_states": sorted(missing_workspace_states),
        "covered_workspace_states": sorted(workspace_states_seen),
    }
    gate.assert_clean()
    return {
        "verdict": "PASS",
        "baseOrigin": f"{urlsplit(base_url).scheme}://{urlsplit(base_url).netloc}",
        "syntheticAccounts": 2,
        "transitions": transitions,
        "routeA": route_a,
        "routeB": route_b,
        "routesDiffer": route_a != route_b,
        "exactResume": {"diagnostic": True, "guided": True},
        "workspaceContract": {
            "version": 1,
            "requiredStates": sorted(ACTIVE_WORKSPACE_TYPES),
            "coveredStates": sorted(workspace_states_seen),
            "complete": True,
        },
        "photoResults": photo_results,
        "liveAi": live_ai,
        "guidedCountsForMastery": False,
        "mastery": mastery_snapshots,
        "finalMastery": mastery_snapshots[-1],
        "screenshots": len(gate.checks),
        "checks": gate.checks,
        "interaction": interaction,
        "assets": assets,
        "consoleErrors": gate.console_errors,
        "pageErrors": gate.page_errors,
        "requestErrors": gate.request_errors,
        "apiErrors": gate.api_errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8414")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--fixture-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "fixtures",
    )
    parser.add_argument(
        "--chrome",
        type=Path,
        default=DEFAULT_CHROME if DEFAULT_CHROME.exists() else None,
    )
    args = parser.parse_args()
    summary = run(args)
    target = args.output_dir.resolve() / "live-cjm-summary.json"
    target.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
