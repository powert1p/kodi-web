"""
DV (Divisibility) difficulty scorer — DV01 through DV07.

Scoring profiles:
    Divisors/multiples   DV01
    Divisibility rules   DV02
    Prime numbers        DV03
    Prime factorization  DV04
    Coprime              DV05
    GCD                  DV06
    LCM                  DV07
"""

from __future__ import annotations

import math
import re

DV_TOPICS = {
    'DV01', 'DV02', 'DV03', 'DV04', 'DV05', 'DV06', 'DV07',
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


def _is_yesno(text: str) -> bool:
    return bool(re.search(r'1\s*[—–-]\s*да.*0\s*[—–-]\s*нет|является\s+ли|делится\s+ли|верно\s+ли', text.lower()))


def _is_word_problem(text: str) -> bool:
    tl = text.lower()
    markers = ['яблок', 'груш', 'пакет', 'автобус', 'маяк', 'бочк',
               'ожерель', 'бусин', 'тетрад', 'ручек', 'набор']
    return any(m in tl for m in markers)


def _multi_condition(text: str) -> bool:
    tl = text.lower()
    return bool(re.search(r'одновременно|но не|и на|кратн\w+.*но не кратн', tl))


# ── scoring profiles ──────────────────────────────────────────────────

def _score_divisors(text: str) -> float:
    """DV01 — divisors and multiples."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)
    yesno = -1.0 if _is_yesno(text) else 0.0
    word = 2.0 if _is_word_problem(text) else 0.0
    multi = 1.5 if _multi_condition(text) else 0.0

    base = (0.5 * math.log2(max(mn, 2)) + 0.8 * nc + 0.01 * tl +
            yesno + word + multi)
    return round(max(base, 0.5), 2)


def _score_div_rules(text: str) -> float:
    """DV02 — divisibility rules."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)
    yesno = -1.0 if _is_yesno(text) else 0.0
    multi = 2.0 if _multi_condition(text) else 0.0
    digit_puzzle = 1.5 if re.search(r'\*|звездочк|вместо', text.lower()) else 0.0

    base = (0.4 * math.log2(max(mn, 2)) + 0.8 * nc + 0.01 * tl +
            yesno + multi + digit_puzzle)
    return round(max(base, 0.5), 2)


def _score_primes(text: str) -> float:
    """DV03 — prime numbers."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)
    yesno = -1.0 if _is_yesno(text) else 0.0
    range_q = 1.5 if re.search(r'от\s+\d+\s+до\s+\d+|промежутк', text.lower()) else 0.0

    base = (0.5 * math.log2(max(mn, 2)) + 0.8 * nc + 0.01 * tl +
            yesno + range_q)
    return round(max(base, 0.5), 2)


def _score_factorization(text: str) -> float:
    """DV04 — prime factorization."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)

    base = (0.5 * math.log2(max(mn, 2)) + 0.8 * nc + 0.01 * tl)
    return round(base, 2)


def _score_coprime(text: str) -> float:
    """DV05 — coprime numbers."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)
    yesno = -1.0 if _is_yesno(text) else 0.0
    euler = 2.0 if re.search(r'эйлер|φ\(', text.lower()) else 0.0

    base = (0.4 * math.log2(max(mn, 2)) + 0.8 * nc + 0.01 * tl +
            yesno + euler)
    return round(max(base, 0.5), 2)


def _score_gcd(text: str) -> float:
    """DV06 — GCD."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)
    word = 2.0 if _is_word_problem(text) else 0.0
    three_nums = 1.5 if nc >= 5 else 0.0

    base = (0.4 * math.log2(max(mn, 2)) + 0.8 * nc + 0.01 * tl +
            word + three_nums)
    return round(base, 2)


def _score_lcm(text: str) -> float:
    """DV07 — LCM."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)
    word = 2.0 if _is_word_problem(text) else 0.0
    three_nums = 1.5 if nc >= 5 else 0.0

    base = (0.4 * math.log2(max(mn, 2)) + 0.8 * nc + 0.01 * tl +
            word + three_nums)
    return round(base, 2)


# ── routing ───────────────────────────────────────────────────────────

_SCORE_MAP = {
    'DV01': _score_divisors,
    'DV02': _score_div_rules,
    'DV03': _score_primes,
    'DV04': _score_factorization,
    'DV05': _score_coprime,
    'DV06': _score_gcd,
    'DV07': _score_lcm,
}


def score_problem(text: str, topic: str) -> float:
    fn = _SCORE_MAP.get(topic)
    if fn:
        return fn(text)
    return 0.0
