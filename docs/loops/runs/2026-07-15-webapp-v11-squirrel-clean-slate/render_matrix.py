"""Production browser matrix for the v11 redesign.

Runs against a production Vite preview, keeps API fixtures strict and captures both
happy paths and the product states required by the frozen rubric.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, Route, sync_playwright

from render_app import ANALYTICS, PROFILE, SECOND, SREZ, TASK, VERIFICATION, fulfill


ROOT = Path(__file__).resolve().parent
OUT = ROOT / os.environ.get("KODI_RENDER_ROUND", "round-production-final")
SHOTS = OUT / "screenshots"
BASE = os.environ.get("KODI_RENDER_BASE", "http://127.0.0.1:4173")
CHROME = Path.home() / (
    "Library/Caches/ms-playwright/chromium-1228/chrome-mac-arm64/"
    "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
)


@dataclass(frozen=True)
class Scenario:
    name: str
    path: str
    mode: str = "default"
    action: str | None = None
    authenticated: bool = True
    widths: tuple[int, ...] = (375,)
    reduced_motion: bool = True
    pending_endpoint: str | None = None


BASELINES = (
    Scenario("login", "/login", authenticated=False, widths=(375, 1280)),
    Scenario("hub", "/", widths=(375, 1280)),
    Scenario("drill", "/drill/wt-pc-01", widths=(375, 1280)),
    Scenario("srez", "/srez", widths=(375, 1280)),
    Scenario("analytics", "/analytics", widths=(375, 1280)),
    Scenario("closure", "/closure/wt-pc-01", widths=(375, 1280)),
    Scenario("not-found", "/route-that-does-not-exist", widths=(375, 1280)),
)

STATES = (
    Scenario("login-error", "/login", mode="auth-check-error", action="auth-error", authenticated=False),
    Scenario("register-grade", "/login", action="auth-grade", authenticated=False),
    Scenario("register-pin", "/login", action="auth-pin", authenticated=False),
    Scenario("hub-loading", "/", pending_endpoint="/trainer/wrong-tasks"),
    Scenario("hub-error", "/", mode="hub-error"),
    Scenario("hub-onboarding", "/", mode="hub-new"),
    Scenario("hub-empty", "/", mode="hub-empty"),
    Scenario("analytics-loading", "/analytics", pending_endpoint="/trainer/analytics"),
    Scenario("analytics-error", "/analytics", mode="analytics-error"),
    Scenario("analytics-empty", "/analytics", mode="analytics-empty"),
    Scenario("drill-loading", "/drill/wt-pc-01", pending_endpoint="/trainer/wrong-tasks"),
    Scenario("drill-error", "/drill/wt-pc-01", mode="drill-error"),
    Scenario("drill-first-error", "/drill/wt-pc-01", action="drill-wrong"),
    Scenario("drill-inserted-rung", "/drill/wt-pc-01", action="drill-inserted"),
    Scenario("drill-solved-reduced", "/drill/wt-pc-01", action="drill-solved"),
    Scenario("drill-solved-motion", "/drill/wt-pc-01", action="drill-solved", reduced_motion=False),
    Scenario("drill-finished", "/drill/wt-pc-01", action="drill-finished"),
    Scenario("srez-loading", "/srez", pending_endpoint="/trainer/srez/start"),
    Scenario("srez-error", "/srez", mode="srez-start-error"),
    Scenario("srez-empty", "/srez", mode="srez-empty"),
    Scenario("srez-wrong", "/srez", action="srez-answer"),
    Scenario("srez-correct", "/srez", mode="srez-correct", action="srez-answer"),
    Scenario("srez-network", "/srez", mode="srez-answer-error", action="srez-network"),
    Scenario("srez-finished", "/srez", mode="srez-one", action="srez-finish"),
    Scenario("closure-loading", "/closure/wt-pc-01", pending_endpoint="/trainer/verification/start"),
    Scenario("closure-start-error", "/closure/wt-pc-01", mode="closure-start-error"),
    Scenario("closure-wrong", "/closure/wt-pc-01", action="closure-answer"),
    Scenario("closure-network", "/closure/wt-pc-01", mode="closure-answer-error", action="closure-network"),
    Scenario("closure-success", "/closure/wt-pc-01", mode="closure-correct", action="closure-answer"),
    Scenario("keyboard-focus", "/", action="keyboard-focus"),
)


def api_handler(mode: str, unexpected: list[str]):
    def handle(route: Route) -> None:
        url = route.request.url
        if "/api/trainer/events" in url:
            fulfill(route, {})
        elif "/api/auth/phone/check" in url:
            if mode == "auth-check-error":
                fulfill(route, {"detail": "Не удалось проверить номер"}, status=500)
            else:
                fulfill(route, {"exists": False})
        elif "/api/auth/phone/login" in url or "/api/auth/phone/register" in url:
            fulfill(route, {"access_token": "visual-test"})
        elif "/api/auth/me" in url:
            fulfill(route, PROFILE)
        elif "/trainer/wrong-tasks" in url:
            if mode in {"hub-error", "drill-error"}:
                fulfill(route, {"detail": "fixture failure"}, status=500)
            elif mode == "hub-new":
                fulfill(route, {"tasks": [], "has_activity": False})
            elif mode == "hub-empty":
                fulfill(route, {"tasks": [], "has_activity": True})
            else:
                fulfill(route, {"tasks": [TASK, SECOND], "has_activity": True})
        elif "/trainer/problem-topics" in url:
            fulfill(route, {"topics": []})
        elif "/trainer/analytics" in url:
            if mode == "analytics-error":
                fulfill(route, {"detail": "fixture failure"}, status=500)
            elif mode == "analytics-empty":
                fulfill(route, {"my_top": []})
            else:
                fulfill(route, ANALYTICS)
        elif "/trainer/srez/start" in url:
            if mode == "srez-start-error":
                fulfill(route, {"detail": "fixture failure"}, status=500)
            elif mode == "srez-empty":
                fulfill(route, {"tasks": []})
            elif mode == "srez-one":
                fulfill(route, {"tasks": [{**SREZ[0], "total": 1}]})
            else:
                fulfill(route, {"tasks": SREZ})
        elif "/trainer/srez/answer" in url:
            if mode == "srez-answer-error":
                fulfill(route, {"detail": "fixture failure"}, status=500)
            else:
                fulfill(route, {"is_correct": mode == "srez-correct"})
        elif "/trainer/verification/start" in url:
            if mode == "closure-start-error":
                fulfill(route, {"detail": "fixture failure"}, status=500)
            else:
                fulfill(route, VERIFICATION)
        elif "/trainer/verification/answer" in url:
            if mode == "closure-answer-error":
                fulfill(route, {"detail": "fixture failure"}, status=500)
            else:
                fulfill(route, {"correct": mode == "closure-correct"})
        else:
            unexpected.append(url)
            fulfill(route, {"detail": "unexpected fixture request"}, status=501)

    return handle


def inspect(page: Page) -> dict[str, Any]:
    return page.evaluate(
        """
        () => {
          const visible = (el) => {
            const style = getComputedStyle(el)
            const rect = el.getBoundingClientRect()
            return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0
          }
          const inViewport = (el) => {
            const rect = el.getBoundingClientRect()
            return visible(el) && rect.bottom > 0 && rect.top < innerHeight && rect.right > 0 && rect.left < innerWidth
          }
          const controls = [...document.querySelectorAll('button,a,input,summary')].filter(visible)
          const inputs = [...document.querySelectorAll('input:not([type=file])')].filter(visible)
          const images = [...document.querySelectorAll('img')].filter(visible)
          const squirrels = images.filter((img) => img.currentSrc.includes('squirrel-'))
          const resources = performance.getEntriesByType('resource').map((entry) => entry.name)
          const primary = [...document.querySelectorAll('button,a')].filter((el) =>
            /Продолжить|Разобрать|Проверить|Начать|сегодняшнему плану/i.test(el.textContent || '') && inViewport(el)
          )
          const active = document.activeElement
          const activeStyle = active ? getComputedStyle(active) : null
          const doneNode = document.querySelector('.solution-ladder__node--done')
          const doneStyle = doneNode ? getComputedStyle(doneNode) : null
          return {
            overflowX: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) > innerWidth + 1,
            scrollHeight: document.documentElement.scrollHeight,
            imagesLoaded: images.every((img) => img.complete && img.naturalWidth > 0),
            badAssetLoaded: resources.some((url) => /aiplus-logo-lockup|mascot-(coach|celebrate)/.test(url)),
            squirrelCount: squirrels.length,
            maxSquirrelViewportRatio: squirrels.length ? Math.max(...squirrels.map((img) => {
              const rect = img.getBoundingClientRect()
              return (rect.width * rect.height) / (innerWidth * innerHeight)
            })) : 0,
            minControlHeight: controls.length ? Math.min(...controls.map((el) => el.getBoundingClientRect().height)) : null,
            minInputFont: inputs.length ? Math.min(...inputs.map((el) => parseFloat(getComputedStyle(el).fontSize))) : null,
            h1: document.querySelectorAll('h1').length,
            main: [...document.querySelectorAll('main,[role=main]')].filter(visible).length,
            primaryInViewport: primary.length,
            fontOnest: document.fonts.check('600 20px "Onest"', 'Разбор Ә Ғ Қ Ң Ө Ұ Ү Һ І'),
            fontTektur: document.fonts.check('600 20px "Tektur"', 'Шаг 02'),
            reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches,
            activeElement: active ? {
              tag: active.tagName,
              id: active.id,
              text: (active.textContent || '').trim().slice(0, 100),
              outlineWidth: activeStyle.outlineWidth,
              outlineStyle: activeStyle.outlineStyle,
            } : null,
            doneMotion: doneStyle ? {
              animationName: doneStyle.animationName,
              animationDuration: doneStyle.animationDuration,
            } : null,
          }
        }
        """
    )


def run_action(page: Page, action: str | None) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    if action is None:
        return evidence
    if action.startswith("auth-"):
        page.get_by_label("Номер телефона").fill("+7 700 123 45 67")
        page.get_by_role("button", name="Продолжить").click()
        page.wait_for_timeout(220)
        if action != "auth-error":
            page.get_by_label("Имя").fill("Аян")
            page.get_by_role("button", name="Далее").click()
            page.wait_for_timeout(120)
        if action == "auth-pin":
            page.get_by_role("radio", name="6").click()
            page.get_by_role("button", name="Далее").click()
            page.wait_for_timeout(120)
    elif action.startswith("drill-"):
        field = page.get_by_label("Введите ответ")
        field.fill("1" if action != "drill-solved" and action != "drill-finished" else "180")
        page.get_by_role("button", name="Проверить шаг").click()
        page.wait_for_timeout(180)
        if action == "drill-inserted":
            page.get_by_label("Введите ответ").fill("2")
            page.get_by_role("button", name="Проверить шаг").click()
            page.wait_for_timeout(220)
        elif action == "drill-finished":
            evidence["focusAfterStep1"] = page.locator(":focus").text_content()
            page.get_by_label("Введите ответ").fill("1380")
            page.get_by_role("button", name="Проверить шаг").click()
            page.wait_for_timeout(160)
            page.get_by_role("button", name="новая цена").click()
            page.wait_for_timeout(220)
        if action == "drill-solved":
            evidence["focusAfterStep"] = page.locator(":focus").text_content()
    elif action in {"srez-answer", "srez-network", "srez-finish"}:
        field = page.get_by_label("Введите ответ")
        value = "84" if action == "srez-network" else "42"
        field.fill(value)
        page.get_by_role("button", name="Проверить").click()
        page.wait_for_timeout(260)
        evidence["preservedValue"] = field.input_value()
        if action == "srez-finish":
            page.get_by_role("button", name="Следующий вопрос").click()
            page.wait_for_timeout(180)
    elif action in {"closure-answer", "closure-network"}:
        field = page.get_by_label("Введите ответ контрольной")
        value = "800" if action == "closure-answer" else "1377"
        field.fill(value)
        page.get_by_role("button", name="Проверить решение").click()
        page.wait_for_timeout(260)
        evidence["preservedValue"] = field.input_value() if action == "closure-network" else value
    elif action == "keyboard-focus":
        page.keyboard.press("Tab")
        page.wait_for_timeout(80)
    return evidence


def main() -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {}
    failures: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=str(CHROME))
        for scenario in (*BASELINES, *STATES):
            for width in scenario.widths:
                height = 844 if width == 375 else 900
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    color_scheme="light",
                    reduced_motion="reduce" if scenario.reduced_motion else "no-preference",
                    device_scale_factor=1,
                    service_workers="block",
                )
                unexpected: list[str] = []
                context.route("**/api/**", api_handler(scenario.mode, unexpected))
                if scenario.authenticated:
                    context.add_init_script("localStorage.setItem('kodi.jwt', 'visual-test')")
                if scenario.pending_endpoint:
                    context.add_init_script(
                        f"""
                        (() => {{
                          const endpoint = {json.dumps(scenario.pending_endpoint)}
                          const nativeFetch = window.fetch.bind(window)
                          window.fetch = (...args) => {{
                            const input = args[0]
                            const url = typeof input === 'string' ? input : input.url
                            if (url.includes(endpoint)) return new Promise(() => {{}})
                            return nativeFetch(...args)
                          }}
                        }})()
                        """
                    )

                page = context.new_page()
                console_errors: list[str] = []
                request_failures: list[str] = []
                page.on("pageerror", lambda error: console_errors.append(f"pageerror: {error}"))
                page.on("console", lambda message: console_errors.append(f"console: {message.text}") if message.type == "error" else None)
                page.on("requestfailed", lambda request: request_failures.append(f"{request.method} {request.url}: {request.failure}"))

                page.goto(f"{BASE}/app{scenario.path}", wait_until="domcontentloaded")
                wait = 2200 if scenario.mode.endswith("error") or scenario.mode in {"hub-error", "drill-error", "analytics-error"} else 360
                page.wait_for_timeout(wait)
                page.evaluate(
                    """async () => Promise.all([
                      document.fonts.load('600 20px "Onest"', 'Разбор Ә Ғ Қ Ң Ө Ұ Ү Һ І'),
                      document.fonts.load('600 20px "Tektur"', 'Шаг 02')
                    ])"""
                )
                action_evidence = run_action(page, scenario.action)
                details = inspect(page)
                key = f"{width}-{scenario.name}"
                expected_http_error = scenario.mode.endswith("error")
                unexpected_console = [
                    error for error in console_errors
                    if not (expected_http_error and "status of 500" in error)
                ]
                report[key] = {
                    "details": details,
                    "actionEvidence": action_evidence,
                    "consoleErrors": console_errors,
                    "unexpectedConsoleErrors": unexpected_console,
                    "requestFailures": request_failures,
                    "unexpectedApi": unexpected,
                }
                page.screenshot(path=str(SHOTS / f"{key}.png"), full_page=False)

                if unexpected_console:
                    failures.append(f"{key}: {'; '.join(unexpected_console)}")
                if request_failures and not scenario.pending_endpoint:
                    failures.append(f"{key}: {'; '.join(request_failures)}")
                if unexpected:
                    failures.append(f"{key}: unexpected API {'; '.join(unexpected)}")
                if details["overflowX"]:
                    failures.append(f"{key}: horizontal overflow")
                if not details["imagesLoaded"]:
                    failures.append(f"{key}: image load failure")
                if details["badAssetLoaded"]:
                    failures.append(f"{key}: rejected legacy asset loaded")
                if details["squirrelCount"] > 1:
                    failures.append(f"{key}: mascot budget {details['squirrelCount']}")
                if details["minControlHeight"] is not None and details["minControlHeight"] < 44:
                    failures.append(f"{key}: touch target {details['minControlHeight']}")
                if details["minInputFont"] is not None and details["minInputFont"] < 16:
                    failures.append(f"{key}: input font {details['minInputFont']}")
                if details["main"] != 1:
                    failures.append(f"{key}: main landmarks {details['main']}")
                if not details["fontOnest"] or not details["fontTektur"]:
                    failures.append(f"{key}: font probe failed")
                if scenario.action == "closure-network" and action_evidence.get("preservedValue") != "1377":
                    failures.append(f"{key}: closure input was not preserved")
                if scenario.action == "srez-network" and action_evidence.get("preservedValue") != "84":
                    failures.append(f"{key}: srez input was not preserved")
                context.close()
        browser.close()

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "mechanical.txt").write_text("PASS\n" if not failures else "FAIL\n" + "\n".join(failures), encoding="utf-8")
    if failures:
        raise RuntimeError("Render matrix failed:\n- " + "\n- ".join(failures))
    print(f"Rendered {len(report)} production states to {SHOTS}")


if __name__ == "__main__":
    main()
