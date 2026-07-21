"""Рендерит три clean-slate concept на одном честном content-set."""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).parent
SOURCE = ROOT / "concepts" / "prototype.html"
OUT = ROOT / "renders" / "concepts"
CHROMIUM = (
    Path.home()
    / "Library/Caches/ms-playwright/chromium-1217/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=str(CHROMIUM))
        for concept in ("a", "b", "c"):
            for width, height in ((375, 844), (1280, 900)):
                context = browser.new_context(viewport={"width": width, "height": height})
                page = context.new_page()
                errors: list[str] = []
                page.on("pageerror", lambda error: errors.append(f"pageerror: {error}"))
                page.on(
                    "console",
                    lambda message: errors.append(f"console: {message.text}")
                    if message.type == "error"
                    else None,
                )

                for screen in ("hub", "drill", "srez"):
                    url = f"{SOURCE.as_uri()}?concept={concept}&screen={screen}"
                    page.goto(url, wait_until="load")
                    page.evaluate("document.fonts.ready")
                    page.wait_for_timeout(250)
                    details = page.evaluate(
                        """() => ({
                          title: document.title,
                          viewport: innerWidth,
                          scrollWidth: document.documentElement.scrollWidth,
                          overflow: document.documentElement.scrollWidth > innerWidth + 1,
                          h1Font: getComputedStyle(document.querySelector('h1')).fontFamily,
                          minTarget: Math.min(...[...document.querySelectorAll('a,button,input')]
                            .map(el => Math.min(el.getBoundingClientRect().width, el.getBoundingClientRect().height))
                            .filter(value => value > 0)),
                        })"""
                    )
                    page.screenshot(
                        path=OUT / f"{concept}-{screen}-{width}.png",
                        full_page=True,
                    )
                    report[f"{concept}-{screen}-{width}"] = details

                report[f"{concept}-{width}-errors"] = errors
                context.close()
        browser.close()

    (OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    failures = [key for key, value in report.items() if key.endswith("-errors") and value]
    overflow = [
        key
        for key, value in report.items()
        if isinstance(value, dict) and value.get("overflow")
    ]
    if failures or overflow:
        raise SystemExit(f"concept render failed: errors={failures}, overflow={overflow}")
    print(f"concept render passed: {len(report)} checks, output={OUT}")


if __name__ == "__main__":
    main()
