#!/usr/bin/env python3
"""Complete the final independent evidence task through the real photo UI."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
from typing import Any
from urllib.parse import urlsplit

from playwright.sync_api import Response, sync_playwright

from capture_runtime_gate import DEFAULT_CHROME, RuntimeGate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8412")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--chrome", type=Path, default=DEFAULT_CHROME if DEFAULT_CHROME.exists() else None)
    args = parser.parse_args()
    phone = os.environ.get("KODI_TEST_PHONE")
    pin = os.environ.get("KODI_TEST_PIN")
    if not phone or not pin:
        raise SystemExit("KODI_TEST_PHONE and KODI_TEST_PIN are required")
    fixture = args.fixture.resolve()
    assert fixture.is_file(), fixture

    gate = RuntimeGate(args.output_dir.resolve())
    responses: list[dict[str, Any]] = []
    base_url = args.base_url.rstrip("/")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=str(args.chrome) if args.chrome else None,
        )
        mobile = browser.new_context(
            viewport={"width": 375, "height": 844},
            has_touch=True,
            is_mobile=True,
            service_workers="block",
        )
        page = mobile.new_page()
        gate.attach(page)

        def on_response(response: Response) -> None:
            if urlsplit(response.url).path != "/api/journey/photo":
                return
            responses.append(
                {
                    "method": response.request.method,
                    "status": response.status,
                    "elapsedMs": round((time.monotonic() - photo_started) * 1000),
                }
            )

        photo_started = time.monotonic()
        page.on("response", on_response)
        gate.login(page, base_url, phone, pin)
        reshoot_button = page.get_by_role("button", name="Переснять фото", exact=True)
        if reshoot_button.is_visible():
            reshoot_button.click()
        correct_button = page.get_by_role("button", name="Исправить решение", exact=True)
        if correct_button.is_visible():
            correct_button.click()
        continue_button = page.get_by_role("button", name="Решить ещё одну задачу", exact=True)
        if continue_button.is_visible():
            continue_button.click()
        page.get_by_label("Фото всего решения").wait_for(state="attached", timeout=20_000)
        page.locator(".problem-statement").wait_for(timeout=20_000)
        task = gate.checkpoint(page, "final-evidence-task-mobile")
        assert "Alumni Sans" in (task["headingFont"] or ""), task

        page.get_by_label("Фото всего решения").set_input_files(str(fixture))
        page.get_by_role("button", name="Отправить решение", exact=True).wait_for()
        page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
        page.wait_for_timeout(100)
        photo_started = time.monotonic()
        page.get_by_role("button", name="Отправить решение", exact=True).click()
        page.wait_for_function(
            """() => [...document.querySelectorAll('button')].some((button) =>
              ['Завершить тему', 'Решить ещё одну задачу', 'Исправить решение', 'Переснять фото', 'Повторить проверку'].includes(button.textContent?.trim() || '')
            )""",
            timeout=90_000,
        )
        finish_button = page.get_by_role("button", name="Завершить тему", exact=True)
        if not finish_button.is_visible():
            heading = page.locator(".journey-main h1").text_content()
            raise AssertionError(f"photo did not reach mastery feedback: {heading}")
        page.get_by_text("3/3", exact=True).wait_for(timeout=5_000)
        assert page.evaluate("window.scrollY") == 0
        mastery = gate.checkpoint(page, "mastery-3-of-3-mobile")
        assert mastery["heading"] == "Ход решения сошёлся", mastery
        assert len(responses) == 1 and responses[0]["status"] == 200, responses

        finish_button.click()
        page.get_by_text("Навык подтверждён", exact=False).first.wait_for(timeout=20_000)
        topic_mobile = gate.checkpoint(page, "topic-result-mobile")
        mobile.close()

        desktop = browser.new_context(
            viewport={"width": 1280, "height": 900},
            service_workers="block",
        )
        desktop_page = desktop.new_page()
        gate.attach(desktop_page)
        gate.login(desktop_page, base_url, phone, pin)
        topic_desktop = gate.checkpoint(desktop_page, "topic-result-desktop")
        assets = gate.build_assets(desktop_page)
        desktop.close()
        browser.close()

    gate.assert_clean()
    summary = {
        "verdict": "PASS",
        "baseOrigin": f"{urlsplit(base_url).scheme}://{urlsplit(base_url).netloc}",
        "photoResponse": responses[0],
        "fixture": fixture.name,
        "screens": [task, mastery, topic_mobile, topic_desktop],
        "assets": assets,
        "consoleErrors": gate.console_errors,
        "pageErrors": gate.page_errors,
        "requestErrors": gate.request_errors,
        "apiErrors": gate.api_errors,
    }
    target = args.output_dir.resolve() / "complete-mastery-summary.json"
    target.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
