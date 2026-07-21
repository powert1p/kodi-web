#!/usr/bin/env python3
"""Prove that a saved photo survives a provider outage and retries in place."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
from typing import Any
from urllib.parse import urlsplit

from playwright.sync_api import Browser, Page, Response, sync_playwright

from capture_runtime_gate import DEFAULT_CHROME, RuntimeGate


def _context(browser: Browser, *, mobile: bool):
    return browser.new_context(
        viewport={"width": 375, "height": 844} if mobile else {"width": 1280, "height": 900},
        has_touch=mobile,
        is_mobile=mobile,
        service_workers="block",
    )


def _wait_for_heading(page: Page, text: str) -> None:
    page.locator(".journey-main h1", has_text=text).wait_for(timeout=90_000)
    page.wait_for_timeout(500)


def _response_record(response: Response, started: float) -> dict[str, Any]:
    return {
        "method": response.request.method,
        "path": urlsplit(response.url).path,
        "status": response.status,
        "elapsedMs": round((time.monotonic() - started) * 1000),
    }


def _assert_saved_recovery(page: Page, fixture_name: str) -> None:
    _wait_for_heading(page, "Проверка на паузе")
    page.get_by_role("button", name="Повторить проверку", exact=True).wait_for()
    page.get_by_text("Фото сохранено", exact=True).wait_for()
    page.get_by_text(fixture_name, exact=True).wait_for()
    assert page.get_by_label("Фото всего решения").count() == 0


def _login_page(
    browser: Browser,
    gate: RuntimeGate,
    *,
    base_url: str,
    phone: str,
    pin: str,
    mobile: bool,
) -> tuple[Any, Page]:
    context = _context(browser, mobile=mobile)
    page = context.new_page()
    gate.attach(page)
    gate.login(page, base_url, phone, pin)
    return context, page


def run_error_phase(
    browser: Browser,
    gate: RuntimeGate,
    *,
    base_url: str,
    phone: str,
    pin: str,
    fixture: Path,
) -> dict[str, Any]:
    context, page = _login_page(
        browser,
        gate,
        base_url=base_url,
        phone=phone,
        pin=pin,
        mobile=True,
    )
    for action in ("Решить ещё одну задачу", "Исправить решение", "Переснять фото"):
        button = page.get_by_role("button", name=action, exact=True)
        if button.count() and button.is_visible():
            button.click()
            break
    page.get_by_label("Фото всего решения").wait_for(state="attached", timeout=20_000)
    task = gate.checkpoint(page, "provider-outage-task-mobile")
    page.get_by_label("Фото всего решения").set_input_files(str(fixture))
    page.get_by_role("button", name="Отправить решение", exact=True).wait_for()
    page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
    page.wait_for_timeout(100)
    started = time.monotonic()
    with page.expect_response(
        lambda candidate: urlsplit(candidate.url).path == "/api/journey/photo",
        timeout=90_000,
    ) as response_info:
        page.get_by_role("button", name="Отправить решение", exact=True).click()
    response = response_info.value
    response.finished()
    photo_response = _response_record(response, started)
    assert photo_response["status"] == 503, photo_response
    payload = response.json()
    assert payload["detail"]["code"] == "ai_unavailable", payload
    assert payload["detail"]["state"]["next_step"]["reason"] == "provider_error", payload

    _assert_saved_recovery(page, fixture.name)
    recovery = gate.checkpoint(page, "provider-outage-recovery-mobile")
    page.reload(wait_until="networkidle")
    _assert_saved_recovery(page, fixture.name)
    reloaded = gate.checkpoint(page, "provider-outage-reload-mobile")
    assert recovery["heading"] == reloaded["heading"] == "Проверка на паузе"
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(750)
    context.close()

    desktop_context, desktop_page = _login_page(
        browser,
        gate,
        base_url=base_url,
        phone=phone,
        pin=pin,
        mobile=False,
    )
    _assert_saved_recovery(desktop_page, fixture.name)
    desktop = gate.checkpoint(desktop_page, "provider-outage-recovery-desktop")
    assets = gate.build_assets(desktop_page)
    interaction = gate.keyboard_and_motion(desktop_page)
    desktop_page.wait_for_load_state("networkidle")
    desktop_page.wait_for_timeout(750)
    desktop_context.close()

    expected_error = "POST /api/journey/photo -> 503"
    assert gate.api_errors == [expected_error], gate.api_errors
    assert not gate.console_errors, gate.console_errors
    assert not gate.page_errors, gate.page_errors
    assert not gate.request_errors, gate.request_errors
    return {
        "verdict": "PASS",
        "phase": "provider-error",
        "photoResponse": photo_response,
        "expectedApiErrors": [expected_error],
        "screens": [task, recovery, reloaded, desktop],
        "assets": assets,
        "interaction": interaction,
    }


def run_recovery_phase(
    browser: Browser,
    gate: RuntimeGate,
    *,
    base_url: str,
    phone: str,
    pin: str,
    fixture: Path,
) -> dict[str, Any]:
    context, page = _login_page(
        browser,
        gate,
        base_url=base_url,
        phone=phone,
        pin=pin,
        mobile=True,
    )
    _assert_saved_recovery(page, fixture.name)
    before = gate.checkpoint(page, "saved-photo-before-retry-mobile")
    started = time.monotonic()
    with page.expect_response(
        lambda candidate: urlsplit(candidate.url).path == "/api/journey/photo/retry",
        timeout=90_000,
    ) as response_info:
        page.get_by_role("button", name="Повторить проверку", exact=True).click()
    response = response_info.value
    response.finished()
    retry_response = _response_record(response, started)
    assert retry_response["status"] == 200, retry_response
    payload = response.json()
    assert payload["next_step"]["type"] in {"photo_feedback", "transfer_feedback"}, payload
    assert payload["next_step"]["verdict"] == "correct", payload

    _wait_for_heading(page, "Ход решения сошёлся")
    assert page.get_by_label("Фото всего решения").count() == 0
    feedback = gate.checkpoint(page, "saved-photo-retry-success-mobile")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(750)
    context.close()

    desktop_context, desktop_page = _login_page(
        browser,
        gate,
        base_url=base_url,
        phone=phone,
        pin=pin,
        mobile=False,
    )
    _wait_for_heading(desktop_page, "Ход решения сошёлся")
    desktop = gate.checkpoint(desktop_page, "saved-photo-retry-success-desktop")
    assets = gate.build_assets(desktop_page)
    interaction = gate.keyboard_and_motion(desktop_page)
    desktop_page.wait_for_load_state("networkidle")
    desktop_page.wait_for_timeout(750)
    desktop_context.close()

    gate.assert_clean()
    return {
        "verdict": "PASS",
        "phase": "provider-recovery",
        "retryResponse": retry_response,
        "retryUsedSavedPhoto": True,
        "screens": [before, feedback, desktop],
        "assets": assets,
        "interaction": interaction,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("error", "recover"))
    parser.add_argument("--base-url", default="http://127.0.0.1:8414")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument(
        "--chrome",
        type=Path,
        default=DEFAULT_CHROME if DEFAULT_CHROME.exists() else None,
    )
    args = parser.parse_args()
    phone = os.environ.get("KODI_TEST_PHONE")
    pin = os.environ.get("KODI_TEST_PIN")
    if not phone or not pin:
        raise SystemExit("KODI_TEST_PHONE and KODI_TEST_PIN are required")
    fixture = args.fixture.resolve()
    assert fixture.is_file(), fixture

    output_dir = args.output_dir.resolve()
    gate = RuntimeGate(output_dir)
    base_url = args.base_url.rstrip("/")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=str(args.chrome) if args.chrome else None,
        )
        if args.phase == "error":
            result = run_error_phase(
                browser,
                gate,
                base_url=base_url,
                phone=phone,
                pin=pin,
                fixture=fixture,
            )
        else:
            result = run_recovery_phase(
                browser,
                gate,
                base_url=base_url,
                phone=phone,
                pin=pin,
                fixture=fixture,
            )
        browser.close()

    summary = {
        **result,
        "baseOrigin": f"{urlsplit(base_url).scheme}://{urlsplit(base_url).netloc}",
        "fixture": fixture.name,
        "consoleErrors": gate.console_errors,
        "pageErrors": gate.page_errors,
        "requestErrors": gate.request_errors,
        "apiErrors": gate.api_errors,
    }
    target = output_dir / f"provider-{args.phase}-summary.json"
    target.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
