"""
PR (Proportions) difficulty scorer — PR01 through PR06.
"""

from __future__ import annotations

import math
import re

PR_TOPICS = {'PR01', 'PR02', 'PR03', 'PR04', 'PR05', 'PR06'}


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


def _score_ratio(text: str) -> float:
    """PR01 — ratios."""
    mn = _max_number(text)
    nc = _num_count(text)
    has_frac = 1 if '/' in text else 0
    word_problem = 1 if re.search(r'класс|мальчик|девоч', text.lower()) else 0
    base = (0.3 * math.log2(max(mn, 2)) + 0.5 * nc +
            1.5 * has_frac + 1.5 * word_problem)
    return round(base, 2)


def _score_proportion(text: str) -> float:
    """PR02 — proportions (verify/solve)."""
    mn = _max_number(text)
    nc = _num_count(text)
    has_frac = 1 if '/' in text else 0
    has_decimal = 1 if re.search(r'\d+[.,]\d', text) else 0
    base = (0.3 * math.log2(max(mn, 2)) + 0.5 * nc +
            1.0 * has_frac + 1.0 * has_decimal)
    return round(base, 2)


def _score_solve_x(text: str) -> float:
    """PR03 — solve for x in proportion."""
    mn = _max_number(text)
    nc = _num_count(text)
    has_decimal = 1 if re.search(r'\d+[.,]\d', text) else 0
    has_nested = 1 if re.search(r'\(.*[xy].*\)', text.lower()) else 0
    base = (0.3 * math.log2(max(mn, 2)) + 0.8 * nc +
            1.5 * has_decimal + 2.0 * has_nested)
    return round(base, 2)


def _score_direct(text: str) -> float:
    """PR04 — direct proportionality word problems."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)
    base = (0.3 * math.log2(max(mn, 2)) + 0.8 * nc + 0.02 * tl)
    return round(base, 2)


def _score_inverse(text: str) -> float:
    """PR05 — inverse proportionality word problems."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)
    base = (0.3 * math.log2(max(mn, 2)) + 0.8 * nc + 0.02 * tl + 1.0)
    return round(base, 2)


def _score_compound(text: str) -> float:
    """PR06 — compound proportionality."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)
    base = (0.3 * math.log2(max(mn, 2)) + 0.8 * nc + 0.02 * tl + 2.0)
    return round(base, 2)


_SCORE_MAP = {
    'PR01': _score_ratio,
    'PR02': _score_proportion,
    'PR03': _score_solve_x,
    'PR04': _score_direct,
    'PR05': _score_inverse,
    'PR06': _score_compound,
}


def score_problem(text: str, topic: str) -> float:
    fn = _SCORE_MAP.get(topic)
    return fn(text) if fn else 0.0
