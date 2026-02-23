"""
GE (Geometry) topic classifier — GE01 through GE12.

GE01: Perimeter (rectangle, square, triangle)
GE02: Area (rectangle, square, triangle)
GE03: Composite area (cut-out, L-shape, frame)
GE04: Angles (types, measurement, supplementary, vertical)
GE05: Circumference
GE06: Circle area
GE07: Combined circle problems (ring, semicircle, sector)
GE08: Scale (map problems)
GE09: Symmetry
GE10: Cube/parallelepiped nets, faces, edges
GE11: Painted cube puzzles (faces after cutting)
GE12: Counting figures on a diagram
"""

from __future__ import annotations

import re

from .base import ClassifyResult


def _lower(text: str) -> str:
    return text.lower().strip()


# ── keyword lists (ordered by priority) ────────────────────────────────

_GE12_KW = [
    r'сколько отрезков',
    r'сколько.*неразвёрнут.*углов',
    r'сколько.*треугольник.*на.*чертеж',
    r'сколько.*прямоугольник.*на.*рисунк',
    r'сколько.*прямоугольник.*можно.*насчитать',
    r'сколько всего прямоугольников',
    r'отмечен.*точ.*сколько',
    r'проведен.*прямы.*сколько',
    r'на прямой отмечен',
    r'через.*точк.*проведен.*прямы',
    r'разделён.*линиями.*сколько',
    r'разделён.*полоск.*сколько',
]

_GE11_KW = [
    r'куб.*покрас',
    r'покрас.*куб',
    r'распилили на.*кубик',
    r'окрашенн.*гран',
    r'гран.*окрашен',
    r'кубик.*с\s+\d\s+окрашенн',
    r'маленьк.*кубик.*гран',
    r'куб.*×.*×.*распил',
]

_GE10_KW = [
    'развёртк', 'развертк',
    'граней у куба', 'сколько граней',
    'сколько рёбер', 'сколько ребер',
    'сколько вершин',
    r'поверхност.*куб',
    r'куб.*поверхност',
    r'ребро куба',
    r'ребр.*куб.*площадь',
    'параллелепипед',
    r'призм',
]

_GE09_KW = [
    'симметри', 'ось симметри', 'осей симметри',
]

_GE08_KW = [
    'масштаб', 'на карте',
]

_GE07_KW = [
    'кольц', 'полукруг', 'четверть круга', 'сектор',
    r'внешн.*радиус.*внутренн',
    r'внутренн.*радиус.*внешн',
]

_GE06_KW = [
    r'площадь круга',
    r'площадь.*круг',
    r'площадь.*окружност',
]

_GE05_KW = [
    r'длин.*окружност',
    r'окружност.*длин',
]

_GE04_KW = [
    r'угол(?!ьн)',     # "угол", "углов" but NOT "угольник/угольной"
    'градус', '°',
    r'смежн\w*\s+угол',  # "смежные углы" — adjacent words only
    r'вертикальн\w*\s+угол',  # "вертикальные углы" — adjacent words only
    'биссектрис',
]

_GE03_KW = [
    'вырезали', 'вырезан',
    r'г-образн',
    r'рамк',
    r'составн.*фигур',
    r'оставшейся фигур',
    r'закрашенн.*фигур',
]

_GE02_KW = [
    'площадь',
]

_GE01_KW = [
    'периметр',
]


# ── classifier ─────────────────────────────────────────────────────────

def classify_ge(text: str) -> ClassifyResult:
    """Classify a problem into GE01–GE12."""
    tl = _lower(text)

    # GE12: counting figures on diagram (most specific)
    for pat in _GE12_KW:
        if re.search(pat, tl):
            return ClassifyResult('GE12', 0.90, f'counting figures: {pat[:30]}')

    # GE11: painted cube puzzles
    for pat in _GE11_KW:
        if re.search(pat, tl):
            return ClassifyResult('GE11', 0.95, f'painted cube: {pat[:30]}')

    # GE10: cube nets, faces, edges, surface area
    for kw in _GE10_KW:
        if re.search(kw, tl):
            return ClassifyResult('GE10', 0.90, f'cube net/properties: {kw[:25]}')
    if 'куб' in tl and ('поверхност' in tl or 'объём' in tl or 'объем' in tl):
        return ClassifyResult('GE10', 0.85, 'cube + surface/volume')

    # GE09: symmetry
    for kw in _GE09_KW:
        if kw in tl:
            return ClassifyResult('GE09', 0.95, f'symmetry: {kw}')

    # GE08: scale / map
    for kw in _GE08_KW:
        if kw in tl:
            return ClassifyResult('GE08', 0.95, f'scale: {kw}')

    # GE07: combined circle (ring, semicircle, sector) — BEFORE GE05/GE06
    for pat in _GE07_KW:
        if re.search(pat, tl):
            return ClassifyResult('GE07', 0.90, f'combined circle: {pat[:30]}')

    # GE06: circle area — BEFORE GE05
    for pat in _GE06_KW:
        if re.search(pat, tl):
            return ClassifyResult('GE06', 0.90, f'circle area: {pat[:30]}')
    if ('радиус' in tl or 'диаметр' in tl) and 'площадь' in tl and 'периметр' not in tl:
        return ClassifyResult('GE06', 0.80, 'radius/diameter + площадь')
    if ('круг' in tl or 'π' in tl or '3.14' in tl or '3,14' in tl) and 'площадь' in tl:
        return ClassifyResult('GE06', 0.80, 'circle + площадь')

    # GE05: circumference
    for pat in _GE05_KW:
        if re.search(pat, tl):
            return ClassifyResult('GE05', 0.90, f'circumference: {pat[:30]}')
    if 'окружност' in tl and 'площадь' not in tl:
        return ClassifyResult('GE05', 0.80, 'окружность without площадь')

    # GE04: angles (use regex to avoid matching "угольник" inside "прямоугольник")
    for pat in _GE04_KW:
        if re.search(pat, tl):
            return ClassifyResult('GE04', 0.85, f'angles: {pat[:20]}')

    # GE03: composite area — BEFORE GE02
    # Skip GE03 if "круг"/"окружност" is the cut shape (→ GE06/GE07)
    has_circle = 'круг' in tl or 'окружност' in tl
    asks_perimeter = bool(re.search(r'найдите периметр|периметр получ', tl))
    for pat in _GE03_KW:
        if re.search(pat, tl) and not has_circle and not asks_perimeter:
            return ClassifyResult('GE03', 0.90, f'composite area: {pat[:30]}')

    # GE02: area (general fallback for area problems)
    for kw in _GE02_KW:
        if kw in tl:
            return ClassifyResult('GE02', 0.85, f'area: {kw}')

    # GE01: perimeter
    for kw in _GE01_KW:
        if kw in tl:
            return ClassifyResult('GE01', 0.90, f'perimeter: {kw}')

    return ClassifyResult('NONE', 0.0, 'no GE match')
