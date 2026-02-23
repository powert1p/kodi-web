"""
FR (Fractions) difficulty scorer — FR01 through FR13.

Five scoring profiles:
    A (Computation)      FR06 FR07 FR08 FR09 FR12
    B (Simplify/Convert) FR02 FR03 FR04
    C (Comparison)       FR05
    D (Word/Concept)     FR01 FR10 FR11
    E (Visual)           FR13
"""

from __future__ import annotations

import math
import re

FR_TOPICS = {
    'FR01', 'FR02', 'FR03', 'FR04', 'FR05', 'FR06', 'FR07',
    'FR08', 'FR09', 'FR10', 'FR11', 'FR12', 'FR13',
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _count_ops(text: str) -> int:
    expr = text.split(":", 1)[-1] if ":" in text else text
    n = len(re.findall(r'[+\u2212\u00d7\u00b7\u22c5\u00f7]', expr))
    n += len(re.findall(r'(?<!\d)\s*:\s*(?=\s*\d)', expr))
    return n

def _fractions(text: str) -> list[tuple[int, int]]:
    return [(int(n), int(d)) for n, d in re.findall(r'(\d+)/(\d+)', text)]

def _max_denom(fracs): return max((d for _, d in fracs), default=1)
def _max_numer(fracs): return max((n for n, _ in fracs), default=1)
def _has_mixed(text): return 1 if re.search(r'\d+\s+\d+/\d+', text) else 0

def _bracket_depth(text: str) -> int:
    d = mx = 0
    for ch in text:
        if ch == '(': d += 1; mx = max(mx, d)
        elif ch == ')': d -= 1
    return mx

def _has_nested(text):
    return 1 if (text.count('/') >= 3 or re.search(r'\d/\(', text) or re.search(r'1/\(', text)) else 0

_WORD_MARKERS = [
    'задач', 'рабоч', 'турист', 'магазин', 'яблок', 'книг', 'бак ',
    'бассейн', 'поезд', 'скорост', 'расстоян', 'процент', 'раствор',
    'деталь', 'ученик', 'пирожк', 'торт', 'кусок', 'часть', 'метр',
    ' км', ' кг', 'литр', 'стоим', 'цена', 'товар', 'зарплат', 'денег',
    'тенге', 'маша', 'петя', 'класс', 'библиотек', 'дерев', 'саду',
    'маршрут', 'верёвк', 'прямоугольник', 'площад', 'квадрат', 'круг',
    'фигур', 'сектор', 'полос', 'фрукт', 'молок', 'бидон', 'птиц',
    'рынок', 'слов', 'карман', 'столов', 'привал',
]
def _is_word(text): return 1 if any(w in text.lower() for w in _WORD_MARKERS) else 0
def _has_neg(text): return 1 if ('(\u2212' in text or '(-' in text or re.search(r'\u2212\d+/\d+', text)) else 0
def _has_dec_with_frac(text, fc): return 1 if re.search(r'\d+[,.]\d+', text) and fc > 0 else 0
def _has_pow(text): return 1 if ('\u00b2' in text or '\u00b3' in text or '^' in text) else 0

_STEP_WORDS = ['потом', 'затем', 'остаток', 'после', 'оставш', 'далее', 'второй день', 'третий', 'первый день']
def _step_count(text): return sum(1 for w in _STEP_WORDS if w in text.lower())
def _number_count(text): return len(re.findall(r'\b\d+\b', text))

def _gcd(a, b):
    while b: a, b = b, a % b
    return a

def _lcm(a, b): return a * b // _gcd(a, b) if a and b else max(a, b)

# ---------------------------------------------------------------------------
# Scoring profiles
# ---------------------------------------------------------------------------

def _score_computation(text, topic):
    fracs = _fractions(text)
    fc, md = len(fracs), _max_denom(fracs)
    ops, mixed, bd = _count_ops(text), _has_mixed(text), _bracket_depth(text)
    nested, neg = _has_nested(text), _has_neg(text)
    dec, pw = _has_dec_with_frac(text, fc), _has_pow(text)
    steps, word = _step_count(text), _is_word(text)
    base = (1.5*ops + 0.5*fc + 0.3*math.log2(max(md,2)) + 1.5*mixed +
            1.0*bd + 2.0*nested + 1.5*word + 1.0*neg + 1.0*dec + 1.5*pw + 1.5*steps)
    if topic == 'FR12': base += 1.0*bd + 1.0*nested
    elif topic == 'FR06': base += 0.5*(1 if len(set(d for _,d in fracs))>1 else 0)
    elif topic in ('FR07','FR08'): base += 0.5*max(fc-1,0)
    return round(base, 2)

def _score_simplify(text, topic):
    fracs = _fractions(text)
    fc, md, mn = len(fracs), _max_denom(fracs), _max_numer(fracs)
    mixed, word, nc, tl = _has_mixed(text), _is_word(text), _number_count(text), len(text)
    qf = 1 if ('является' in text.lower() or 'несократим' in text.lower()) else 0
    if topic == 'FR03':
        gs = 0
        for n,d in fracs:
            g = _gcd(n,d)
            if g > 1: gs = max(gs, math.log2(max(n,d)))
        return round(1.0*gs + 0.5*fc + 0.3*math.log2(max(md,2)) + 1.5*qf + 1.5*word + 0.01*tl, 2)
    elif topic == 'FR04':
        denoms = [d for _,d in fracs]
        lcm_val = 1
        for d in denoms: lcm_val = _lcm(lcm_val, d)
        hm = 1 if ('?' in text or 'пропущен' in text.lower()) else 0
        return round(0.8*math.log2(max(lcm_val,2)) + 0.5*fc + 1.5*hm + 1.0*(1 if len(set(denoms))>2 else 0) + 0.01*tl, 2)
    else:  # FR02
        hc = 1 if ('больш' in text.lower() or 'наимен' in text.lower() or 'сравн' in text.lower()) else 0
        return round(0.3*math.log2(max(md,2)) + 0.5*fc + 1.5*mixed + 2.0*hc + 1.0*(1 if 'неправильн' in text.lower() else 0) + 0.01*tl, 2)

def _score_comparison(text):
    fracs = _fractions(text)
    fc, md = len(fracs), _max_denom(fracs)
    denoms = set(d for _,d in fracs)
    mixed = _has_mixed(text)
    wc = 1 if 'не вычисля' in text.lower() else 0
    fb = 1 if ('между' in text.lower() or 'посередин' in text.lower()) else 0
    fe = 1 if ('наименьш' in text.lower() or 'наибольш' in text.lower()) else 0
    base = (0.5*fc + 0.3*math.log2(max(md,2)) +
            (1.0*(len(denoms)-1) if len(denoms)>1 else 0) +
            1.5*mixed + 2.0*wc + 2.0*fb + 1.5*fe + 0.01*len(text))
    return round(base, 2)

def _score_word(text, topic):
    fracs = _fractions(text)
    fc, md = len(fracs), _max_denom(fracs)
    steps, tl_len, word = _step_count(text), len(text), _is_word(text)
    ops, mixed = _count_ops(text), _has_mixed(text)
    nums = re.findall(r'\b\d+\b', text)
    max_num = max((int(n) for n in nums), default=1)
    nss = math.log2(max(max_num,2))
    if topic == 'FR01':
        pop = 1 if ('разделен' in text.lower() and ('ещё' in text.lower() or 'еще' in text.lower())) else 0
        return round(0.3*math.log2(max(md,2)) + 0.5*fc + 1.5*steps + 2.0*pop + 1.0*word + 0.01*tl_len, 2)
    elif topic == 'FR10':
        return round(0.3*math.log2(max(md,2)) + 0.5*fc + 0.3*nss + 1.5*steps + 1.5*(1 if ops>=2 else 0) + 1.0*word + 0.01*tl_len, 2)
    else:  # FR11
        hr = 1 if 'остал' in text.lower() else 0
        return round(0.3*math.log2(max(md,2)) + 0.5*fc + 0.3*nss + 1.5*steps + 1.5*hr + 1.0*word + 0.01*tl_len, 2)

def _score_visual(text):
    fracs = _fractions(text)
    fc, md = len(fracs), _max_denom(fracs)
    pop = 1 if ('разделен' in text.lower() and ('ещё' in text.lower() or 'еще' in text.lower() or 'пополам' in text.lower())) else 0
    mc = 1 if ('синим' in text.lower() or 'красн' in text.lower()) else 0
    dc = len(re.findall(r'разделён|разделен|разрез', text.lower()))
    return round(0.3*math.log2(max(md,2)) + 0.5*fc + 2.0*pop + 1.5*mc + 1.0*dc + 0.01*len(text), 2)

# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

_A = {'FR06','FR07','FR08','FR09','FR12'}
_B = {'FR02','FR03','FR04'}
_C = {'FR05'}
_D = {'FR01','FR10','FR11'}
_E = {'FR13'}

def score_problem(text: str, topic: str) -> float:
    if topic in _A: return _score_computation(text, topic)
    if topic in _B: return _score_simplify(text, topic)
    if topic in _C: return _score_comparison(text)
    if topic in _D: return _score_word(text, topic)
    if topic in _E: return _score_visual(text)
    return 0.0
