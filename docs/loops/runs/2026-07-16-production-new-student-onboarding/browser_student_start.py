#!/usr/bin/env python3
"""CJM нового ученика: регистрация должна сразу открыть и сохранить урок."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
from typing import Any
from urllib.parse import urlsplit

from playwright.sync_api import (
    Browser,
    Error as PlaywrightError,
    Locator,
    Page,
    Request,
    Response,
    sync_playwright,
)


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
const LEGACY_SHELL = `<!doctype html>
<html><body><main>Legacy Flutter shell</main><script>
addEventListener('load', async () => {
  await navigator.serviceWorker.register(
    '/flutter_service_worker.js?retire-e2e=1',
    {scope: '/', updateViaCache: 'none'},
  );
});
</script></body></html>`;
self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    await Promise.all(LEGACY_CACHES.map((name) => caches.open(name)));
    const appCache = await caches.open('flutter-app-cache');
    await appCache.put(
      '/app/login',
      new Response(LEGACY_SHELL, {headers: {'Content-Type': 'text/html'}}),
    );
    await self.skipWaiting();
  })());
});
self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});
self.addEventListener('fetch', (event) => {
  if (event.request.mode !== 'navigate') return;
  event.respondWith(
    caches.match(event.request).then((cached) => cached ?? fetch(event.request)),
  );
});
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
        self.touch_targets: dict[str, list[dict[str, float]]] = {}

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

    def record_touch_target(self, locator: Locator, label: str) -> None:
        self.touch_targets.setdefault(label, []).append(
            assert_touch_target(locator, label)
        )


def assert_touch_target(locator: Locator, label: str) -> dict[str, float]:
    box = locator.bounding_box()
    assert box is not None, f"{label} is not visible"
    assert box["width"] >= 44 and box["height"] >= 44, (
        f"{label} is only {box['width']}x{box['height']}"
    )
    return {
        "width_px": round(box["width"], 1),
        "height_px": round(box["height"], 1),
    }


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


def wait_for_async_condition(
    page: Page,
    expression: str,
    *,
    arg: Any,
    timeout_ms: int,
) -> None:
    """Poll an async browser predicate and wait for its resolved boolean value."""
    deadline = time.monotonic() + timeout_ms / 1000
    last_error: PlaywrightError | None = None
    while time.monotonic() < deadline:
        try:
            if page.evaluate(expression, arg):
                return
        except PlaywrightError as error:
            # The legacy worker intentionally reloads the current client while
            # handing control back to the network, destroying one JS context.
            last_error = error
        time.sleep(0.25)

    suffix = f"; last browser error: {last_error}" if last_error else ""
    raise AssertionError(f"async browser condition timed out after {timeout_ms}ms{suffix}")


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


def assert_public_route_matrix(browser: Browser, base_url: str) -> dict[str, Any]:
    """Prove redirect, SPA fallback and missing-asset behavior on the live origin."""
    context = browser.new_context(service_workers="block")
    cases = {
        "/": {"status": 308, "location": "/app/"},
        "/app": {"status": 308, "location": "/app/"},
        "/app/": {"status": 200, "spa": True},
        "/app/login": {"status": 200, "spa": True},
        "/app/lesson/mixtures-1": {"status": 200, "spa": True},
        "/app/assets/__acceptance_missing__.js": {"status": 404, "spa": False},
    }
    result: dict[str, Any] = {}
    try:
        for route, expected in cases.items():
            response = context.request.get(
                f"{base_url}{route}",
                max_redirects=0,
            )
            body = response.text()
            content_type = response.headers.get("content-type", "")
            location = response.headers.get("location")
            spa_shell = (
                response.status == 200
                and "text/html" in content_type
                and '<div id="root"></div>' in body
            )
            assert response.status == expected["status"], (
                f"{route} -> {response.status}, expected {expected['status']}"
            )
            if "location" in expected:
                assert location is not None
                assert urlsplit(location).path == expected["location"], (
                    f"{route} redirects to {location}, expected {expected['location']}"
                )
            if "spa" in expected:
                assert spa_shell is expected["spa"], (
                    f"{route} SPA fallback={spa_shell}, expected {expected['spa']}"
                )
            result[route] = {
                "status": response.status,
                "location": location,
                "content_type": content_type,
                "body_bytes": len(body.encode("utf-8")),
                "spa_shell": spa_shell,
            }
    finally:
        context.close()
    return result


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
    evidence.record_touch_target(continue_button, "continue button")
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


def assert_registration_path_failure_recovery(
    browser: Browser,
    base_url: str,
    evidence: Evidence,
) -> dict[str, Any]:
    """A created account must survive a failed first learning-path request."""
    context = browser.new_context(
        viewport={"width": 375, "height": 844},
        has_touch=True,
        is_mobile=True,
        reduced_motion="reduce",
        service_workers="block",
    )
    page = context.new_page()
    path_statuses: list[int] = []
    failure_injected = False

    def record_path_status(response: Response) -> None:
        if urlsplit(response.url).path == "/api/learning/path/current":
            path_statuses.append(response.status)

    page.on("response", record_path_status)

    def fail_first_path_request(route: Any) -> None:
        nonlocal failure_injected
        if not failure_injected:
            failure_injected = True
            route.fulfill(
                status=503,
                content_type="application/json",
                body=json.dumps({"detail": "acceptance injected path failure"}),
            )
            return
        route.continue_()

    context.route("**/api/learning/path/current", fail_first_path_request)
    phone = f"+7707{time.time_ns() % 10_000_000:07d}"
    pin = "8426"
    try:
        page.goto(f"{base_url}/app/login", wait_until="domcontentloaded")
        fill_phone_step(page, phone, evidence)
        page.get_by_role("heading", name="Как тебя зовут?").wait_for()
        page.get_by_label("Имя").fill("Саян")
        page.get_by_role("button", name="Далее").click()
        page.get_by_role("heading", name="В какой класс идёшь?").wait_for()
        page.get_by_role("radio", name="7", exact=True).click()
        page.get_by_role("button", name="Далее").click()
        page.get_by_role("heading", name="Придумай PIN").wait_for()
        page.get_by_label("Придумай PIN").fill(pin)
        page.get_by_role("button", name="Создать аккаунт и начать").click()

        page.wait_for_url(re.compile(r"/app/?$"), timeout=20_000)
        page.get_by_text("Мой путь", exact=True).wait_for(timeout=20_000)
        page.get_by_role("heading", name="Смеси и концентрации").wait_for(
            timeout=20_000
        )
        token = page.evaluate("localStorage.getItem('kodi.jwt')")
        assert isinstance(token, str) and token.count(".") == 2
        me = fetch_json(page, "/api/auth/me")
        recovered_path = fetch_json(page, "/api/learning/path/current")
        assert path_statuses and path_statuses[0] == 503
        assert 200 in path_statuses, f"path did not recover: {path_statuses}"
        student_id = me.get("id")
        assert isinstance(student_id, int)
        recovered_lesson_id = (
            recovered_path.get("lesson", {})
            .get("primary_action", {})
            .get("lesson_id")
        )
        assert recovered_lesson_id == "mixtures-1"
        return {
            "injected_first_path_status": 503,
            "fallback_destination": urlsplit(page.url).path,
            "jwt_preserved": True,
            "auth_me_student_id": student_id,
            "recovered_path_status": 200,
            "recovered_lesson_id": recovered_lesson_id,
            "account_preserved": True,
            "path_request_statuses": path_statuses,
        }
    finally:
        context.close()


def assert_legacy_service_worker_migration(
    browser: Browser,
    base_url: str,
) -> dict[str, Any]:
    context = browser.new_context(service_workers="allow", reduced_motion="reduce")
    synthetic_worker_requests: list[str] = []
    worker_route_requests: list[str] = []
    worker_url = f"{base_url}/flutter_service_worker.js"

    def serve_synthetic_legacy_worker(route: Any) -> None:
        assert route.request.service_worker is not None
        worker_route_requests.append(route.request.url)
        if synthetic_worker_requests:
            route.continue_()
        else:
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

    context.route(
        re.compile(rf"^{re.escape(worker_url)}(?:\\?.*)?$"),
        serve_synthetic_legacy_worker,
    )
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

    migration_settled = """async ([legacyCaches, preserveCache]) => {
      const isReady = async () => {
        const registrations = await navigator.serviceWorker.getRegistrations()
        const cacheNames = await caches.keys()
        const appRegistration = registrations.find(
          (item) => new URL(item.scope).pathname === '/app/'
        )
        const appWorker = appRegistration?.active
          ?? appRegistration?.waiting
          ?? appRegistration?.installing
        return (
          !registrations.some((item) => new URL(item.scope).pathname === '/')
          && appWorker
          && new URL(appWorker.scriptURL).pathname === '/app/sw.js'
          && legacyCaches.every((name) => !cacheNames.includes(name))
          && cacheNames.includes(preserveCache)
          && document.body.innerText.includes('AiPlus')
        )
      }
      if (!(await isReady())) return false
      await new Promise((resolve) => setTimeout(resolve, 1500))
      return isReady()
    }"""
    page.goto(f"{base_url}/app/login", wait_until="domcontentloaded")
    wait_for_async_condition(
        page,
        migration_settled,
        arg=[sorted(LEGACY_CACHE_NAMES), PRESERVE_CACHE_NAME],
        timeout_ms=30_000,
    )
    same_client_controller = page.evaluate(
        """() => navigator.serviceWorker.controller
          ? new URL(navigator.serviceWorker.controller.scriptURL).pathname
          : null"""
    )
    # После unregister старый worker вправе контролировать уже открытый client
    # до конца его lifecycle. Без старого client новый PWA завершает activation.
    page.close()
    time.sleep(2)
    page = context.new_page()
    page.goto(f"{base_url}/app/login", wait_until="domcontentloaded")
    wait_for_async_condition(
        page,
        """async ([legacyCaches, preserveCache]) => {
          const registrations = await navigator.serviceWorker.getRegistrations()
          const cacheNames = await caches.keys()
          return (
            navigator.serviceWorker.controller
            && new URL(navigator.serviceWorker.controller.scriptURL).pathname === '/app/sw.js'
            && !registrations.some((item) => new URL(item.scope).pathname === '/')
            && registrations.some((item) =>
              new URL(item.scope).pathname === '/app/'
              && item.active?.state === 'activated'
            )
            && legacyCaches.every((name) => !cacheNames.includes(name))
            && cacheNames.includes(preserveCache)
          )
        }""",
        arg=[sorted(LEGACY_CACHE_NAMES), PRESERVE_CACHE_NAME],
        timeout_ms=30_000,
    )
    next_client_controller = page.evaluate(
        """() => navigator.serviceWorker.controller
          ? new URL(navigator.serviceWorker.controller.scriptURL).pathname
          : null"""
    )
    after = page.evaluate(
        """async () => {
          const ready = await navigator.serviceWorker.ready
          return {
            controller: navigator.serviceWorker.controller
              ? new URL(navigator.serviceWorker.controller.scriptURL).pathname
              : null,
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
        "legacy Flutter caches remain: "
        f"{remaining_legacy_caches}; requests={worker_route_requests}; after={after}"
    )
    assert PRESERVE_CACHE_NAME in after["caches"], "unrelated cache was deleted"
    assert not any(item["scope"] == "/" for item in after["registrations"]), (
        f"root worker registration remains: {after['registrations']}"
    )
    assert after["ready_registration"] == {
        "scope": "/app/",
        "script": "/app/sw.js",
    }, f"current PWA worker was not preserved: {after['ready_registration']}"
    assert after["controller"] == "/app/sw.js", (
        "new client is not controlled by the current PWA worker: "
        f"same_client={same_client_controller}; next_client={next_client_controller}; "
        f"requests={worker_route_requests}; after={after}"
    )
    assert any(name.startswith("workbox-precache-") for name in after["caches"]), (
        f"current PWA precache was not created: {after['caches']}"
    )
    context.close()
    return {
        "synthetic_worker_requested": worker_url,
        "worker_route_requests": worker_route_requests,
        "same_client_after_reload_controller": same_client_controller,
        "next_client_controller": next_client_controller,
        "before": before,
        "after": after,
    }


def register_mobile(
    page: Page,
    base_url: str,
    phone: str,
    pin: str,
    evidence: Evidence,
) -> dict[str, Any]:
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
    evidence.record_touch_target(grade, "grade 7")
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
    evidence.record_touch_target(create, "create and start button")
    submit_started = time.perf_counter()
    with page.expect_response(
        lambda response: urlsplit(response.url).path == "/api/learning/path/current"
        and response.status == 200
    ) as path_response_info:
        create.click()

    page.wait_for_url(re.compile(r"/app/lesson/mixtures-1$"), timeout=20_000)
    page.get_by_role("heading", name="Что остаётся неизменным").wait_for(timeout=20_000)
    submit_to_activity_ms = round((time.perf_counter() - submit_started) * 1000)
    assert page.get_by_role("button", name="Начать урок").count() == 0
    path_payload = path_response_info.value.json()
    lesson_id = (
        path_payload.get("lesson", {})
        .get("primary_action", {})
        .get("lesson_id")
    )
    assert lesson_id == "mixtures-1"
    assert urlsplit(page.url).path == f"/app/lesson/{lesson_id}"
    me = fetch_json(page, "/api/auth/me")
    assert me.get("grade") == 7
    assert me.get("photo_consent") is None
    student_id = me.get("id")
    assert isinstance(student_id, int)
    token = page.evaluate("localStorage.getItem('kodi.jwt')")
    assert isinstance(token, str) and token.count(".") == 2
    session_id = current_session_id(page)
    evidence.checkpoint(page, "03-first-math-direct")
    return {
        "student_id": student_id,
        "path_response_lesson_id": lesson_id,
        "browser_destination": urlsplit(page.url).path,
        "submit_to_activity_ms": submit_to_activity_ms,
        "initial_session_id": session_id,
        "photo_consent": me.get("photo_consent"),
    }


def complete_first_math_step(page: Page, evidence: Evidence) -> None:
    advance = page.get_by_role("button", name="Перейти к своему шагу")
    evidence.record_touch_target(advance, "worked example advance")
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
    evidence.record_touch_target(check, "check math step")
    with page.expect_response(
        lambda response: urlsplit(response.url).path == "/api/learning/answer"
        and response.status == 200
    ):
        check.click()

    page.get_by_role("heading", name="Теперь измени общую массу").wait_for()
    page.get_by_text("2/6 сохранено", exact=True).wait_for()
    evidence.checkpoint(page, "04-first-result-saved")


def assert_reload_resume(
    page: Page,
    evidence: Evidence,
    expected_session_id: int,
) -> int:
    page.reload(wait_until="domcontentloaded")
    page.get_by_role("heading", name="Теперь измени общую массу").wait_for(timeout=20_000)
    page.get_by_text("2/6 сохранено", exact=True).wait_for()
    observed_session_id = current_session_id(page)
    assert observed_session_id == expected_session_id
    evidence.checkpoint(page, "05-mobile-reload-resume")
    return observed_session_id


def login_existing(
    page: Page,
    base_url: str,
    phone: str,
    pin: str,
    evidence: Evidence,
    checkpoint: str,
    expected_session_id: int,
) -> int:
    page.goto(f"{base_url}/app/login", wait_until="domcontentloaded")
    fill_phone_step(page, phone, evidence)
    page.get_by_role("heading", name="Добро пожаловать!").wait_for()
    pin_input = page.get_by_label("PIN-код")
    assert_has_focus(pin_input, "existing student PIN")
    pin_input.fill(pin)
    login = page.get_by_role("button", name="Войти и продолжить урок")
    evidence.record_touch_target(login, "continue lesson login")
    login.click()
    page.wait_for_url(re.compile(r"/app/lesson/mixtures-1$"), timeout=20_000)
    page.get_by_role("heading", name="Теперь измени общую массу").wait_for(timeout=20_000)
    page.get_by_text("2/6 сохранено", exact=True).wait_for()
    observed_session_id = current_session_id(page)
    assert observed_session_id == expected_session_id
    evidence.checkpoint(page, checkpoint)
    return observed_session_id


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
        route_matrix = assert_public_route_matrix(browser, base_url)
        legacy_worker_migration = assert_legacy_service_worker_migration(browser, base_url)
        assert_recoverable_network_error(browser, base_url, evidence)
        path_failure_recovery = assert_registration_path_failure_recovery(
            browser,
            base_url,
            evidence,
        )
        mobile = browser.new_context(
            viewport={"width": 375, "height": 844},
            has_touch=True,
            is_mobile=True,
            reduced_motion="reduce",
            service_workers="allow",
        )
        mobile_page = mobile.new_page()
        evidence.attach(mobile_page)
        registration = register_mobile(mobile_page, base_url, phone, pin, evidence)
        session_id = registration["initial_session_id"]
        assert isinstance(session_id, int)
        complete_first_math_step(mobile_page, evidence)
        mobile_reload_session_id = assert_reload_resume(
            mobile_page,
            evidence,
            session_id,
        )
        mobile_page.evaluate("localStorage.removeItem('kodi.jwt')")
        mobile_relogin_session_id = login_existing(
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
        desktop_relogin_session_id = login_existing(
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

    observed_session_ids = [
        session_id,
        mobile_reload_session_id,
        mobile_relogin_session_id,
        desktop_relogin_session_id,
    ]
    unique_session_ids = sorted(set(observed_session_ids))
    assert unique_session_ids == [session_id], (
        f"duplicate learning sessions detected: {observed_session_ids}"
    )

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
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_origin": f"{urlsplit(base_url).scheme}://{urlsplit(base_url).netloc}",
        "viewports": ["375x844 touch", "1280x900"],
        "route_matrix": route_matrix,
        "registration_to_activity": registration,
        "continuity": {
            "initial_session_id": session_id,
            "mobile_reload_session_id": mobile_reload_session_id,
            "mobile_relogin_session_id": mobile_relogin_session_id,
            "desktop_relogin_session_id": desktop_relogin_session_id,
            "unique_session_ids": unique_session_ids,
            "duplicate_session_created": False,
            "saved_progress": "2/6",
        },
        "path_failure_recovery": path_failure_recovery,
        "touch_targets": evidence.touch_targets,
        "checkpoints": evidence.checkpoints,
        "checks": [
            "registration contains no parent-consent control",
            "lesson id from /api/learning/path/current maps directly to the browser route",
            "registration opens /app/lesson/mixtures-1 without a path-screen click",
            "a failed first path request preserves the account and recovers on the path screen",
            "first worked example and first student answer persist on the server",
            "reload and both re-logins keep one server session id and resume at 2/6",
            "public route matrix covers redirects, SPA deep links and missing asset 404",
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
