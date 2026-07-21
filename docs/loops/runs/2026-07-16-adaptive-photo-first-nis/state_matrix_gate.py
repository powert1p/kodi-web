#!/usr/bin/env python3
"""Render the production journey state contract at both release viewports.

This gate deliberately labels synthetic journey payloads as UI contract fixtures.
It proves that the production bundle can render every typed state without console,
focus, overflow, or touch-target regressions. Live backend and Gemini evidence is
kept in separate directories and is never represented by this script.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Callable

from playwright.sync_api import Browser, BrowserContext, Page, Route, sync_playwright

from capture_runtime_gate import DEFAULT_CHROME, RuntimeGate


VIEWPORTS = (
    ("mobile", 375, 844, True),
    ("desktop", 1280, 900, False),
)

EXAM_MAP = {
    "title": "Поступление в NIS · математика",
    "scope_note": "Проверяем только математику первого дня и строим маршрут по подтверждённым навыкам.",
    "cycle": "Набор 2026–2027",
    "verified_on": "2026-07-16",
    "source_url": "https://www.nis.edu.kz/",
    "source_note": "Официальная структура конкурсного отбора NIS",
    "disclaimer": "Формат может обновляться — перед экзаменом сверь правила на сайте NIS.",
    "day_one": [
        {"name": "Математика", "questions": 40, "minutes": 60, "covered": True},
        {"name": "Количественные характеристики", "questions": 60, "minutes": 30, "covered": True},
        {"name": "Естествознание", "questions": 20, "minutes": 30, "covered": False},
    ],
}

PROFILE = {
    "target": "nis-grade-7",
    "weekly_goal": 4,
    "session_minutes": 30,
    "target_window": "spring-2027",
    "prep_experience": "self",
    "weak_topics": ["PC05", "EQ04"],
    "strong_topics": ["DA02"],
    "mock_math_band": "21-30",
    "language": "ru",
}

TOPICS_FOUNDATION = [
    {
        "id": "PC06",
        "title": "Смеси и концентрации",
        "strand": "Проценты и отношения",
        "goal": "Научиться переводить условие смеси в доли и проверять результат обратным действием.",
        "reason": "Диагностика показала: проценты считаются уверенно, но модель текстовой задачи пока распадается.",
        "status": "next",
        "diagnostic_level": "foundation",
    },
    {
        "id": "EQ04",
        "title": "Текстовые уравнения",
        "strand": "Алгебра",
        "goal": "Составлять уравнение из условия, а не угадывать действие.",
        "reason": "Это следующая опора для сложных задач NIS.",
        "status": "planned",
        "diagnostic_level": "developing",
    },
    {
        "id": "FR05",
        "title": "Дроби в задачах",
        "strand": "Числа",
        "goal": "Сравнивать и преобразовывать дробные величины.",
        "reason": "Навык понадобится в задачах на скорость и совместную работу.",
        "status": "planned",
        "diagnostic_level": "developing",
    },
    {
        "id": "GE04",
        "title": "Углы и отношения",
        "strand": "Геометрические отношения",
        "goal": "Переводить отношение частей угла в точную градусную меру.",
        "reason": "Геометрическая опора уже есть; маршрут проверит её на составной задаче.",
        "status": "planned",
        "diagnostic_level": "secure",
    },
    {
        "id": "DA02",
        "title": "Графики движения и данных",
        "strand": "Данные и зависимости",
        "goal": "Считывать изменения с графика и связывать их с расчётом величины.",
        "reason": "Навык чтения графиков подтверждён и будет закреплён в маршруте.",
        "status": "planned",
        "diagnostic_level": "secure",
    },
]

TOPICS_SECURE = [
    {
        "id": "EQ04",
        "title": "Текстовые уравнения",
        "strand": "Алгебра",
        "goal": "Составлять многошаговые уравнения из текста.",
        "reason": "Проценты уже подтверждены, поэтому маршрут начинает с новой точки роста.",
        "status": "next",
        "diagnostic_level": "foundation",
    },
    {**TOPICS_FOUNDATION[0], "status": "planned", "diagnostic_level": "secure"},
    {**TOPICS_FOUNDATION[2], "status": "planned", "diagnostic_level": "secure"},
    {**TOPICS_FOUNDATION[3], "status": "planned", "diagnostic_level": "secure"},
    {**TOPICS_FOUNDATION[4], "status": "planned", "diagnostic_level": "secure"},
]

SKILLS_FOUNDATION = [
    {"id": "PC05", "title": "Проценты", "level": "developing", "label": "Опора есть, нужна практика", "route_topic_id": "PC06"},
    {"id": "EQ04", "title": "Текстовые уравнения", "level": "foundation", "label": "Начинаем с модели условия", "route_topic_id": "EQ04"},
    {"id": "FR05", "title": "Дроби", "level": "developing", "label": "База есть", "route_topic_id": "FR05"},
    {"id": "GE04", "title": "Геометрические отношения", "level": "secure", "label": "Опора подтверждена", "route_topic_id": "GE04"},
    {"id": "DA02", "title": "Графики и данные", "level": "secure", "label": "Опора подтверждена", "route_topic_id": "DA02"},
]

SKILLS_SECURE = [
    {**skill, "level": "secure", "label": "Опора подтверждена"}
    if skill["id"] in {"PC05", "FR05", "GE04", "DA02"}
    else {**skill, "level": "foundation", "label": "Первая точка роста"}
    for skill in SKILLS_FOUNDATION
]

PROBLEM = {
    "id": 1765,
    "content_idx": 1765,
    "node_id": "PC06",
    "statement": "В 300 г раствора содержится 25% соли. В раствор добавили 200 г воды. Каков процент соли в новом растворе?",
    "topic": {"id": "PC06", "title": "Смеси и концентрации"},
}

TRANSFER_PROBLEM = {
    "id": 331,
    "content_idx": 331,
    "node_id": "PC06",
    "statement": "Из 300 г 20%-го раствора выпарили 100 г воды. Какова новая концентрация?",
    "topic": {"id": "PC06", "title": "Смеси и концентрации"},
}

MASTERY_BELOW = {
    "value": 0.83,
    "threshold": 0.85,
    "reached": False,
    "evidence": {
        "correct": 2,
        "required_correct": 3,
        "remaining_correct": 1,
        "total": 3,
        "accuracy": 0.67,
        "minimum_accuracy": 0.5,
        "probability_reached": False,
        "correct_reached": False,
        "accuracy_reached": True,
    },
}

MASTERY_REACHED = {
    "value": 0.93,
    "threshold": 0.85,
    "reached": True,
    "evidence": {
        "correct": 3,
        "required_correct": 3,
        "remaining_correct": 0,
        "total": 4,
        "accuracy": 0.75,
        "minimum_accuracy": 0.5,
        "probability_reached": True,
        "correct_reached": True,
        "accuracy_reached": True,
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


def context(
    topics: list[dict[str, Any]] | None = None,
    skills: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    route_topics = copy.deepcopy(topics or TOPICS_FOUNDATION)
    return {
        "exam_map": copy.deepcopy(EXAM_MAP),
        "profile": copy.deepcopy(PROFILE),
        "route": {
            "topics": route_topics,
            "index": 0,
            "completed": [],
            "skill_profile": copy.deepcopy(skills or SKILLS_FOUNDATION),
        },
    }


def state(
    revision: int,
    next_step: dict[str, Any],
    *,
    topics: list[dict[str, Any]] | None = None,
    skills: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload = {
        "journey_id": 9001,
        "revision": revision,
        "next_step": next_step,
        "context": context(topics, skills),
    }
    step_type = next_step["type"]
    if step_type not in ACTIVE_WORKSPACE_TYPES:
        return payload

    problem = next_step["problem"]
    is_transfer = step_type in {"transfer_task", "transfer_feedback"}
    evidence_label = None
    if step_type in {"photo_processing", "photo_recovery"}:
        evidence_label = next_step["preserved_photo"]["name"]
    elif step_type in {"photo_feedback", "transfer_feedback"}:
        evidence_label = "reshenie-smesi.jpg"
    verdict = None
    recovery_reason = None
    if step_type in {"photo_feedback", "transfer_feedback"}:
        verdict = "correct" if next_step["verdict"] == "correct" else "needs_revision"
    elif step_type == "photo_recovery":
        verdict = "uncertain"
        recovery_reason = next_step["reason"]

    payload.update({
        "workspace_version": 1,
        "task": {
            "journey_id": 9001,
            "problem_id": problem["id"],
            "topic": copy.deepcopy(problem["topic"]),
            "mode": "transfer" if is_transfer else "independent",
            "statement": problem["statement"],
            "position": 1,
        },
        "learner_evidence": {
            "kind": "photo",
            "status": WORKSPACE_EVIDENCE_STATUS[step_type],
            "label": evidence_label,
        },
        "context_layer": {
            "kind": WORKSPACE_CONTEXT_KIND[step_type],
            "verdict": verdict,
            "recovery_reason": recovery_reason,
        },
        "response": {
            "default_mode": "photo",
            "typed_available": step_type in {"independent_task", "transfer_task"},
            "help_available": step_type == "independent_task",
        },
        "support": {
            "used": step_type == "guided_step",
            "highest_hint_rung": 1 if step_type == "guided_step" else 0,
        },
    })
    return payload


def profile_step(screen: int) -> dict[str, Any]:
    titles = (
        "Сначала настроим твою подготовку",
        "Выберем спокойный ритм",
        "Что учесть в диагностике",
        "Есть результат пробника?",
    )
    return {
        "type": "profile",
        "title": titles[screen],
        "primary_action": "Продолжить",
        "student": {"name": "Амина", "grade": 6},
        "description": "Четыре коротких шага — после них увидишь карту подготовки и стартовую диагностику.",
        "screen": screen,
        "substep": 0,
        "screen_count": 4,
        "draft": copy.deepcopy(PROFILE),
    }


def task_step(kind: str, *, consent: bool = False) -> dict[str, Any]:
    transfer = kind == "transfer_task"
    return {
        "type": kind,
        "title": "Докажи решение на бумаге" if not transfer else "Проверь навык на новой задаче",
        "primary_action": "Сфотографировать решение",
        "mode": "transfer" if transfer else "independent",
        "problem": copy.deepcopy(TRANSFER_PROBLEM if transfer else PROBLEM),
        "instruction": "Реши задачу целиком, затем сфотографируй весь лист одним кадром.",
        "photo_required": True,
        "help_available": not transfer,
        "photo_consent_required": consent,
    }


def recovery_step(reason: str) -> dict[str, Any]:
    messages = {
        "unreadable": "Часть вычислений не читается. Сделай новый снимок при хорошем свете.",
        "wrong_photo": "На фото другая задача. Сверь условие и сними нужную страницу.",
        "unsure": "Не удалось уверенно проверить весь ход решения. Пересними лист целиком.",
        "provider_error": "Сервис проверки временно недоступен. Фото сохранено — повторная съёмка не нужна.",
    }
    return {
        "type": "photo_recovery",
        "problem": copy.deepcopy(PROBLEM),
        "reason": reason,
        "message": messages[reason],
        "preserved_photo": {"name": "reshenie-smesi.jpg"},
        "return_stage": "independent_task",
        "primary_action": "Повторить проверку" if reason == "provider_error" else "Сделать новое фото",
    }


def fixture_states() -> list[tuple[str, dict[str, Any], str | None]]:
    states: list[tuple[str, dict[str, Any], str | None]] = []
    revision = 10

    def add(name: str, step: dict[str, Any], action: str | None = None, *, topics=None, skills=None) -> None:
        nonlocal revision
        states.append((name, state(revision, step, topics=topics, skills=skills), action))
        revision += 1

    for screen in range(4):
        add(f"profile-{screen + 1}", profile_step(screen))
    add(
        "exam-map",
        {"type": "exam_map", "title": EXAM_MAP["title"], "primary_action": "Перейти к диагностике", "scope_note": EXAM_MAP["scope_note"]},
    )
    add(
        "diagnostic-intro",
        {"type": "diagnostic_intro", "title": "Найдём честную точку старта", "primary_action": "Начать диагностику", "description": "Пять опорных задач определят порядок тем. Это не оценка и не экзамен.", "estimated_minutes": 8},
    )
    add(
        "diagnostic-question-start",
        {"type": "diagnostic_question", "title": "Опорная задача", "primary_action": "Проверить ответ", "progress": {"answered": 0, "current": 1, "planned": 5}, "question": {"id": 321, "statement": "Цена после скидки 20% стала 4 800 ₸. Какой была цена до скидки?", "answer_type": "number"}},
    )
    add(
        "diagnostic-question-resume",
        {"type": "diagnostic_question", "title": "Опорная задача", "primary_action": "Проверить ответ", "progress": {"answered": 3, "current": 4, "planned": 5}, "question": {"id": 1409, "statement": "Три пятых числа равны 42. Найди число.", "answer_type": "number"}},
        "fill-diagnostic",
    )
    add(
        "diagnostic-result",
        {"type": "diagnostic_result", "title": "Маршрут готов", "primary_action": "Показать маршрут", "score": {"correct": 3, "total": 5}, "skill_profile": copy.deepcopy(SKILLS_FOUNDATION), "description": "Нашли две сильные опоры и одну первую точку роста."},
    )
    add(
        "route-foundation",
        {"type": "route_ready", "title": "Твой маршрут", "primary_action": "Начать первую тему", "topics": copy.deepcopy(TOPICS_FOUNDATION)},
    )
    add(
        "route-secure-alternative",
        {"type": "route_ready", "title": "Твой маршрут", "primary_action": "Начать первую тему", "topics": copy.deepcopy(TOPICS_SECURE)},
        topics=TOPICS_SECURE,
        skills=SKILLS_SECURE,
    )
    add(
        "lesson-intro",
        {"type": "lesson_intro", "title": "Смеси без угадывания", "primary_action": "Начать самостоятельную задачу", "topic": copy.deepcopy(TOPICS_FOUNDATION[0]), "description": TOPICS_FOUNDATION[0]["reason"], "goal": TOPICS_FOUNDATION[0]["goal"]},
    )
    add("photo-consent-child", task_step("independent_task", consent=True))
    add("photo-consent-parent", task_step("independent_task", consent=True), "parent-handoff")
    add("photo-task-empty", task_step("independent_task"))
    add("photo-task-selected", task_step("independent_task"), "select-photo")
    typed_checked = task_step("independent_task")
    typed_checked["typed_feedback"] = {
        "verdict": "correct",
        "message": "Ответ совпадает с условием. Теперь подтверди ход решения фото.",
        "error_focus": "none",
        "counts_for_mastery": False,
    }
    add("typed-feedback-correct", typed_checked)
    add("tutor-open", task_step("independent_task"), "open-tutor")
    add(
        "photo-processing",
        {"type": "photo_processing", "title": "Проверяем ход решения", "primary_action": "Обновить состояние", "problem": copy.deepcopy(PROBLEM), "message": "Сверяем каждый шаг с условием задачи.", "preserved_photo": {"name": "reshenie-smesi.jpg"}},
    )
    for reason in ("unreadable", "wrong_photo", "unsure", "provider_error"):
        add(f"photo-recovery-{reason}", recovery_step(reason))
    add(
        "photo-feedback-incorrect",
        {"type": "photo_feedback", "problem": copy.deepcopy(PROBLEM), "verdict": "incorrect", "message": "Масса соли найдена верно. Первое расхождение — в вычислении общей массы раствора.", "failed_step": 2, "confirmed_steps": [{"number": 1, "label": "Найдено 75 г соли"}], "correction": "После добавления воды масса раствора равна 300 + 200 = 500 г. Тогда 75 ÷ 500 = 0,15, то есть 15%.", "help_available": True, "primary_action": "Исправить решение"},
    )
    add(
        "photo-feedback-correct",
        {"type": "photo_feedback", "problem": copy.deepcopy(PROBLEM), "verdict": "correct", "message": "75 г соли в 500 г раствора дают 15%. Нужна ещё одна новая задача, чтобы доказать устойчивость.", "confirmed_steps": [{"number": 1, "label": "75 г соли"}, {"number": 2, "label": "500 г раствора"}, {"number": 3, "label": "15% соли"}], "mastery": copy.deepcopy(MASTERY_BELOW), "primary_action": "Следующая задача"},
    )
    guided_base = {"type": "guided_step", "title": "Соберём модель по одному шагу", "primary_action": "Проверить шаг", "problem": copy.deepcopy(PROBLEM), "step": {"number": 1, "total": 3, "instruction": "Сколько граммов соли было в исходном растворе?"}, "photo_required": False, "mastery_note": "Разбор помогает понять тему, но не повышает mastery. После него будет новая самостоятельная задача."}
    add("guided-initial", {**guided_base, "feedback": None})
    add("guided-wrong", {**guided_base, "feedback": {"correct": False, "message": "Не спеши: 25% — это 0,25 от 300 г. Попробуй ещё раз."}})
    add("guided-correct", {**guided_base, "step": {"number": 2, "total": 3, "instruction": "Какой стала общая масса раствора после добавления 200 г воды?"}, "feedback": {"correct": True, "message": "Да: масса соли не меняется."}})
    add("guided-offline-preserved-input", {**guided_base, "feedback": None}, "guided-offline")
    add("transfer-task", task_step("transfer_task"))
    add(
        "transfer-below-mastery",
        {"type": "transfer_feedback", "problem": copy.deepcopy(TRANSFER_PROBLEM), "verdict": "correct", "message": "60 г соли остались в 200 г раствора: концентрация стала 30%. Осталась одна новая задача.", "mastery": copy.deepcopy(MASTERY_BELOW), "primary_action": "Решить ещё одну"},
    )
    add(
        "transfer-mastery-reached",
        {"type": "transfer_feedback", "problem": copy.deepcopy(TRANSFER_PROBLEM), "verdict": "correct", "message": "60 г соли остались в 200 г раствора: 30%. Навык подтверждён тремя самостоятельными решениями.", "mastery": copy.deepcopy(MASTERY_REACHED), "primary_action": "Посмотреть результат"},
    )
    add(
        "topic-result",
        {"type": "topic_result", "title": "Тема подтверждена", "primary_action": "Перейти к следующей теме", "topic": {**copy.deepcopy(TOPICS_FOUNDATION[0]), "status": "completed"}, "mastery": copy.deepcopy(MASTERY_REACHED)},
    )
    completed_topics = [{**copy.deepcopy(topic), "status": "completed"} for topic in TOPICS_FOUNDATION]
    add(
        "route-complete",
        {"type": "route_complete", "title": "Первый маршрут пройден", "primary_action": "Открыть прогресс", "description": "Все темы этого маршрута подтверждены самостоятельными решениями."},
        topics=completed_topics,
    )
    add(
        "empty-route-recovery",
        {"type": "route_ready", "title": "Твой маршрут", "primary_action": "Обновить маршрут", "topics": []},
        topics=[],
    )
    return states


def new_context(browser: Browser, width: int, height: int, mobile: bool) -> BrowserContext:
    return browser.new_context(
        viewport={"width": width, "height": height},
        has_touch=mobile,
        is_mobile=mobile,
        service_workers="block",
    )


def install_state_route(page: Page, payload: dict[str, Any]) -> None:
    page.add_init_script("localStorage.setItem('kodi.jwt', 'ui-contract-fixture-token')")
    page.route(
        "**/api/journey/current",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(payload, ensure_ascii=False),
        ),
    )


def run_action(page: Page, action: str | None, sample_photo: Path) -> list[str]:
    expected_failures: list[str] = []
    if action == "parent-handoff":
        page.get_by_role("button", name="Позвать взрослого").click()
        page.get_by_role("heading", name="Разрешение на проверку фото").wait_for()
    elif action == "select-photo":
        page.get_by_label("Фото всего решения").set_input_files(str(sample_photo))
        page.get_by_text(sample_photo.name, exact=True).wait_for()
    elif action == "fill-diagnostic":
        page.get_by_label("Твой ответ").fill("70")
    elif action == "guided-offline":
        page.evaluate("Object.defineProperty(navigator, 'onLine', {get: () => false})")
        page.route("**/api/journey/guided/answer", lambda route: route.abort("internetdisconnected"))
        page.get_by_label("Ответ шага").fill("75")
        page.get_by_role("button", name="Проверить шаг").click()
        page.get_by_role("alert").filter(has_text="Нет соединения").wait_for(timeout=10_000)
        expected_failures.append("POST /api/journey/guided/answer")
        assert page.get_by_label("Ответ шага").input_value() == "75"
    elif action == "open-tutor":
        page.get_by_role("button", name="Спросить AI-помощника").click()
        tutor_input = page.get_by_label("Твой вопрос")
        tutor_input.wait_for()
        assert tutor_input.evaluate("element => element === document.activeElement")
    return expected_failures


def capture_fixture_states(
    browser: Browser,
    gate: RuntimeGate,
    *,
    base_url: str,
    sample_photo: Path,
) -> tuple[list[str], list[str], dict[str, Any] | None]:
    assets: set[str] = set()
    expected_failures: list[str] = []
    interaction: dict[str, Any] | None = None
    for viewport_name, width, height, mobile in VIEWPORTS:
        for name, payload, action in fixture_states():
            context_handle = new_context(browser, width, height, mobile)
            page = context_handle.new_page()
            gate.attach(page)
            install_state_route(page, payload)
            page.goto(f"{base_url}/app/", wait_until="networkidle")
            page.locator(".journey-main h1").wait_for(timeout=20_000)
            expected_failures.extend(run_action(page, action, sample_photo))
            step_type = payload["next_step"]["type"]
            if step_type in ACTIVE_WORKSPACE_TYPES:
                assert page.locator(
                    f'.learning-workspace[data-stage="{step_type}"]'
                ).count() == 1
            if name == "transfer-task":
                assert page.get_by_role("button", name="Не знаю, как начать").count() == 0
            checkpoint = gate.checkpoint(
                page,
                f"{name}-{viewport_name}",
                require_heading_focus=step_type not in ACTIVE_WORKSPACE_TYPES and action not in {
                    "fill-diagnostic",
                    "select-photo",
                    "guided-offline",
                    "parent-handoff",
                    "open-tutor",
                },
            )
            assets.update(gate.build_assets(page))
            if name == "lesson-intro" and viewport_name == "mobile":
                interaction = gate.keyboard_and_motion(page)
            assert checkpoint["headingFont"] is not None
            context_handle.close()
    return sorted(assets), expected_failures, interaction


def capture_auth_states(browser: Browser, gate: RuntimeGate, *, base_url: str) -> list[str]:
    assets: set[str] = set()
    for viewport_name, width, height, mobile in VIEWPORTS:
        context_handle = new_context(browser, width, height, mobile)
        page = context_handle.new_page()
        gate.attach(page)
        page.route(
            "**/api/auth/phone/check",
            lambda route: route.fulfill(status=200, content_type="application/json", body='{"exists":false}'),
        )
        page.goto(f"{base_url}/app/login", wait_until="networkidle")
        gate.checkpoint(page, f"auth-phone-{viewport_name}", heading_selector=".login-main h1", require_heading_focus=False)
        page.get_by_label("Номер телефона").fill("+7 700 555 01 01")
        page.get_by_role("button", name="Продолжить", exact=True).click()
        page.get_by_label("Имя").wait_for()
        gate.checkpoint(page, f"auth-register-name-{viewport_name}", heading_selector=".login-main h1", require_heading_focus=False)
        page.get_by_label("Имя").fill("Амина")
        page.get_by_role("button", name="Далее", exact=True).click()
        page.get_by_role("radiogroup", name="Класс").wait_for()
        gate.checkpoint(page, f"auth-register-grade-{viewport_name}", heading_selector=".login-main h1", require_heading_focus=False)
        page.get_by_role("radio", name="6", exact=True).click()
        page.get_by_role("button", name="Далее", exact=True).click()
        page.get_by_label("Придумай PIN").wait_for()
        gate.checkpoint(page, f"auth-register-pin-{viewport_name}", heading_selector=".login-main h1", require_heading_focus=False)
        assets.update(gate.build_assets(page))
        context_handle.close()

        login_context = new_context(browser, width, height, mobile)
        login_page = login_context.new_page()
        gate.attach(login_page)
        login_page.route(
            "**/api/auth/phone/check",
            lambda route: route.fulfill(status=200, content_type="application/json", body='{"exists":true}'),
        )
        login_page.goto(f"{base_url}/app/login", wait_until="networkidle")
        login_page.get_by_label("Номер телефона").fill("+7 700 555 01 02")
        login_page.get_by_role("button", name="Продолжить", exact=True).click()
        login_page.get_by_label("PIN-код").wait_for()
        gate.checkpoint(login_page, f"auth-login-returning-{viewport_name}", heading_selector=".login-main h1", require_heading_focus=False)
        assets.update(gate.build_assets(login_page))
        login_context.close()
    return sorted(assets)


def capture_transport_states(
    browser: Browser,
    gate: RuntimeGate,
    *,
    base_url: str,
) -> list[str]:
    expected_failures: list[str] = []
    for viewport_name, width, height, mobile in VIEWPORTS:
        loading_context = new_context(browser, width, height, mobile)
        loading_page = loading_context.new_page()
        gate.attach(loading_page)
        loading_page.add_init_script("localStorage.setItem('kodi.jwt', 'ui-contract-fixture-token')")
        pending_routes: list[Route] = []
        loading_page.route("**/api/journey/current", lambda route: pending_routes.append(route))
        loading_page.goto(f"{base_url}/app/", wait_until="domcontentloaded")
        loading_page.get_by_role("status", name="Загружаем твой маршрут").wait_for()
        gate.checkpoint(loading_page, f"transport-loading-{viewport_name}", heading_selector=None, require_heading_focus=False)
        for route in pending_routes:
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(fixture_states()[0][1], ensure_ascii=False),
            )
        loading_page.locator(".journey-main h1").wait_for(timeout=10_000)
        loading_context.close()

        offline_context = new_context(browser, width, height, mobile)
        offline_page = offline_context.new_page()
        gate.attach(offline_page)
        offline_page.add_init_script(
            "localStorage.setItem('kodi.jwt', 'ui-contract-fixture-token'); "
            "Object.defineProperty(navigator, 'onLine', {get: () => false})"
        )
        offline_page.route("**/api/journey/current", lambda route: route.abort("internetdisconnected"))
        offline_page.goto(f"{base_url}/app/", wait_until="networkidle")
        offline_page.get_by_role("heading", name="Учёба никуда не пропала").wait_for(timeout=20_000)
        gate.checkpoint(offline_page, f"transport-offline-{viewport_name}")
        expected_failures.append("GET /api/journey/current")
        offline_context.close()
    return expected_failures


def strip_expected_failures(gate: RuntimeGate, expected: list[str]) -> list[str]:
    remaining = list(gate.request_errors)
    matched: list[str] = []
    for prefix in dict.fromkeys(expected):
        prefix_matches = [item for item in remaining if item.startswith(prefix)]
        assert prefix_matches, f"expected transport failure did not occur: {prefix}"
        matched.extend(prefix_matches)
        remaining = [item for item in remaining if not item.startswith(prefix)]
    gate.request_errors = remaining
    return matched


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8414")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--sample-photo",
        type=Path,
        default=Path(__file__).parent / "fixtures" / "full-solution-correct.png",
    )
    parser.add_argument("--chrome", type=Path, default=DEFAULT_CHROME if DEFAULT_CHROME.exists() else None)
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    sample_photo = args.sample_photo.resolve()
    if not sample_photo.is_file():
        raise SystemExit(f"Sample photo not found: {sample_photo}")

    gate = RuntimeGate(args.output_dir.resolve())
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=str(args.chrome) if args.chrome else None,
        )
        auth_assets = capture_auth_states(browser, gate, base_url=base_url)
        assets, fixture_expected, interaction = capture_fixture_states(
            browser,
            gate,
            base_url=base_url,
            sample_photo=sample_photo,
        )
        transport_expected = capture_transport_states(browser, gate, base_url=base_url)
        browser.close()

    expected_failures = strip_expected_failures(gate, fixture_expected + transport_expected)
    gate.assert_clean()
    summary = {
        "verdict": "PASS",
        "evidenceMode": "production-runtime-ui-contract-fixtures",
        "honestyBoundary": (
            "Journey JSON is deterministic typed fixture data. It validates the current production bundle UI only; "
            "real backend, persistence, photo recovery, and Gemini are proven by separate CJM evidence."
        ),
        "baseUrl": base_url,
        "viewports": [
            {"name": name, "width": width, "height": height, "touch": mobile}
            for name, width, height, mobile in VIEWPORTS
        ],
        "stateCount": len(fixture_states()) + 5 + 2,
        "screenshotCount": len(gate.checks),
        "checks": gate.checks,
        "assets": sorted(set(auth_assets) | set(assets)),
        "expectedTransportFailures": expected_failures,
        "consoleErrors": gate.console_errors,
        "pageErrors": gate.page_errors,
        "requestErrors": gate.request_errors,
        "apiErrors": gate.api_errors,
        "keyboardAndReducedMotion": interaction,
    }
    output = gate.output_dir / "state-matrix-summary.json"
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": "PASS", "screenshots": len(gate.checks), "summary": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
