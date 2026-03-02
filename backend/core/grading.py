"""Answer grading — rule-based + Claude LLM fallback.

Strategy:
    1. Multi-stage normalisation and comparison pipeline (fast, free).
    2. If rule-based says "incorrect" and ANTHROPIC_API_KEY is set,
       ask Claude to double-check (catches false negatives from open-format).

    Rule-based handles:
    - "1/2" vs "0.5" vs "0,5", integer vs float
    - Mixed numbers: "2 1/3"
    - Unicode minus signs (−, –, —)
    - Units: "32%" == "32", "75°" == "75", "12 см" == "12"
    - Multi-value: "16; 25" vs "25; 16" (set comparison)
    - Text with number: "Уменьшится на 51%" vs "51"
    - Parentheses/braces: "(3; 2)" vs "3; 2"
"""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from fractions import Fraction

logger = logging.getLogger(__name__)

_anthropic_client = None

# ── Character normalisation tables ────────────────────────────

_DASHES = str.maketrans({
    "\u2212": "-",  # MINUS SIGN
    "\u2013": "-",  # EN DASH
    "\u2014": "-",  # EM DASH
    "\u2010": "-",  # HYPHEN
    "\u2011": "-",  # NON-BREAKING HYPHEN
    "\u00d7": "*",  # MULTIPLICATION SIGN
})

_MIXED_RE = re.compile(r"^(-?\d+)\s+(\d+\s*/\s*\d+)$")

# ── Unit / suffix stripping ───────────────────────────────────

_UNITS_RE = re.compile(
    r"\s*(?:"
    r"км/час|км/ч|м/с|т/га"           # compound speed/area units first
    r"|см(?:[²³]|\^[23])?|дм(?:[²³]|\^[23])?"  # length + area/volume
    r"|мм(?:[²³]|\^[23])?|км(?:[²³]|\^[23])?"
    r"|м(?:[²³]|\^[23])?"             # metre (must come after км/мм/дм/см)
    r"|кг|г(?:р(?:амм\w*)?)?|тонн\w*" # mass
    r"|литр\w*|л"                      # volume
    r"|тг|тенге|сом|руб\w*"           # currency
    r"|мин(?:ут\w*)?|час\w*|сек(?:унд\w*)?" # time
    r"|лет|год\w*|месяц\w*|дн(?:ей|я)?"    # time periods
    r"|недел\w*"                       # weeks
    r"|градус\w*|°"                    # degrees
    r"|%"                              # percent
    r")\s*$",
    re.IGNORECASE,
)


def _strip_wrapping(text: str) -> str:
    """Remove wrapping parentheses or braces if balanced inside."""
    if len(text) < 2:
        return text
    if (text[0] == "(" and text[-1] == ")") or \
       (text[0] == "{" and text[-1] == "}"):
        inner = text[1:-1]
        opener = text[0]
        closer = text[-1]
        depth = 0
        balanced = True
        for ch in inner:
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
            if depth < 0:
                balanced = False
                break
        if balanced and depth == 0:
            return inner
    return text


# ── Normalisation ─────────────────────────────────────────────

def _normalise(text: str) -> str:
    """Lower-case, strip, collapse whitespace, normalise unicode,
    strip units and wrapping brackets."""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_DASHES)
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*:\s*", ":", text)
    text = text.rstrip(".")
    text = _strip_wrapping(text)
    text = _UNITS_RE.sub("", text)
    text = text.replace(",", ".")
    text = text.strip()
    return text


def _normalise_keep_separators(text: str) -> str:
    """Normalise but keep ; and , as-is (for multi-value splitting)."""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_DASHES)
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*:\s*", ":", text)
    text = text.rstrip(".")
    text = _strip_wrapping(text)
    return text


def _compact(text: str) -> str:
    """Aggressive normalisation: remove all spaces, treat : as /."""
    return _normalise(text).replace(" ", "").replace(":", "/")


