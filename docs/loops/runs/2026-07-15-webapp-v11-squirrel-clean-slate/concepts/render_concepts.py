"""Рендерит и механически проверяет три clean-slate концепции v11."""

from __future__ import annotations

import json
import os
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "prototype.html"
OUTPUT = ROOT.parent / "round-concepts" / "renders"
CHROME = Path.home() / (
    "Library/Caches/ms-playwright/chromium-1228/chrome-mac-arm64/"
    "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
)
CONCEPTS = ("a", "b", "c")
SCREENS = ("hub", "drill", "srez")
VIEWPORTS = ((375, 844), (1280, 900))


def build_contact_sheet(concept: str) -> None:
    mobile_width = 260
    desktop_width = 680
    gutter = 18
    label_height = 30
    rows: list[tuple[Image.Image, Image.Image, str]] = []

    for screen in SCREENS:
        mobile = Image.open(OUTPUT / f"{concept}-{screen}-375.png").convert("RGB")
        desktop = Image.open(OUTPUT / f"{concept}-{screen}-1280.png").convert("RGB")
        mobile.thumbnail((mobile_width, 585), Image.Resampling.LANCZOS)
        desktop.thumbnail((desktop_width, 478), Image.Resampling.LANCZOS)
        rows.append((mobile, desktop, screen.upper()))

    row_height = max(max(m.height, d.height) + label_height for m, d, _ in rows)
    canvas = Image.new(
        "RGB",
        (mobile_width + desktop_width + gutter * 3, row_height * len(rows) + gutter),
        "#d9d9d9",
    )
    draw = ImageDraw.Draw(canvas)

    for index, (mobile, desktop, label) in enumerate(rows):
        y = gutter + index * row_height
        draw.text((gutter, y), f"{label} · 375", fill="#111111")
        draw.text((gutter * 2 + mobile_width, y), f"{label} · 1280", fill="#111111")
        canvas.paste(mobile, (gutter, y + label_height))
        canvas.paste(desktop, (gutter * 2 + mobile_width, y + label_height))

    canvas.save(OUTPUT / f"contact-{concept}.jpg", quality=92)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {}
    failures: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=str(CHROME))

        for concept in CONCEPTS:
            for screen in SCREENS:
                for width, height in VIEWPORTS:
                    context = browser.new_context(
                        viewport={"width": width, "height": height},
                        color_scheme="light",
                        reduced_motion="reduce",
                        device_scale_factor=1,
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

                    url = SOURCE.as_uri() + f"?concept={concept}&screen={screen}"
                    page.goto(url, wait_until="load")
                    page.evaluate("document.fonts.ready")
                    page.wait_for_timeout(180)

                    details = page.evaluate(
                        """
                        () => {
                          const visible = (element) => {
                            const style = getComputedStyle(element)
                            const rect = element.getBoundingClientRect()
                            return style.display !== 'none' && style.visibility !== 'hidden' &&
                              rect.width > 0 && rect.height > 0
                          }
                          const controls = [...document.querySelectorAll('button,a,input')].filter(visible)
                          const images = [...document.querySelectorAll('img')].filter(visible)
                          const inputs = [...document.querySelectorAll('input')].filter(visible)
                          const primary = document.querySelector('.primary')
                          const primaryRect = primary?.getBoundingClientRect()
                          return {
                            scrollWidth: document.documentElement.scrollWidth,
                            scrollHeight: document.documentElement.scrollHeight,
                            overflowX: document.documentElement.scrollWidth > innerWidth + 1,
                            fonts: document.fonts.status,
                            imagesLoaded: images.every((image) => image.complete && image.naturalWidth > 0),
                            minControlHeight: controls.length ? Math.min(...controls.map(
                              (element) => element.getBoundingClientRect().height
                            )) : null,
                            minInputFont: inputs.length ? Math.min(...inputs.map(
                              (element) => Number.parseFloat(getComputedStyle(element).fontSize)
                            )) : null,
                            primaryVisible: primaryRect ? primaryRect.top >= -1 &&
                              primaryRect.bottom <= innerHeight + 1 : null,
                          }
                        }
                        """
                    )

                    key = f"{concept}-{screen}-{width}"
                    report[key] = {"details": details, "errors": errors}
                    page.screenshot(path=str(OUTPUT / f"{key}.png"), full_page=False)

                    if errors:
                        failures.append(f"{key}: {'; '.join(errors)}")
                    if details["overflowX"]:
                        failures.append(f"{key}: horizontal overflow")
                    if not details["imagesLoaded"]:
                        failures.append(f"{key}: image failed to load")
                    if details["fonts"] != "loaded":
                        failures.append(f"{key}: fonts={details['fonts']}")
                    if details["minControlHeight"] is not None and details["minControlHeight"] < 44:
                        failures.append(f"{key}: min control height={details['minControlHeight']}")
                    if details["minInputFont"] is not None and details["minInputFont"] < 16:
                        failures.append(f"{key}: input font={details['minInputFont']}")
                    if details["primaryVisible"] is False:
                        failures.append(f"{key}: primary action outside first viewport")

                    context.close()

        browser.close()

    for concept in CONCEPTS:
        build_contact_sheet(concept)

    (OUTPUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if failures:
        raise RuntimeError("Concept render failed:\n- " + "\n- ".join(failures))

    print(f"Concept render passed: {len(report)} screenshots; output={OUTPUT}")


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    main()
