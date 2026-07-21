#!/usr/bin/env python3
"""Freeze responsive runtime evidence for the authenticated learning journey."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from playwright.sync_api import Browser, Page, Request, Response, TimeoutError as PlaywrightTimeoutError, sync_playwright


DEFAULT_CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


class RuntimeGate:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.console_errors: list[str] = []
        self.page_errors: list[str] = []
        self.request_errors: list[str] = []
        self.api_errors: list[str] = []
        self.checks: list[dict[str, Any]] = []

    def attach(self, page: Page) -> None:
        def on_console(message: Any) -> None:
            if message.type == "error" and "Failed to load resource" not in message.text:
                self.console_errors.append(message.text[:300])

        def on_response(response: Response) -> None:
            path = urlsplit(response.url).path
            if path.startswith("/api/") and response.status >= 400:
                self.api_errors.append(f"{response.request.method} {path} -> {response.status}")

        def on_request_failed(request: Request) -> None:
            self.request_errors.append(
                f"{request.method} {urlsplit(request.url).path}: {request.failure or 'failed'}"
            )

        page.on("console", on_console)
        page.on("pageerror", lambda error: self.page_errors.append(str(error)[:300]))
        page.on("response", on_response)
        page.on("requestfailed", on_request_failed)

    @staticmethod
    def login(page: Page, base_url: str, phone: str, pin: str) -> None:
        page.goto(f"{base_url}/app/login", wait_until="networkidle")
        page.get_by_label("Номер телефона").fill(phone)
        page.get_by_role("button", name="Продолжить", exact=True).click()
        page.get_by_label("PIN-код").wait_for()
        page.get_by_label("PIN-код").fill(pin)
        page.get_by_role("button", name="Войти и продолжить урок", exact=True).click()
        try:
            page.wait_for_url(f"{base_url}/app", timeout=20_000)
        except PlaywrightTimeoutError as error:
            alerts = page.get_by_role("alert").all_text_contents()
            raise AssertionError(
                f"login did not reach the app root: url={page.url!r}, alerts={alerts!r}"
            ) from error
        page.locator(".journey-main h1").wait_for(timeout=20_000)
        page.wait_for_timeout(650)

    def checkpoint(
        self,
        page: Page,
        name: str,
        *,
        heading_selector: str | None = ".journey-main h1",
        require_heading_focus: bool | None = None,
    ) -> dict[str, Any]:
        page.evaluate(
            "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
        )
        page.wait_for_timeout(350)
        viewport = page.viewport_size or {"width": 0, "height": 0}
        metrics = page.evaluate(
            """(headingSelector) => {
              const heading = headingSelector ? document.querySelector(headingSelector) : null;
              const candidates = [...document.querySelectorAll(
                'button:not([disabled]), a[href], summary, input:not([type="hidden"]):not([disabled])'
              )];
              const smallTargets = candidates.flatMap((element) => {
                const style = getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                if (style.display === 'none' || style.visibility === 'hidden' || rect.width === 0 || rect.height === 0) return [];
                if (element.matches('input[type="checkbox"], input[type="radio"], input[type="file"], .sr-only')) return [];
                if (element.classList.contains('fixed') && rect.bottom < 0) return [];
                return rect.width + 0.1 < 44 || rect.height + 0.1 < 44
                  ? [{tag: element.tagName, text: (element.textContent || element.getAttribute('aria-label') || '').trim().slice(0, 80), width: rect.width, height: rect.height}]
                  : [];
              });
              return {
                width: innerWidth,
                height: innerHeight,
                scrollWidth: document.documentElement.scrollWidth,
                overflow: document.documentElement.scrollWidth - innerWidth,
                heading: heading?.textContent?.trim() || null,
                headingFont: heading ? getComputedStyle(heading).fontFamily : null,
                activeTag: document.activeElement?.tagName || null,
                activeText: document.activeElement?.textContent?.trim().slice(0, 120) || null,
                activeIsHeading: document.activeElement === heading,
                activeWorkspace: Boolean(document.querySelector('.learning-workspace')),
                smallTargets,
              };
            }""",
            heading_selector,
        )
        assert metrics["width"] == viewport["width"] and metrics["height"] == viewport["height"]
        assert metrics["overflow"] <= 1, f"horizontal overflow at {name}: {metrics['overflow']}px"
        assert not metrics["smallTargets"], f"small touch targets at {name}: {metrics['smallTargets']}"
        focus_required = not metrics["activeWorkspace"] if require_heading_focus is None else require_heading_focus
        if focus_required:
            assert metrics["activeIsHeading"], f"route heading did not receive focus at {name}: {metrics}"
        screenshot = self.output_dir / f"{name}-{viewport['width']}x{viewport['height']}.png"
        page.screenshot(path=str(screenshot), full_page=False)
        digest = hashlib.sha256(screenshot.read_bytes()).hexdigest()
        result = {"name": name, "screenshot": screenshot.name, "sha256": digest, **metrics}
        self.checks.append(result)
        return result

    def keyboard_and_motion(self, page: Page) -> dict[str, Any]:
        skip_result = page.evaluate(
            """() => {
              document.body.setAttribute('tabindex', '-1');
              document.body.focus();
              const link = [...document.querySelectorAll('a')].find((node) => node.textContent?.trim() === 'К содержанию');
              const before = link?.getBoundingClientRect();
              return {beforeTop: before?.top ?? null};
            }"""
        )
        page.keyboard.press("Tab")
        skip_result.update(
            page.evaluate(
                """() => {
                  const active = document.activeElement;
                  const rect = active?.getBoundingClientRect();
                  const style = active ? getComputedStyle(active) : null;
                  return {
                    activeText: active?.textContent?.trim() || null,
                    top: rect?.top ?? null,
                    height: rect?.height ?? null,
                    transitionDuration: style?.transitionDuration || null,
                  };
                }"""
            )
        )
        assert skip_result["activeText"] == "К содержанию", skip_result
        assert skip_result["top"] is not None and skip_result["top"] >= 0, skip_result
        assert skip_result["height"] is not None and skip_result["height"] >= 44, skip_result
        assert skip_result["transitionDuration"] in {"0s", "0s, 0s"}, skip_result

        page.emulate_media(reduced_motion="reduce")
        page.wait_for_timeout(100)
        motion = page.evaluate(
            """() => {
              const seconds = (value) => value.split(',').map((item) => {
                const token = item.trim();
                return token.endsWith('ms') ? Number.parseFloat(token) / 1000 : Number.parseFloat(token) || 0;
              });
              let maxAnimation = 0;
              let maxTransition = 0;
              for (const element of document.querySelectorAll('.journey-shell, .journey-shell *')) {
                const style = getComputedStyle(element);
                maxAnimation = Math.max(maxAnimation, ...seconds(style.animationDuration));
                maxTransition = Math.max(maxTransition, ...seconds(style.transitionDuration));
              }
              return {matches: matchMedia('(prefers-reduced-motion: reduce)').matches, maxAnimation, maxTransition};
            }"""
        )
        assert motion["matches"] is True, motion
        assert motion["maxAnimation"] <= 0.001 and motion["maxTransition"] <= 0.001, motion
        return {"skipLink": skip_result, "reducedMotion": motion}

    @staticmethod
    def build_assets(page: Page) -> list[str]:
        assets = page.evaluate(
            """() => performance.getEntriesByType('resource')
              .map((entry) => new URL(entry.name).pathname)
              .filter((path) => path.includes('/assets/') && (path.endsWith('.js') || path.endsWith('.css')))
              .map((path) => path.split('/').pop())"""
        )
        return sorted(set(assets))

    def assert_clean(self) -> None:
        assert not self.console_errors, self.console_errors
        assert not self.page_errors, self.page_errors
        assert not self.request_errors, self.request_errors
        assert not self.api_errors, self.api_errors


def capture_context(
    browser: Browser,
    gate: RuntimeGate,
    *,
    base_url: str,
    phone: str,
    pin: str,
    width: int,
    height: int,
    name: str,
    mobile: bool,
) -> tuple[dict[str, Any], list[str], dict[str, Any]]:
    context = browser.new_context(
        viewport={"width": width, "height": height},
        has_touch=mobile,
        is_mobile=mobile,
        service_workers="block",
    )
    page = context.new_page()
    gate.attach(page)
    gate.login(page, base_url, phone, pin)
    checkpoint = gate.checkpoint(page, name)
    assets = gate.build_assets(page)
    interaction = gate.keyboard_and_motion(page)
    context.close()
    return checkpoint, assets, interaction


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8412")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--name", default="runtime-postfix")
    parser.add_argument("--chrome", type=Path, default=DEFAULT_CHROME if DEFAULT_CHROME.exists() else None)
    args = parser.parse_args()
    phone = os.environ.get("KODI_TEST_PHONE")
    pin = os.environ.get("KODI_TEST_PIN")
    if not phone or not pin:
        raise SystemExit("KODI_TEST_PHONE and KODI_TEST_PIN are required")

    gate = RuntimeGate(args.output_dir.resolve())
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=str(args.chrome) if args.chrome else None,
        )
        mobile, mobile_assets, mobile_interaction = capture_context(
            browser,
            gate,
            base_url=args.base_url.rstrip("/"),
            phone=phone,
            pin=pin,
            width=375,
            height=844,
            name=f"{args.name}-mobile",
            mobile=True,
        )
        desktop, desktop_assets, desktop_interaction = capture_context(
            browser,
            gate,
            base_url=args.base_url.rstrip("/"),
            phone=phone,
            pin=pin,
            width=1280,
            height=900,
            name=f"{args.name}-desktop",
            mobile=False,
        )
        browser.close()

    gate.assert_clean()
    summary = {
        "verdict": "PASS",
        "baseOrigin": f"{urlsplit(args.base_url).scheme}://{urlsplit(args.base_url).netloc}",
        "screens": [mobile, desktop],
        "assets": sorted(set(mobile_assets + desktop_assets)),
        "interaction": {"mobile": mobile_interaction, "desktop": desktop_interaction},
        "consoleErrors": gate.console_errors,
        "pageErrors": gate.page_errors,
        "requestErrors": gate.request_errors,
        "apiErrors": gate.api_errors,
    }
    target = args.output_dir.resolve() / f"{args.name}-summary.json"
    target.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