# ── Number parsing ────────────────────────────────────────────

def _try_as_number(text: str) -> float | None:
    """Try to parse text as a number (int, float, simple or mixed fraction).

    Supports: 42, 3.14, 3,14, -5, 1/2, -2/3, 2 1/3, -1 3/4, 4:9.
    """
    text = text.replace(",", ".").strip()
    if text.count(":") == 1 and "/" not in text:
        text = text.replace(":", "/")

    m = _MIXED_RE.match(text)
    if m:
        try:
            whole = int(m.group(1))
            frac = Fraction(m.group(2).replace(" ", ""))
            sign = -1 if whole < 0 else 1
            return float(abs(whole)) * sign + sign * float(frac)
        except (ValueError, ZeroDivisionError):
            pass

    text = text.replace(" ", "")
    if "/" in text:
        try:
            return float(Fraction(text))
        except (ValueError, ZeroDivisionError):
            pass
    try:
        return float(text)
    except ValueError:
        return None


def _try_as_fraction(text: str) -> Fraction | None:
    """Try to parse text as an exact Fraction.

    Supports: 1/2, 4/6, 0.5, 0,5, 2 1/3, -3/4, 4:9.
    """
    text = text.replace(",", ".").strip()
    if text.count(":") == 1 and "/" not in text:
        text = text.replace(":", "/")

    m = _MIXED_RE.match(text)
    if m:
        try:
            whole = int(m.group(1))
            frac = Fraction(m.group(2).replace(" ", ""))
            sign = -1 if whole < 0 else 1
            return Fraction(abs(whole)) * sign + frac * sign
        except (ValueError, ZeroDivisionError):
            pass

    text = text.replace(" ", "")
    try:
        return Fraction(text)
    except (ValueError, ZeroDivisionError):
        return None


# ── Multi-value comparison ────────────────────────────────────

def _compare_multi_value(sa: str, ca: str) -> bool | None:
    """Compare answers that contain multiple values separated by ; or ,.

    Returns True/False if comparison is possible, None if not applicable.
    Both inputs should be normalised with _normalise_keep_separators.
    """
    for sep in (";", ","):
        if sep not in ca and sep not in sa:
            continue

        ca_parts = [_normalise(p) for p in ca.split(sep) if p.strip()]
        if len(ca_parts) < 2:
            # Also try the other separator for ca
            other = "," if sep == ";" else ";"
            ca_parts = [_normalise(p) for p in ca.split(other) if p.strip()]
            if len(ca_parts) < 2:
                continue

        # Split sa by either ; or ,
        sa_parts = [_normalise(p) for p in re.split(r"[;,]", sa) if p.strip()]

        if len(ca_parts) != len(sa_parts):
            return None

        ca_nums = [_try_as_number(p) for p in ca_parts]
        sa_nums = [_try_as_number(p) for p in sa_parts]

        if all(n is not None for n in ca_nums) and \
           all(n is not None for n in sa_nums):
            if _nums_equal(ca_nums, sa_nums):
                return True
            if _nums_equal(sorted(ca_nums), sorted(sa_nums)):
                return True
            return False

        # Text fallback: compare sorted parts
        if sorted(ca_parts) == sorted(sa_parts):
            return True
        if ca_parts == sa_parts:
            return True
        return False

    return None


def _nums_equal(a: list[float | None], b: list[float | None]) -> bool:
    """Element-wise numeric comparison with tolerance."""
    if len(a) != len(b):
        return False
    return all(
        x is not None and y is not None and abs(x - y) < 1e-6
        for x, y in zip(a, b)
    )


# ── Extract number from text answer ──────────────────────────

_NUMBER_IN_TEXT_RE = re.compile(r"-?\d+(?:[.,]\d+)?(?:\s*/\s*\d+)?")


