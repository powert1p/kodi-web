"""Production render-smoke V8: Chromium 375/1280, API fixtures and state gates."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from playwright.sync_api import BrowserContext, Page, Route, sync_playwright


BASE = os.environ.get("KODI_RENDER_BASE", "http://127.0.0.1:5173")
OUT = Path(__file__).parent / "renders" / "react"
CHROMIUM = os.environ.get(
    "PLAYWRIGHT_CHROMIUM_EXECUTABLE",
    str(
        Path.home()
        / "Library/Caches/ms-playwright/chromium-1217/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
    ),
)

TASK = {
    "id": "wt-pc-01",
    "problem_id": 4821,
    "node_id": "PC02",
    "topic_label": "Проценты",
    "statement": "Цена товара $1200$ ₸ выросла на $15\\%$, а затем снизилась на $10\\%$. Найдите итоговую цену.",
    "answer": "1242",
    "primary_micro_skill": "percent_of_change",
    "primary_micro_skill_label": "Изменение на процент",
    "decomp_idx": 0,
    "state": "revisit",
    "wrong_answer": "1230",
    "mastery": 0.31,
    "theory_ru": "**Метод** — каждый процент считается от актуальной величины. Второе изменение применяй к результату первого.\n\n**Ловушка** — считать оба процента от начальной цены.",
    "steps": [
        {"n": 1, "instruction_ru": "Сколько тенге составляет рост на $15\\%$ от $1200$?", "micro_skill": "percent_of_number", "micro_skill_label": "Процент от числа", "expected_value": "180", "kind": "compute", "reveal": "$1200 \\cdot 0{,}15 = 180$ ₸."},
        {"n": 2, "instruction_ru": "Какой стала цена после роста?", "micro_skill": "add_percent", "micro_skill_label": "Прибавить процент", "expected_value": "1380", "kind": "compute", "reveal": "$1200 + 180 = 1380$ ₸."},
        {"n": 3, "instruction_ru": "Снижение считаем от новой или старой цены?", "micro_skill": "percent_base", "micro_skill_label": "База процента", "expected_value": "новая", "kind": "choose", "reveal": "От новой цены."},
    ],
}

SECOND_TASK = {
    **TASK,
    "id": "wt-fr-02",
    "problem_id": 5093,
    "topic_label": "Дроби",
    "statement": "Вычислите $\\dfrac{3}{4} + \\dfrac{5}{6}$.",
    "wrong_answer": "13/12",
    "state": "almost",
}

SREZ = [
    {"problem_id": 9001, "node_title": "Цифры числа и разряды", "statement": "Найдите двузначное число, если оно равно удвоенному произведению своих цифр.", "answer_type": "number", "position": 1, "total": 12},
    {"problem_id": 9002, "node_title": "Проценты", "statement": "Какое число составляет $40\\%$ от $250$?", "answer_type": "number", "position": 2, "total": 12},
]


def json_response(route: Route, body: Any, status: int = 200) -> None:
    route.fulfill(status=status, content_type="application/json", body=json.dumps(body, ensure_ascii=False))


def api_handler(mode: str = "normal") -> Callable[[Route], None]:
    def handle(route: Route) -> None:
        url = route.request.url
        if "/api/auth/me" in url:
            json_response(route, {"id": 1, "first_name": "Аян", "last_name": None, "username": None, "full_name": "Аян", "lang": "ru", "grade": 7, "registered": True, "diagnostic_complete": True, "has_paused_diagnostic": False, "photo_consent": None})
        elif "/trainer/wrong-tasks" in url:
            if mode == "hub-error":
                json_response(route, {"detail": "temporary"}, status=503)
            else:
                json_response(route, {"tasks": [] if mode == "hub-empty" else [TASK, SECOND_TASK], "has_activity": True})
        elif "/trainer/problem-topics" in url:
            json_response(route, {"topics": [{"topic_id": "PC", "strand": "Числа", "name_ru": "Проценты", "error_count": 7, "top_micro_skills": [], "nodes_mastery_avg": 0.34, "closure_progress": 0.25}]})
        elif "/trainer/analytics" in url:
            items = [] if mode == "analytics-empty" else [
                {"micro_skill": "percent_base", "label_ru": "База процента", "error_count": 7, "last_cause_text": "снижение посчитано от старой цены", "node_id": "PC02"},
                {"micro_skill": "common_denominator", "label_ru": "Общий знаменатель", "error_count": 5, "last_cause_text": None, "node_id": "FR04"},
                {"micro_skill": "distribute_terms", "label_ru": "Раскрытие скобок", "error_count": 3, "last_cause_text": None, "node_id": "LE01"},
            ]
            json_response(route, {"my_top": items})
        elif "/trainer/srez/start" in url:
            json_response(route, {"tasks": [] if mode == "srez-empty" else SREZ})
        elif "/trainer/srez/answer" in url:
            json_response(route, {"is_correct": False})
        elif "/trainer/verification/start" in url:
            json_response(route, {"problem_id": 4899, "node_id": "PC02", "topic_label": "Проценты", "statement": "Цена $800$ ₸ выросла на $25\\%$, затем снизилась на $20\\%$. Найдите итоговую цену.", "micro_skill": "percent_of_change", "micro_skill_label": "Изменение на процент", "xp": 30})
        elif "/trainer/verification/answer" in url:
            json_response(route, {"correct": False})
        else:
            json_response(route, {})
    return handle


def attach_diagnostics(page: Page, errors: list[str], failed: list[str]) -> None:
    page.on("pageerror", lambda error: errors.append(f"pageerror: {error}"))
    page.on("console", lambda message: errors.append(f"console: {message.text}") if message.type == "error" else None)
    page.on("requestfailed", lambda request: failed.append(f"{request.method} {request.url}: {request.failure}"))


def inspect_page(page: Page) -> dict[str, Any]:
    return page.evaluate(
        """async () => {
          await document.fonts.ready;
          const root = document.documentElement;
          const body = document.body;
          const visible = [...document.querySelectorAll('button,a,input,textarea,select,summary')]
            .filter((el) => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; });
          const smallTargets = visible.map((el) => { const r = el.getBoundingClientRect(); return {tag: el.tagName, label: el.getAttribute('aria-label') || el.textContent?.trim().slice(0,50), w: Math.round(r.width), h: Math.round(r.height)}; })
            .filter((item) => item.w < 44 || item.h < 44);
          const h1 = document.querySelector('h1');
          const primary = [...document.querySelectorAll('button')].find((el) => getComputedStyle(el).backgroundColor === 'rgb(215, 248, 58)');
          const primaryRect = primary?.getBoundingClientRect();
          return {
            title: document.title,
            bodyScrollWidth: body.scrollWidth,
            rootClientWidth: root.clientWidth,
            overflow: Math.max(body.scrollWidth, root.scrollWidth) > root.clientWidth + 1,
            tekturLoaded: document.fonts.check('800 32px "Tektur"', 'KODI Проценты Ң'),
            onestLoaded: document.fonts.check('600 20px "Onest"', 'Разбор решения'),
            h1Font: h1 ? getComputedStyle(h1).fontFamily : null,
            proofNodes: document.querySelectorAll('.proof-trace__node').length,
            smallTargets,
            primaryInViewport: primaryRect ? primaryRect.top >= 0 && primaryRect.bottom <= innerHeight : null,
          };
        }"""
    )


def keyboard_focus(page: Page) -> dict[str, Any]:
    page.mouse.click(2, 2)
    page.keyboard.press("Tab")
    return page.evaluate(
        """() => {
          const el = document.activeElement;
          const style = el ? getComputedStyle(el) : null;
          return {tag: el?.tagName || null, label: el?.getAttribute('aria-label') || el?.textContent?.trim().slice(0,80) || null, outlineStyle: style?.outlineStyle || null, outlineWidth: style?.outlineWidth || null};
        }"""
    )


def render_main(context: BrowserContext, width: int, report: dict[str, Any]) -> None:
    page = context.new_page()
    errors: list[str] = []
    failed: list[str] = []
    attach_diagnostics(page, errors, failed)
    routes = [
        ("hub", "/app/"),
        ("drill", "/app/drill/wt-pc-01"),
        ("srez", "/app/srez"),
        ("closure", "/app/closure/wt-pc-01"),
        ("closure-success", "/app/closure/wt-pc-01?dev=celebrate"),
        ("analytics", "/app/analytics"),
    ]
    for name, path in routes:
        page.goto(BASE + path, wait_until="networkidle")
        page.wait_for_timeout(850)
        details = inspect_page(page)
        details["keyboardFocus"] = keyboard_focus(page)
        report[f"{width}-{name}"] = details
        page.screenshot(path=OUT / f"{width}-{name}.png", full_page=True)
        if name == "srez":
            page.get_by_label("Введите ответ").fill("10")
            page.get_by_role("button", name="Проверить").click()
            page.get_by_role("button", name="Следующий вопрос").wait_for()
            report[f"{width}-srez-feedback"] = inspect_page(page)
            page.screenshot(path=OUT / f"{width}-srez-feedback.png", full_page=True)

    page.emulate_media(reduced_motion="reduce")
    page.goto(BASE + "/app/", wait_until="networkidle")
    report[f"{width}-reduced-motion"] = page.locator(".proof-trace__line").first.evaluate(
        "el => ({animationName: getComputedStyle(el).animationName, strokeDashoffset: getComputedStyle(el).strokeDashoffset})"
    )
    report[f"{width}-errors"] = errors
    report[f"{width}-request-failures"] = failed
    page.close()


def render_state(browser: Any, name: str, mode: str, path: str, init_script: str | None = None) -> dict[str, Any]:
    context = browser.new_context(viewport={"width": 375, "height": 844}, device_scale_factor=1)
    context.route("**/api/**", api_handler(mode))
    context.add_init_script("localStorage.setItem('kodi.jwt', 'visual-test')")
    if init_script:
        context.add_init_script(init_script)
    page = context.new_page()
    errors: list[str] = []
    failed: list[str] = []
    attach_diagnostics(page, errors, failed)
    page.goto(BASE + path, wait_until="domcontentloaded")
    page.wait_for_timeout(700)
    details = inspect_page(page)
    details["errors"] = [error for error in errors if not (mode == "hub-error" and "503" in error)]
    details["requestFailures"] = failed
    page.screenshot(path=OUT / f"375-{name}.png", full_page=True)
    context.close()
    return details


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=CHROMIUM)
        for width, height in ((375, 844), (1280, 900)):
            auth = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=1)
            auth.route("**/api/**", api_handler())
            auth.add_init_script("localStorage.setItem('kodi.jwt', 'visual-test')")
            render_main(auth, width, report)
            auth.close()

            anon = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=1)
            anon.route("**/api/**", api_handler())
            login = anon.new_page()
            login_errors: list[str] = []
            login_failed: list[str] = []
            attach_diagnostics(login, login_errors, login_failed)
            login.goto(BASE + "/app/login", wait_until="networkidle")
            login.wait_for_timeout(850)
            report[f"{width}-login"] = inspect_page(login)
            report[f"{width}-login"]["keyboardFocus"] = keyboard_focus(login)
            report[f"{width}-login-errors"] = login_errors
            report[f"{width}-login-request-failures"] = login_failed
            login.screenshot(path=OUT / f"{width}-login.png", full_page=True)
            anon.close()

        report["375-hub-loading"] = render_state(
            browser,
            "hub-loading",
            "normal",
            "/app/",
            """const nativeFetch = window.fetch.bind(window); window.fetch = (input, init) => String(input).includes('/trainer/wrong-tasks') ? new Promise(() => {}) : nativeFetch(input, init);""",
        )
        report["375-hub-error"] = render_state(browser, "hub-error", "hub-error", "/app/")
        report["375-hub-empty"] = render_state(browser, "hub-empty", "hub-empty", "/app/")
        report["375-analytics-empty"] = render_state(browser, "analytics-empty", "analytics-empty", "/app/analytics")
        report["375-srez-empty"] = render_state(browser, "srez-empty", "srez-empty", "/app/srez")
        browser.close()

    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    failures = [key for key, value in report.items() if key.endswith(("-errors", "-request-failures")) and value]
    failures += [key for key, value in report.items() if isinstance(value, dict) and value.get("errors")]
    overflow = [key for key, value in report.items() if isinstance(value, dict) and value.get("overflow")]
    fonts = [key for key, value in report.items() if isinstance(value, dict) and "tekturLoaded" in value and (not value["tekturLoaded"] or not value["onestLoaded"])]
    touch = [key for key, value in report.items() if isinstance(value, dict) and value.get("smallTargets")]
    if failures or overflow or fonts or touch:
        raise SystemExit(f"render gate failed: failures={failures}, overflow={overflow}, fonts={fonts}, touch={touch}")
    print(f"render gate passed: {len(report)} checks, output={OUT}")


if __name__ == "__main__":
    main()
