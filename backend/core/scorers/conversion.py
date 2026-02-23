"""
CV (Conversions) difficulty scorer — CV01 through CV06.
"""

from __future__ import annotations

import math
import re

CV_TOPICS = {'CV01', 'CV02', 'CV03', 'CV04', 'CV05', 'CV06'}


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


def _has_mixed_units(text: str) -> bool:
    """Detect mixed unit expressions like '3 т 20 ц 15 кг'."""
    return bool(re.search(r'\d+\s+\w+\s+\d+\s+\w+\s+\d+\s+\w+', text))


def _has_decimal(text: str) -> bool:
    return bool(re.search(r'\d+[.,]\d', text))


def _score_conversion(text: str) -> float:
    """Generic conversion scorer used for all CV topics."""
    mn = _max_number(text)
    nc = _num_count(text)
    decimal = 1.5 if _has_decimal(text) else 0
    mixed = 2.0 if _has_mixed_units(text) else 0
    very_small = 1.5 if re.search(r'0[.,]0{2,}', text) else 0
    base = (0.3 * math.log2(max(mn, 2)) + 0.8 * nc +
            decimal + mixed + very_small)
    return round(base, 2)


_SCORE_MAP = {
    'CV01': _score_conversion,
    'CV02': _score_conversion,
    'CV03': _score_conversion,
    'CV04': _score_conversion,
    'CV05': _score_conversion,
    'CV06': _score_conversion,
}


def score_problem(text: str, topic: str) -> float:
    fn = _SCORE_MAP.get(topic)
    return fn(text) if fn else 0.0
