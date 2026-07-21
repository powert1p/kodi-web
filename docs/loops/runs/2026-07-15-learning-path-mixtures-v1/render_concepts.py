from __future__ import annotations

import argparse
import contextlib
import http.server
import socket
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[4]
RUN_DIR = Path(__file__).resolve().parent


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return


def free_port() -> int:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(RUN_DIR / "round-concepts"))
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    port = free_port()
    handler = lambda *handler_args, **handler_kwargs: QuietHandler(  # noqa: E731
        *handler_args, directory=str(ROOT), **handler_kwargs
    )
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    route = "docs/loops/runs/2026-07-15-learning-path-mixtures-v1/concept.html"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        screens_by_concept = {
            "a": ("today", "lesson", "wrong", "retry", "resume", "result"),
            "b": ("today", "lesson"),
            "c": ("today", "lesson"),
        }
        for concept, screens in screens_by_concept.items():
            for screen in screens:
                for name, width, height in (("mobile", 375, 844), ("desktop", 1280, 900)):
                    page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
                    errors: list[str] = []
                    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(
                        f"http://127.0.0.1:{port}/{route}?concept={concept}&screen={screen}",
                        wait_until="networkidle",
                    )
                    overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
                    if not page.locator("#app").inner_text().strip():
                        errors.append("empty concept render")
                    if overflow:
                        raise RuntimeError(f"horizontal overflow: {concept}/{screen}/{name}")
                    if errors:
                        raise RuntimeError(f"console errors: {concept}/{screen}/{name}: {errors}")
                    page.screenshot(path=str(output / f"{concept}-{screen}-{name}.png"), full_page=False)
                    page.close()
        browser.close()
    server.shutdown()


if __name__ == "__main__":
    main()
