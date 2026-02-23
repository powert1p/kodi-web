"""
CB (Combinatorics) difficulty scorer — CB01 through CB07.
"""

from __future__ import annotations

import math
import re

CB_TOPICS = {'CB01', 'CB02', 'CB03', 'CB04', 'CB05', 'CB06', 'CB07'}


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


def _score_principle(text: str) -> float:
    """CB01 — multiplication/addition principle."""
    nc = _num_count(text)
    mn = _max_number(text)
    tl = _text_len(text)
    has_addition = 1 if re.search(r'или|всего маршрут', text.lower()) else 0
    base = (0.3 * math.log2(max(mn, 2)) + 0.8 * nc +
            0.01 * tl + 1.0 * has_addition)
    return round(base, 2)


def _score_no_repeat(text: str) -> float:
    """CB02 — permutations without repetition / grid paths."""
    nc = _num_count(text)
    mn = _max_number(text)
    tl = _text_len(text)
    is_grid = 1 if re.search(r'вправо|вверх|сетк', text.lower()) else 0
    base = (0.3 * math.log2(max(mn, 2)) + 0.8 * nc +
            0.01 * tl + 1.5 * is_grid)
    return round(base, 2)


def _score_with_repeat(text: str) -> float:
    """CB03 — permutations with repetition / anagrams."""
    nc = _num_count(text)
    tl = _text_len(text)
    word_len = 0
    m = re.search(r'слова\s+(\w+)', text)
    if m:
        word_len = len(m.group(1))
    constraints = len(re.findall(r'первая\s+цифра|нечётн|чётн|условие', text.lower()))
    base = (0.5 * nc + 0.02 * tl + 0.5 * word_len +
            1.5 * min(constraints, 2))
    return round(base, 2)


def _score_constrained(text: str) -> float:
    """CB04 — counting with constraints."""
    nc = _num_count(text)
    mn = _max_number(text)
    tl = _text_len(text)
    constraints = len(re.findall(r'нечётн|чётн|кратн|делится|различн|больше|меньше', text.lower()))
    base = (0.3 * math.log2(max(mn, 2)) + 0.8 * nc +
            0.02 * tl + 1.5 * min(constraints, 3))
    return round(base, 2)


def _score_permutation(text: str) -> float:
    """CB05 — permutations (n!)."""
    nc = _num_count(text)
    mn = _max_number(text)
    tl = _text_len(text)
    base = (0.4 * math.log2(max(mn, 2)) + 0.5 * nc + 0.01 * tl)
    return round(base, 2)


def _score_factorial(text: str) -> float:
    """CB06 — factorials."""
    mn = _max_number(text)
    nc = _num_count(text)
    has_division = 1 if re.search(r'!/|÷', text) else 0
    has_trailing_zeros = 1 if re.search(r'нулей|нул\w+\s+в\s+конце', text.lower()) else 0
    base = (0.4 * math.log2(max(mn, 2)) + 0.8 * nc +
            1.5 * has_division + 2.0 * has_trailing_zeros)
    return round(base, 2)


def _score_probability(text: str) -> float:
    """CB07 — basic probability."""
    nc = _num_count(text)
    tl = _text_len(text)
    mn = _max_number(text)
    is_conditional = 1 if re.search(r'не возвращая|зависим|условн', text.lower()) else 0
    multi_event = 1 if re.search(r'оба|одновременно|два раза|дважды', text.lower()) else 0
    base = (0.3 * math.log2(max(mn, 2)) + 0.5 * nc + 0.02 * tl +
            2.5 * is_conditional + 1.5 * multi_event)
    return round(base, 2)


_SCORE_MAP = {
    'CB01': _score_principle,
    'CB02': _score_no_repeat,
    'CB03': _score_with_repeat,
    'CB04': _score_constrained,
    'CB05': _score_permutation,
    'CB06': _score_factorial,
    'CB07': _score_probability,
}


def score_problem(text: str, topic: str) -> float:
    fn = _SCORE_MAP.get(topic)
    return fn(text) if fn else 0.0
