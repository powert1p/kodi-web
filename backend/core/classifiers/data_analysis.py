"""DA (Data Analysis) classifier — DA01–DA03."""
from __future__ import annotations
import re
from .base import ClassifyResult

def classify_da(text: str) -> ClassifyResult:
    tl = text.lower().strip()

    # DA03: mean, median, mode, range
    if re.search(r'медиан|мод[уа]|размах|среднее\s+арифметическ', tl):
        return ClassifyResult('DA03', 0.95, 'statistics measure')

    # DA02: read graphs (line, speed-time, distance-time)
    if re.search(r'график\w*|графику|ускорен', tl):
        return ClassifyResult('DA02', 0.90, 'graph reading')

    # DA01: read diagrams (bar, pie)
    if re.search(r'диаграмм|столбчат|круговой', tl):
        return ClassifyResult('DA01', 0.90, 'diagram reading')

    # Fallback: data-related
    if re.search(r'таблиц', tl):
        return ClassifyResult('DA01', 0.75, 'table reading')

    return ClassifyResult('NONE', 0.0, 'no DA match')