def _extract_number_from_text(text: str) -> float | None:
    """Extract a single number from a text answer like 'Уменьшится на 51%'.

    Returns the number if exactly one is found, None otherwise.
    """
    nums = _NUMBER_IN_TEXT_RE.findall(text)
    if len(nums) == 1:
        return _try_as_number(nums[0])
    return None


# ── Unit conversion ───────────────────────────────────────────

# Unit conversion tables — value is the multiplier to convert to base unit
_UNIT_TO_BASE = {
    # Длина → метры
    'мм': ('length', 0.001), 'см': ('length', 0.01), 'дм': ('length', 0.1),
    'м': ('length', 1.0), 'км': ('length', 1000.0),
    'mm': ('length', 0.001), 'cm': ('length', 0.01), 'dm': ('length', 0.1),
    'm': ('length', 1.0), 'km': ('length', 1000.0),
    # Масса → граммы
    'мг': ('mass', 0.001), 'г': ('mass', 1.0), 'кг': ('mass', 1000.0),
    'ц': ('mass', 100000.0), 'т': ('mass', 1000000.0),
    'тонн': ('mass', 1000000.0), 'тонна': ('mass', 1000000.0),
    'mg': ('mass', 0.001), 'g': ('mass', 1.0), 'kg': ('mass', 1000.0),
    't': ('mass', 1000000.0),
    # Площадь → м²
    'мм²': ('area', 1e-6), 'см²': ('area', 1e-4), 'дм²': ('area', 0.01),
    'м²': ('area', 1.0), 'км²': ('area', 1e6),
    'га': ('area', 10000.0), 'а': ('area', 100.0),
    'mm²': ('area', 1e-6), 'cm²': ('area', 1e-4), 'dm²': ('area', 0.01),
    'm²': ('area', 1.0), 'km²': ('area', 1e6),
    # Объём → литры
    'мл': ('volume', 0.001), 'л': ('volume', 1.0), 'дл': ('volume', 0.1),
    'см³': ('volume', 0.001), 'дм³': ('volume', 1.0), 'м³': ('volume', 1000.0),
    'ml': ('volume', 0.001), 'l': ('volume', 1.0),
    'cm³': ('volume', 0.001), 'dm³': ('volume', 1.0), 'm³': ('volume', 1000.0),
    # Время → секунды (все словоформы)
    'с': ('time', 1.0), 'сек': ('time', 1.0),
    'секунд': ('time', 1.0), 'секунда': ('time', 1.0), 'секунды': ('time', 1.0),
    'мин': ('time', 60.0),
    'минут': ('time', 60.0), 'минута': ('time', 60.0), 'минуты': ('time', 60.0),
    'ч': ('time', 3600.0),
    'час': ('time', 3600.0), 'часа': ('time', 3600.0), 'часов': ('time', 3600.0),
    'сут': ('time', 86400.0), 'суток': ('time', 86400.0),
    'день': ('time', 86400.0), 'дня': ('time', 86400.0), 'дней': ('time', 86400.0),
    'sec': ('time', 1.0), 'min': ('time', 60.0), 'h': ('time', 3600.0),
    # Скорость → м/с
    'м/с': ('speed', 1.0), 'м/мин': ('speed', 1/60),
    'км/ч': ('speed', 1/3.6), 'км/час': ('speed', 1/3.6),
}

_UNIT_NUMBER_RE = re.compile(r'^(-?\d+(?:[.,]\d+)?)\s*(.+)$')


def _extract_number_and_unit(text: str):
    """Extract (number, unit) from text like '3см', '0.3 дм', '150kg'."""
    text = text.strip().lower()
    # Normalise unicode dashes to ASCII minus
    text = text.translate(_DASHES)
    # Replace comma with period for Russian decimals
    text = text.replace(',', '.')
    # Try to match number followed by optional unit
    m = _UNIT_NUMBER_RE.match(text)
    if m:
        try:
            num = float(m.group(1))
            unit = m.group(2).strip()
            if unit in _UNIT_TO_BASE:
                return num, unit
        except ValueError:
            pass
    return None, None


