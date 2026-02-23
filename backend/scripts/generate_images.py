"""Generate PNG image cards for all problems in the problem bank.

Usage:
    python scripts/generate_images.py            # Russian (default)
    python scripts/generate_images.py --lang kz   # Kazakh

Reads data/problems_v10.json, renders each problem as a dark-themed card
with DejaVu Serif font (bundled in fonts/), writes PNGs to static/questions/
(or static/questions_kz/ for Kazakh), and updates the JSON with an
``image_file`` / ``image_file_kz`` field per problem.

Rendering features:
- Stacked fractions (e.g. 1/3 rendered with numerator, bar, denominator)
- Mixed fractions (e.g. 2 1/5)
- Unicode math symbols rendered natively by STIX Two
- Adaptive canvas height based on line count
- Word wrapping within card width
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ── Paths ──────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PROBLEMS_PATH = (
    DATA_DIR / "problems_v10.json" if (DATA_DIR / "problems_v10.json").exists()
    else DATA_DIR / "problems_v9.json" if (DATA_DIR / "problems_v9.json").exists()
    else DATA_DIR / "problems_v8.json" if (DATA_DIR / "problems_v8.json").exists()
    else DATA_DIR / "problems_v7.json" if (DATA_DIR / "problems_v7.json").exists()
    else DATA_DIR / "problems_v6.json" if (DATA_DIR / "problems_v6.json").exists()
    else DATA_DIR / "problems_v5.json" if (DATA_DIR / "problems_v5.json").exists()
    else DATA_DIR / "problems_v4.json" if (DATA_DIR / "problems_v4.json").exists()
    else DATA_DIR / "problems_v3.json"
)
OUTPUT_DIR = PROJECT_ROOT / "static" / "questions"

# ── Font (bundled DejaVu Serif — full Cyrillic + math coverage) ─

FONT_PATH = str(PROJECT_ROOT / "fonts" / "DejaVuSerif.ttf")

CHAR_REPLACEMENTS = {
    "\u2236": ":",    # RATIO → colon
    "\u25fb": "[]",   # WHITE MEDIUM SQUARE → brackets
    "\u2605": "*",    # BLACK STAR → asterisk
    "\u25c6": "*",    # BLACK DIAMOND → asterisk
    "\u1d43": "^a",   # MODIFIER LETTER SMALL A
    "\u1d47": "^b",   # MODIFIER LETTER SMALL B
}

# ── Design constants ───────────────────────────────────────────

CARD_WIDTH = 800
PAD_X = 52
PAD_Y = 48
FONT_SIZE = 36
FRAC_FONT_SIZE = 26
LINE_SPACING = 62
MIN_HEIGHT = 140

BG_COLOR = (24, 28, 36)
CARD_COLOR = (32, 37, 48)
TEXT_COLOR = (240, 242, 245)
FRAC_LINE_COLOR = (200, 205, 212)
BORDER_COLOR = (55, 62, 72)
CORNER_RADIUS = 18
BORDER_WIDTH = 1

# ── Tokeniser ──────────────────────────────────────────────────

_FRAC_RE = re.compile(
    r"("
    r"\d+\s+\d+/\d+"       # mixed: 2 3/4
    r"|[−\-]?\d+/\d+"      # simple or negative: 3/4, −3/4
    r")"
)

_PAREN_FRAC_RE = re.compile(r"\(([−\-]?\d+/\d+)\)")


def _preprocess_fractions(text: str) -> str:
    """Separate parentheses from fractions so the tokenizer can find them.

    (1/2) -> ( 1/2 ),  (−3/4) -> ( −3/4 ).
    Parentheses are preserved as word tokens; fractions become frac tokens.
    Does NOT touch complex expressions like 1/(1+2).
    """
    return _PAREN_FRAC_RE.sub(r"( \1 )", text)


def _tokenize(text: str) -> list[tuple[str, str]]:
    """Split text into typed tokens for rendering.

    Token types: 'word', 'frac', 'neg_frac', 'mixed_frac', 'br'.
    """
    text = _preprocess_fractions(text)
    tokens: list[tuple[str, str]] = []
    for line in text.split("\n"):
        if tokens:
            tokens.append(("br", ""))
        for part in _FRAC_RE.split(line):
            stripped = part.strip()
            if not stripped:
                continue
            if re.match(r"^\d+\s+\d+/\d+$", stripped):
                tokens.append(("mixed_frac", stripped))
            elif re.match(r"^[−\-]\d+/\d+$", stripped):
                tokens.append(("neg_frac", stripped))
            elif re.match(r"^\d+/\d+$", stripped):
                tokens.append(("frac", stripped))
            else:
                for word in part.split():
                    if word:
                        tokens.append(("word", word))
    return tokens


# ── Complex fraction detection & recursive renderer ───────────

_COMPLEX_FRAC_RE = re.compile(
    r'[\w\d\)]\s*/\s*\('       # something / (
    r'|'
    r'\)\s*/\s*[\w\d\(]'       # ) / something
)


def _has_complex_fraction(text: str) -> bool:
    """Detect if text contains fraction expressions needing recursive rendering."""
    return bool(_COMPLEX_FRAC_RE.search(text))


def _matching_paren(s: str, start: int) -> int:
    """Find index of ')' matching '(' at position start. Returns -1 if not found."""
    depth = 0
    for i in range(start, len(s)):
        if s[i] == '(':
            depth += 1
        elif s[i] == ')':
            depth -= 1
            if depth == 0:
                return i
    return -1


def _reverse_matching_paren(s: str, end: int) -> int:
    """Find index of '(' matching ')' at position end. Returns -1 if not found."""
    depth = 0
    for i in range(end, -1, -1):
        if s[i] == ')':
            depth += 1
        elif s[i] == '(':
            depth -= 1
            if depth == 0:
                return i
    return -1


def _strip_outer_parens(s: str) -> str:
    """Strip one layer of outer parentheses if they wrap the entire expression."""
    s = s.strip()
    if s.startswith('(') and _matching_paren(s, 0) == len(s) - 1:
        return s[1:-1].strip()
    return s


def _find_main_fraction(expr: str) -> tuple | None:
    """Find the main fraction bar in a math expression.

    Returns (before, numerator, denominator, after) if found, None otherwise.
    The main fraction is the '/' at the lowest paren depth where at least one
    operand is parenthesized (not a simple digit/digit fraction).
    """
    expr_stripped = expr.strip()
    if not expr_stripped:
        return None

    depth = 0
    slashes: list[tuple[int, int]] = []
    for i, ch in enumerate(expr_stripped):
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        elif ch == '/':
            slashes.append((i, depth))

    if not slashes:
        return None

    min_depth = min(d for _, d in slashes)

    for pos, d in slashes:
        if d != min_depth:
            continue

        # Extract left operand
        left_part = expr_stripped[:pos].rstrip()
        if left_part.endswith(')'):
            paren_start = _reverse_matching_paren(left_part, len(left_part) - 1)
            if paren_start < 0:
                continue
            left_operand = left_part[paren_start:]
            before = left_part[:paren_start].rstrip()
        else:
            m = re.search(r'([\w\d.,]+)$', left_part)
            if not m:
                continue
            left_operand = m.group(1)
            before = left_part[:m.start()].rstrip()

        # Extract right operand
        right_part = expr_stripped[pos + 1:].lstrip()
        if right_part.startswith('('):
            paren_end = _matching_paren(right_part, 0)
            if paren_end < 0:
                continue
            right_operand = right_part[:paren_end + 1]
            after = right_part[paren_end + 1:].lstrip()
        else:
            m = re.match(r'([\w\d.,]+)', right_part)
            if not m:
                continue
            right_operand = m.group(1)
            after = right_part[m.end():].lstrip()

        # Skip simple digit/digit fractions
        if re.match(r'^[−\-]?\d+$', left_operand) and re.match(r'^[−\-]?\d+$', right_operand):
            continue

        # Skip if operand contains = < > (equation boundary, not fraction)
        if re.search(r'[=<>]', left_operand + right_operand):
            continue

        num = _strip_outer_parens(left_operand)
        den = _strip_outer_parens(right_operand)
        return (before, num, den, after)

    return None


# Tree node types: ('text', str), ('frac', num_node, den_node), ('seq', [nodes])
ExprTree = tuple


def _parse_expr_tree(expr: str) -> ExprTree:
    """Parse a math expression into a tree for recursive fraction rendering."""
    expr = expr.strip()
    if not expr:
        return ('text', '')

    result = _find_main_fraction(expr)
    if result is None:
        return ('text', expr)

    before, num_str, den_str, after = result
    frac_node = ('frac', _parse_expr_tree(num_str), _parse_expr_tree(den_str))

    parts: list[ExprTree] = []
    if before:
        parts.append(_parse_expr_tree(before))
    parts.append(frac_node)
    if after:
        parts.append(_parse_expr_tree(after))

    if len(parts) == 1:
        return parts[0]
    return ('seq', parts)


def _measure_tree(
    draw: ImageDraw.ImageDraw,
    node: ExprTree,
    fnt: ImageFont.FreeTypeFont,
    fnt_frac: ImageFont.FreeTypeFont,
) -> tuple[int, int, int]:
    """Measure width, height, and baseline-y of an expression tree node.

    Returns (width, height, baseline_from_top).
    """
    kind = node[0]

    if kind == 'text':
        text = node[1]
        tokens = _tokenize(text)
        w = 0
        space_w = _text_width(draw, " ", fnt)
        for i, tok in enumerate(tokens):
            if tok[0] == 'br':
                continue
            if i > 0:
                w += space_w
            w += _measure_token(draw, tok, fnt, fnt_frac)
        h = FONT_SIZE + 12
        return (w, h, h // 2)

    elif kind == 'frac':
        num_node, den_node = node[1], node[2]
        nw, nh, _ = _measure_tree(draw, num_node, fnt_frac, fnt_frac)
        dw, dh, _ = _measure_tree(draw, den_node, fnt_frac, fnt_frac)
        bar_pad = 8
        w = max(nw, dw) + 12
        h = nh + bar_pad + dh + 4
        baseline = nh + bar_pad // 2
        return (w, h, baseline)

    elif kind == 'seq':
        parts = node[1]
        total_w = 0
        max_above = 0
        max_below = 0
        space_w = _text_width(draw, " ", fnt)
        for i, part in enumerate(parts):
            pw, ph, pb = _measure_tree(draw, part, fnt, fnt_frac)
            if i > 0:
                total_w += space_w
            total_w += pw
            above = pb
            below = ph - pb
            if above > max_above:
                max_above = above
            if below > max_below:
                max_below = below
        return (total_w, max_above + max_below, max_above)

    return (0, 0, 0)


def _draw_tree(
    draw: ImageDraw.ImageDraw,
    node: ExprTree,
    x: int,
    y: int,
    baseline: int,
    fnt: ImageFont.FreeTypeFont,
    fnt_frac: ImageFont.FreeTypeFont,
) -> int:
    """Draw an expression tree node. Returns the x position after drawing."""
    kind = node[0]

    if kind == 'text':
        text = node[1]
        tokens = _tokenize(text)
        space_w = _text_width(draw, " ", fnt)
        text_y = y + baseline - FONT_SIZE // 2 - 2
        cx = x
        for i, tok in enumerate(tokens):
            if tok[0] == 'br':
                continue
            if i > 0:
                cx += space_w
            typ, val = tok
            if typ in ('frac', 'neg_frac'):
                if typ == 'neg_frac':
                    sign = val[0]
                    draw.text((cx, text_y), sign, fill=TEXT_COLOR, font=fnt)
                    cx += _text_width(draw, sign, fnt) + 2
                    num, den = val[1:].split('/')
                else:
                    num, den = val.split('/')
                num_w = _text_width(draw, num, fnt_frac)
                den_w = _text_width(draw, den, fnt_frac)
                frac_w = max(num_w, den_w) + 10
                center_y = text_y + FONT_SIZE // 2
                draw.text((cx + (frac_w - num_w) // 2, center_y - 28), num, fill=TEXT_COLOR, font=fnt_frac)
                draw.rectangle([cx + 2, center_y - 1, cx + frac_w - 2, center_y + 1], fill=FRAC_LINE_COLOR)
                draw.text((cx + (frac_w - den_w) // 2, center_y + 5), den, fill=TEXT_COLOR, font=fnt_frac)
                cx += frac_w
            elif typ == 'mixed_frac':
                parts = val.split()
                whole = parts[0]
                num, den = parts[1].split('/')
                draw.text((cx, text_y), whole, fill=TEXT_COLOR, font=fnt)
                cx += _text_width(draw, whole, fnt) + 2
                num_w = _text_width(draw, num, fnt_frac)
                den_w = _text_width(draw, den, fnt_frac)
                frac_w = max(num_w, den_w) + 10
                center_y = text_y + FONT_SIZE // 2
                draw.text((cx + (frac_w - num_w) // 2, center_y - 28), num, fill=TEXT_COLOR, font=fnt_frac)
                draw.rectangle([cx + 2, center_y - 1, cx + frac_w - 2, center_y + 1], fill=FRAC_LINE_COLOR)
                draw.text((cx + (frac_w - den_w) // 2, center_y + 5), den, fill=TEXT_COLOR, font=fnt_frac)
                cx += frac_w
            else:
                draw.text((cx, text_y), val, fill=TEXT_COLOR, font=fnt)
                cx += _text_width(draw, val, fnt)
        return cx

    elif kind == 'frac':
        num_node, den_node = node[1], node[2]
        nw, nh, _ = _measure_tree(draw, num_node, fnt_frac, fnt_frac)
        dw, dh, _ = _measure_tree(draw, den_node, fnt_frac, fnt_frac)
        bar_pad = 8
        frac_w = max(nw, dw) + 12
        bar_y = y + baseline

        # Numerator (centered above bar)
        num_x = x + (frac_w - nw) // 2
        num_y = bar_y - bar_pad // 2 - nh
        _draw_tree(draw, num_node, num_x, num_y, nh // 2, fnt_frac, fnt_frac)

        # Bar
        draw.rectangle([x + 2, bar_y - 1, x + frac_w - 2, bar_y + 1], fill=FRAC_LINE_COLOR)

        # Denominator (centered below bar)
        den_x = x + (frac_w - dw) // 2
        den_y = bar_y + bar_pad // 2
        _draw_tree(draw, den_node, den_x, den_y, dh // 2, fnt_frac, fnt_frac)

        return x + frac_w

    elif kind == 'seq':
        parts = node[1]
        space_w = _text_width(draw, " ", fnt)
        cx = x
        for i, part in enumerate(parts):
            if i > 0:
                cx += space_w
            pw, ph, pb = _measure_tree(draw, part, fnt, fnt_frac)
            _draw_tree(draw, part, cx, y, baseline, fnt, fnt_frac)
            cx += pw
        return cx

    return x


def _render_complex_card(
    text: str,
    fnt: ImageFont.FreeTypeFont,
    fnt_frac: ImageFont.FreeTypeFont,
) -> Image.Image:
    """Render a card with recursive fraction layout for complex expressions."""
    for old_ch, new_ch in CHAR_REPLACEMENTS.items():
        text = text.replace(old_ch, new_ch)

    # Split into instruction prefix and math expression
    m = re.match(
        r'^(.*?(?:Вычислите|Найдите\s+\w+|Решите|Сократите|Упростите)\s*:\s*)(.*)',
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        prefix = m.group(1)
        expr = m.group(2)
    else:
        prefix = ''
        expr = text

    tree = _parse_expr_tree(expr)

    tmp = Image.new("RGB", (1, 1))
    tmp_draw = ImageDraw.Draw(tmp)

    prefix_w = _text_width(tmp_draw, prefix, fnt) if prefix else 0
    ew, eh, ebl = _measure_tree(tmp_draw, tree, fnt, fnt_frac)

    content_w = prefix_w + ew
    max_line_w = CARD_WIDTH - 2 * PAD_X - 20

    # If too wide, put expression on the next line
    two_lines = content_w > max_line_w and prefix
    if two_lines:
        line1_h = FONT_SIZE + 16
        total_h = PAD_Y * 2 + line1_h + max(eh, FONT_SIZE + 12) + 16
    else:
        total_h = PAD_Y * 2 + max(eh, FONT_SIZE + 12) + 16

    total_h = max(total_h, MIN_HEIGHT)
    total_h = max(total_h, eh + PAD_Y * 2 + 20)
    img = Image.new("RGB", (CARD_WIDTH, total_h), BG_COLOR)
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle(
        [10, 10, CARD_WIDTH - 10, total_h - 10],
        radius=CORNER_RADIUS,
        fill=CARD_COLOR,
        outline=BORDER_COLOR,
        width=BORDER_WIDTH,
    )

    if two_lines:
        draw.text((PAD_X, PAD_Y), prefix, fill=TEXT_COLOR, font=fnt)
        expr_y = PAD_Y + line1_h
        expr_baseline = ebl
        _draw_tree(draw, tree, PAD_X, expr_y, expr_baseline, fnt, fnt_frac)
    else:
        cx = PAD_X
        line_baseline = max(ebl, FONT_SIZE // 2 + 2)
        if prefix:
            draw.text((cx, PAD_Y + line_baseline - FONT_SIZE // 2 - 2), prefix, fill=TEXT_COLOR, font=fnt)
            cx += prefix_w
        _draw_tree(draw, tree, cx, PAD_Y, line_baseline, fnt, fnt_frac)

    return img


# ── Measurement helpers ────────────────────────────────────────


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _measure_token(
    draw: ImageDraw.ImageDraw,
    token: tuple[str, str],
    fnt: ImageFont.FreeTypeFont,
    fnt_frac: ImageFont.FreeTypeFont,
) -> int:
    typ, val = token
    if typ == "frac":
        num, den = val.split("/")
        return max(_text_width(draw, num, fnt_frac), _text_width(draw, den, fnt_frac)) + 10
    elif typ == "neg_frac":
        sign = val[0]
        num, den = val[1:].split("/")
        sign_w = _text_width(draw, sign, fnt) + 2
        frac_w = max(_text_width(draw, num, fnt_frac), _text_width(draw, den, fnt_frac)) + 10
        return sign_w + frac_w
    elif typ == "mixed_frac":
        parts = val.split()
        whole = parts[0]
        num, den = parts[1].split("/")
        whole_w = _text_width(draw, whole + " ", fnt)
        frac_w = max(_text_width(draw, num, fnt_frac), _text_width(draw, den, fnt_frac)) + 10
        return whole_w + frac_w
    else:
        return _text_width(draw, val, fnt)


# ── Line wrapping ─────────────────────────────────────────────


def _wrap_tokens(
    draw: ImageDraw.ImageDraw,
    tokens: list[tuple[str, str]],
    fnt: ImageFont.FreeTypeFont,
    fnt_frac: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[list[tuple[str, str]]]:
    """Word-wrap tokens into lines that fit within max_width."""
    space_w = _text_width(draw, " ", fnt)
    lines: list[list[tuple[str, str]]] = []
    current_line: list[tuple[str, str]] = []
    current_w = 0

    for token in tokens:
        if token[0] == "br":
            if current_line:
                lines.append(current_line)
            current_line = []
            current_w = 0
            continue
        tw = _measure_token(draw, token, fnt, fnt_frac)
        needed = tw + (space_w if current_line else 0)
        if current_w + needed > max_width and current_line:
            lines.append(current_line)
            current_line = [token]
            current_w = tw
        else:
            current_line.append(token)
            current_w += needed

    if current_line:
        lines.append(current_line)
    return lines


# ── Rendering ─────────────────────────────────────────────────


def _render_card(
    text: str,
    fnt: ImageFont.FreeTypeFont,
    fnt_frac: ImageFont.FreeTypeFont,
) -> Image.Image:
    """Render a single problem text into a PNG card image."""
    for old_ch, new_ch in CHAR_REPLACEMENTS.items():
        text = text.replace(old_ch, new_ch)

    tmp = Image.new("RGB", (1, 1))
    tmp_draw = ImageDraw.Draw(tmp)

    tokens = _tokenize(text)
    max_line_w = CARD_WIDTH - 2 * PAD_X - 20
    lines = _wrap_tokens(tmp_draw, tokens, fnt, fnt_frac, max_line_w)
    space_w = _text_width(tmp_draw, " ", fnt)

    # Detect system-of-equations lines (starting with "{") and collect groups
    BRACE_INDENT = 42
    brace_groups: list[tuple[int, int]] = []  # (first_line_idx, last_line_idx)
    brace_lines: set[int] = set()
    i = 0
    while i < len(lines):
        if lines[i] and lines[i][0] == ("word", "{"):
            group_start = i
            while i < len(lines) and lines[i] and lines[i][0] == ("word", "{"):
                lines[i] = lines[i][1:]  # strip the "{" token
                brace_lines.add(i)
                i += 1
            brace_groups.append((group_start, i - 1))
        else:
            i += 1

    # Compute height
    height = PAD_Y * 2 + len(lines) * LINE_SPACING
    height = max(height, MIN_HEIGHT)

    # Create final canvas
    img = Image.new("RGB", (CARD_WIDTH, height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Card background with rounded corners
    draw.rounded_rectangle(
        [10, 10, CARD_WIDTH - 10, height - 10],
        radius=CORNER_RADIUS,
        fill=CARD_COLOR,
        outline=BORDER_COLOR,
        width=BORDER_WIDTH,
    )

    # Render lines
    y = PAD_Y
    for line_idx, line_tokens in enumerate(lines):
        x = PAD_X + (BRACE_INDENT if line_idx in brace_lines else 0)
        for i, (typ, val) in enumerate(line_tokens):
            if i > 0:
                x += space_w

            if typ in ("frac", "neg_frac"):
                if typ == "neg_frac":
                    sign = val[0]
                    draw.text((x, y), sign, fill=TEXT_COLOR, font=fnt)
                    x += _text_width(draw, sign, fnt) + 2
                    num, den = val[1:].split("/")
                else:
                    num, den = val.split("/")

                num_w = _text_width(draw, num, fnt_frac)
                den_w = _text_width(draw, den, fnt_frac)
                frac_w = max(num_w, den_w) + 10
                center_y = y + FONT_SIZE // 2

                draw.text(
                    (x + (frac_w - num_w) // 2, center_y - 28),
                    num, fill=TEXT_COLOR, font=fnt_frac,
                )
                draw.rectangle(
                    [x + 2, center_y - 1, x + frac_w - 2, center_y + 1],
                    fill=FRAC_LINE_COLOR,
                )
                draw.text(
                    (x + (frac_w - den_w) // 2, center_y + 5),
                    den, fill=TEXT_COLOR, font=fnt_frac,
                )
                x += frac_w

            elif typ == "mixed_frac":
                parts = val.split()
                whole = parts[0]
                num, den = parts[1].split("/")

                draw.text((x, y), whole, fill=TEXT_COLOR, font=fnt)
                x += _text_width(draw, whole, fnt) + 2

                num_w = _text_width(draw, num, fnt_frac)
                den_w = _text_width(draw, den, fnt_frac)
                frac_w = max(num_w, den_w) + 10
                center_y = y + FONT_SIZE // 2

                draw.text(
                    (x + (frac_w - num_w) // 2, center_y - 28),
                    num, fill=TEXT_COLOR, font=fnt_frac,
                )
                draw.rectangle(
                    [x + 2, center_y - 1, x + frac_w - 2, center_y + 1],
                    fill=FRAC_LINE_COLOR,
                )
                draw.text(
                    (x + (frac_w - den_w) // 2, center_y + 5),
                    den, fill=TEXT_COLOR, font=fnt_frac,
                )
                x += frac_w

            else:
                draw.text((x, y), val, fill=TEXT_COLOR, font=fnt)
                x += _text_width(draw, val, fnt)

        y += LINE_SPACING

    # Draw large curly braces for system-of-equations groups
    for g_start, g_end in brace_groups:
        top_y = PAD_Y + g_start * LINE_SPACING + 4
        bot_y = PAD_Y + g_end * LINE_SPACING + FONT_SIZE - 2
        brace_h = bot_y - top_y
        brace_x = PAD_X - 6

        if brace_h < 10:
            continue

        # Scale the "{" glyph to span the full height of the equation group
        brace_font_size = max(int(brace_h * 1.25), FONT_SIZE)
        brace_fnt = ImageFont.truetype(FONT_PATH, brace_font_size)
        bbox = draw.textbbox((0, 0), "{", font=brace_fnt)
        glyph_h = bbox[3] - bbox[1]

        # Center the glyph vertically over the group
        mid_y = (top_y + bot_y) // 2
        glyph_y = mid_y - glyph_h // 2 - bbox[1]

        draw.text((brace_x, glyph_y), "{", fill=TEXT_COLOR, font=brace_fnt)

    return img


# ── Main ──────────────────────────────────────────────────────


def generate_all(lang: str = "ru") -> None:
    """Generate image cards for every problem and update JSON."""
    if lang == "kz":
        out_dir = PROJECT_ROOT / "static" / "questions_kz"
        text_field = "text_kz"
        img_field = "image_file_kz"
        prefix = "static/questions_kz"
    else:
        out_dir = OUTPUT_DIR
        text_field = "text_ru"
        img_field = "image_file"
        prefix = "static/questions"

    out_dir.mkdir(parents=True, exist_ok=True)

    with open(PROBLEMS_PATH, encoding="utf-8") as f:
        data = json.load(f)

    problems = data["problems"]
    print(f"Loaded {len(problems)} problems from {PROBLEMS_PATH.name} (lang={lang})")

    fnt = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    fnt_frac = ImageFont.truetype(FONT_PATH, FRAC_FONT_SIZE)

    t0 = time.time()
    generated = 0
    skipped = 0

    for idx, p in enumerate(problems):
        existing_img = p.get(img_field, "")
        if existing_img and not existing_img.startswith(prefix):
            skipped += 1
            continue

        text = p.get(text_field, "")
        if not text.strip():
            if lang == "kz":
                text = p.get("text_ru", "")
            if not text.strip():
                skipped += 1
                continue

        node_id = p.get("node_id", "UNK")
        sub_diff = p.get("sub_difficulty", 0)

        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        suffix = f"_{lang}" if lang != "ru" else ""
        filename = f"{node_id}_L{sub_diff}_{text_hash}{suffix}.png"
        filepath = out_dir / filename

        if _has_complex_fraction(text):
            img = _render_complex_card(text, fnt, fnt_frac)
        else:
            img = _render_card(text, fnt, fnt_frac)
        img.save(str(filepath), "PNG", optimize=True)

        p[img_field] = f"{prefix}/{filename}"
        generated += 1

        if (generated % 100) == 0:
            print(f"  ... {generated} images generated")

    elapsed = time.time() - t0

    with open(PROBLEMS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total_size = sum(
        fp.stat().st_size for fp in out_dir.glob("*.png")
    )

    print(
        f"\nDone: {generated} images generated, {skipped} skipped "
        f"({elapsed:.1f}s)"
    )
    print(f"Total size: {total_size / 1024 / 1024:.1f} MB")
    print(f"Output: {out_dir}")
    print(f"JSON updated: {PROBLEMS_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate problem image cards")
    parser.add_argument("--lang", default="ru", choices=["ru", "kz"],
                        help="Language: ru (default) or kz")
    args = parser.parse_args()
    generate_all(lang=args.lang)
