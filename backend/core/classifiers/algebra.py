"""AL (Algebraic Expressions) classifier — AL01–AL04."""
from __future__ import annotations
import re
from .base import ClassifyResult

def classify_al(text: str) -> ClassifyResult:
    tl = text.lower().strip()

    # AL04: systems of inequalities
    if re.search(r'систем\w+\s+неравенств', tl):
        return ClassifyResult('AL04', 0.95, 'system of inequalities')
    if re.search(r'неравенств', tl) and re.search(r';\s*\d|и\s+\d*x', tl):
        return ClassifyResult('AL04', 0.85, 'compound inequalities')

    # AL03: single inequalities (count integers)
    if re.search(r'неравенств|сколько\s+целых', tl):
        return ClassifyResult('AL03', 0.85, 'inequality')
    if re.search(r'<.*x.*<|≤.*x.*≤|>\s*x|x\s*<', tl):
        return ClassifyResult('AL03', 0.80, 'inequality notation')

    # AL02: expand brackets
    if re.search(r'раскройте\s+скобк', tl):
        return ClassifyResult('AL02', 0.95, 'раскройте скобки')
    if re.search(r'раскройте.*упрост|упрост.*раскройте', tl):
        return ClassifyResult('AL02', 0.85, 'expand+simplify')

    # AL01: evaluate / simplify
    if re.search(r'значение\s+выражени|упростите|коэффициент', tl):
        return ClassifyResult('AL01', 0.85, 'evaluate/simplify')
    if re.search(r'найдите.*при\s+[a-z]\s*=', tl):
        return ClassifyResult('AL01', 0.85, 'substitute')

    return ClassifyResult('NONE', 0.0, 'no AL match')