def _try_unit_conversion(student_raw: str, correct_raw: str) -> bool:
    """Compare answers after unit conversion. Returns True if equivalent."""
    s_num, s_unit = _extract_number_and_unit(student_raw)
    c_num, c_unit = _extract_number_and_unit(correct_raw)
    if s_num is None or c_num is None:
        return False
    if s_unit is None or c_unit is None:
        return False
    s_dim, s_factor = _UNIT_TO_BASE[s_unit]
    c_dim, c_factor = _UNIT_TO_BASE[c_unit]
    if s_dim != c_dim:
        return False
    s_base = s_num * s_factor
    c_base = c_num * c_factor
    return abs(s_base - c_base) < 1e-6


# ── Symbol ↔ word equivalence ─────────────────────────────────

_SYMBOL_TO_WORD = {
    "*": "умножение", "×": "умножение", "·": "умножение",
    "+": "сложение",
    "-": "вычитание", "−": "вычитание",
    "/": "деление", "÷": "деление",
}
_WORD_TO_SYMBOLS = {}
for _sym, _word in _SYMBOL_TO_WORD.items():
    _WORD_TO_SYMBOLS.setdefault(_word, set()).add(_sym)


# ── Main grading logic ────────────────────────────────────────

def check_answer_rule_based(
    student_answer: str, correct_answer: str, answer_type: str | None = None
) -> bool:
    """Rule-based check. Returns True if clearly correct."""
    sa = _normalise(student_answer)
    ca = _normalise(correct_answer)

    if not sa:
        return False

    # ── 0.5. Unit-aware gate ──
    # If both raw answers have recognised units, delegate entirely to
    # unit conversion so that "3см" vs "3кг" is NOT accepted.
    _s_num, _s_unit = _extract_number_and_unit(student_answer)
    _c_num, _c_unit = _extract_number_and_unit(correct_answer)
    if _s_unit is not None and _c_unit is not None:
        return _try_unit_conversion(student_answer, correct_answer)

    # ── 0. Symbol ↔ word equivalence (e.g. * == умножение) ──
    if sa in _SYMBOL_TO_WORD and ca == _SYMBOL_TO_WORD[sa]:
        return True
    if ca in _SYMBOL_TO_WORD and sa == _SYMBOL_TO_WORD[ca]:
        return True
    if sa in _WORD_TO_SYMBOLS and ca in _WORD_TO_SYMBOLS[sa]:
        return True
    if ca in _WORD_TO_SYMBOLS and sa in _WORD_TO_SYMBOLS[ca]:
        return True

    # ── 1. Exact string match after normalisation ──
    if sa == ca:
        return True

    # ── 2. Numeric comparison (works for all answer_types) ──
    sn = _try_as_number(sa)
    cn = _try_as_number(ca)
    if sn is not None and cn is not None:
        if abs(sn - cn) < 1e-6:
            return True

    # ── 3. Exact fraction comparison ──
    if answer_type in ("fraction", None):
        sf = _try_as_fraction(sa)
        cf = _try_as_fraction(ca)
        if sf is not None and cf is not None and sf == cf:
            return True

    # ── 4. Compact string comparison (all spaces removed, : → /) ──
    if _compact(student_answer) == _compact(correct_answer):
        return True

    # ── 5. Multi-value comparison (;  or , separated) ──
    ca_raw = _normalise_keep_separators(correct_answer)
    sa_raw = _normalise_keep_separators(student_answer)
    multi = _compare_multi_value(sa_raw, ca_raw)
    if multi is not None:
        return multi

    # ── 6. Text-embedded number extraction ──
    # If correct answer has text + number, and student typed just the number
    if sn is not None and cn is None:
        extracted = _extract_number_from_text(ca)
        if extracted is not None and abs(sn - extracted) < 1e-6:
            return True
    # Reverse: student typed text, correct is just number
    if cn is not None and sn is None:
        extracted = _extract_number_from_text(sa)
        if extracted is not None and abs(cn - extracted) < 1e-6:
            return True

    return False


