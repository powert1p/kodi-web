"""ST (Sets) classifier — ST01–ST02."""
from __future__ import annotations
import re
from .base import ClassifyResult

def classify_st(text: str) -> ClassifyResult:
    tl = text.lower().strip()

    # ST02: Venn diagrams / inclusion-exclusion
    if re.search(r'венн|хотя\s+бы\s+один|ни\s+то\s+ни\s+друг', tl):
        return ClassifyResult('ST02', 0.95, 'Venn/inclusion-exclusion')
    if re.search(r'из\s+\d+\s+(человек|ученик|студент|участник)', tl):
        return ClassifyResult('ST02', 0.85, 'people counting')
    if re.search(r'любят.*и.*любят|знают.*и.*знают|сдали.*и.*сдали', tl):
        return ClassifyResult('ST02', 0.85, 'overlap counting')

    # ST01: set operations
    if re.search(r'∩|∪|\\\\|A\s*∩\s*B|A\s*∪\s*B|A\s*\\\s*B', text):
        return ClassifyResult('ST01', 0.95, 'set operation symbol')
    if re.search(r'множеств|элемент\w+\s+в|пересечени|объединени|разност\w+\s+множеств', tl):
        return ClassifyResult('ST01', 0.85, 'set operation')
    if re.search(r'двузначн\w+\s+чисел.*множеств|множеств\w+.*двузначн', tl):
        return ClassifyResult('ST01', 0.80, 'set of numbers')

    return ClassifyResult('NONE', 0.0, 'no ST match')
