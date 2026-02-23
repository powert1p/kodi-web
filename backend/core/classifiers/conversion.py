"""
CV (Conversions) topic classifier — CV01 through CV06.

CV01: Time conversions (hours, minutes, seconds)
CV02: Length conversions (km, m, cm, mm)
CV03: Mass conversions (kg, g, t,ц)
CV04: Area conversions (m², cm², km², га)
CV05: Volume conversions (л, мл, м³, см³)
CV06: Speed conversions (км/ч, м/с)
"""

from __future__ import annotations

import re

from .base import ClassifyResult


def _lower(text: str) -> str:
    return text.lower().strip()


_CV06_KW = [
    'км/ч', 'м/с', 'км / ч', 'м / с',
]

_CV04_KW = [
    'м²', 'см²', 'км²', 'дм²', 'мм²',
    r'м\^2', r'см\^2', r'км\^2', r'дм\^2',
    r'\bга\b', r'\bгектар',
    r'\bар\b', r'\bсоток',
    r'размером\s+\d+.*×.*м\s',
    r'площад',
    r'плитк\w+.*сторон',
]

_CV05_KW = [
    'м³', 'см³', 'дм³', 'мм³',
    r'м\^3', r'см\^3', r'дм\^3',
    r'\bлитр', r'\bмл\b', r'\bмиллилитр',
]

_CV03_KW = [
    r'\bкг\b', r'\bграмм', r'\bтонн', r'\bцентнер',
    r'\bг\b(?!\s*/)',  # "г" but not "г/" (part of speed)
    r'\bмг\b',
]

_CV02_KW = [
    r'\bкм\b(?!\s*/)', r'\bметр', r'\bсм\b', r'\bмм\b', r'\bдм\b',
    r'\bкилометр', r'\bсантиметр', r'\bмиллиметр', r'\bдециметр',
]

_CV01_KW = [
    r'\bчас', r'\bминут', r'\bсекунд',
    r'\bсут', r'\bнедел',
    r'\bч\b', r'\bмин\b', r'\bсек\b',
]


def classify_cv(text: str) -> ClassifyResult:
    """Classify a problem into CV01–CV06."""
    tl = _lower(text)

    # CV06: speed conversions
    for kw in _CV06_KW:
        if kw in tl:
            return ClassifyResult('CV06', 0.95, f'speed: {kw}')

    # CV04: area conversions (check before length to avoid м² matching as м)
    for kw in _CV04_KW:
        if re.search(kw, tl):
            return ClassifyResult('CV04', 0.95, f'area: {kw}')

    # CV05: volume conversions (check before length to avoid м³ matching as м)
    for kw in _CV05_KW:
        if re.search(kw, tl):
            return ClassifyResult('CV05', 0.95, f'volume: {kw}')

    # CV03: mass conversions
    for kw in _CV03_KW:
        if re.search(kw, tl):
            return ClassifyResult('CV03', 0.90, f'mass: {kw}')

    # CV02: length conversions
    for kw in _CV02_KW:
        if re.search(kw, tl):
            return ClassifyResult('CV02', 0.90, f'length: {kw}')

    # CV01: time conversions
    for kw in _CV01_KW:
        if re.search(kw, tl):
            return ClassifyResult('CV01', 0.85, f'time: {kw}')

    return ClassifyResult('NONE', 0.0, 'no CV match')