# ── Claude LLM fallback ──────────────────────────────────────

_CLAUDE_PROMPT = (
    "Ты проверяешь математическую задачу ученика 7-8 класса.\n\n"
    "Задача:\n{problem_text}\n\n"
    "Правильный ответ: {correct_answer}\n"
    "Ответ ученика: {student_answer}\n\n"
    "Ответ ученика математически эквивалентен правильному?\n"
    "Учитывай: разные записи (дроби/десятичные), знаки, порядок, "
    "округление, единицы измерения, эквивалентные выражения, "
    "символы операций (* = умножение, / = деление и т.п.).\n\n"
    "ВАЖНО: Первое слово ответа ОБЯЗАТЕЛЬНО YES или NO.\n"
    "Затем одно предложение-пояснение на русском."
)

_CLAUDE_TIMEOUT = 8.0


def _get_anthropic_client():
    """Lazy-init the async Anthropic client."""
    global _anthropic_client
    if _anthropic_client is None:
        try:
            import anthropic
            from core.config import settings
            if settings.anthropic_api_key:
                _anthropic_client = anthropic.AsyncAnthropic(
                    api_key=settings.anthropic_api_key
                )
        except ImportError:
            logger.warning("anthropic package not installed, LLM fallback disabled")
    return _anthropic_client


async def check_with_claude(
    student_answer: str, correct_answer: str, problem_text: str
) -> tuple[bool, str]:
    """Ask Claude whether the student's answer is equivalent.

    Returns (is_correct, explanation).
    Falls back to (False, "") on any error.
    """
    client = _get_anthropic_client()
    if client is None:
        return False, ""

    prompt = _CLAUDE_PROMPT.format(
        problem_text=problem_text[:500],
        correct_answer=correct_answer[:200],
        student_answer=student_answer[:200],
    )

    try:
        response = await asyncio.wait_for(
            client.messages.create(
                model="claude-sonnet-4-5-20241022",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}],
            ),
            timeout=_CLAUDE_TIMEOUT,
        )
        text = response.content[0].text.strip()
        lines = text.split("\n")
        first_line = lines[0].strip().upper()
        explanation = "\n".join(lines[1:]).strip()

        if first_line.startswith("YES"):
            rest = lines[0].strip()[3:].strip().lstrip(".,:-").strip()
            full = f"{rest}\n{explanation}".strip() if rest else explanation
            return True, full or "Подтверждено AI"
        if first_line.startswith("NO"):
            rest = lines[0].strip()[2:].strip().lstrip(".,:-").strip()
            full = f"{rest}\n{explanation}".strip() if rest else explanation
            return False, full or "Ответ ученика не эквивалентен правильному"

        text_upper = text.upper()
        if "\nYES" in text_upper or text_upper.endswith("YES"):
            return True, text
        return False, text

    except asyncio.TimeoutError:
        logger.warning("Claude timeout (%.1fs)", _CLAUDE_TIMEOUT)
        return False, ""
    except (RuntimeError, ValueError, AttributeError, IndexError) as exc:
        logger.warning("Claude LLM check failed: %s", exc)
        return False, ""


# ── Public API ────────────────────────────────────────────────


def check_answer(
    student_answer: str, correct_answer: str, answer_type: str | None = None
) -> bool:
    """Synchronous rule-based check."""
    return check_answer_rule_based(student_answer, correct_answer, answer_type)


async def check_answer_smart(
    student_answer: str,
    correct_answer: str,
    problem_text: str,
    answer_type: str | None = None,
) -> tuple[bool, str]:
    """Rule-based check. Claude is invoked separately on dispute only."""
    is_correct = check_answer_rule_based(
        student_answer, correct_answer, answer_type
    )
    return is_correct, ""
