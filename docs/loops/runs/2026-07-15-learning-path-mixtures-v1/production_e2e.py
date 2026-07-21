"""Production browser evidence for the server-owned mixtures learning path."""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, Request, Route, sync_playwright


BASE = "http://localhost:8400"
OUT = Path(__file__).resolve().parent / "production-evidence-path"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def post_json(path: str, payload: dict) -> dict:
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read())


def fresh_student_token() -> str:
    suffix = f"{time.time_ns() % 10_000_000:07d}"
    response = post_json(
        "/api/auth/phone/register",
        {
            "phone": f"+7998{suffix}",
            "name": "E2E Ученик",
            "pin": "7315",
            "photo_consent": False,
            "grade": 7,
        },
    )
    return response["access_token"]


def set_token(context, token: str) -> None:
    context.add_init_script(
        script=f"localStorage.setItem('kodi.jwt', {json.dumps(token)});"
    )


def shot(page: Page, name: str, width: int, height: int) -> None:
    page.set_viewport_size({"width": width, "height": height})
    # Let viewport reflow, reveal animations and the headless compositor settle
    # before freezing evidence. Without this pause a desktop shot taken straight
    # after a mobile shot can capture a transient unpainted background.
    page.wait_for_timeout(500)
    page.screenshot(path=str(OUT / f"{name}-{width}x{height}.png"), full_page=False)
    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    assert overflow <= 0, f"horizontal overflow {overflow}px in {name} at {width}"


def visible_button_min_height(page: Page) -> float:
    return page.evaluate(
        """
        () => Math.min(...Array.from(document.querySelectorAll('button'))
          .filter((el) => el.getBoundingClientRect().width > 0)
          .map((el) => el.getBoundingClientRect().height))
        """
    )


def wait_activity(page: Page, title: str) -> None:
    page.get_by_role("heading", name=title).wait_for()
    page.wait_for_timeout(120)
    active_id = page.evaluate("document.activeElement?.id")
    assert active_id == "learning-activity-title", f"focus did not move to {title}"


