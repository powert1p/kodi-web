"""
DV (Divisibility) topic classifier — DV01 through DV07.

DV01: Divisors and multiples (count divisors, is X a multiple of Y)
DV02: Divisibility rules (does N divide by 2/3/4/5/9/11, digit puzzles)
DV03: Prime numbers (is N prime, count primes in range)
DV04: Prime factorization (factor into primes, count prime factors)
DV05: Coprime numbers (are A,B coprime, Euler's totient)
DV06: GCD (НОД)
DV07: LCM (НОК)
"""

from __future__ import annotations

import re

from .base import ClassifyResult


def _lower(text: str) -> str:
    return text.lower().strip()


# ── keyword lists ──────────────────────────────────────────────────────

_DV07_KW = [
    'нок',
    'наименьшее общее кратное',
]

_DV07_PAT = [
    r'наименьшее.*которое\s+делится\s+на',
]

_DV06_KW = [
    'нод',
    'наибольший общий делитель',
]

_DV05_KW = [
    'взаимно прост',
    'функции эйлера',
    'φ(',
]

_DV04_KW = [
    r'разлож\w*\s+на\s+прост',
    r'простых\s+множител',
    r'простых\s+делител',
    r'простых\s+нечетных\s+множител',
    r'простые\s+множител',
]

_DV03_KW = [
    r'простое\s+число',
    r'простым\s+числом',
    r'простых\s+чисел',
    r'простые\s+числа',
    r'прост\w+\s+число',
    r'составн\w+\s+числ',
]

_DV02_KW = [
    r'делится\s+ли',
    r'делится\s+на\s+\d',
    r'делятся\s+на',
    r'признак\s+делимости',
    r'делилось\s+на',
    r'вместо\s*\*',
    r'на\s+месте\s+звездочки',
    r'значени\w*\s+x\s+число\s+\d+x',
    r'при\s+каком.*значени.*число.*делится',
    r'число.*делится\s+на\s+\d+\s+без\s+остатка',
]


# ── classifier ─────────────────────────────────────────────────────────

def classify_dv(text: str) -> ClassifyResult:
    """Classify a problem into DV01–DV07."""
    tl = _lower(text)

    # DV07: LCM
    for kw in _DV07_KW:
        if kw in tl:
            return ClassifyResult('DV07', 0.95, f'LCM: {kw}')
    for pat in _DV07_PAT:
        if re.search(pat, tl):
            return ClassifyResult('DV07', 0.90, f'LCM pattern: {pat[:30]}')

    # DV05: coprime — check BEFORE DV06 so НОД=1 goes here
    for kw in _DV05_KW:
        if kw in tl:
            return ClassifyResult('DV05', 0.95, f'coprime: {kw}')
    if re.search(r'нод.*=\s*1\b', tl):
        return ClassifyResult('DV05', 0.90, 'НОД = 1 → coprime')

    # DV06: GCD
    for kw in _DV06_KW:
        if kw in tl:
            return ClassifyResult('DV06', 0.95, f'GCD: {kw}')

    # DV04: prime factorization
    for pat in _DV04_KW:
        if re.search(pat, tl):
            return ClassifyResult('DV04', 0.90, f'factorization: {pat[:30]}')

    # DV03: prime numbers
    for pat in _DV03_KW:
        if re.search(pat, tl):
            return ClassifyResult('DV03', 0.90, f'prime number: {pat[:30]}')

    # DV02: divisibility rules
    for pat in _DV02_KW:
        if re.search(pat, tl):
            return ClassifyResult('DV02', 0.85, f'divisibility rule: {pat[:30]}')

    # DV01: divisors and multiples (fallback within DV)
    if re.search(r'делител', tl) or re.search(r'кратн', tl):
        return ClassifyResult('DV01', 0.85, 'divisors/multiples')

    return ClassifyResult('NONE', 0.0, 'no DV match')
