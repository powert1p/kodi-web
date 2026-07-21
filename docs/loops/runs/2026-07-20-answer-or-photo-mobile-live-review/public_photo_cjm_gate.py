#!/usr/bin/env python3
"""Public browser gate for AI tutor and HEIC/JPEG journey photo handling."""

from __future__ import annotations

import argparse
import json
import random
import time
import traceback
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from PIL import Image
from playwright.sync_api import Page, Response, sync_playwright


REPO_ROOT = Path(__file__).resolve().parents[4]
PROBLEMS = json.loads(
    (REPO_ROOT / "backend/data/problems_v10.json").read_text(encoding="utf-8")
)["problems"]
FIXTURE_DIR = (
    REPO_ROOT
    / "docs/loops/runs/2026-07-16-adaptive-photo-first-nis/fixtures"
)


def current_state(page: Page) -> dict[str, Any]:
    state = page.evaluate(
        """async () => {
          const response = await fetch('/api/journey/current', {
            headers: {Authorization: `Bearer ${localStorage.getItem('kodi.jwt')}`},
          });
          if (!response.ok) throw new Error(`current:${response.status}`);
          return response.json();
        }"""
    )
    assert isinstance(state, dict), "journey/current must return an object"
    return state


def task_marker(state: dict[str, Any]) -> dict[str, Any]:
    step = state.get("next_step") or {}
    problem = step.get("problem") or {}
    return {
        "revision": state.get("revision"),
        "stage": step.get("type"),
        "problem_id": problem.get("id"),
        "content_idx": problem.get("content_idx"),
        "statement": problem.get("statement"),
    }


def wait_workspace(page: Page) -> None:
    page.get_by_test_id("learning-workspace").wait_for(
        state="visible", timeout=30_000
    )


def make_phone() -> str:
    return f"+7707{random.SystemRandom().randrange(10_000_000, 99_999_999)}"


def register_and_reach_pc06_task(page: Page, base_url: str) -> dict[str, Any]:
    phone = make_phone()
    pin = str(random.SystemRandom().randrange(1000, 9999))
    page.goto(f"{base_url}/app/login", wait_until="domcontentloaded")
    page.get_by_label("Номер телефона", exact=True).fill(phone)
    page.get_by_role("button", name="Продолжить", exact=True).click()
    page.get_by_label("Имя", exact=True).fill("QA Photo")
    page.get_by_role("button", name="Далее", exact=True).click()
    page.get_by_role("radio", name="6", exact=True).check()
    page.get_by_role("button", name="Далее", exact=True).click()
    page.get_by_label("Придумай PIN", exact=True).fill(pin)
    page.get_by_role(
        "button", name="Создать аккаунт и настроить маршрут", exact=True
    ).click()
    page.wait_for_url("**/app", timeout=30_000)

    page.get_by_role("button", name="Продолжить к ритму", exact=True).click()
    page.get_by_role("radio", name="4 раза", exact=False).check()
    page.get_by_role("button", name="Дальше", exact=True).click()
    page.get_by_role("radio", name="30 минут", exact=False).check()
    page.get_by_role("button", name="Дальше", exact=True).click()
    page.get_by_role("radio", name="Сам", exact=True).check()
    page.get_by_role("button", name="Продолжить к темам", exact=False).click()
    page.get_by_role(
        "heading", name="Что учесть в диагностике", exact=True
    ).wait_for(timeout=20_000)
    page.get_by_role("radio", name="Проценты: сложно", exact=True).check()
    page.get_by_role(
        "radio", name="Текстовые уравнения: получается", exact=True
    ).check()
    page.get_by_role("button", name="Продолжить", exact=True).click()
    page.get_by_role(
        "heading", name="Есть результат пробника?", exact=True
    ).wait_for(timeout=20_000)
    page.get_by_role("radio", name="21–30 верных из 40", exact=True).check()
    page.get_by_role(
        "button", name="Построить диагностику", exact=False
    ).click()
    page.get_by_role(
        "button", name="Перейти к диагностике", exact=True
    ).click()
    page.get_by_role(
        "heading", name="Найдём твою точку старта", exact=True
    ).wait_for(timeout=20_000)
    page.get_by_role("button", name="Начать диагностику", exact=True).click()

    deadline = time.monotonic() + 30
    while True:
        state = current_state(page)
        if (state.get("next_step") or {}).get("type") == "diagnostic_question":
            break
        if time.monotonic() > deadline:
            raise TimeoutError("diagnostic question did not become authoritative")
        page.wait_for_timeout(100)

    diagnostic_answers: list[dict[str, Any]] = []
    deadline = time.monotonic() + 180
    while True:
        state = current_state(page)
        step = state.get("next_step") or {}
        if step.get("type") != "diagnostic_question":
            break
        if time.monotonic() > deadline:
            raise TimeoutError("diagnostic did not finish within 180 seconds")
        question = step.get("question") or {}
        content_idx = question.get("id")
        assert isinstance(content_idx, int), question
        answer = "1200" if not diagnostic_answers else str(
            PROBLEMS[content_idx]["answer"]
        )
        page.get_by_label("Твой ответ", exact=True).fill(answer)
        with page.expect_response(
            lambda response: urlsplit(response.url).path
            == "/api/journey/diagnostic/answer",
            timeout=30_000,
        ) as response_info:
            page.locator("form.answer-form button[type=submit]").click()
        assert response_info.value.status == 200, response_info.value.text()
        diagnostic_answers.append(
            {"content_idx": content_idx, "forced_wrong": len(diagnostic_answers) == 0}
        )

    page.get_by_role("button", name="Показать мой маршрут", exact=True).click()
    page.get_by_role("button", name="Начать первую тему", exact=True).click()
    page.get_by_role("button", name="Начать задачу", exact=True).click()
    wait_workspace(page)
    state = current_state(page)
    marker = task_marker(state)
    assert marker["content_idx"] == 1765, marker
    assert state["next_step"]["photo_required"] is False, state["next_step"]
    return {
        "state": state,
        "diagnostic_answers": diagnostic_answers,
        "account": "fresh synthetic browser registration",
        "credentials": {"phone": phone, "pin": pin},
    }


