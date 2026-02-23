"""
LG (Logic) difficulty scorer — LG01 through LG07.
"""

from __future__ import annotations

import math
import re

LG_TOPICS = {'LG01', 'LG02', 'LG03', 'LG04', 'LG05', 'LG06', 'LG07'}


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


def _score_pattern(text: str) -> float:
    """LG01 — pattern continuation."""
    nc = _num_count(text)
    mn = _max_number(text)
    has_missing = 1 if '?' in text or 'пропущ' in text.lower() else 0
    has_extra = 1 if 'лишнее' in text.lower() else 0
    base = (0.3 * math.log2(max(mn, 2)) + 0.5 * nc +
            1.5 * has_missing + 1.0 * has_extra)
    return round(base, 2)


def _score_progression(text: str) -> float:
    """LG02 — arithmetic/geometric progressions."""
    nc = _num_count(text)
    mn = _max_number(text)
    is_gp = 1 if re.search(r'геометрическ|ГП', text) else 0
    wants_sum = 1 if re.search(r'S[₁₂₃₅₁₀]|найдите\s+сумм', text.lower()) else 0
    base = (0.3 * math.log2(max(mn, 2)) + 0.5 * nc +
            1.5 * is_gp + 2.0 * wants_sum)
    return round(base, 2)


def _score_series(text: str) -> float:
    """LG03 — series sums."""
    mn = _max_number(text)
    nc = _num_count(text)
    has_step = 1 if re.search(r'[+]\s*\d+\s*[+]\s*\d+\s*[+]\s*\.\.\.', text) else 0
    base = (0.4 * math.log2(max(mn, 2)) + 0.3 * nc + 1.5 * has_step)
    return round(base, 2)


def _score_rebus(text: str) -> float:
    """LG04 — cryptarithmetic/rebuses."""
    nc = _num_count(text)
    tl = _text_len(text)
    multi_digit = 1 if re.search(r'AB|двузначн', text) else 0
    multi_cond = len(re.findall(r'причём|условию|удовлетворя', text.lower()))
    base = (0.5 * nc + 0.02 * tl + 2.0 * multi_digit +
            1.5 * min(multi_cond, 2))
    return round(base, 2)


def _score_custom_op(text: str) -> float:
    """LG05 — custom operations."""
    nc = _num_count(text)
    has_nested = 1 if re.search(r'[★◆⊕⊗∎⊛]\s*\(|[★◆⊕⊗∎⊛].*[★◆⊕⊗∎⊛]', text) else 0
    has_square = 1 if '²' in text else 0
    base = (0.5 * nc + 2.5 * has_nested + 1.5 * has_square)
    return round(base, 2)


def _score_logic(text: str) -> float:
    """LG06 — logic (syllogisms, knights/liars, true/false)."""
    tl = _text_len(text)
    nc = _num_count(text)
    people = len(re.findall(r'рыцар|лжец|жител', text.lower()))
    statements = len(re.findall(r'говорит:|сказал:', text.lower()))
    base = (0.02 * tl + 0.5 * nc + 1.0 * min(people, 3) +
            1.5 * min(statements, 3))
    return round(base, 2)


def _score_puzzle(text: str) -> float:
    """LG07 — logic puzzles (matching)."""
    tl = _text_len(text)
    names = len(re.findall(r'[А-ЯЁ][а-яё]{2,}', text))
    constraints = len(re.findall(r'не из|не играет|не плавает|не любит|не получил|не в \d|не сидит', text.lower()))
    base = (0.02 * tl + 0.8 * min(names, 6) + 1.5 * min(constraints, 4))
    return round(base, 2)


_SCORE_MAP = {
    'LG01': _score_pattern,
    'LG02': _score_progression,
    'LG03': _score_series,
    'LG04': _score_rebus,
    'LG05': _score_custom_op,
    'LG06': _score_logic,
    'LG07': _score_puzzle,
}


def score_problem(text: str, topic: str) -> float:
    fn = _SCORE_MAP.get(topic)
    return fn(text) if fn else 0.0
