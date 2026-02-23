"""
WP (Word Problems) topic classifier — WP01 through WP10.

WP01: Speed-time-distance (basic)
WP02: Meeting / opposite movement
WP03: Water current (upstream/downstream)
WP04: Productivity (work rate, solo)
WP05: Joint work
WP06: Harvest / yield
WP07: Arithmetic mean
WP08: Cuts / splits
WP09: Page numbering / digit counting
WP10: Days of week (cyclic)
"""

from __future__ import annotations

import re

from .base import ClassifyResult


def _lower(text: str) -> str:
    return text.lower().strip()


# ── keyword lists ──────────────────────────────────────────────────────

_WP10_KW = [
    'понедельник', 'вторник', r'\bсреда\b', r'\bсреду\b', r'\bсреды\b',
    'четверг', 'пятниц', 'суббот',
    'воскресень', 'день недели', r'\bдней назад\b',
    r'через\s+\d+\s+дней\s+будет',
]

_WP09_KW = [
    'нумераци', 'сколько цифр', 'количество цифр',
    'цифр потребу', 'цифр.*использова', 'использова.*цифр',
    'страниц.*цифр', 'цифр.*страниц',
    'потерянн.*страниц', 'сколько всего страниц',
    'страниц.*в книге', 'страниц.*в журнале',
]

_WP08_KW = [
    'распил', 'разрез', 'бревно', 'верёвк', 'веревк',
    'на.*част', 'куб разрез', 'проволок.*разрез',
]

_WP07_KW = [
    'среднее арифметическое', 'средн.*арифм', 'средн.*оценк',
    'среднее значение', 'средн.*скорость.*весь.*путь',
]

_WP06_KW = [
    'урожай', 'ц/га', 'ц с га', 'центнер.*га', 'га.*центнер',
    'с поля.*собра', 'собра.*с поля', 'посевн', 'засея',
]

_WP03_KW = [
    'по течени', 'против течени', 'течени.*реки', 'скорость течени',
    'по.*против.*течени', 'лодк.*течени', 'катер.*течени',
    'плот.*течени', 'баржа.*течени',
    'вниз по реке', 'вверх по реке',
]

_WP02_KW = [
    'навстречу', 'противополож.*направлен',
    'удаляются друг', 'сближаются',
    'встретятся', 'встретились',
    'из.*пунктов.*одновременно',
    'выехал.*из.*навстречу',
]

_WP05_KW = [
    r'первый.*за\s+\d+.*второй.*за\s+\d+',
    r'первая труба.*за\s+\d+.*вторая',
    r'вместе.*за\s+\d+',
    r'совместн.*работ',
    r'вместе.*работу',
    r'подключился.*второй',
    r'один.*за\s+\d+.*вместе.*за\s+\d+',
    r'первый рабочий.*за\s+\d+.*второй.*за\s+\d+',
]

_WP04_KW = [
    'производительн',
    r'делает\s+\d+\s+деталей',
    r'изготов.*\d+\s+деталей',
    r'деталей в час',
]


# ── classifier ─────────────────────────────────────────────────────────

def classify_wp(text: str) -> ClassifyResult:
    """Classify a problem into WP01–WP10."""
    tl = _lower(text)

    # WP10: days of week (very specific vocabulary)
    for kw in _WP10_KW:
        if re.search(kw, tl):
            return ClassifyResult('WP10', 0.95, f'keyword: {kw}')

    # WP09: page numbering / digit counting
    for kw in _WP09_KW:
        if re.search(kw, tl):
            return ClassifyResult('WP09', 0.95, f'keyword: {kw}')

    # WP08: cuts and splits
    for kw in _WP08_KW:
        if kw in tl:
            return ClassifyResult('WP08', 0.90, f'keyword: {kw}')

    # WP07: arithmetic mean
    for kw in _WP07_KW:
        if re.search(kw, tl):
            return ClassifyResult('WP07', 0.95, f'keyword: {kw}')

    # WP06: harvest / yield
    for kw in _WP06_KW:
        if re.search(kw, tl):
            return ClassifyResult('WP06', 0.90, f'keyword: {kw}')

    # WP03: water current (check BEFORE WP01/WP02 since it overlaps)
    for kw in _WP03_KW:
        if re.search(kw, tl):
            return ClassifyResult('WP03', 0.95, f'keyword: {kw}')

    # WP02: meeting / opposite movement (check BEFORE WP01)
    for kw in _WP02_KW:
        if re.search(kw, tl):
            return ClassifyResult('WP02', 0.90, f'keyword: {kw}')

    # WP05: joint work (regex patterns — check BEFORE WP04)
    for pat in _WP05_KW:
        if re.search(pat, tl):
            return ClassifyResult('WP05', 0.90, f'pattern: {pat[:40]}')

    # WP04: productivity (solo work rate)
    for pat in _WP04_KW:
        if re.search(pat, tl):
            return ClassifyResult('WP04', 0.85, f'keyword: {pat[:30]}')

    # WP01: basic speed-time-distance (fallback for motion problems)
    motion_kw = [
        'скорость', 'расстояни', 'километр', 'км/ч', 'м/с',
        'ехал', 'проехал', 'шёл', 'шел', 'прошёл', 'прошел',
        'пешеход', 'велосипед', 'поезд', 'автомобил', 'машин',
        'путь', 'дорог',
    ]
    for kw in motion_kw:
        if kw in tl:
            return ClassifyResult('WP01', 0.85, f'motion keyword: {kw}')

    return ClassifyResult('NONE', 0.0, 'no WP match')
