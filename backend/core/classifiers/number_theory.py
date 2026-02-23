"""NM (Number Sets) classifier — NM01–NM03."""
from __future__ import annotations
import re
from .base import ClassifyResult

def classify_nm(text: str) -> ClassifyResult:
    tl = text.lower().strip()

    # NM03: number line distances, midpoints
    if re.search(r'расстояни\w+\s+между|середин\w+\s+отрезк', tl):
        return ClassifyResult('NM03', 0.90, 'distance/midpoint')
    if re.search(r'\|[A-Za-z]{2}\|', text):
        return ClassifyResult('NM03', 0.90, 'segment length |AB|')
    if re.search(r'координатн\w+\s+прям\w+.*точк|точк\w+.*координатн\w+\s+прям', tl):
        if re.search(r'правее|левее|единиц', tl):
            return ClassifyResult('NM03', 0.85, 'number line position')

    # NM01: opposite numbers, ordering, |x| <= N
    if re.search(r'противополож', tl):
        return ClassifyResult('NM01', 0.90, 'opposite number')
    if re.search(r'наименьш|наибольш|упорядоч', tl):
        return ClassifyResult('NM01', 0.85, 'ordering')
    if re.search(r'\|[xх]\|\s*[≤<]', text):
        return ClassifyResult('NM01', 0.85, '|x| constraint')

    # NM02: integer arithmetic
    if re.search(r'вычислите|найдите\s+значение', tl):
        return ClassifyResult('NM02', 0.80, 'integer arithmetic')

    return ClassifyResult('NONE', 0.0, 'no NM match')