def grant_photo_consent(page: Page) -> dict[str, Any]:
    state = current_state(page)
    if not state["next_step"].get("photo_consent_required"):
        return {"required": False, "status": "already_granted"}
    page.get_by_role("button", name="Позвать взрослого", exact=True).click()
    page.get_by_role(
        "heading", name="Разрешение на проверку фото", exact=True
    ).wait_for(timeout=15_000)
    page.get_by_role("checkbox").check()
    with page.expect_response(
        lambda response: urlsplit(response.url).path == "/api/trainer/consent",
        timeout=15_000,
    ) as response_info:
        page.get_by_role(
            "button", name="Разрешить проверку фото", exact=True
        ).click()
    response = response_info.value
    assert response.status == 200, response.text()
    page.get_by_label("Фото всего решения", exact=True).wait_for(
        state="attached", timeout=15_000
    )
    assert not current_state(page)["next_step"].get("photo_consent_required")
    return {"required": True, "status": response.status}


def exercise_tutor(page: Page) -> dict[str, Any]:
    page.get_by_role("button", name="Спросить AI-помощника", exact=True).click()
    field = page.get_by_label("Твой вопрос", exact=True)
    field.fill("Я не знаю, с чего начать. Задай мне первый вопрос.")
    started = time.perf_counter()
    with page.expect_response(
        lambda response: urlsplit(response.url).path.endswith("/tutor/chat"),
        timeout=180_000,
    ) as response_info:
        page.get_by_role("button", name="Отправить вопрос", exact=True).click()
    response = response_info.value
    assert response.status == 200, response.text()
    payload = response.json()
    reply = str(payload.get("reply") or "").strip()
    assert reply, payload
    page.locator(".learning-tutor__history").get_by_text(
        reply, exact=True
    ).wait_for(timeout=30_000)
    page.get_by_role("button", name="Закрыть помощника", exact=True).click()
    return {
        "status": response.status,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "reply_chars": len(reply),
        "reply": reply,
    }


