"""
PC (Percentages) difficulty scorer — PC01 through PC06.
"""

from __future__ import annotations

import math
import re

PC_TOPICS = {'PC01', 'PC02', 'PC03', 'PC04', 'PC05', 'PC06'}


def _numbers(text: str) -> list[float]:
    raw = re.findall(r'\d+(?:[.,]\d+)?', text)
    out = []
    for r in raw:
        r = r.replace(',', '.')
        try:
            out.append(float(r))
        except ValueError:
            pass
    return out


def _max_number(text: str) -> float:
    nums = _numbers(text)
    return max(nums) if nums else 0


def _num_count(text: str) -> int:
    return len(_numbers(text))


def _text_len(text: str) -> int:
    return len(text)


def _score_basic(text: str) -> float:
    """PC01 — basic percent concepts."""
    nc = _num_count(text)
    tl = _text_len(text)
    has_frac = 1 if '/' in text else 0
    has_decimal = 1 if re.search(r'0[.,]\d', text) else 0
    base = 0.8 * nc + 0.02 * tl + 1.5 * has_frac + 1.0 * has_decimal
    return round(max(base, 0.5), 2)


def _score_find_pct(text: str) -> float:
    """PC02 — find X% of N."""
    mn = _max_number(text)
    nc = _num_count(text)
    has_decimal_pct = 1 if re.search(r'\d+[.,]\d+\s*%', text) else 0
    over_100 = 1 if re.search(r'[12]\d\d\s*%', text) else 0
    base = (0.3 * math.log2(max(mn, 2)) + 0.8 * nc +
            2.0 * has_decimal_pct + 1.5 * over_100)
    return round(base, 2)


def _score_find_number(text: str) -> float:
    """PC03 — find number given X% = value."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)
    multi_step = 1 if re.search(r'первый день.*второй день|остал', text.lower()) else 0
    base = (0.3 * math.log2(max(mn, 2)) + 0.8 * nc + 0.01 * tl +
            3.0 * multi_step)
    return round(base, 2)


def _score_what_pct(text: str) -> float:
    """PC04 — what percent is A of B."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)
    multi_change = 1 if re.search(r'увеличили.*уменьшили|уменьшили.*увеличили', text.lower()) else 0
    base = (0.3 * math.log2(max(mn, 2)) + 0.8 * nc + 0.01 * tl +
            3.0 * multi_change)
    return round(base, 2)


def _score_word(text: str) -> float:
    """PC05 — word problems with percentages."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)
    compound = 1 if re.search(r'через.*год|ежегодн|дважды', text.lower()) else 0
    multi_step = 1 if nc > 4 else 0
    base = (0.3 * math.log2(max(mn, 2)) + 0.8 * nc + 0.02 * tl +
            2.0 * compound + 1.5 * multi_step)
    return round(base, 2)


def _score_mixture(text: str) -> float:
    """PC06 — mixture/concentration."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)
    num_solutions = len(re.findall(r'\d+\s*%\s*-?\w*\s*раствор|\d+\s*г\s+\d+\s*%', text.lower()))
    evaporate = 1 if re.search(r'выпарили|добавили.*вод', text.lower()) else 0
    base = (0.3 * math.log2(max(mn, 2)) + 0.8 * nc + 0.02 * tl +
            1.5 * num_solutions + 1.5 * evaporate)
    return round(base, 2)


_SCORE_MAP = {
    'PC01': _score_basic,
    'PC02': _score_find_pct,
    'PC03': _score_find_number,
    'PC04': _score_what_pct,
    'PC05': _score_word,
    'PC06': _score_mixture,
}


def score_problem(text: str, topic: str) -> float:
    fn = _SCORE_MAP.get(topic)
    return fn(text) if fn else 0.0
