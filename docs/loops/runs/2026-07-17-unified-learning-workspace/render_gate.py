#!/usr/bin/env python3
"""Deterministic browser evidence gate for the frozen workspace concept round."""

from __future__ import annotations

import hashlib
import json
import os
from fractions import Fraction
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, Page, sync_playwright


RUN_DIR = Path(__file__).resolve().parent
PROTOTYPE = RUN_DIR / "prototype" / "index.html"
MATRIX_PATH = RUN_DIR / "STATE-MATRIX.json"
RUBRIC_PATH = RUN_DIR / "RUBRIC.md"
OUTPUT_DIR = RUN_DIR / "round-concepts" / "evidence"
SCREENSHOT_DIR = OUTPUT_DIR / "screenshots"
REPORT_PATH = RUN_DIR / "round-concepts" / "MECHANICAL.json"
CHROMIUM = Path(
    os.environ.get(
        "CHROMIUM_EXECUTABLE",
        "/Users/esetseitkamal/Library/Caches/ms-playwright/"
        "chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell",
    )
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> None:
    raise AssertionError(message)


def assert_truth() -> dict[str, str]:
    remainder = Fraction(1, 1) - Fraction(3, 8)
    result = remainder * Fraction(2, 5)
    if remainder != Fraction(5, 8) or result != Fraction(1, 4):
        fail("Frozen fraction fixture is mathematically inconsistent")
    return {"remainder": str(remainder), "result": str(result)}


def browser_checks(page: Page, state: str, viewport: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    console_errors: list[str] = []

    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda error: errors.append(str(error)))

    page.wait_for_load_state("load")
    page.evaluate("document.fonts.ready")

    checks = page.evaluate(
        """({ state, width, height }) => {
          const text = document.body.innerText.toLocaleLowerCase('ru-RU');
          const visible = (el) => {
            const style = getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
          };
          const interactives = [...document.querySelectorAll('button, a, input')].filter(visible);
          const targetFailures = interactives
            .map((el) => ({
              tag: el.tagName,
              name: (el.getAttribute('aria-label') || el.innerText || el.labels?.[0]?.innerText || el.placeholder || '').trim(),
              width: Math.round(el.getBoundingClientRect().width * 10) / 10,
              height: Math.round(el.getBoundingClientRect().height * 10) / 10,
            }))
            .filter((item) => item.width < 44 || item.height < 44);
          const unnamed = interactives
            .filter((el) => !(el.getAttribute('aria-label') || el.innerText || el.labels?.[0]?.innerText || el.placeholder || '').trim())
            .map((el) => el.outerHTML.slice(0, 160));
          const primary = [...document.querySelectorAll('[data-primary="true"]')].filter(visible);
          const requiredText = {
            independent: ['Найди долю всех книг', 'Самостоятельно', 'Сфотографировать решение', 'Ввести только ответ'],
            needs_revision: ['Найди долю всех книг', '2/5', 'Сначала найди, сколько книг осталось', 'Исправить решение', 'Взять подсказку', 'Спросить помощника'],
            hint_h2: ['Найди долю всех книг', 'Подсказка 2 из 4', 'Какой шаг должен быть первым?', 'Вернуться к решению'],
            tutor_open: ['Найди долю всех книг', 'эта задача, шаг 1', 'Твой ответ помощнику', 'Отправить помощнику'],
            uncertain: ['Найди долю всех книг', 'Математический вердикт не вынесен', 'Фото сохранено', 'Переснять фото', 'Ввести нечитабельный фрагмент'],
          }[state];
          const missingText = requiredText.filter((needle) => !text.includes(needle.toLocaleLowerCase('ru-RU')));
          const statement = document.querySelector('.statement');
          const statementSize = parseFloat(getComputedStyle(statement).fontSize);
          const taskVisible = visible(document.querySelector('.task-anchor'));
          const contextVisible = visible(document.querySelector('.contextual-layer'));
          const overflow = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - width;
          const fontFamily = getComputedStyle(document.querySelector('#task-title')).fontFamily;
          const fontsReady = document.fonts.status === 'loaded' && document.fonts.check('18px Onest', 'Доли от оставшейся части');
          return {
            targetFailures,
            unnamed,
            primaryCount: primary.length,
            missingText,
            statementSize,
            taskVisible,
            contextVisible,
            overflow,
            fontFamily,
            fontsReady,
            interactiveCount: interactives.length,
            viewportHeight: height,
          };
        }""",
        {"state": state, "width": viewport["width"], "height": viewport["height"]},
    )

    if checks["targetFailures"]:
        fail(f"Targets below 44px: {checks['targetFailures']}")
    if checks["unnamed"]:
        fail(f"Unnamed interactives: {checks['unnamed']}")
    if checks["primaryCount"] != 1:
        fail(f"Expected exactly one primary CTA, got {checks['primaryCount']}")
    if checks["missingText"]:
        fail(f"Missing state requirements: {checks['missingText']}")
    if checks["statementSize"] < 18:
        fail(f"Math statement below 18px: {checks['statementSize']}")
    if not checks["taskVisible"] or not checks["contextVisible"]:
        fail("Task or contextual layer is not visible")
    if checks["overflow"] > 1:
        fail(f"Horizontal overflow: {checks['overflow']}px")
    if not checks["fontsReady"]:
        fail("Required Cyrillic font did not load")
    if errors or console_errors:
        fail(f"Browser errors: page={errors}, console={console_errors}")

    focus = page.evaluate(
        """async () => {
          const visible = (el) => {
            const style = getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
          };
          const elements = [...document.querySelectorAll('button, a, input')].filter(visible);
          const failures = [];
          for (const el of elements) {
            el.focus({ preventScroll: true });
            el.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
            await new Promise((resolve) => requestAnimationFrame(resolve));
            const rect = el.getBoundingClientRect();
            const dock = document.querySelector('.response-dock');
            const dockRect = dock.getBoundingClientRect();
            const isDockChild = dock.contains(el);
            const obscuredByDock = !isDockChild && getComputedStyle(dock).position === 'fixed' && rect.bottom > dockRect.top - 3;
            const outside = rect.top < 0 || rect.bottom > innerHeight || rect.left < 0 || rect.right > innerWidth;
            if (document.activeElement !== el || obscuredByDock || outside) {
              failures.push({
                name: (el.getAttribute('aria-label') || el.innerText || el.placeholder || el.tagName).trim(),
                active: document.activeElement === el,
                obscuredByDock,
                outside,
                rect: { top: rect.top, bottom: rect.bottom, left: rect.left, right: rect.right },
              });
            }
          }
          window.scrollTo(0, 0);
          return { checked: elements.length, failures };
        }"""
    )
    if focus["failures"]:
        fail(f"Focus visibility/obstruction failures: {focus['failures']}")

    motion = page.evaluate(
        """() => {
          const parse = (value) => value.split(',').map((part) => parseFloat(part) || 0);
          const offenders = [];
          for (const el of document.querySelectorAll('*')) {
            const style = getComputedStyle(el);
            const durations = [...parse(style.animationDuration), ...parse(style.transitionDuration)];
            if (durations.some((duration) => duration > 0.011)) offenders.push(el.tagName + '.' + el.className);
          }
          return offenders.slice(0, 10);
        }"""
    )
    if motion:
        fail(f"Reduced-motion duration offenders: {motion}")

    checks["focus"] = focus
    checks["console_errors"] = console_errors
    checks["page_errors"] = errors
    return checks


def render(browser: Browser, matrix: dict[str, Any], rubric_digest: str, matrix_digest: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for concept in matrix["concepts"]:
        for state in matrix["states"]:
            for viewport in matrix["viewports"]:
                context = browser.new_context(
                    viewport={"width": viewport["width"], "height": viewport["height"]},
                    device_scale_factor=1,
                    reduced_motion="reduce",
                    color_scheme="light",
                    locale="ru-RU",
                )
                page = context.new_page()
                url = f"{PROTOTYPE.as_uri()}?concept={concept}&state={state['id']}"
                page.goto(url, wait_until="load")
                checks = browser_checks(page, state["id"], viewport)
                page.evaluate("document.activeElement?.blur(); window.scrollTo(0, 0)")
                page.wait_for_timeout(40)
                filename = f"{concept}-{state['id']}-{viewport['id']}.png"
                screenshot = SCREENSHOT_DIR / filename
                page.screenshot(path=str(screenshot), full_page=False, animations="disabled")
                records.append(
                    {
                        "concept": concept,
                        "state": state["id"],
                        "viewport": viewport["id"],
                        "url": url,
                        "screenshot": str(screenshot.relative_to(RUN_DIR)),
                        "screenshot_sha256": sha256(screenshot),
                        "rubric_sha256": rubric_digest,
                        "state_matrix_sha256": matrix_digest,
                        "checks": checks,
                    }
                )
                context.close()
    return records


def main() -> None:
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    expected = len(matrix["concepts"]) * len(matrix["states"]) * len(matrix["viewports"])
    if expected != matrix["expected_render_count"] or expected != 30:
        fail(f"Frozen matrix count mismatch: computed {expected}")
    if not CHROMIUM.exists():
        fail(f"Chromium executable not found: {CHROMIUM}")

    rubric_digest = sha256(RUBRIC_PATH)
    matrix_digest = sha256(MATRIX_PATH)
    if rubric_digest != "49d6de2eee2ad24ed2b07bbd95a84c78bae63897282dd2496b9723976555fa9d":
        fail("Frozen rubric digest mismatch")
    if matrix_digest != "5cc8a4b47d48bc7b8b05e7f0e8a3392ff1d21fcba253914c491596a6da5fe0b8":
        fail("Frozen state matrix digest mismatch")

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    truth = assert_truth()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=str(CHROMIUM), headless=True)
        records = render(browser, matrix, rubric_digest, matrix_digest)
        browser.close()

    if len(records) != expected:
        fail(f"Rendered {len(records)} screenshots, expected {expected}")
    if len({record["screenshot"] for record in records}) != expected:
        fail("Screenshot paths are not unique")

    metadata = {
        "contract_version": matrix["contract_version"],
        "rubric_sha256": rubric_digest,
        "state_matrix_sha256": matrix_digest,
        "truth": truth,
        "expected_render_count": expected,
        "actual_render_count": len(records),
        "records": records,
    }
    (OUTPUT_DIR / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(
            {
                "status": "PASS",
                "renders": len(records),
                "truth": truth,
                "critical_failures": 0,
                "rubric_sha256": rubric_digest,
                "state_matrix_sha256": matrix_digest,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"PASS: {len(records)} renders; truth={truth['result']}; critical_failures=0")


if __name__ == "__main__":
    main()
