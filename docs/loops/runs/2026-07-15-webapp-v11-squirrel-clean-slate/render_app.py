"""Production render harness for v11. Generates real React renders with API fixtures."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from playwright.sync_api import Route, sync_playwright


ROOT = Path(__file__).resolve().parent
OUT = ROOT / os.environ.get("KODI_RENDER_ROUND", "round-production-0")
BASE = os.environ.get("KODI_RENDER_BASE", "http://127.0.0.1:5173")
CHROME = Path.home() / (
    "Library/Caches/ms-playwright/chromium-1228/chrome-mac-arm64/"
    "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
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
    "theory_ru": "**Метод** — каждый процент считается от актуальной величины.",
    "steps": [
        {"n": 1, "instruction_ru": "Сколько тенге составляет рост на $15\\%$ от $1200$?", "micro_skill": "percent_of_number", "micro_skill_label": "Процент от числа", "expected_value": "180", "kind": "compute", "reveal": "$1200 \\cdot 0{,}15 = 180$ ₸."},
        {"n": 2, "instruction_ru": "Какой стала цена после роста?", "micro_skill": "add_percent", "micro_skill_label": "Прибавить процент", "expected_value": "1380", "kind": "compute", "reveal": "$1200 + 180 = 1380$ ₸."},
        {"n": 3, "instruction_ru": "Снижение считаем от новой цены или от старой?", "micro_skill": "percent_base", "micro_skill_label": "База процента", "expected_value": "новая", "kind": "choose", "reveal": "От новой цены $1380$."},
    ],
}

SECOND = {
    **TASK,
    "id": "wt-fr-02",
    "problem_id": 5093,
    "node_id": "FR04",
    "topic_label": "Дроби",
    "statement": "Вычислите $\\dfrac{3}{4} + \\dfrac{5}{6} - \\dfrac{2}{3}$.",
    "answer": "11/12",
    "wrong_answer": "13/12",
    "state": "almost",
    "steps": [],
    "theory_ru": None,
}

PROFILE = {
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
}

SREZ = [
    {"problem_id": 9001, "node_title": "Цифры числа и разряды", "statement": "Найдите двузначное число, если оно равно удвоенному произведению своих цифр.", "answer_type": "number", "position": 1, "total": 12},
    {"problem_id": 9002, "node_title": "Проценты", "statement": "Какое число составляет $40\\%$ от $250$?", "answer_type": "number", "position": 2, "total": 12},
]

ANALYTICS = {
    "my_top": [
        {"micro_skill": "percent_base", "label_ru": "База процента", "error_count": 7, "last_cause_text": "снижение посчитано от старой цены", "node_id": "PC02"},
        {"micro_skill": "common_denominator", "label_ru": "Общий знаменатель", "error_count": 5, "last_cause_text": None, "node_id": "FR04"},
        {"micro_skill": "distribute_terms", "label_ru": "Раскрытие скобок", "error_count": 3, "last_cause_text": None, "node_id": "LE01"},
    ]
}

VERIFICATION = {
    "problem_id": 4899,
    "node_id": "PC02",
    "topic_label": "Проценты",
    "statement": "Цена $800$ ₸ выросла на $25\\%$, затем снизилась на $20\\%$. Найдите итоговую цену.",
    "micro_skill": "percent_of_change",
    "micro_skill_label": "Изменение на процент",
    "xp": 30,
}


def fulfill(route: Route, payload: Any, status: int = 200) -> None:
    route.fulfill(status=status, content_type="application/json", body=json.dumps(payload, ensure_ascii=False))


def api(route: Route) -> None:
    url = route.request.url
    if "/api/auth/me" in url:
        fulfill(route, PROFILE)
    elif "/trainer/wrong-tasks" in url:
        fulfill(route, {"tasks": [TASK, SECOND], "has_activity": True})
    elif "/trainer/problem-topics" in url:
        fulfill(route, {"topics": []})
    elif "/trainer/analytics" in url:
        fulfill(route, ANALYTICS)
    elif "/trainer/srez/start" in url:
        fulfill(route, {"tasks": SREZ})
    elif "/trainer/srez/answer" in url:
        fulfill(route, {"is_correct": False})
    elif "/trainer/verification/start" in url:
        fulfill(route, VERIFICATION)
    elif "/trainer/verification/answer" in url:
        fulfill(route, {"correct": False})
    else:
        fulfill(route, {})


def inspect(page) -> dict[str, Any]:
    return page.evaluate(
        """
        () => {
          const visible = (el) => {
            const style = getComputedStyle(el)
            const rect = el.getBoundingClientRect()
            return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0
          }
          const controls = [...document.querySelectorAll('button,a,input,summary')].filter(visible)
          const inputs = [...document.querySelectorAll('input:not([type=file])')].filter(visible)
          const images = [...document.querySelectorAll('img')].filter(visible)
          return {
            overflowX: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) > innerWidth + 1,
            scrollHeight: document.documentElement.scrollHeight,
            imagesLoaded: images.every((img) => img.complete && img.naturalWidth > 0),
            minControlHeight: controls.length ? Math.min(...controls.map((el) => el.getBoundingClientRect().height)) : null,
            minInputFont: inputs.length ? Math.min(...inputs.map((el) => parseFloat(getComputedStyle(el).fontSize))) : null,
            h1: document.querySelectorAll('h1').length,
            main: [...document.querySelectorAll('main,[role=main]')].filter(visible).length,
            fontOnest: document.fonts.check('600 20px "Onest"', 'Разбор Ң'),
            fontTektur: document.fonts.check('600 20px "Tektur"', 'Шаг 02'),
          }
        }
        """
    )


SCENARIOS = [
    ("login", "/login", False),
    ("hub", "/", True),
    ("drill", "/drill/wt-pc-01", True),
    ("srez", "/srez", True),
    ("analytics", "/analytics", True),
    ("closure", "/closure/wt-pc-01", True),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {}
    failures: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=str(CHROME))
        for width, height in ((375, 844), (1280, 900)):
            for name, path, authenticated in SCENARIOS:
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    color_scheme="light",
                    reduced_motion="reduce",
                    device_scale_factor=1,
                )
                context.route("**/api/**", api)
                if authenticated:
                    context.add_init_script("localStorage.setItem('kodi.jwt', 'visual-test')")
                page = context.new_page()
                errors: list[str] = []
                page.on("pageerror", lambda error: errors.append(f"pageerror: {error}"))
                page.on("console", lambda message: errors.append(f"console: {message.text}") if message.type == "error" else None)
                page.goto(f"{BASE}/app{path}", wait_until="networkidle")
                page.evaluate("document.fonts.ready")
                page.wait_for_timeout(300)
                details = inspect(page)
                key = f"{width}-{name}"
                report[key] = {"details": details, "errors": errors}
                page.screenshot(path=str(OUT / f"{key}.png"), full_page=False)

                if errors:
                    failures.append(f"{key}: {'; '.join(errors)}")
                if details["overflowX"]:
                    failures.append(f"{key}: horizontal overflow")
                if not details["imagesLoaded"]:
                    failures.append(f"{key}: image load failure")
                if details["minControlHeight"] is not None and details["minControlHeight"] < 44:
                    failures.append(f"{key}: touch target {details['minControlHeight']}")
                if details["minInputFont"] is not None and details["minInputFont"] < 16:
                    failures.append(f"{key}: input font {details['minInputFont']}")
                context.close()
        browser.close()

    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if failures:
        raise RuntimeError("Render gate failed:\n- " + "\n- ".join(failures))
    print(f"Rendered {len(report)} scenarios to {OUT}")


if __name__ == "__main__":
    main()
