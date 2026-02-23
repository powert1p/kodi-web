"""
AR (Arithmetic) difficulty scorer — AR01 through AR11.

Scoring profiles:
    Basic ops      AR01 (add/sub), AR02 (mul), AR03 (div), AR04 (div+rem)
    Order of ops   AR05
    Multi-digit    AR06
    Rounding       AR07
    Clever         AR08
    Powers         AR09
    Digits         AR10, AR11
"""

from __future__ import annotations

import math
import re

AR_TOPICS = {
    'AR01', 'AR02', 'AR03', 'AR04', 'AR05', 'AR06',
    'AR07', 'AR08', 'AR09', 'AR10', 'AR11',
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _numbers(text: str) -> list[int]:
    return [int(n) for n in re.findall(r'\b\d+\b', text)]

def _max_number(text: str) -> int:
    nums = _numbers(text)
    return max(nums) if nums else 0

def _max_digits(text: str) -> int:
    nums = re.findall(r'\b\d+\b', text)
    return max((len(n) for n in nums), default=0)

def _op_count(text: str) -> int:
    expr = text.split(":", 1)[-1] if ":" in text else text
    return len(re.findall(r'[+\u2212−×·⋅∙÷]', expr))

def _op_types(text: str) -> set[str]:
    expr = text.split(":", 1)[-1] if ":" in text else text
    ops = set()
    if '+' in expr: ops.add('add')
    if re.search(r'[\u2212−]', expr): ops.add('sub')
    if re.search(r'[×·⋅∙]', expr): ops.add('mul')
    if '÷' in expr or re.search(r'\)\s*:\s*[\d(]', expr): ops.add('div')
    return ops

def _bracket_depth(text: str) -> int:
    expr = text.split(':', 1)[-1] if ':' in text and len(text.split(':', 1)[0]) < 30 else text
    d = mx = 0
    for ch in expr:
        if ch == '(': d += 1; mx = max(mx, d)
        elif ch == ')': d -= 1
    return mx

def _is_word(text: str) -> bool:
    markers = ['задач', 'рабоч', 'магазин', 'яблок', 'книг', 'купил', 'скольк',
               'ученик', 'класс', 'билет', 'фрукт', 'килограмм', ' кг', 'литр',
               'столов', 'стуль', 'тенге', 'привез', 'собрал']
    low = text.lower()
    return any(w in low for w in markers)

def _text_len(text: str) -> int:
    return len(text)

# ---------------------------------------------------------------------------
# Scoring profiles
# ---------------------------------------------------------------------------

def _score_basic_op(text: str, topic: str) -> float:
    """AR01 (add/sub ≤100), AR02 (mul table), AR03 (div), AR04 (div+rem)."""
    mn = _max_number(text)
    md = _max_digits(text)
    oc = _op_count(text)
    word = 1 if _is_word(text) else 0
    tl = _text_len(text)
    num_size = math.log2(max(mn, 2))

    if topic == 'AR01':
        base = 0.5 * num_size + 1.0 * oc + 2.0 * word + 0.01 * tl
    elif topic == 'AR02':
        base = 0.8 * num_size + 1.0 * oc + 1.5 * (1 if md >= 2 else 0) + 2.0 * word + 0.01 * tl
    elif topic == 'AR03':
        base = 0.5 * num_size + 1.0 * oc + 1.5 * (1 if mn > 100 else 0) + 2.0 * word + 0.01 * tl
    else:  # AR04
        multi_step = 1 if re.search(r'делим.*затем|сначала.*потом', text.lower()) else 0
        remainder_check = 1 if re.search(r'может ли|возможно ли|при каком', text.lower()) else 0
        base = (0.5 * num_size + 1.0 * oc + 1.5 * multi_step +
                2.0 * remainder_check + 2.0 * word + 0.01 * tl)
    return round(base, 2)


def _score_order_of_ops(text: str) -> float:
    """AR05 — order of operations (brackets, priority)."""
    mn = _max_number(text)
    oc = _op_count(text)
    ot = len(_op_types(text))
    bd = _bracket_depth(text)
    word = 1 if _is_word(text) else 0
    tl = _text_len(text)

    base = (0.3 * math.log2(max(mn, 2)) + 1.5 * oc + 2.0 * ot +
            2.0 * bd + 3.0 * word + 0.01 * tl)
    return round(base, 2)


def _score_multi_digit(text: str) -> float:
    """AR06 — operations with multi-digit numbers."""
    mn = _max_number(text)
    md = _max_digits(text)
    oc = _op_count(text)
    ot = len(_op_types(text))
    word = 1 if _is_word(text) else 0
    tl = _text_len(text)

    base = (0.5 * math.log2(max(mn, 2)) + 1.5 * md + 1.0 * oc +
            1.5 * ot + 2.5 * word + 0.01 * tl)
    return round(base, 2)


def _score_rounding(text: str) -> float:
    """AR07 — rounding numbers."""
    mn = _max_number(text)
    md = _max_digits(text)
    tl = _text_len(text)

    precision_markers = {
        'до единиц': 1, 'до десятков': 2, 'до сотен': 3,
        'до тысяч': 4, 'до десятков тысяч': 5,
        'до десятых': 2, 'до сотых': 3, 'до тысячных': 4,
    }
    precision = 1
    low = text.lower()
    for marker, level in precision_markers.items():
        if marker in low:
            precision = level
            break

    has_decimal = 1 if re.search(r'\d+[.,]\d+', text) else 0
    word = 1 if _is_word(text) else 0

    base = (0.5 * math.log2(max(mn, 2)) + 1.0 * md + 1.5 * precision +
            1.5 * has_decimal + 2.0 * word + 0.01 * tl)
    return round(base, 2)


def _score_clever(text: str) -> float:
    """AR08 — clever/efficient computation."""
    mn = _max_number(text)
    oc = _op_count(text)
    ot = len(_op_types(text))
    tl = _text_len(text)

    has_pattern = 0
    low = text.lower()
    if re.search(r'(?:99|101|98|102|999|1001)\s*[×·]', text): has_pattern = 1
    if re.search(r'(?:25|125)\s*[×·]\s*\d+\s*[×·]\s*(?:4|8)', text): has_pattern = 1
    if re.search(r'разност.*квадрат|квадрат.*разност', low): has_pattern = 2
    if re.search(r'формул.*сокращ', low): has_pattern = 2

    base = (0.3 * math.log2(max(mn, 2)) + 1.5 * oc + 1.0 * ot +
            2.0 * has_pattern + 0.01 * tl)
    return round(base, 2)


def _score_powers(text: str) -> float:
    """AR09 — powers of natural numbers."""
    mn = _max_number(text)
    tl = _text_len(text)
    word = 1 if _is_word(text) else 0

    exponents = re.findall(r'[²³⁴⁵⁶⁷⁸⁹]|\^(\d+)', text)
    max_exp = 2
    for e in exponents:
        if isinstance(e, str) and e.isdigit():
            max_exp = max(max_exp, int(e))
        elif e in ('²', '2'): max_exp = max(max_exp, 2)
        elif e in ('³', '3'): max_exp = max(max_exp, 3)

    oc = _op_count(text)
    compare = 1 if re.search(r'сравни|больш|меньш', text.lower()) else 0

    base = (0.5 * math.log2(max(mn, 2)) + 1.5 * max_exp + 1.0 * oc +
            2.0 * compare + 2.0 * word + 0.01 * tl)
    return round(base, 2)


def _score_digits(text: str, topic: str) -> float:
    """AR10 (digit properties) and AR11 (last digit of power/product)."""
    mn = _max_number(text)
    tl = _text_len(text)
    word = 1 if _is_word(text) else 0

    if topic == 'AR11':
        exponents = re.findall(r'[²³⁴⁵⁶⁷⁸⁹]|\^(\d+)', text)
        max_exp = 2
        for e in exponents:
            if isinstance(e, str) and e.isdigit():
                max_exp = max(max_exp, int(e))
        oc = _op_count(text)
        base = (0.5 * math.log2(max(mn, 2)) + 2.0 * math.log2(max(max_exp, 2)) +
                1.5 * oc + 2.0 * word + 0.01 * tl)
    else:  # AR10
        md = _max_digits(text)
        sum_digits = 1 if 'сумма цифр' in text.lower() else 0
        prod_digits = 1 if 'произведение цифр' in text.lower() else 0
        find_number = 1 if re.search(r'найди.*число|какое.*число', text.lower()) else 0
        base = (0.5 * math.log2(max(mn, 2)) + 1.0 * md + 2.0 * sum_digits +
                2.0 * prod_digits + 2.0 * find_number + 2.0 * word + 0.01 * tl)
    return round(base, 2)


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

_BASIC = {'AR01', 'AR02', 'AR03', 'AR04'}
_DIGITS = {'AR10', 'AR11'}

def score_problem(text: str, topic: str) -> float:
    if topic in _BASIC:
        return _score_basic_op(text, topic)
    if topic == 'AR05':
        return _score_order_of_ops(text)
    if topic == 'AR06':
        return _score_multi_digit(text)
    if topic == 'AR07':
        return _score_rounding(text)
    if topic == 'AR08':
        return _score_clever(text)
    if topic == 'AR09':
        return _score_powers(text)
    if topic in _DIGITS:
        return _score_digits(text, topic)
    return 0.0
