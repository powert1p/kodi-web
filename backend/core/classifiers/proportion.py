"""
PR (Proportions) topic classifier — PR01 through PR06.

PR01: Ratios (find ratio of A to B)
PR02: Proportions — verify/solve (верна ли пропорция, найдите x из пропорции)
PR03: Solve for x in proportion equation
PR04: Direct proportionality word problems
PR05: Inverse proportionality word problems
PR06: Compound proportionality (multiple factors)
"""

from __future__ import annotations

import re

from .base import ClassifyResult


def _lower(text: str) -> str:
    return text.lower().strip()


def _count_changing_factors(text: str) -> int:
    """Count how many independent factors change in a word problem."""
    tl = text.lower()
    factors = 0
    if re.search(r'рабочи\w*|человек|мастер', tl):
        factors += 1
    if re.search(r'час\w*|дн\w+|смен', tl):
        factors += 1
    if re.search(r'рейс\w*|маршрут', tl):
        factors += 1
    if re.search(r'комнат|высот|длин|ширин', tl):
        factors += 1
    if re.search(r'машин|труб|кран', tl):
        factors += 1
    return factors


def classify_pr(text: str) -> ClassifyResult:
    """Classify a problem into PR01–PR06."""
    tl = _lower(text)

    # PR06: compound proportionality — multiple changing factors
    factors = _count_changing_factors(text)
    if factors >= 2 and re.search(r'сколько', tl):
        has_two_scenarios = bool(re.search(r'\d+\s+\w+\s+за\s+\d+|\d+\s+\w+\s+по\s+\d+', tl))
        if has_two_scenarios or factors >= 3:
            return ClassifyResult('PR06', 0.90, f'compound: {factors} factors')

    # PR05: inverse proportionality
    if re.search(r'обратн\w*\s+пропорц', tl):
        return ClassifyResult('PR05', 0.95, 'обратная пропорциональность')
    inv_markers = [
        r'\d+\s+рабочи\w*\s+.*за\s+\d+\s+дн',
        r'\d+\s+кран\w*\s+.*за\s+\d+',
        r'\d+\s+машин\w*\s+.*за\s+\d+\s+рейс',
        r'скорость.*время',
        r'сократит\w*.*увеличи|увеличи\w*.*сократит',
    ]
    for pat in inv_markers:
        if re.search(pat, tl):
            return ClassifyResult('PR05', 0.85, f'inverse: {pat[:30]}')

    # PR04: direct proportionality word problems
    if re.search(r'прям\w*\s+пропорц', tl):
        return ClassifyResult('PR04', 0.95, 'прямая пропорциональность')
    dir_markers = [
        r'за\s+\d+\s+час\w*\s+.*сколько\s+за\s+\d+',
        r'\d+\s+м\s+.*стоят.*сколько\s+стоят\s+\d+',
        r'за\s+\d+\s+дн\w*\s+.*сколько\s+за\s+\d+',
        r'проехал.*за\s+\d+\s+час.*сколько.*за\s+\d+',
        r'количество\s+луковиц.*пропорционально',
    ]
    for pat in dir_markers:
        if re.search(pat, tl):
            return ClassifyResult('PR04', 0.85, f'direct: {pat[:30]}')

    # PR02: proportion verification
    if re.search(r'верна\s+ли\s+пропорци', tl):
        return ClassifyResult('PR02', 0.95, 'верна ли пропорция')
    if re.search(r'пропорци', tl):
        return ClassifyResult('PR02', 0.85, 'пропорция context')

    # PR03: solve for x in ratio/fraction equation
    if re.search(r'найдите\s+[xy]', tl) and re.search(r'[/:]', text):
        return ClassifyResult('PR03', 0.85, 'найдите x с дробями')

    # PR01: ratios
    if re.search(r'отношени', tl):
        return ClassifyResult('PR01', 0.90, 'отношение')
    if re.search(r'\d+\s*:\s*\d+', text) and not re.search(r'найдите\s+[xy]', tl):
        return ClassifyResult('PR01', 0.80, 'ratio notation A:B')

    # Fallback for word problems with proportional reasoning
    if re.search(r'сколько', tl) and factors >= 1:
        return ClassifyResult('PR04', 0.70, 'word problem fallback')

    return ClassifyResult('NONE', 0.0, 'no PR match')