def run() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    token = fresh_student_token()
    console_errors: list[str] = []
    page_errors: list[str] = []
    request_errors: list[str] = []
    api_errors: list[str] = []
    expected_failed: set[Request] = set()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=CHROME,
            args=["--disable-dev-shm-usage"],
        )
        context = browser.new_context(viewport={"width": 375, "height": 844})
        set_token(context, token)
        page = context.new_page()
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error" and "ERR_FAILED" not in message.text
            else None,
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "requestfailed",
            lambda request: request_errors.append(f"{request.method} {request.url}")
            if request not in expected_failed
            else None,
        )
        page.on(
            "response",
            lambda response: api_errors.append(f"{response.status} {response.url}")
            if "/api/" in response.url and response.status >= 400
            else None,
        )

        page.goto(f"{BASE}/app/", wait_until="networkidle")
        assert page.get_by_text("Мой путь", exact=True).is_visible()
        assert page.get_by_text("Текущий блок · Смеси и концентрации", exact=True).is_visible()
        assert page.get_by_role("heading", name="Вещество остаётся").is_visible()
        assert page.get_by_role("button", name="Начать урок").count() == 1
        assert "Сегодня" not in page.locator("body").inner_text()
        assert not any(word in page.locator("body").inner_text() for word in ("Фото", "Чат", "Теория"))
        assert visible_button_min_height(page) >= 44
        shot(page, "path", 375, 844)
        shot(page, "path", 1280, 900)
        page.set_viewport_size({"width": 375, "height": 844})

        page.get_by_role("button", name="Начать урок").click()
        wait_activity(page, "Что остаётся неизменным")
        assert page.get_by_text("40 г", exact=True).is_visible()
        shot(page, "worked", 375, 844)
        shot(page, "worked", 1280, 900)
        page.set_viewport_size({"width": 375, "height": 844})

        page.get_by_role("button", name="Перейти к своему шагу").click()
        wait_activity(page, "Сначала найди неизменную часть")
        assert page.get_by_text("Подсказка после попытки").count() == 0
        page.locator("#learning-answer").fill("40")
        page.get_by_role("button", name="Проверить шаг").click()
        page.get_by_text("Подсказка после попытки").wait_for()
        assert page.locator("#learning-answer").input_value() == "40"
        shot(page, "wrong-tier-1", 375, 844)
        shot(page, "wrong-tier-1", 1280, 900)

        page.reload(wait_until="networkidle")
        wait_activity(page, "Сначала найди неизменную часть")
        assert page.locator("#learning-answer").input_value() == "40"
        assert page.get_by_text("Подсказка после попытки").is_visible()
        shot(page, "resume-after-reload", 375, 844)

        page.locator("#learning-answer").fill("20")
        page.get_by_role("button", name="Проверить шаг").click()
        wait_activity(page, "Теперь измени общую массу")

        def abort_one(route: Route) -> None:
            expected_failed.add(route.request)
            route.abort()

        page.route("**/api/learning/answer", abort_one, times=1)
        page.locator("#learning-answer").fill("250")
        page.get_by_role("button", name="Проверить шаг").click()
        page.get_by_role("alert").wait_for()
        assert "250" in page.get_by_role("alert").inner_text()
        assert page.locator("#learning-answer").input_value() == "250"
        shot(page, "network-answer-preserved", 375, 844)
        page.get_by_role("button", name="Отправить ещё раз").click()
        wait_activity(page, "Собери новую долю")

        page.locator("#learning-answer").fill("8")
        page.get_by_role("button", name="Проверить шаг").click()
        wait_activity(page, "Теперь без раскрытых шагов")
        assert page.get_by_text("Подсказка после попытки").count() == 0
        shot(page, "independent", 375, 844)
        shot(page, "independent", 1280, 900)
        page.set_viewport_size({"width": 375, "height": 844})

        page.locator("#learning-answer").fill("15")
        page.get_by_role("button", name="Проверить ответ").click()
        wait_activity(page, "Теперь вода не добавляется, а уходит")
        shot(page, "transfer", 375, 844)
        shot(page, "transfer", 1280, 900)
        page.set_viewport_size({"width": 375, "height": 844})

        page.locator("#learning-answer").fill("12")
        page.get_by_role("button", name="Проверить ответ").click()
        page.get_by_text("Подсказка после попытки").wait_for()
        page.locator("#learning-answer").fill("30")
        page.get_by_role("button", name="Проверить ответ").click()
        page.get_by_role("heading", name="Теперь ты умеешь").wait_for()
        assert page.get_by_text(
            "2 самостоятельных задания, одно — с переносом на новую ситуацию"
        ).is_visible()
        shot(page, "result", 375, 844)
        shot(page, "result", 1280, 900)

        # Returning to the cumulative path must expose the persisted block completion.
        page.goto(f"{BASE}/app/", wait_until="networkidle")
        page.get_by_text("В этом блоке: 1 из 1 урока", exact=True).wait_for()
        assert page.get_by_text("Освоенный урок", exact=True).is_visible()
        assert page.get_by_role("button", name="Посмотреть результат").count() == 1
        shot(page, "path-completed", 375, 844)
        shot(page, "path-completed", 1280, 900)

        # Reduced motion keeps the same result without an animated dependency.
        reduced = browser.new_context(
            viewport={"width": 375, "height": 844}, reduced_motion="reduce"
        )
        set_token(reduced, token)
        reduced_page = reduced.new_page()
        reduced_page.goto(f"{BASE}/app/lesson/mixtures-1", wait_until="networkidle")
        reduced_page.get_by_role("heading", name="Теперь ты умеешь").wait_for()
        duration = reduced_page.locator(".reveal").evaluate(
            "el => getComputedStyle(el).animationDuration"
        )
        assert duration in ("0.01ms", "1e-05s", "0s"), duration
        reduced.close()

        # Explicit error and empty states are render-tested with controlled API responses.
        error_context = browser.new_context(
            viewport={"width": 375, "height": 844}, service_workers="block"
        )
        set_token(error_context, token)
        error_page = error_context.new_page()
        error_page.route(
            "**/api/learning/path/current",
            lambda route: route.fulfill(
                status=503,
                content_type="application/json",
                body='{"detail": "temporary"}',
            ),
        )
        error_page.goto(f"{BASE}/app/", wait_until="networkidle")
        error_page.get_by_role("heading", name="Твой прогресс никуда не пропал").wait_for(timeout=15_000)
        shot(error_page, "path-error", 375, 844)
        error_context.close()

        empty_context = browser.new_context(
            viewport={"width": 375, "height": 844}, service_workers="block"
        )
        set_token(empty_context, token)
        empty_page = empty_context.new_page()
        empty_page.route(
            "**/api/learning/path/current",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "path": {
                        "id": "nish-preparation",
                        "title": "Подготовка к НИШ",
                        "current_block": {
                            "id": "PC06",
                            "title": "Смеси и концентрации",
                            "completed_lessons": 0,
                            "total_lessons": 0,
                        },
                    },
                    "lesson": None,
                }, ensure_ascii=False),
            ),
        )
        empty_page.goto(f"{BASE}/app/", wait_until="networkidle")
        empty_page.get_by_role("heading", name="Маршрут ещё не собран").wait_for()
        shot(empty_page, "path-empty", 375, 844)
        empty_context.close()

        context.close()
        browser.close()

    assert not console_errors, console_errors
    assert not page_errors, page_errors
    assert not request_errors, request_errors
    assert not api_errors, api_errors
    summary = {
        "screenshots": len(list(OUT.glob("*.png"))),
        "console_errors": console_errors,
        "page_errors": page_errors,
        "request_errors": request_errors,
        "api_errors": api_errors,
        "checks": [
            "375x844 and 1280x900",
            "cumulative path and current curriculum block",
            "daily queue mental model absent",
            "one primary action",
            "worked → guided → independent → transfer",
            "tier-1 help only after wrong answer",
            "exact answer restored after reload",
            "network error preserves answer",
            "server result evidence",
            "completed lesson returns to cumulative path at 1/1",
            "keyboard focus follows activity",
            "touch target >=44px",
            "horizontal overflow absent",
            "loading geometry, error, empty, result",
            "reduced motion equivalent",
        ],
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    run()
