#!/usr/bin/env python3
"""CJM нового ученика: регистрация должна сразу открыть и сохранить урок."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any
from urllib.parse import urlsplit

from playwright.sync_api import Browser, Locator, Page, Request, Response, sync_playwright


DEFAULT_CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
LEGACY_CACHE_NAMES = {
    "flutter-app-cache",
    "flutter-temp-cache",
    "flutter-app-manifest",
}
PRESERVE_CACHE_NAME = "kodi-e2e-preserve-cache"
SYNTHETIC_LEGACY_FLUTTER_SW = """
const LEGACY_CACHES = [
  'flutter-app-cache',
  'flutter-temp-cache',
  'flutter-app-manifest',
];
self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    await Promise.all(LEGACY_CACHES.map((name) => caches.open(name)));
    await self.skipWaiting();
  })());
});
self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});
self.addEventListener('fetch', () => {});
"""


class Evidence:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.console_errors: list[str] = []
        self.page_errors: list[str] = []
        self.request_errors: list[str] = []
        self.api_errors: list[str] = []
        self.api_statuses: Counter[tuple[str, str, int]] = Counter()
        self.checkpoints: list[str] = []

    def attach(self, page: Page) -> None:
        def on_console(message: Any) -> None:
            if message.type == "error":
                self.console_errors.append(message.text[:300])

        def on_response(response: Response) -> None:
            route = urlsplit(response.url).path
            if not route.startswith("/api/"):
                return
            key = (response.request.method, route, response.status)
            self.api_statuses[key] += 1
            if response.status >= 400:
                self.api_errors.append(f"{key[0]} {key[1]} -> {key[2]}")

        def on_request_failed(request: Request) -> None:
            route = urlsplit(request.url).path
            self.request_errors.append(
                f"{request.method} {route}: {request.failure or 'failed'}"
            )

        page.on("console", on_console)
        page.on("pageerror", lambda error: self.page_errors.append(str(error)[:300]))
        page.on("response", on_response)
        page.on("requestfailed", on_request_failed)

    def checkpoint(self, page: Page, name: str) -> None:
        page.wait_for_timeout(200)
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert overflow <= 1, f"horizontal overflow {overflow}px at {name}"
        viewport = page.viewport_size or {"width": 0, "height": 0}
        page.screenshot(
            path=str(self.output_dir / f"{name}-{viewport['width']}x{viewport['height']}.png"),
            full_page=False,
        )
        self.checkpoints.append(name)

    def assert_clean(self) -> None:
        assert not self.console_errors, f"console errors: {self.console_errors}"
        assert not self.page_errors, f"page errors: {self.page_errors}"
        assert not self.request_errors, f"request failures: {self.request_errors}"
        assert not self.api_errors, f"API errors: {self.api_errors}"


def assert_touch_target(locator: Locator, label: str) -> None:
    box = locator.bounding_box()
    assert box is not None, f"{label} is not visible"
    assert box["width"] >= 44 and box["height"] >= 44, (
        f"{label} is only {box['width']}x{box['height']}"
    )


def assert_focusable(locator: Locator, label: str) -> None:
    locator.focus()
    assert locator.evaluate("element => element === document.activeElement"), (
        f"{label} did not receive keyboard focus"
    )


def assert_has_focus(locator: Locator, label: str) -> None:
    locator.wait_for()
    assert locator.evaluate("element => element === document.activeElement"), (
        f"{label} was not focused by the product"
    )


def fetch_json(page: Page, route: str) -> dict[str, Any]:
    result = page.evaluate(
        """
        async (route) => {
          const response = await fetch(route, {
            headers: {Authorization: `Bearer ${localStorage.getItem('kodi.jwt')}`},
          })
          return {status: response.status, payload: await response.json()}
        }
        """,
        route,
    )
    assert result["status"] == 200, f"GET {route} -> {result['status']}"
    payload = result["payload"]
    assert isinstance(payload, dict)
    return payload


def current_session_id(page: Page) -> int:
    result = page.evaluate(
        """
        async () => {
          const response = await fetch('/api/learning/start', {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${localStorage.getItem('kodi.jwt')}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({lesson_id: 'mixtures-1'}),
          })
          return {status: response.status, payload: await response.json()}
        }
        """
    )
    assert result["status"] == 200, f"POST /api/learning/start -> {result['status']}"
    session_id = result["payload"].get("session_id")
    assert isinstance(session_id, int)
    return session_id


def fill_phone_step(
    page: Page,
    phone: str,
    evidence: Evidence,
    checkpoint: str | None = None,
    verify_loading: bool = False,
) -> None:
    phone_input = page.get_by_label("Номер телефона")
    assert_has_focus(phone_input, "phone input")
    if checkpoint:
        evidence.checkpoint(page, checkpoint)
    phone_input.fill(phone)
    continue_button = page.get_by_role("button", name="Продолжить")
    assert_touch_target(continue_button, "continue button")
    cdp = None
    if verify_loading:
        cdp = page.context.new_cdp_session(page)
        cdp.send("Network.enable")
        cdp.send("Network.emulateNetworkConditions", {
            "offline": False,
            "latency": 700,
            "downloadThroughput": 10 * 1024 * 1024,
            "uploadThroughput": 10 * 1024 * 1024,
        })
    continue_button.click()
    if cdp is not None:
        loading_status = page.get_by_role("status")
        loading_status.wait_for(timeout=2_000)
        loading_button = loading_status.locator("xpath=ancestor::button")
        assert loading_button.is_disabled(), "loading submit must be disabled"
        cdp.send("Network.emulateNetworkConditions", {
            "offline": False,
            "latency": 0,
            "downloadThroughput": 10 * 1024 * 1024,
            "uploadThroughput": 10 * 1024 * 1024,
        })
        cdp.detach()


def assert_recoverable_network_error(
    browser: Browser,
    base_url: str,
    evidence: Evidence,
) -> None:
    context = browser.new_context(
        viewport={"width": 375, "height": 844},
        has_touch=True,
        is_mobile=True,
        reduced_motion="reduce",
        service_workers="allow",
    )
    page = context.new_page()
    page.goto(f"{base_url}/app/login", wait_until="domcontentloaded")
    phone_input = page.get_by_label("Номер телефона")
    assert_has_focus(phone_input, "error-state phone input")
    phone_input.fill("+77060000000")
    context.set_offline(True)
    page.get_by_role("button", name="Продолжить").click()
    alert = page.get_by_role("alert")
    alert.wait_for(timeout=5_000)
    assert alert.get_attribute("aria-live") == "polite"
    assert alert.inner_text() == (
        "Не получилось подключиться. Проверь интернет и попробуй ещё раз."
    )
    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    assert overflow <= 1, f"horizontal overflow {overflow}px at network error"
    page.screenshot(
        path=str(evidence.output_dir / "00-network-error-recovery-375x844.png"),
        full_page=False,
    )
    evidence.checkpoints.append("00-network-error-recovery")
    context.set_offline(False)
    context.close()


def assert_legacy_service_worker_migration(
    browser: Browser,
    base_url: str,
) -> dict[str, Any]:
    context = browser.new_context(service_workers="allow", reduced_motion="reduce")
    synthetic_worker_requests: list[str] = []
    worker_url = f"{base_url}/flutter_service_worker.js"

    def serve_synthetic_legacy_worker(route: Any) -> None:
        assert route.request.service_worker is not None
        synthetic_worker_requests.append(route.request.url)
        route.fulfill(
            status=200,
            headers={
                "Content-Type": "application/javascript",
                "Service-Worker-Allowed": "/",
                "Cache-Control": "no-store",
            },
            body=SYNTHETIC_LEGACY_FLUTTER_SW,
        )

    context.route(worker_url, serve_synthetic_legacy_worker, times=1)
    page = context.new_page()
    page.goto(f"{base_url}/health", wait_until="domcontentloaded")
    before = page.evaluate(
        """async (preserveCache) => {
          const registration = await navigator.serviceWorker.register(
            '/flutter_service_worker.js',
            {scope: '/'},
          )
          const worker = registration.installing ?? registration.waiting ?? registration.active
          if (!worker) throw new Error('legacy worker was not created')

          if (worker.state !== 'activated') {
            await new Promise((resolve, reject) => {
              const timeout = setTimeout(
                () => reject(new Error('legacy activation timeout')),
                10000,
              )
              worker.addEventListener('statechange', () => {
                if (worker.state === 'activated') {
                  clearTimeout(timeout)
                  resolve()
                }
              })
            })
          }
          if (!navigator.serviceWorker.controller) {
            await new Promise((resolve, reject) => {
              const timeout = setTimeout(
                () => reject(new Error('legacy controller timeout')),
                10000,
              )
              navigator.serviceWorker.addEventListener('controllerchange', () => {
                clearTimeout(timeout)
                resolve()
              }, {once: true})
            })
          }

          await caches.open(preserveCache)
          return {
            controller: new URL(navigator.serviceWorker.controller.scriptURL).pathname,
            registrations: (await navigator.serviceWorker.getRegistrations()).map((item) => ({
              scope: new URL(item.scope).pathname,
              script: item.active ? new URL(item.active.scriptURL).pathname : null,
              state: item.active?.state ?? null,
            })),
            caches: await caches.keys(),
          }
        }""",
        PRESERVE_CACHE_NAME,
    )
    assert synthetic_worker_requests == [worker_url]
    assert before["controller"] == "/flutter_service_worker.js"
    assert {registration["scope"] for registration in before["registrations"]} == {"/"}
    assert LEGACY_CACHE_NAMES.issubset(set(before["caches"])), (
        f"synthetic legacy worker did not create its caches: {before['caches']}"
    )
    assert PRESERVE_CACHE_NAME in before["caches"]

    context.unroute(worker_url, serve_synthetic_legacy_worker)
    page.goto(f"{base_url}/app/login", wait_until="domcontentloaded")
    page.wait_for_function(
        """async ([legacyCaches, preserveCache]) => {
          const registrations = await navigator.serviceWorker.getRegistrations()
          const cacheNames = await caches.keys()
          return (
            !registrations.some((item) => new URL(item.scope).pathname === '/')
            && registrations.some((item) =>
              new URL(item.scope).pathname === '/app/'
              && item.active?.state === 'activated'
            )
            && legacyCaches.every((name) => !cacheNames.includes(name))
            && cacheNames.includes(preserveCache)
          )
        }""",
        arg=[sorted(LEGACY_CACHE_NAMES), PRESERVE_CACHE_NAME],
        timeout=20_000,
    )
    page.reload(wait_until="domcontentloaded")
    page.wait_for_function(
        """() => navigator.serviceWorker.controller
          && new URL(navigator.serviceWorker.controller.scriptURL).pathname === '/app/sw.js'""",
        timeout=10_000,
    )
    after = page.evaluate(
        """async () => {
          const ready = await navigator.serviceWorker.ready
          return {
            controller: new URL(navigator.serviceWorker.controller.scriptURL).pathname,
            registrations: (await navigator.serviceWorker.getRegistrations()).map((registration) => ({
              scope: new URL(registration.scope).pathname,
              script: registration.active ? new URL(registration.active.scriptURL).pathname : null,
            })),
            ready_registration: {
              scope: new URL(ready.scope).pathname,
              script: new URL(ready.active.scriptURL).pathname,
            },
            caches: await caches.keys(),
          }
        }"""
    )
    remaining_legacy_caches = sorted(LEGACY_CACHE_NAMES.intersection(after["caches"]))
    assert remaining_legacy_caches == [], (
        f"legacy Flutter caches remain: {remaining_legacy_caches}"
    )
    assert PRESERVE_CACHE_NAME in after["caches"], "unrelated cache was deleted"
    assert after["controller"] == "/app/sw.js"
    assert after["ready_registration"] == {
        "scope": "/app/",
        "script": "/app/sw.js",
    }, f"current PWA worker was not preserved: {after['ready_registration']}"
    context.close()
    return {
        "synthetic_worker_requested": worker_url,
        "before": before,
        "after": after,
    }


def register_mobile(page: Page, base_url: str, phone: str, pin: str, evidence: Evidence) -> int:
    page.goto(f"{base_url}/app/login", wait_until="domcontentloaded")
    fill_phone_step(page, phone, evidence, "01-registration-start", verify_loading=True)

    page.get_by_role("heading", name="Как тебя зовут?").wait_for()
    name_input = page.get_by_label("Имя")
    assert_has_focus(name_input, "name input")
    name_input.fill("Аян")
    page.get_by_role("button", name="Далее").click()

    page.get_by_role("heading", name="В какой класс идёшь?").wait_for()
    assert_has_focus(page.get_by_role("radio", name="4", exact=True), "first grade option")
    grade = page.get_by_role("radio", name="7", exact=True)
    assert_touch_target(grade, "grade 7")
    grade.click()
    page.get_by_role("button", name="Далее").click()

    page.get_by_role("heading", name="Придумай PIN").wait_for()
    assert page.get_by_role("checkbox").count() == 0, (
        "child registration must not ask for parent photo consent"
    )
    pin_input = page.get_by_label("Придумай PIN")
    assert_has_focus(pin_input, "PIN input")
    pin_input.fill(pin)
    evidence.checkpoint(page, "02-registration-ready")
    create = page.get_by_role("button", name="Создать аккаунт и начать")
    assert_touch_target(create, "create and start button")
    create.click()

    page.wait_for_url(re.compile(r"/app/lesson/mixtures-1$"), timeout=20_000)
    page.get_by_role("heading", name="Что остаётся неизменным").wait_for(timeout=20_000)
    assert page.get_by_role("button", name="Начать урок").count() == 0
    me = fetch_json(page, "/api/auth/me")
    assert me.get("grade") == 7
    assert me.get("photo_consent") is None
    token = page.evaluate("localStorage.getItem('kodi.jwt')")
    assert isinstance(token, str) and token.count(".") == 2
    session_id = current_session_id(page)
    evidence.checkpoint(page, "03-first-math-direct")
    return session_id


def complete_first_math_step(page: Page, evidence: Evidence) -> None:
    advance = page.get_by_role("button", name="Перейти к своему шагу")
    assert_touch_target(advance, "worked example advance")
    with page.expect_response(
        lambda response: urlsplit(response.url).path == "/api/learning/advance"
        and response.status == 200
    ):
        advance.click()

    page.get_by_role("heading", name="Сначала найди неизменную часть").wait_for()
    # LearningPage сначала фокусирует новый заголовок в requestAnimationFrame.
    # Проверяем Tab/focus поля уже после завершения этого accessibility-перехода.
    page.wait_for_timeout(100)
    answer = page.get_by_label(re.compile(r"^Ответ:"))
    assert_focusable(answer, "learning answer")
    answer.fill("20")
    check = page.get_by_role("button", name="Проверить шаг")
    assert_touch_target(check, "check math step")
    with page.expect_response(
        lambda response: urlsplit(response.url).path == "/api/learning/answer"
        and response.status == 200
    ):
        check.click()

    page.get_by_role("heading", name="Теперь измени общую массу").wait_for()
    page.get_by_text("2/6 сохранено", exact=True).wait_for()
    evidence.checkpoint(page, "04-first-result-saved")


def assert_reload_resume(page: Page, evidence: Evidence, expected_session_id: int) -> None:
    page.reload(wait_until="domcontentloaded")
    page.get_by_role("heading", name="Теперь измени общую массу").wait_for(timeout=20_000)
    page.get_by_text("2/6 сохранено", exact=True).wait_for()
    assert current_session_id(page) == expected_session_id
    evidence.checkpoint(page, "05-mobile-reload-resume")


def login_existing(
    page: Page,
    base_url: str,
    phone: str,
    pin: str,
    evidence: Evidence,
    checkpoint: str,
    expected_session_id: int,
) -> None:
    page.goto(f"{base_url}/app/login", wait_until="domcontentloaded")
    fill_phone_step(page, phone, evidence)
    page.get_by_role("heading", name="Добро пожаловать!").wait_for()
    pin_input = page.get_by_label("PIN-код")
    assert_has_focus(pin_input, "existing student PIN")
    pin_input.fill(pin)
    login = page.get_by_role("button", name="Войти и продолжить урок")
    assert_touch_target(login, "continue lesson login")
    login.click()
    page.wait_for_url(re.compile(r"/app/lesson/mixtures-1$"), timeout=20_000)
    page.get_by_role("heading", name="Теперь измени общую массу").wait_for(timeout=20_000)
    page.get_by_text("2/6 сохранено", exact=True).wait_for()
    assert current_session_id(page) == expected_session_id
    evidence.checkpoint(page, checkpoint)


def run(args: argparse.Namespace) -> dict[str, Any]:
    base_url = args.base_url.rstrip("/")
    phone = f"+7706{time.time_ns() % 10_000_000:07d}"
    pin = "7319"
    evidence = Evidence(args.output_dir.resolve())

    with sync_playwright() as playwright:
        browser: Browser = playwright.chromium.launch(
            headless=True,
            executable_path=str(args.chrome) if args.chrome else None,
        )
        legacy_worker_migration = assert_legacy_service_worker_migration(browser, base_url)
        assert_recoverable_network_error(browser, base_url, evidence)
        mobile = browser.new_context(
            viewport={"width": 375, "height": 844},
            has_touch=True,
            is_mobile=True,
            reduced_motion="reduce",
            service_workers="allow",
        )
        mobile_page = mobile.new_page()
        evidence.attach(mobile_page)
        session_id = register_mobile(mobile_page, base_url, phone, pin, evidence)
        complete_first_math_step(mobile_page, evidence)
        assert_reload_resume(mobile_page, evidence, session_id)
        mobile_page.evaluate("localStorage.removeItem('kodi.jwt')")
        login_existing(
            mobile_page,
            base_url,
            phone,
            pin,
            evidence,
            "06-mobile-relogin-resume",
            session_id,
        )
        mobile.close()

        desktop = browser.new_context(
            viewport={"width": 1280, "height": 900},
            reduced_motion="reduce",
            service_workers="allow",
        )
        desktop_page = desktop.new_page()
        evidence.attach(desktop_page)
        login_existing(
            desktop_page,
            base_url,
            phone,
            pin,
            evidence,
            "07-desktop-login-resume",
            session_id,
        )
        desktop.close()
        browser.close()

    evidence.assert_clean()
    required_calls = {
        ("POST", "/api/auth/phone/register", 200),
        ("GET", "/api/learning/path/current", 200),
        ("POST", "/api/learning/start", 200),
        ("POST", "/api/learning/advance", 200),
        ("POST", "/api/learning/answer", 200),
        ("POST", "/api/auth/phone/login", 200),
    }
    missing = sorted(key for key in required_calls if evidence.api_statuses[key] == 0)
    assert not missing, f"required live API calls are missing: {missing}"

    summary = {
        "verdict": "PASS",
        "base_origin": f"{urlsplit(base_url).scheme}://{urlsplit(base_url).netloc}",
        "viewports": ["375x844 touch", "1280x900"],
        "checkpoints": evidence.checkpoints,
        "checks": [
            "registration contains no parent-consent control",
            "registration opens /app/lesson/mixtures-1 without a path-screen click",
            "first worked example and first student answer persist on the server",
            "reload resumes at 2/6",
            "mobile and desktop re-login resume the same lesson at 2/6",
            "critical touch targets are at least 44x44",
            "keyboard focus reaches form and answer controls",
            "registration exposes a disabled loading state under network latency",
            "recoverable network error is announced with an accessible alert",
            "reduced-motion mode completes the full journey",
            "preinstalled synthetic Flutter root SW unregisters and removes its caches",
            "zero horizontal overflow",
            "zero console, page, request, and API errors",
        ],
        "api_statuses": {
            f"{method} {route} {status}": count
            for (method, route, status), count in sorted(evidence.api_statuses.items())
        },
        "legacy_worker_migration": legacy_worker_migration,
        "console_errors": evidence.console_errors,
        "page_errors": evidence.page_errors,
        "request_errors": evidence.request_errors,
        "api_errors": evidence.api_errors,
    }
    (evidence.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8409")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--chrome",
        type=Path,
        default=DEFAULT_CHROME if DEFAULT_CHROME.exists() else None,
    )
    args = parser.parse_args()
    print(json.dumps(run(args), ensure_ascii=False))


if __name__ == "__main__":
    main()
