"""MD (Absolute Value / Modulus) classifier — MD01–MD03."""
from __future__ import annotations
import re
from .base import ClassifyResult

def _has_modulus(text: str) -> bool:
    return '|' in text or 'модул' in text.lower()

def classify_md(text: str) -> ClassifyResult:
    tl = text.lower().strip()

    if not _has_modulus(text):
        return ClassifyResult('NONE', 0.0, 'no modulus')

    # MD03: inequalities with |x|
    if re.search(r'неравенств', tl) or re.search(r'\|.*[<>≤≥]|\s*[<>≤≥]\s*\|', text):
        return ClassifyResult('MD03', 0.90, 'modulus inequality')
    if re.search(r'сколько\s+целых', tl):
        return ClassifyResult('MD03', 0.85, 'count integers with |x|')

    # MD02: equations with |x|
    if re.search(r'уравнени|корн\w+|реш\w+\s*:', tl):
        return ClassifyResult('MD02', 0.90, 'modulus equation')
    if re.search(r'\|\s*\w+\s*[−+-]\s*\d+\s*\|\s*=', text):
        return ClassifyResult('MD02', 0.85, '|x-a|=b pattern')

    # MD01: compute |x|
    if re.search(r'найдите|вычислите', tl):
        return ClassifyResult('MD01', 0.85, 'compute modulus')

    return ClassifyResult('MD01', 0.70, 'modulus fallback')
