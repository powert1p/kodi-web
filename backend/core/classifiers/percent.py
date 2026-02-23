"""
PC (Percentages) topic classifier — PC01 through PC06.

PC01: Basic percent concepts (convert to %, what is 1%)
PC02: Find X% of N
PC03: Find number given X% = value
PC04: What percent is A of B
PC05: Word problems with percentages (discount, bank, population)
PC06: Mixture/concentration problems
"""

from __future__ import annotations

import re

from .base import ClassifyResult


def _lower(text: str) -> str:
    return text.lower().strip()


_PC06_KW = [
    'раствор', 'концентрац', 'смешали', 'смесь', 'смеси',
    'г воды', 'г соли', 'выпарили', 'сплав',
]

_PC05_KW = [
    'банк', 'вклад', 'годовых', 'скидк', 'снизили цен',
    'повысили цен', 'подоро', 'подешев', 'учеников',
    'населен', 'зарплат', 'стоила', 'стоимость',
    'магазин', 'товар', 'книга стоила', 'страниц',
    r'квадрат.*увеличи',
]

_PC04_PAT = [
    r'сколько процентов составля',
    r'на сколько процентов',
    r'во сколько раз.*процент',
    r'увеличили на.*%.*уменьшили на.*%',
    r'уменьшили на.*%.*увеличили на.*%',
]

_PC03_PAT = [
    r'\d+\s*%\s*числа\s+равн',
    r'процентов\s+числа\s+равн',
    r'%\s+от\s+числа\s+равн',
    r'первый день.*%.*второй день.*остал',
]

_PC02_PAT = [
    r'найдите\s+\d+\s*%\s*(от|числа)',
    r'\d+\s*%\s+(от|числа)\s+\d+',
    r'чему\s+равн\w*\s+\d+\s*%',
]

_PC01_KW = [
    'выразите', 'переведите', 'что такое',
    'запишите', 'в виде процент', 'в виде дроби',
    'в процентах',
]


def classify_pc(text: str) -> ClassifyResult:
    """Classify a problem into PC01–PC06."""
    tl = _lower(text)

    # PC06: mixture/concentration
    for kw in _PC06_KW:
        if kw in tl:
            return ClassifyResult('PC06', 0.95, f'mixture: {kw}')

    # PC05: word problems with percents
    for kw in _PC05_KW:
        if re.search(kw, tl):
            return ClassifyResult('PC05', 0.85, f'word problem: {kw[:20]}')

    # PC04: what percent is A of B
    for pat in _PC04_PAT:
        if re.search(pat, tl):
            return ClassifyResult('PC04', 0.90, f'what percent: {pat[:30]}')

    # PC03: find number given X% = value
    for pat in _PC03_PAT:
        if re.search(pat, tl):
            return ClassifyResult('PC03', 0.90, f'find number: {pat[:30]}')

    # PC02: find X% of N
    for pat in _PC02_PAT:
        if re.search(pat, tl):
            return ClassifyResult('PC02', 0.90, f'find percent of: {pat[:30]}')

    # PC01: basic concepts / conversion
    for kw in _PC01_KW:
        if kw in tl:
            return ClassifyResult('PC01', 0.85, f'basic concept: {kw}')

    # Fallback: any problem with %
    if '%' in text or 'процент' in tl:
        return ClassifyResult('PC02', 0.70, 'percent fallback')

    return ClassifyResult('NONE', 0.0, 'no PC match')
