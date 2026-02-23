"""
EQ (Equations) difficulty scorer — EQ01 through EQ08.

Scoring profiles:
    Simple equations    EQ01
    Multi-step          EQ02
    Fraction equations  EQ03
    Word → equation     EQ04
    Systems             EQ05
    Word → system       EQ06
    Sum/diff + ineq     EQ07
    Missing operator    EQ08
"""

from __future__ import annotations

import math
import re

EQ_TOPICS = {
    'EQ01', 'EQ02', 'EQ03', 'EQ04', 'EQ05', 'EQ06',
    'EQ07', 'EQ08',
}


# ── helpers ────────────────────────────────────────────────────────────

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


def _has_brackets(text: str) -> bool:
    return '(' in text and ')' in text


def _bracket_depth(text: str) -> int:
    depth = max_d = 0
    for ch in text:
        if ch == '(':
            depth += 1
            max_d = max(max_d, depth)
        elif ch == ')':
            depth = max(0, depth - 1)
    return max_d


def _fraction_count(text: str) -> int:
    return len(re.findall(r'[xхy\d]+\s*/\s*[xхy\d(]+', text))


def _term_count(text: str) -> int:
    return len(re.findall(r'[xхy]', text.lower()))


def _has_two_sides(text: str) -> bool:
    parts = re.split(r'\s*=\s*', text)
    if len(parts) < 2:
        return False
    lhs, rhs = parts[0], parts[1]
    return bool(re.search(r'[xхy]', lhs) and re.search(r'[xхy]', rhs))


# ── scoring profiles ──────────────────────────────────────────────────

def _score_simple(text: str) -> float:
    """EQ01 — simple one-step equations."""
    mn = _max_number(text)
    nc = _num_count(text)
    base = 0.5 * math.log2(max(mn, 2)) + 0.8 * nc
    if _has_brackets(text):
        base += 2.0
    return round(base, 2)


def _score_multistep(text: str) -> float:
    """EQ02 — multi-step equations."""
    mn = _max_number(text)
    nc = _num_count(text)
    bd = _bracket_depth(text)
    two_sides = 1 if _has_two_sides(text) else 0
    terms = _term_count(text)

    base = (0.3 * math.log2(max(mn, 2)) + 0.8 * nc +
            1.5 * bd + 2.0 * two_sides + 0.5 * terms)
    return round(base, 2)


def _score_fraction_eq(text: str) -> float:
    """EQ03 — fraction equations."""
    mn = _max_number(text)
    nc = _num_count(text)
    fc = _fraction_count(text)
    bd = _bracket_depth(text)
    two_sides = 1 if _has_two_sides(text) else 0

    base = (0.3 * math.log2(max(mn, 2)) + 0.5 * nc +
            2.0 * fc + 1.5 * bd + 1.5 * two_sides)
    return round(base, 2)


def _score_word_eq(text: str) -> float:
    """EQ04 — word problems → single equation."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)
    has_frac = 1 if re.search(r'\d+/\d+', text) else 0

    multi_step = 1 if nc > 4 else 0
    age_problem = 1 if re.search(r'возраст|старше|младше|лет', text.lower()) else 0
    consecutive = 1 if re.search(r'последовательн', text.lower()) else 0

    base = (0.2 * math.log2(max(mn, 2)) + 0.8 * nc + 0.02 * tl +
            2.0 * has_frac + 1.5 * multi_step + 1.0 * age_problem +
            0.5 * consecutive)
    return round(base, 2)


def _score_system(text: str) -> float:
    """EQ05 — systems of equations."""
    mn = _max_number(text)
    nc = _num_count(text)
    terms = _term_count(text)
    three_var = 1 if re.search(r'[zз]', text.lower()) else 0
    method = 1 if re.search(r'метод', text.lower()) else 0

    base = (0.3 * math.log2(max(mn, 2)) + 0.5 * nc +
            1.0 * terms + 2.0 * three_var + 1.0 * method)
    return round(base, 2)


def _score_word_system(text: str) -> float:
    """EQ06 — word problems → system."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)
    has_pricing = 1 if re.search(r'стоят?|тенге|цен', text.lower()) else 0

    base = (0.2 * math.log2(max(mn, 2)) + 0.8 * nc + 0.02 * tl +
            2.0 * has_pricing)
    return round(base, 2)


def _score_sum_diff(text: str) -> float:
    """EQ07 — sum/difference + inequalities."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)

    inequality = 1 if re.search(r'неравенств|[<>≤≥]', text.lower()) else 0
    system_ineq = 1 if re.search(r'систем.*неравенств', text.lower()) else 0

    base = (0.3 * math.log2(max(mn, 2)) + 0.8 * nc + 0.01 * tl +
            3.0 * inequality + 2.0 * system_ineq)
    return round(base, 2)


def _score_missing_op(text: str) -> float:
    """EQ08 — missing operator / number puzzles."""
    mn = _max_number(text)
    nc = _num_count(text)
    placeholders = len(re.findall(r'[◻☐__]', text))
    multi_choice = 1 if re.search(r'\(1\).*\(2\).*\(3\)', text) else 0

    base = (0.3 * math.log2(max(mn, 2)) + 0.8 * nc +
            1.5 * placeholders + 1.5 * multi_choice)
    return round(base, 2)


# ── routing ───────────────────────────────────────────────────────────

_SCORE_MAP = {
    'EQ01': _score_simple,
    'EQ02': _score_multistep,
    'EQ03': _score_fraction_eq,
    'EQ04': _score_word_eq,
    'EQ05': _score_system,
    'EQ06': _score_word_system,
    'EQ07': _score_sum_diff,
    'EQ08': _score_missing_op,
}


def score_problem(text: str, topic: str) -> float:
    fn = _SCORE_MAP.get(topic)
    if fn:
        return fn(text)
    return 0.0
