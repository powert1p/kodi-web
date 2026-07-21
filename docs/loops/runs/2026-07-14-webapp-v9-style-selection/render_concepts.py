"""Рендерит пять визуальных направлений на одинаковом учебном сценарии."""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).parent
SOURCE = ROOT / "prototype.html"
OUT = ROOT / "renders"
CHROMIUM = (
    Path.home()
    / "Library/Caches/ms-playwright/chromium-1217/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {}
    failures: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=str(CHROMIUM))
        for concept in range(1, 6):
            for width, height in ((375, 844), (1280, 900)):
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    color_scheme="light",
                    reduced_motion="reduce",
                )
                page = context.new_page()
                errors: list[str] = []
                page.on("pageerror", lambda error: errors.append(f"pageerror: {error}"))
                page.on(
                    "console",
                    lambda message: errors.append(f"console: {message.text}")
                    if message.type == "error"
                    else None,
                )

                page.goto(f"{SOURCE.as_uri()}?concept={concept}", wait_until="load")
                page.evaluate("document.fonts.ready")
                page.wait_for_timeout(180)
                details = page.evaluate(
                    """() => {
                      const visible = (el) => {
                        const style = getComputedStyle(el)
                        const rect = el.getBoundingClientRect()
                        return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0
                      }
                      const active = [...document.querySelectorAll('.concept')].find(visible)
                      const stage = active.querySelector(
                        '.studio-stage, .route-stage, .math-board, .club-stage, .poster-stage'
                      )
                      const stageRect = stage.getBoundingClientRect()
                      const visibleStageHeight = Math.max(0, Math.min(innerHeight, stageRect.bottom) - Math.max(0, stageRect.top))
                      const primary = active.querySelector('.primary-button')
                      const primaryRect = primary.getBoundingClientRect()
                      const controls = [...active.querySelectorAll('button, label')].filter(visible)
                      const images = [...active.querySelectorAll('img')].filter(visible)
                      return {
                        title: document.title,
                        viewport: { width: innerWidth, height: innerHeight },
                        scrollWidth: document.documentElement.scrollWidth,
                        scrollHeight: document.documentElement.scrollHeight,
                        overflowX: document.documentElement.scrollWidth > innerWidth + 1,
                        stageViewportShare: Number((visibleStageHeight / innerHeight).toFixed(3)),
                        primaryVisible: primaryRect.top >= 0 && primaryRect.bottom <= innerHeight,
                        minControlHeight: Math.min(...controls.map((el) => el.getBoundingClientRect().height)),
                        minControlWidth: Math.min(...controls.map((el) => el.getBoundingClientRect().width)),
                        fonts: document.fonts.status,
                        h1Font: getComputedStyle(active.querySelector('h1')).fontFamily,
                        imagesLoaded: images.every((img) => img.complete && img.naturalWidth > 0),
                      }
                    }"""
                )

                page.screenshot(path=OUT / f"0{concept}-{width}.png", full_page=False)
                key = f"0{concept}-{width}"
                report[key] = {"details": details, "errors": errors}

                if errors:
                    failures.append(f"{key}: console={errors}")
                if details["overflowX"]:
                    failures.append(f"{key}: horizontal overflow")
                if details["scrollHeight"] > height + 8:
                    failures.append(
                        f"{key}: first screen scrolls ({details['scrollHeight']} > {height})"
                    )
                if not details["imagesLoaded"]:
                    failures.append(f"{key}: image failed to load")
                if details["fonts"] != "loaded":
                    failures.append(f"{key}: fonts={details['fonts']}")
                if details["minControlHeight"] < 44:
                    failures.append(f"{key}: min control height={details['minControlHeight']}")
                if not details["primaryVisible"]:
                    failures.append(f"{key}: primary CTA is outside first viewport")

                context.close()
        browser.close()

    (OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if failures:
        raise SystemExit("concept render failed:\n- " + "\n- ".join(failures))
    print(f"concept render passed: {len(report)} viewports, output={OUT}")


if __name__ == "__main__":
    main()
