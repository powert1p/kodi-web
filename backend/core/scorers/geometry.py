"""
GE (Geometry) difficulty scorer — GE01 through GE12.

Scoring profiles:
    Perimeter/Area  GE01, GE02, GE03
    Angles          GE04
    Circles         GE05, GE06, GE07
    Scale           GE08
    Symmetry        GE09
    3D cubes        GE10, GE11
    Counting        GE12
"""

from __future__ import annotations

import math
import re

GE_TOPICS = {
    'GE01', 'GE02', 'GE03', 'GE04', 'GE05', 'GE06',
    'GE07', 'GE08', 'GE09', 'GE10', 'GE11', 'GE12',
}


# ── helpers ────────────────────────────────────────────────────────────

def _numbers(text: str) -> list[float]:
    raw = re.findall(r'\d+(?:[.,]\d+)?', text)
    out = []
    for r in raw:
        r = r.replace(',', '.')
        try:
            out.append(float(r))
        except ValueError:
            pass
    return out


def _max_number(text: str) -> float:
    nums = _numbers(text)
    return max(nums) if nums else 0


def _num_count(text: str) -> int:
    return len(_numbers(text))


def _text_len(text: str) -> int:
    return len(text)


def _has_fraction(text: str) -> bool:
    return bool(re.search(r'\d+/\d+', text))


def _is_word_problem(text: str) -> bool:
    tl = text.lower()
    markers = ['задач', 'сад', 'поле', 'комнат', 'забор', 'бассейн',
               'участок', 'огород', 'стен', 'пол', 'крыш']
    return any(m in tl for m in markers)


def _is_reverse(text: str) -> bool:
    tl = text.lower()
    return bool(re.search(r'найди.*сторон|найди.*радиус|найди.*диаметр|чему равн.*сторон', tl))


# ── scoring profiles ──────────────────────────────────────────────────

def _score_perimeter_area(text: str, topic: str) -> float:
    """GE01 (perimeter), GE02 (area), GE03 (composite area)."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)
    frac = 1 if _has_fraction(text) else 0
    word = 1 if _is_word_problem(text) else 0
    reverse = 1 if _is_reverse(text) else 0

    base = (0.3 * math.log2(max(mn, 2)) + 1.0 * nc + 0.02 * tl +
            2.0 * frac + 2.0 * word + 2.5 * reverse)

    if topic == 'GE03':
        base += 1.5

    return round(base, 2)


def _score_angles(text: str) -> float:
    """GE04 — angles."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)

    polygon = bool(re.search(r'треугольник|четырёхугольник|пятиугольник|многоугольник', text.lower()))
    algebraic = bool(re.search(r'[xх]|2α|3α', text))
    multi_angle = nc > 3

    base = (0.2 * math.log2(max(mn, 2)) + 1.0 * nc + 0.02 * tl +
            2.0 * polygon + 3.0 * algebraic + 1.5 * multi_angle)
    return round(base, 2)


def _score_circle(text: str, topic: str) -> float:
    """GE05 (circumference), GE06 (circle area), GE07 (combined)."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)
    reverse = 1 if _is_reverse(text) else 0
    frac = 1 if _has_fraction(text) or '22/7' in text else 0

    base = (0.3 * math.log2(max(mn, 2)) + 1.0 * nc + 0.02 * tl +
            2.0 * reverse + 1.5 * frac)

    if topic == 'GE07':
        base += 2.0
    elif topic == 'GE06':
        base += 0.5

    return round(base, 2)


def _score_scale(text: str) -> float:
    """GE08 — scale / map."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)

    unit_convert = bool(re.search(r'км|метр|см|мм', text.lower()))
    reverse = bool(re.search(r'сколько на карте|какой масштаб|определите масштаб', text.lower()))
    large_scale = 1 if mn > 100000 else 0

    base = (0.3 * math.log2(max(mn, 2)) + 1.0 * nc + 0.02 * tl +
            1.5 * unit_convert + 2.0 * reverse + 1.0 * large_scale)
    return round(base, 2)


def _score_symmetry(text: str) -> float:
    """GE09 — symmetry."""
    tl_low = text.lower()
    nc = _num_count(text)
    tl = _text_len(text)

    complex_shapes = ['правильн.*шестиугольник', 'пятиугольник', 'ромб',
                      'букв', 'цифр', 'парабол']
    shape_complexity = sum(1 for s in complex_shapes if re.search(s, tl_low))
    simple_shapes = ['квадрат', 'круг', 'окружност', 'равносторонн']
    is_simple = any(s in tl_low for s in simple_shapes)

    base = (0.5 * nc + 0.02 * tl + 2.0 * shape_complexity - 1.0 * is_simple)
    return round(max(base, 0.5), 2)


def _score_3d(text: str, topic: str) -> float:
    """GE10 (cube nets), GE11 (painted cubes)."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)

    if topic == 'GE11':
        cube_size = 3
        m = re.search(r'(\d+)\s*[×x]\s*(\d+)\s*[×x]\s*(\d+)', text)
        if m:
            cube_size = int(m.group(1))
        face_types = sum(1 for kw in ['0 окрашенн', '1 окрашенн', '2 окрашенн', '3 окрашенн']
                         if kw in text.lower())
        base = (1.0 * cube_size + 1.5 * nc + 2.0 * face_types + 0.02 * tl)
    else:
        surface_area = bool(re.search(r'поверхност|площадь', text.lower()))
        volume = bool(re.search(r'объём|объем', text.lower()))
        base = (0.3 * math.log2(max(mn, 2)) + 1.0 * nc + 0.02 * tl +
                2.0 * surface_area + 2.0 * volume)
    return round(base, 2)


def _score_counting(text: str) -> float:
    """GE12 — counting figures on diagram."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)

    triangles = bool(re.search(r'треугольник', text.lower()))
    complex_fig = bool(re.search(r'прямоугольник|квадрат', text.lower()))

    base = (0.5 * math.log2(max(mn, 2)) + 1.5 * nc + 0.02 * tl +
            2.0 * triangles + 1.5 * complex_fig)
    return round(base, 2)


# ── routing ───────────────────────────────────────────────────────────

_PERIM_AREA = {'GE01', 'GE02', 'GE03'}
_CIRCLE = {'GE05', 'GE06', 'GE07'}
_CUBE_3D = {'GE10', 'GE11'}


def score_problem(text: str, topic: str) -> float:
    if topic in _PERIM_AREA:
        return _score_perimeter_area(text, topic)
    if topic == 'GE04':
        return _score_angles(text)
    if topic in _CIRCLE:
        return _score_circle(text, topic)
    if topic == 'GE08':
        return _score_scale(text)
    if topic == 'GE09':
        return _score_symmetry(text)
    if topic in _CUBE_3D:
        return _score_3d(text, topic)
    if topic == 'GE12':
        return _score_counting(text)
    return 0.0
