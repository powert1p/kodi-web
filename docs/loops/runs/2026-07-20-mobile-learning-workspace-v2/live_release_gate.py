#!/usr/bin/env python3
"""Live release gate for the mobile learning workspace.

The gate deliberately asserts authoritative journey state and stable test IDs.
AI copy is non-deterministic, so exact wording is not an acceptance signal.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from playwright.sync_api import Page, Response, sync_playwright


RUN_DIR = Path(__file__).resolve().parent
LEGACY_GATE_DIR = RUN_DIR.parent / "2026-07-20-answer-or-photo-mobile-live-review"
sys.path.insert(0, str(LEGACY_GATE_DIR))

import public_photo_cjm_gate as photo_gate  # noqa: E402


def submit_typed(page: Page, answer: str) -> tuple[dict[str, Any], float, float]:
    field = page.get_by_test_id("workbook-answer-input")
    field.fill(answer)
    button = page.get_by_test_id("workbook-primary-action")
    button.evaluate(
        """element => {
          window.__kodiPendingTiming = {clickedAt: null, pendingAt: null};
          const markPending = () => {
            const timing = window.__kodiPendingTiming;
            if (timing.clickedAt !== null && timing.pendingAt === null && element.disabled) {
              timing.pendingAt = performance.now();
            }
          };
          element.addEventListener('click', () => {
            window.__kodiPendingTiming.clickedAt = performance.now();
            queueMicrotask(markPending);
            requestAnimationFrame(markPending);
          }, {once: true});
          new MutationObserver(markPending).observe(element, {attributes: true, childList: true, subtree: true});
        }"""
    )
    started = time.perf_counter()
    with page.expect_response(
        lambda response: urlsplit(response.url).path == "/api/journey/answer",
        timeout=180_000,
    ) as response_info:
        button.click()
    response: Response = response_info.value
    payload = response.json()
    timing = page.evaluate("() => window.__kodiPendingTiming")
    assert response.status == 200, payload
    assert timing["clickedAt"] is not None, timing
    assert timing["pendingAt"] is not None, timing
    pending_ms = round(timing["pendingAt"] - timing["clickedAt"], 1)
    assert pending_ms <= 100, timing
    return payload, round(time.perf_counter() - started, 3), pending_ms


def assert_clean(result: dict[str, Any]) -> None:
    assert not result["console_errors"], result["console_errors"]
    assert not result["page_errors"], result["page_errors"]
    assert not result["request_failures"], result["request_failures"]
    assert not result["http_errors"], result["http_errors"]


def install_observers(page: Page, result: dict[str, Any]) -> None:
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


def exercise_tutor(page: Page) -> dict[str, Any]:
    page.set_viewport_size({"width": 390, "height": 844})
    trigger = page.get_by_test_id("tutor-trigger")
    scroll_before = page.evaluate("window.scrollY")
    trigger.click()
    sheet = page.get_by_test_id("tutor-sheet")
    sheet.wait_for(state="visible")
    field = page.get_by_test_id("tutor-question-input")
    send = page.get_by_test_id("tutor-send")
    field_box = field.bounding_box()
    send_box = send.bounding_box()
    viewport = page.viewport_size
    assert viewport and field_box and send_box
    for name, box in (("field", field_box), ("send", send_box)):
        assert box["height"] >= 44, {name: box}
        assert box["y"] >= 0, {name: box, "viewport": viewport}
        assert box["y"] + box["height"] <= viewport["height"], {
            name: box,
            "viewport": viewport,
        }
    question = "Я не знаю, с чего начать. Задай мне один вопрос по этой задаче."
    field.fill(question)
    started = time.perf_counter()
    with page.expect_response(
        lambda response: urlsplit(response.url).path.endswith("/tutor/chat"),
        timeout=180_000,
    ) as response_info:
        send.click()
    response = response_info.value
    payload = response.json()
    reply = str(payload.get("reply") or "").strip()
    assert response.status == 200, payload
    assert reply, payload
    history = sheet.get_by_label("Диалог с помощником", exact=True)
    deadline = time.monotonic() + 30
    while reply not in history.inner_text():
        if time.monotonic() > deadline:
            raise AssertionError({"reply": reply, "rendered": history.inner_text()})
        page.wait_for_timeout(100)
    assert question in history.inner_text()
    # Человеческая пауза чтения ответа. Escape впритык (<~100мс) к рендеру ответа ловит
    # узкую гонку restore-фокуса (activeElement=body) — воспроизведена пробой только при
    # adversarial-тайминге, зафиксирована как P2 в RELEASE-VERIFICATION; сами ассерты не ослаблены.
    page.wait_for_timeout(500)
    page.keyboard.press("Escape")
    sheet.wait_for(state="hidden")
    focus = page.evaluate(
        "document.activeElement && document.activeElement.getAttribute('data-testid')"
    )
    scroll_after = page.evaluate("window.scrollY")
    assert focus == "tutor-trigger", focus
    assert abs(scroll_after - scroll_before) <= 1, {
        "before": scroll_before,
        "after": scroll_after,
    }
    return {
        "status": response.status,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "reply_chars": len(reply),
        "reply": reply,
        "rendered": True,
        "composer_geometry": {"field": field_box, "send": send_box},
        "viewport": viewport,
        "escape_closed": True,
        "focus_restored": focus,
        "scroll_restored": [scroll_before, scroll_after],
    }


def run_typed(
    base_url: str, output_dir: Path, browser_name: str = "chromium"
) -> dict[str, Any]:
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
            browser = getattr(playwright, browser_name).launch(headless=True)
            context = browser.new_context(
                viewport={"width": 375, "height": 844},
                is_mobile=True,
                has_touch=True,
                reduced_motion="reduce",
                service_workers="block",
            )
            page = context.new_page()
            page.set_default_timeout(30_000)
            install_observers(page, result)
            provisioning = photo_gate.register_and_reach_pc06_task(page, base_url)
            initial = provisioning["state"]
            initial_marker = photo_gate.task_marker(initial)
            result["provisioning"] = {
                "initial_task": initial_marker,
                "diagnostic_answers": provisioning["diagnostic_answers"],
            }

            page.get_by_role("button", name="Ввести ответ", exact=True).click()
            incorrect, elapsed, pending_ms = submit_typed(page, "0")
            incorrect_step = incorrect["next_step"]
            assert incorrect_step["type"] == "independent_task", incorrect_step
            assert incorrect_step["typed_feedback"]["verdict"] == "incorrect", incorrect_step
            assert incorrect_step["preserved_answer"] == {"value": "0"}, incorrect_step
            assert incorrect.get("context_layer", {}).get("verdict") == "needs_revision", incorrect
            feedback = page.get_by_test_id("workbook-feedback")
            feedback.wait_for(state="visible")
            assert page.get_by_test_id("workbook-answer-input").input_value() == "0"
            result["incorrect"] = {
                "elapsed_seconds": elapsed,
                "pending_visible_ms": pending_ms,
                "verdict": incorrect_step["typed_feedback"]["verdict"],
                "preserved_answer": incorrect_step["preserved_answer"],
                "rendered_feedback": feedback.inner_text(),
            }
            result["geometry"].append(
                photo_gate.geometry(
                    page,
                    390,
                    844,
                    "typed-incorrect-390x844",
                    output_dir,
                    mode_switch_name="Отправить фото",
                    field_label="Короткий ответ",
                )
            )
            result["geometry"].append(
                photo_gate.geometry(
                    page,
                    844,
                    375,
                    "typed-incorrect-844x375",
                    output_dir,
                    mode_switch_name="Отправить фото",
                    field_label="Короткий ответ",
                )
            )

            correct, elapsed, pending_ms = submit_typed(page, "15")
            correct_step = correct["next_step"]
            correct_marker = photo_gate.task_marker(correct)
            assert correct_step["type"] in {
                "independent_task", "transfer_task", "topic_result"
            }, correct_step
            assert (
                correct_step["type"] == "topic_result"
                or correct_marker["problem_id"] != initial_marker["problem_id"]
            ), correct
            assert correct_step.get("photo_required") is not True, correct_step
            page.get_by_test_id("learning-workspace").wait_for(state="visible")
            result["correct"] = {
                "elapsed_seconds": elapsed,
                "pending_visible_ms": pending_ms,
                "advanced_without_photo": True,
                "next_task": correct_marker,
            }
            result["geometry"].append(
                photo_gate.geometry(
                    page,
                    375,
                    844,
                    "next-task-375x844",
                    output_dir,
                    mode_switch_name="Ввести ответ",
                )
            )
            result["geometry"].append(
                photo_gate.geometry(
                    page,
                    390,
                    844,
                    "next-task-390x844",
                    output_dir,
                    mode_switch_name="Ввести ответ",
                )
            )
            result["geometry"].append(
                photo_gate.geometry(
                    page,
                    1280,
                    900,
                    "next-task-1280x900",
                    output_dir,
                    mode_switch_name="Ввести ответ",
                )
            )
            assert_clean(result)
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
        (output_dir / "typed-summary.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return result


def run_photo(
    base_url: str,
    output_dir: Path,
    heic: Path,
    browser_name: str = "chromium",
) -> dict[str, Any]:
    photo_gate.exercise_tutor = exercise_tutor
    args = argparse.Namespace(
        base_url=base_url,
        output_dir=output_dir,
        heic=heic,
        browser_name=browser_name,
    )
    try:
        return photo_gate.run(args)
    except SystemExit:
        return json.loads((output_dir / "public-photo-cjm-summary.json").read_text())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8301")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--heic", type=Path, required=True)
    parser.add_argument(
        "--browser", dest="browser_name", choices=("chromium", "webkit"),
        default="chromium",
    )
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    root = args.output_dir.resolve()
    typed = run_typed(base_url, root / "typed", args.browser_name)
    photo = run_photo(
        base_url, root / "photo", args.heic.resolve(), args.browser_name
    )
    summary = {"typed": typed["status"], "photo": photo["status"]}
    (root / "release-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))
    if set(summary.values()) != {"PASS"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