def geometry(
    page: Page,
    width: int,
    height: int,
    label: str,
    output_dir: Path,
    *,
    mode_switch_name: str | None = None,
    field_label: str | None = None,
) -> dict[str, Any]:
    page.set_viewport_size({"width": width, "height": height})
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(150)
    metrics = page.evaluate(
        """() => ({
          inner_width: window.innerWidth,
          inner_height: window.innerHeight,
          scroll_width: document.documentElement.scrollWidth,
          horizontal_overflow: document.documentElement.scrollWidth - window.innerWidth,
        })"""
    )
    primary = page.locator("button[data-primary-action]").bounding_box()
    screenshot = output_dir / f"{label}.png"
    page.screenshot(path=str(screenshot), full_page=False)
    assert primary, f"{label}: primary action is missing"
    assert metrics["horizontal_overflow"] <= 0, metrics
    assert primary["y"] >= 0, f"{label}: primary action starts above viewport: {primary}"
    assert primary["y"] + primary["height"] <= height, (
        f"{label}: primary action ends below viewport: {primary}"
    )

    mode_switch = None
    if mode_switch_name:
        mode_switch = page.get_by_role(
            "button", name=mode_switch_name, exact=True
        ).bounding_box()
        assert mode_switch, f"{label}: response-mode switch is missing"
        assert mode_switch["y"] >= 0, (
            f"{label}: response-mode switch starts above viewport: {mode_switch}"
        )
        assert mode_switch["y"] + mode_switch["height"] <= height, (
            f"{label}: response-mode switch ends below viewport: {mode_switch}"
        )

    field = None
    if field_label:
        field = page.get_by_label(field_label, exact=True).bounding_box()
        assert field, f"{label}: answer field is missing"
        assert field["y"] >= 0, f"{label}: answer field starts above viewport: {field}"
        assert field["y"] + field["height"] <= height, (
            f"{label}: answer field ends below viewport: {field}"
        )

    return {
        "label": label,
        "viewport": [width, height],
        "primary": primary,
        "mode_switch": mode_switch,
        "field": field,
        "screenshot": str(screenshot),
        **metrics,
    }


def upload_photo(page: Page, path: Path, output_dir: Path, label: str) -> dict[str, Any]:
    photo_input = page.get_by_label("Фото всего решения", exact=True)
    photo_input.wait_for(state="attached", timeout=30_000)
    photo_input.evaluate(
        """element => element.addEventListener('change', event => {
          const file = event.target.files && event.target.files[0];
          window.__kodiSelectedPhoto = file ? {
            name: file.name, type: file.type, size: file.size,
          } : null;
        }, {once: true})"""
    )
    photo_input.set_input_files(str(path))
    page.get_by_text(path.name, exact=True).first.wait_for(timeout=30_000)
    selected = page.evaluate("window.__kodiSelectedPhoto")
    started = time.perf_counter()
    with page.expect_response(
        lambda response: urlsplit(response.url).path == "/api/journey/photo",
        timeout=180_000,
    ) as response_info:
        page.get_by_role("button", name="Отправить решение", exact=True).click()
    response: Response = response_info.value
    payload = response.json()
    assert response.status == 200, payload
    assert isinstance(payload, dict), payload
    step = payload.get("next_step") or {}
    stage = step.get("type")
    assert stage in {
        "photo_feedback", "transfer_feedback", "photo_recovery"
    }, payload
    page.locator(f'.learning-workspace[data-stage="{stage}"]').wait_for(
        timeout=30_000
    )
    screenshot = output_dir / f"{label}.png"
    page.screenshot(path=str(screenshot), full_page=False)
    return {
        "file": str(path),
        "selected_file": selected,
        "status": response.status,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "stage": stage,
        "verdict": step.get("verdict"),
        "reason": step.get("reason"),
        "problem": task_marker(payload),
        "screenshot": str(screenshot),
    }


def return_to_task_after_photo(page: Page, state: dict[str, Any]) -> dict[str, Any]:
    step = state["next_step"]
    assert step["type"] in {
        "photo_feedback", "transfer_feedback", "photo_recovery"
    }, step
    page.locator("button[data-primary-action]").click()
    page.locator(
        '.learning-workspace[data-stage="independent_task"], '
        '.learning-workspace[data-stage="transfer_task"]'
    ).wait_for(timeout=30_000)
    return current_state(page)


def make_jpeg(source: Path, target: Path) -> None:
    with Image.open(source) as image:
        image.convert("RGB").save(target, format="JPEG", quality=94)


