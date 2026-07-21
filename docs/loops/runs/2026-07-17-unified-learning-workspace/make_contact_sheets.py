#!/usr/bin/env python3
"""Build lossless concept contact sheets from the frozen browser evidence."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


RUN_DIR = Path(__file__).resolve().parent
EVIDENCE = RUN_DIR / "round-concepts" / "evidence"
SCREENSHOTS = EVIDENCE / "screenshots"
FONT = RUN_DIR.parents[3] / "webapp" / "src" / "theme" / "fonts" / "onest-variable.ttf"
STATES = ["independent", "needs_revision", "hint_h2", "tutor_open", "uncertain"]


def fit(image: Image.Image, width: int, height: int) -> Image.Image:
    copy = image.copy()
    copy.thumbnail((width, height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (width, height), "#DEDCD4")
    canvas.paste(copy, ((width - copy.width) // 2, (height - copy.height) // 2))
    return canvas


def main() -> None:
    metadata = json.loads((EVIDENCE / "metadata.json").read_text(encoding="utf-8"))
    if metadata["actual_render_count"] != 30:
        raise AssertionError("Contact sheet requires all 30 frozen renders")
    font = ImageFont.truetype(str(FONT), 22)
    small = ImageFont.truetype(str(FONT), 16)
    for concept in ["a", "b", "c"]:
        sheet = Image.new("RGB", (1660, 740), "#EEECE5")
        draw = ImageDraw.Draw(sheet)
        draw.text((24, 16), f"CONCEPT {concept.upper()} · DESKTOP / MOBILE", fill="#173A31", font=font)
        for column, state in enumerate(STATES):
            x = 24 + column * 325
            draw.text((x, 52), state, fill="#5E6F69", font=small)
            desktop = Image.open(SCREENSHOTS / f"{concept}-{state}-1280x900.png").convert("RGB")
            sheet.paste(fit(desktop, 300, 211), (x, 80))
            mobile = Image.open(SCREENSHOTS / f"{concept}-{state}-375x844.png").convert("RGB")
            sheet.paste(fit(mobile, 300, 400), (x, 316))
        sheet.save(EVIDENCE / f"contact-{concept}.png", optimize=True)
    print("PASS: contact-a.png, contact-b.png, contact-c.png")


if __name__ == "__main__":
    main()
