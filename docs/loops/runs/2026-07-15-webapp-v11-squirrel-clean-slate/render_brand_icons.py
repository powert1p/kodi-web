"""Рендерит code-native v11 mark в PWA PNG-иконки."""

from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[4]
PUBLIC = ROOT / "webapp" / "public"
SVG = PUBLIC / "favicon.svg"
CHROME = Path.home() / (
    "Library/Caches/ms-playwright/chromium-1228/chrome-mac-arm64/"
    "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
)

OUTPUTS = {
    PUBLIC / "favicon.png": 64,
    PUBLIC / "icons" / "apple-touch-icon.png": 180,
    PUBLIC / "icons" / "icon-192.png": 192,
    PUBLIC / "icons" / "icon-512.png": 512,
    PUBLIC / "icons" / "icon-512-maskable.png": 512,
}


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, executable_path=str(CHROME))
    svg_markup = SVG.read_text(encoding="utf-8")
    for output, size in OUTPUTS.items():
        page = browser.new_page(viewport={"width": size, "height": size}, device_scale_factor=1)
        page.set_content(
            "<style>html,body{margin:0;width:100%;height:100%;overflow:hidden}"
            "svg{display:block;width:100%;height:100%}</style>"
            + svg_markup
        )
        page.locator("svg").wait_for(state="visible")
        page.screenshot(path=str(output), full_page=False)
        page.close()
    browser.close()

print(f"Rendered {len(OUTPUTS)} icons from {SVG}")
