"""Render-smoke v7 на реальных Chromium viewport 375/1280 с API-фикстурами."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from playwright.sync_api import BrowserContext, Page, Route, sync_playwright


BASE = os.environ.get("KODI_RENDER_BASE", "http://127.0.0.1:5173")
OUT = Path(__file__).parent / "renders"
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
        {
            "n": 1,
            "instruction_ru": "Сколько тенге составляет рост на $15\\%$ от $1200$?",
            "micro_skill": "percent_of_number",
            "micro_skill_label": "Процент от числа",
            "expected_value": "180",
            "kind": "compute",
            "reveal": "$1200 \\cdot 0{,}15 = 180$ ₸.",
        },
        {
            "n": 2,
            "instruction_ru": "Какой стала цена после роста?",
            "micro_skill": "add_percent",
            "micro_skill_label": "Прибавить процент",
            "expected_value": "1380",
            "kind": "compute",
            "reveal": "$1200 + 180 = 1380$ ₸.",
        },
        {
            "n": 3,
            "instruction_ru": "Снижение считаем от новой или старой цены?",
            "micro_skill": "percent_base",
            "micro_skill_label": "База процента",
            "expected_value": "новая",
            "kind": "choose",
            "reveal": "От новой цены.",
        },
    ],
}

SREZ = [
    {
        "problem_id": 9001,
        "node_title": "Цифры числа и разряды",
        "statement": "Найдите двузначное число, если оно равно удвоенному произведению своих цифр.",
        "answer_type": "number",
        "position": 1,
        "total": 12,
    },
    {
        "problem_id": 9002,
        "node_title": "Проценты",
        "statement": "Какое число составляет $40\\%$ от $250$?",
        "answer_type": "number",
        "position": 2,
        "total": 12,
    },
]


def json_response(route: Route, body: Any) -> None:
    route.fulfill(status=200, content_type="application/json", body=json.dumps(body, ensure_ascii=False))


def handle_api(route: Route) -> None:
    url = route.request.url
    if "/api/auth/me" in url:
        json_response(
            route,
            {
                "id": 1,
                "first_name": "Аян",
                "last_name": None,
                "username": None,
                "full_name": "Аян",
                "lang": "ru",
                "grade": 7,
                "registered": True,
                "diagnostic_complete": True,
                "has_paused_diagnostic": False,
                "photo_consent": None,
            },
        )
    elif "/trainer/wrong-tasks" in url:
        json_response(route, {"tasks": [TASK, {**TASK, "id": "wt-fr-02", "problem_id": 5093, "topic_label": "Дроби", "statement": "Вычислите $\\dfrac{3}{4} + \\dfrac{5}{6}$.", "wrong_answer": "13/12", "state": "almost"}], "has_activity": True})
    elif "/trainer/problem-topics" in url:
        json_response(route, {"topics": [{"topic_id": "PC", "strand": "Числа", "name_ru": "Проценты", "error_count": 7, "top_micro_skills": [], "nodes_mastery_avg": 0.34, "closure_progress": 0.25}]})
    elif "/trainer/analytics" in url:
        json_response(route, {"my_top": [
            {"micro_skill": "percent_base", "label_ru": "База процента", "error_count": 7, "last_cause_text": "снижение посчитано от старой цены", "node_id": "PC02"},
            {"micro_skill": "common_denominator", "label_ru": "Общий знаменатель", "error_count": 5, "last_cause_text": None, "node_id": "FR04"},
            {"micro_skill": "distribute_terms", "label_ru": "Раскрытие скобок", "error_count": 3, "last_cause_text": None, "node_id": "LE01"},
        ]})
    elif "/trainer/srez/start" in url:
        json_response(route, {"tasks": SREZ})
    elif "/trainer/srez/answer" in url:
        json_response(route, {"is_correct": False})
    elif "/trainer/verification/start" in url:
        json_response(route, {"problem_id": 4899, "node_id": "PC02", "topic_label": "Проценты", "statement": "Цена $800$ ₸ выросла на $25\\%$, затем снизилась на $20\\%$. Найдите итоговую цену.", "micro_skill": "percent_of_change", "micro_skill_label": "Изменение на процент", "xp": 30})
    elif "/trainer/verification/answer" in url:
        json_response(route, {"correct": False})
    else:
        json_response(route, {})


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
          const h1 = document.querySelector('h1');
          return {
            title: document.title,
            bodyScrollWidth: body.scrollWidth,
            rootClientWidth: root.clientWidth,
            overflow: Math.max(body.scrollWidth, root.scrollWidth) > root.clientWidth + 1,
            alumniCyrillic: document.fonts.check('900 32px "Alumni Sans"', 'Разбор'),
            alumniKazakh: document.fonts.check('900 32px "Alumni Sans"', 'Ң'),
            h1Font: h1 ? getComputedStyle(h1).fontFamily : null,
            activeText: document.activeElement?.getAttribute('aria-label') || document.activeElement?.textContent?.trim().slice(0, 80) || null,
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
          return {
            tag: el?.tagName || null,
            type: el?.getAttribute('type') || null,
            label: el?.getAttribute('aria-label') || el?.textContent?.trim().slice(0, 80) || null,
            outlineStyle: style?.outlineStyle || null,
            outlineWidth: style?.outlineWidth || null,
          };
        }"""
    )