def run(args: argparse.Namespace) -> dict[str, Any]:
    base_url = args.base_url.rstrip("/")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "status": "RUNNING",
        "base_url": base_url,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "console_errors": [],
        "page_errors": [],
        "request_failures": [],
        "http_errors": [],
        "geometry": [],
    }
    try:
        with sync_playwright() as playwright:
            browser = getattr(
                playwright, getattr(args, "browser_name", "chromium")
            ).launch(headless=True)
            context = browser.new_context(
                viewport={"width": 375, "height": 844},
                is_mobile=True,
                has_touch=True,
                reduced_motion="reduce",
                service_workers="block",
            )
            page = context.new_page()
            page.set_default_timeout(30_000)
            page.on(
                "console",
                lambda message: result["console_errors"].append(message.text)
                if message.type == "error"
                else None,
            )
            page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            page.on(
                "requestfailed",
                lambda request: result["request_failures"].append(
                    f"{request.method} {request.url}: {request.failure}"
                ),
            )
            page.on(
                "response",
                lambda response: result["http_errors"].append(
                    f"{response.status} {response.url}"
                )
                if response.status >= 400
                else None,
            )

            provisioning = register_and_reach_pc06_task(page, base_url)
            result["provisioning"] = {
                "account": provisioning["account"],
                "diagnostic_answers": provisioning["diagnostic_answers"],
                "initial_task": task_marker(provisioning["state"]),
            }
            result["consent"] = grant_photo_consent(page)
            result["tutor"] = exercise_tutor(page)
            result["geometry"].append(geometry(
                page,
                375,
                844,
                "task-375x844",
                output_dir,
                mode_switch_name="Ввести ответ",
            ))
            result["geometry"].append(geometry(
                page,
                390,
                844,
                "task-390x844",
                output_dir,
                mode_switch_name="Ввести ответ",
            ))
            result["geometry"].append(geometry(
                page,
                844,
                375,
                "task-844x375",
                output_dir,
                mode_switch_name="Ввести ответ",
            ))
            result["geometry"].append(geometry(
                page,
                1280,
                900,
                "task-1280x900",
                output_dir,
                mode_switch_name="Ввести ответ",
            ))
            page.get_by_role("button", name="Ввести ответ", exact=True).click()
            page.get_by_label("Короткий ответ", exact=True).wait_for(state="visible")
            result["geometry"].append(geometry(
                page,
                844,
                375,
                "typed-task-844x375",
                output_dir,
                mode_switch_name="Отправить фото",
                field_label="Короткий ответ",
            ))
            page.get_by_role("button", name="Отправить фото", exact=True).click()
            page.get_by_role("button", name="Ввести ответ", exact=True).wait_for(
                state="visible"
            )
            page.set_viewport_size({"width": 375, "height": 844})

            heic = upload_photo(page, args.heic.resolve(), output_dir, "real-heic")
            result["heic"] = heic
            after_heic = current_state(page)
            assert after_heic["next_step"]["type"] == heic["stage"]
            task_state = return_to_task_after_photo(page, after_heic)
            content_idx = task_marker(task_state)["content_idx"]
            if content_idx == 1765:
                png_fixture = FIXTURE_DIR / "full-solution-correct.png"
            elif content_idx == 331:
                png_fixture = FIXTURE_DIR / "transfer-solution-correct.png"
            else:
                raise AssertionError(f"unexpected task after HEIC: {task_marker(task_state)}")
            jpeg_fixture = output_dir / f"content-{content_idx}-correct.jpeg"
            make_jpeg(png_fixture, jpeg_fixture)
            jpeg = upload_photo(page, jpeg_fixture, output_dir, "known-correct-jpeg")
            result["jpeg"] = jpeg
            assert jpeg["verdict"] == "correct", jpeg
            assert jpeg["stage"] in {"photo_feedback", "transfer_feedback"}, jpeg
            result["geometry"].append(geometry(
                page, 375, 844, "feedback-375x844", output_dir
            ))
            result["geometry"].append(geometry(
                page, 390, 844, "feedback-390x844", output_dir
            ))
            result["geometry"].append(geometry(
                page, 932, 430, "feedback-932x430", output_dir
            ))
            result["geometry"].append(geometry(
                page, 1280, 900, "feedback-1280x900", output_dir
            ))
            result["status"] = "PASS"
            context.close()
            browser.close()
    except Exception as error:
        result["status"] = "FAIL"
        result["failure"] = {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
        }
    finally:
        result["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        target = output_dir / "public-photo-cjm-summary.json"
        target.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if result["status"] != "PASS":
        raise SystemExit(1)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default="https://awesome-seas-gba-expanded.trycloudflare.com",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--heic", type=Path, required=True)
    parser.add_argument(
        "--browser", dest="browser_name", choices=("chromium", "webkit"),
        default="chromium",
    )
    args = parser.parse_args()
    summary = run(args)
    print(json.dumps({
        "status": summary["status"],
        "heic": summary["heic"],
        "jpeg": summary["jpeg"],
        "tutor": summary["tutor"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
