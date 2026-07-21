#!/usr/bin/env python3
"""Public mobile-WebKit gate with a real OS on-screen keyboard visible."""

from __future__ import annotations

import argparse
import json
import time
import traceback
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

import sys as _sys
from pathlib import Path as _Path
# v2-копия живёт в соседнем ран-дире — общие функции остаются в legacy-ране.
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent / "2026-07-20-answer-or-photo-mobile-live-review"))
from public_photo_cjm_gate import register_and_reach_pc06_task, task_marker
from public_typed_cjm_gate import compact_typed_result, submit_typed


IPHONE_SAFARI_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 "
    "Mobile/15E148 Safari/604.1"
)


def keyboard_geometry(page: Any, *, view: str) -> dict[str, Any]:
    metrics = page.evaluate(
        """() => {
          const rect = element => {
            const value = element?.getBoundingClientRect();
            return value ? {
              x: value.x, y: value.y, width: value.width, height: value.height,
              right: value.right, bottom: value.bottom,
            } : null;
          };
          // v2-воркспейс: стабильные test-id вместо legacy-классов answer-or-photo.
          const field = document.querySelector('[data-testid="workbook-answer-input"]');
          const feedback = document.querySelector('[data-testid="workbook-feedback"]');
          const primary = document.querySelector('[data-testid="workbook-primary-action"]');
          const modeSwitch = [...document.querySelectorAll('button')]
            .find(element => element.textContent?.trim() === 'Отправить фото');
          const dockNote = document.querySelector('[data-testid="response-dock"] p');
          const viewport = window.visualViewport;
          return {
            inner_width: window.innerWidth,
            inner_height: window.innerHeight,
            visual_viewport: viewport ? {
              width: viewport.width,
              height: viewport.height,
              offset_left: viewport.offsetLeft,
              offset_top: viewport.offsetTop,
              scale: viewport.scale,
            } : null,
            scroll_width: document.documentElement.scrollWidth,
            horizontal_overflow:
              document.documentElement.scrollWidth - window.innerWidth,
            active_element: document.activeElement === field
              ? 'short-answer'
              : document.activeElement?.tagName?.toLowerCase() || null,
            field: rect(field),
            feedback: rect(feedback),
            primary: rect(primary),
            mode_switch: rect(modeSwitch),
            dock_note: rect(dockNote),
            scroll_y: window.scrollY,
            scroll_height: document.documentElement.scrollHeight,
          };
        }"""
    )
    assert metrics["inner_width"] == 844, metrics
    assert metrics["inner_height"] == 375, metrics
    assert metrics["horizontal_overflow"] <= 0, metrics
    assert metrics["active_element"] == "short-answer", metrics
    for name in ("field", "feedback", "primary", "mode_switch", "dock_note"):
        rect = metrics[name]
        assert rect, f"{name} is missing: {metrics}"
    visible_names = (
        ("field", "primary", "mode_switch", "dock_note")
        if view == "input"
        else ("feedback",)
    )
    for name in visible_names:
        rect = metrics[name]
        assert rect["y"] >= 0, f"{view}:{name} starts above viewport: {rect}"
        assert rect["bottom"] <= metrics["inner_height"], (
            f"{view}:{name} ends below viewport: {rect}"
        )
    return metrics


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    ready_marker = output_dir / "READY"
    ready_marker.unlink(missing_ok=True)
    result: dict[str, Any] = {
        "status": "RUNNING",
        "base_url": args.base_url.rstrip("/"),
        "browser": "Playwright WebKit",
        "browser_executable": str(args.browser_executable),
        "viewport": [844, 375],
        "emulation": "iPhone Safari 17.5 user agent + touch/mobile context",
        "os_keyboard": "macOS Accessibility Keyboard enabled and captured externally",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "console_errors": [],
        "page_errors": [],
        "request_failures": [],
        "http_errors": [],
    }
    try:
        with sync_playwright() as playwright:
            browser = playwright.webkit.launch(
                headless=False,
                executable_path=str(args.browser_executable),
            )
            context = browser.new_context(
                viewport={"width": 375, "height": 844},
                screen={"width": 375, "height": 844},
                is_mobile=True,
                has_touch=True,
                user_agent=IPHONE_SAFARI_USER_AGENT,
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

            provisioning = register_and_reach_pc06_task(page, result["base_url"])
            initial = provisioning["state"]
            result["provisioning"] = {
                "account": provisioning["account"],
                "diagnostic_answers": provisioning["diagnostic_answers"],
                "initial_task": task_marker(initial),
            }

            page.set_viewport_size({"width": 844, "height": 375})
            page.get_by_role("button", name="Ввести ответ", exact=True).click()
            field = page.get_by_label("Короткий ответ", exact=True)
            field.wait_for(state="visible")
            payload, elapsed_seconds, pending_ms = submit_typed(page, "0")
            step = payload["next_step"]
            assert step["typed_feedback"]["verdict"] == "incorrect", step
            assert step["preserved_answer"] == {"value": "0"}, step
            page.get_by_text("Проверь вычисления", exact=True).wait_for(
                state="visible", timeout=30_000
            )
            # v2-копия воркспейса: в short-landscape kicker и <small>-подсказка скрыты по дизайну
            # (LearningWorkspace.css ~1200), видимым остаётся <p> с вердикт-сообщением — его и ждём.
            page.get_by_test_id("response-dock").get_by_text(
                "Проверь вычисления и попробуй ещё раз.",
                exact=True,
            ).wait_for(state="visible")
            assert field.input_value() == "0"
            page.wait_for_timeout(500)
            field.scroll_into_view_if_needed()
            field.click()
            page.wait_for_function(
                "element => document.activeElement === element",
                arg=field.element_handle(),
            )

            result["incorrect"] = compact_typed_result(
                payload, "0", elapsed_seconds, pending_ms
            )
            result["geometry"] = {
                "input_view": keyboard_geometry(page, view="input"),
            }
            result["page_screenshots"] = {
                "input_view": str(output_dir / "public-webkit-input-view.png"),
            }
            page.screenshot(
                path=result["page_screenshots"]["input_view"], full_page=False
            )

            assert not result["console_errors"], result["console_errors"]
            assert not result["page_errors"], result["page_errors"]
            assert not result["request_failures"], result["request_failures"]
            assert not result["http_errors"], result["http_errors"]
            result["status"] = "PASS"
            input_marker = output_dir / "READY_INPUT"
            input_marker.write_text("PASS\n", encoding="utf-8")
            print(f"READY_INPUT {input_marker}", flush=True)
            time.sleep(args.stage_hold_seconds)

            page.locator('[data-testid="workbook-feedback"]').evaluate(
                "element => element.scrollIntoView({block: 'center'})"
            )
            page.wait_for_timeout(250)
            result["geometry"]["feedback_view"] = keyboard_geometry(
                page, view="feedback"
            )
            result["page_screenshots"]["feedback_view"] = str(
                output_dir / "public-webkit-feedback-view.png"
            )
            page.screenshot(
                path=result["page_screenshots"]["feedback_view"], full_page=False
            )
            result["ready_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            ready_marker.write_text("PASS\n", encoding="utf-8")
            print(f"READY_FEEDBACK {ready_marker}", flush=True)
            time.sleep(args.stage_hold_seconds)
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
        (output_dir / "public-webkit-keyboard-summary.json").write_text(
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
    parser.add_argument("--browser-executable", type=Path, required=True)
    parser.add_argument("--stage-hold-seconds", type=int, default=15)
    args = parser.parse_args()
    summary = run(args)
    print(
        json.dumps(
            {
                "status": summary["status"],
                "incorrect": summary["incorrect"],
                "geometry": summary["geometry"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
