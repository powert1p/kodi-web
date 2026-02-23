"""RN (Rational Numbers) classifier — RN01–RN04."""
from __future__ import annotations
import re
from .base import ClassifyResult

def classify_rn(text: str) -> ClassifyResult:
    tl = text.lower().strip()

    # RN03: coordinate PLANE (2D only — with semicolon coords or квадрант)
    if re.search(r'координат\w+\s+плоскост|квадрант|абсцисс\w', tl):
        return ClassifyResult('RN03', 0.90, 'coordinate plane')
    if re.search(r'\bординат\w', tl) and not re.search(r'координатн', tl):
        return ClassifyResult('RN03', 0.85, 'ordinate axis')
    if re.search(r'точк\w+\s*\(\s*[−-]?\d+\s*;\s*[−-]?\d+\s*\)', tl):
        return ClassifyResult('RN03', 0.85, 'point coordinates 2D')

    # RN04: number classification (includes counting specific number types in intervals)
    if re.search(r'натуральн\w+\s+числ|является\s+ли.*натуральн|является\s+ли.*рациональн|является\s+ли.*целы', tl):
        return ClassifyResult('RN04', 0.90, 'number classification')
    if re.search(r'какое\s+число\s+является|множеств\w+\s+рациональн|множеств\w+\s+целых', tl):
        return ClassifyResult('RN04', 0.85, 'number set membership')
    if re.search(r'промежут', tl) and re.search(r'натуральн|составн|нечётн|чётн|простых', tl):
        return ClassifyResult('RN04', 0.85, 'number type in interval')

    # RN01: number line (1D), ordering integers
    if re.search(r'координатн\w+\s+прям|числов\w+\s+прям', tl):
        return ClassifyResult('RN01', 0.85, 'number line')
    if re.search(r'промежут|отрезк\w+\s*\[|интервал', tl):
        return ClassifyResult('RN01', 0.85, 'interval')
    if re.search(r'наибольш|наименьш|упорядоч|расположите', tl):
        if not re.search(r'вычислите', tl):
            return ClassifyResult('RN01', 0.80, 'ordering')

    # RN02: operations with rationals
    if re.search(r'вычислите|найдите\s+значение', tl):
        return ClassifyResult('RN02', 0.80, 'compute rationals')

    return ClassifyResult('NONE', 0.0, 'no RN match')