def render_context(context: BrowserContext, width: int, report: dict[str, Any]) -> None:
    page = context.new_page()
    errors: list[str] = []
    failed: list[str] = []
    attach_diagnostics(page, errors, failed)

    routes = [
        ("hub", "/app/"),
        ("srez", "/app/srez"),
        ("drill", "/app/drill/wt-pc-01"),
        ("analytics", "/app/analytics"),
        ("closure", "/app/closure/wt-pc-01"),
    ]
    for name, path in routes:
        page.goto(BASE + path, wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(1100)
        details = inspect_page(page)
        page.screenshot(path=OUT / f"{width}-{name}.png", full_page=True)
        details["keyboardFocus"] = keyboard_focus(page)
        report[f"{width}-{name}"] = details

        if name == "srez":
            page.get_by_label("Введите ответ").fill("10")
            page.get_by_role("button", name="Проверить").click()
            page.get_by_role("button", name="Следующий вопрос").wait_for()
            page.screenshot(path=OUT / f"{width}-srez-feedback.png", full_page=True)

    page.emulate_media(reduced_motion="reduce")
    page.goto(BASE + "/app/", wait_until="networkidle")
    report[f"{width}-reduced-motion"] = page.locator(".reveal").first.evaluate(
        "el => ({animationName: getComputedStyle(el).animationName, transitionDuration: getComputedStyle(el).transitionDuration})"
    )
    report[f"{width}-errors"] = errors
    report[f"{width}-request-failures"] = failed
    page.close()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=CHROMIUM)

        for width, height in ((375, 844), (1280, 900)):
            auth = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=1)
            auth.route("**/api/**", handle_api)
            auth.add_init_script("localStorage.setItem('kodi.jwt', 'visual-test')")
            render_context(auth, width, report)
            auth.close()

            anon = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=1)
            anon.route("**/api/**", handle_api)
            login = anon.new_page()
            login_errors: list[str] = []
            login_failed: list[str] = []
            attach_diagnostics(login, login_errors, login_failed)
            login.goto(BASE + "/app/login", wait_until="networkidle")
            login.evaluate("document.fonts.ready")
            login.wait_for_timeout(1100)
            report[f"{width}-login"] = inspect_page(login)
            report[f"{width}-login-errors"] = login_errors
            report[f"{width}-login-request-failures"] = login_failed
            login.screenshot(path=OUT / f"{width}-login.png", full_page=True)
            report[f"{width}-login"]["keyboardFocus"] = keyboard_focus(login)
            anon.close()

        browser.close()

    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    failures = [key for key, value in report.items() if key.endswith(("-errors", "-request-failures")) and value]
    overflow = [key for key, value in report.items() if isinstance(value, dict) and value.get("overflow")]
    fonts = [key for key, value in report.items() if isinstance(value, dict) and "alumniCyrillic" in value and (not value["alumniCyrillic"] or not value["alumniKazakh"])]
    if failures or overflow or fonts:
        raise SystemExit(f"render gate failed: failures={failures}, overflow={overflow}, fonts={fonts}")
    print(f"render gate passed: {len(report)} checks, output={OUT}")


if __name__ == "__main__":
    main()
