"""DC (Decimal Fractions) classifier — DC01–DC05."""
from __future__ import annotations
import re
from .base import ClassifyResult

def classify_dc(text: str) -> ClassifyResult:
    tl = text.lower().strip()

    # DC05: repeating decimals / period
    if re.search(r'период|повтор\w*\s+цифр|\(\d+\)|0[.,]\(\d+\)', tl):
        return ClassifyResult('DC05', 0.95, 'period/repeating')
    if re.search(r'периодическ', tl):
        return ClassifyResult('DC05', 0.90, 'периодическая')

    # DC04: convert fraction <-> decimal
    if re.search(r'переведите.*дробь|переведите.*десятичн|представить в виде', tl):
        return ClassifyResult('DC04', 0.90, 'convert frac<->dec')
    if re.search(r'обыкновенн\w+\s+дробь|в\s+десятичную\s+дробь', tl):
        return ClassifyResult('DC04', 0.85, 'fraction conversion')

    # DC02: compare decimals / ordering
    if re.search(r'расположите|порядке\s+возраст|порядке\s+убыван', tl):
        return ClassifyResult('DC02', 0.90, 'ordering')
    if re.search(r'больше|меньше|наименьш|наибольш|сравните|упорядоч', tl):
        if re.search(r'\d+[.,]\d+', text) and not re.search(r'площадь|периметр|найдите\s+\w+\s+площадь', tl):
            return ClassifyResult('DC02', 0.85, 'compare decimals')
    if re.search(r'между\s+какими.*целыми', tl):
        return ClassifyResult('DC02', 0.85, 'between integers')

    # DC03: arithmetic with decimals
    if re.search(r'вычислите|найдите значение|найдите результат', tl):
        return ClassifyResult('DC03', 0.85, 'arithmetic')

    # DC01: write as decimal / what part
    if re.search(r'запишите\s+десятичн|десятых|сотых|тысячных|какую\s+часть', tl):
        return ClassifyResult('DC01', 0.85, 'write as decimal')
    if re.search(r'запишите|в виде.*дроби', tl):
        return ClassifyResult('DC01', 0.80, 'write/convert')

    return ClassifyResult('NONE', 0.0, 'no DC match')
