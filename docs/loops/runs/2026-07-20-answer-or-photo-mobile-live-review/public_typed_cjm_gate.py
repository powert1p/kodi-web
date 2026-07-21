#!/usr/bin/env python3
"""Public browser gate for AI-graded typed answers without mandatory photo proof."""

from __future__ import annotations

import argparse
import json
import time
import traceback
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from playwright.sync_api import Page, Response, sync_playwright

from public_photo_cjm_gate import (
    current_state,
    geometry,
    register_and_reach_pc06_task,
    task_marker,
)


def submit_typed(
    page: Page, answer: str
) -> tuple[dict[str, Any], float, float]:
    field = page.get_by_label("Короткий ответ", exact=True)
    field.fill(answer)
    button = page.get_by_role("button", name="Проверить ответ", exact=True)
    button.evaluate(
        """element => {
            window.__kodiPendingTiming = {clickedAt: null, pendingAt: null};
            const markPending = () => {
                const timing = window.__kodiPendingTiming;
                if (
                    timing.clickedAt !== null &&
                    timing.pendingAt === null &&
                    (element.disabled || element.textContent.includes("Проверяем"))
                ) {
                    timing.pendingAt = performance.now();
                }
            };
            element.addEventListener("click", () => {
                window.__kodiPendingTiming.clickedAt = performance.now();
                queueMicrotask(markPending);
                requestAnimationFrame(markPending);
            }, {once: true});
            new MutationObserver(markPending).observe(element, {
                attributes: true,
                childList: true,
                subtree: true,
                characterData: true,
            });
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
    pending_timing = page.evaluate("() => window.__kodiPendingTiming")
    assert pending_timing["clickedAt"] is not None, pending_timing
    assert pending_timing["pendingAt"] is not None, pending_timing
    pending_ms = round(
        pending_timing["pendingAt"] - pending_timing["clickedAt"], 1
    )
    assert pending_ms <= 100, pending_timing
    assert response.status == 200, payload
    assert isinstance(payload, dict), payload
    return payload, round(time.perf_counter() - started, 3), pending_ms


def compact_typed_result(
    payload: dict[str, Any],
    answer: str,
    elapsed_seconds: float,
    pending_ms: float,
) -> dict[str, Any]:
    step = payload.get("next_step") or {}
    return {
        "answer": answer,
        "status": 200,
        "elapsed_seconds": elapsed_seconds,
        "pending_visible_ms": pending_ms,
        "task": task_marker(payload),
        "photo_required": step.get("photo_required"),
        "typed_feedback": step.get("typed_feedback"),
        "preserved_answer": step.get("preserved_answer"),
    }


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
            browser = playwright.chromium.launch(headless=True)
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
            initial = provisioning["state"]
            result["provisioning"] = {
                "account": provisioning["account"],
                "diagnostic_answers": provisioning["diagnostic_answers"],
                "initial_task": task_marker(initial),
                "photo_consent_required": initial["next_step"].get(
                    "photo_consent_required"
                ),
            }

            page.set_viewport_size({"width": 844, "height": 375})
            page.get_by_role("button", name="Ввести ответ", exact=True).click()
            typed_field = page.get_by_label("Короткий ответ", exact=True)
            typed_field.wait_for(state="visible")

            incorrect_payload, incorrect_elapsed, incorrect_pending_ms = submit_typed(
                page, "0"
            )
            incorrect_step = incorrect_payload["next_step"]
            assert incorrect_step["type"] == "independent_task", incorrect_step
            assert task_marker(incorrect_payload)["problem_id"] == task_marker(initial)[
                "problem_id"
            ]
            assert incorrect_step["typed_feedback"]["verdict"] == "incorrect", (
                incorrect_step
            )
            assert incorrect_step["preserved_answer"] == {"value": "0"}, incorrect_step
            page.get_by_text("Проверь вычисления", exact=True).wait_for(
                state="visible", timeout=30_000
            )
            page.get_by_test_id("response-dock").get_by_text(
                "Проверь вычисления и попробуй ещё раз. Исправь ответ или отправь фото.",
                exact=True,
            ).wait_for(state="visible")
            assert typed_field.input_value() == "0"
            assert page.get_by_role(
                "button", name="Отправить фото", exact=True
            ).is_visible()
            assert page.get_by_role(
                "button", name="Не знаю, как начать", exact=True
            ).is_visible()
            result["incorrect"] = compact_typed_result(
                incorrect_payload,
                "0",
                incorrect_elapsed,
                incorrect_pending_ms,
            )
            result["geometry"].append(
                geometry(
                    page,
                    844,
                    375,
                    "typed-incorrect-844x375",
                    output_dir,
                    mode_switch_name="Отправить фото",
                    field_label="Короткий ответ",
                )
            )

            correct_payload, correct_elapsed, correct_pending_ms = submit_typed(
                page, "15"
            )
            correct_step = correct_payload["next_step"]
            assert correct_step["type"] == "transfer_task", correct_step
            assert correct_step["photo_required"] is False, correct_step
            assert task_marker(correct_payload)["problem_id"] != task_marker(initial)[
                "problem_id"
            ]
            heading = page.get_by_role(
                "heading", name="Проверка переноса", exact=True
            )
            heading.wait_for(state="visible", timeout=30_000)
            page.wait_for_timeout(100)
            result["correct"] = {
                **compact_typed_result(
                    correct_payload,
                    "15",
                    correct_elapsed,
                    correct_pending_ms,
                ),
                "heading_focused": heading.evaluate(
                    "element => document.activeElement === element"
                ),
                "advanced_without_photo": True,
            }
            result["geometry"].append(
                geometry(
                    page,
                    844,
                    375,
                    "next-task-844x375",
                    output_dir,
                    mode_switch_name="Ввести ответ",
                )
            )
            result["geometry"].append(
                geometry(
                    page,
                    375,
                    844,
                    "next-task-375x844",
                    output_dir,
                    mode_switch_name="Ввести ответ",
                )
            )

            assert not result["console_errors"], result["console_errors"]
            assert not result["page_errors"], result["page_errors"]
            assert not result["request_failures"], result["request_failures"]
            assert not result["http_errors"], result["http_errors"]
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
        target = output_dir / "public-typed-cjm-summary.json"
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
    args = parser.parse_args()
    summary = run(args)
    print(
        json.dumps(
            {
                "status": summary["status"],
                "incorrect": summary["incorrect"],
                "correct": summary["correct"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
