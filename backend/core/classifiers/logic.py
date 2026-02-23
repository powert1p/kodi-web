"""
LG (Logic) topic classifier — LG01 through LG07.

LG01: Pattern continuation (sequences)
LG02: Arithmetic/geometric progressions
LG03: Series sums (1+2+...+N)
LG04: Cryptarithmetic / rebuses (A+A=14, AB+BA=99)
LG05: Custom operations (a★b = a+2b)
LG06: Logic problems (syllogisms, true/false, knights/liars)
LG07: Logic puzzles (matching people to items/places)
"""

from __future__ import annotations

import re

from .base import ClassifyResult


def _lower(text: str) -> str:
    return text.lower().strip()


_LG05_SYMBOLS = ['★', '◆', '⊕', '⊗', '∎', '⊛', '#']

_LG05_KW = [
    'определено действие',
    'новое действие',
    'новое логическое действие',
    'используя новое',
]

_LG04_PAT = [
    r'ребус',
    r'\bA\s*[+×]\s*A\b',
    r'\bAB\s*[+×]\s*BA\b',
    r'двузначн\w+\s+числ\w+\s+AB',
    r'10A\s*\+\s*B',
]

_LG07_KW = [
    'не из', 'не играет', 'не плавает', 'не любит',
    'не в 5 классе', 'не в 6 классе', 'не получил',
    'сидят за партами',
]

_LG06_KW = [
    'истинн', 'ложн', 'рыцар', 'лжец',
    'утверждени',
    'все кошки', 'силлогизм',
]

_LG02_KW = [
    'прогресси', 'ап:', 'гп:',
    'a₁', 'd =', 'разность прогрессии',
    r's₁₀', r's₅',
]

_LG03_PAT = [
    r'\d+\s*\+\s*\d+\s*\+\s*\d+\s*\+\s*\.\.\.\s*\+\s*\d+',
    r'1\s*\+\s*2\s*\+\s*3\s*\+',
    r'2\s*\+\s*4\s*\+\s*6\s*\+',
    r'вычислите:\s*\d+\s*\+\s*\d+\s*\+',
]

_LG01_KW = [
    'продолжите', 'следующее число', 'пропущенное',
    'лишнее число', 'неизвестное число в последовательности',
]


def _has_named_people_matching(text: str) -> bool:
    """Detect logic puzzles with named people and matching constraints."""
    tl = text.lower()
    names = len(re.findall(r'[А-ЯЁ][а-яё]{2,}', text))
    constraints = sum(1 for kw in _LG07_KW if kw in tl)
    return names >= 3 and constraints >= 1


def classify_lg(text: str) -> ClassifyResult:
    """Classify a problem into LG01–LG07."""
    tl = _lower(text)

    # LG05: custom operations
    for sym in _LG05_SYMBOLS:
        if sym in text:
            return ClassifyResult('LG05', 0.95, f'custom op symbol: {sym}')
    for kw in _LG05_KW:
        if kw in tl:
            return ClassifyResult('LG05', 0.90, f'custom op: {kw[:25]}')

    # LG04: cryptarithmetic / rebuses
    for pat in _LG04_PAT:
        if re.search(pat, text if pat[0] == '\\' else tl):
            return ClassifyResult('LG04', 0.90, f'rebus: {pat[:25]}')

    # LG07: logic puzzles with matching
    if _has_named_people_matching(text):
        return ClassifyResult('LG07', 0.85, 'named people + constraints')

    # LG06: logic (syllogisms, knights/liars, true/false)
    for kw in _LG06_KW:
        if kw in tl:
            return ClassifyResult('LG06', 0.90, f'logic: {kw}')

    # LG02: progressions
    for kw in _LG02_KW:
        if kw in tl:
            return ClassifyResult('LG02', 0.90, f'progression: {kw}')

    # LG03: series sums
    for pat in _LG03_PAT:
        if re.search(pat, tl):
            return ClassifyResult('LG03', 0.90, f'series sum: {pat[:25]}')

    # LG01: pattern continuation
    for kw in _LG01_KW:
        if kw in tl:
            return ClassifyResult('LG01', 0.85, f'pattern: {kw}')

    # LG02 fallback: sequence with "разность неизвестных"
    if re.search(r'разность неизвестных', tl):
        return ClassifyResult('LG02', 0.80, 'sequence with unknowns')

    return ClassifyResult('NONE', 0.0, 'no LG match')
