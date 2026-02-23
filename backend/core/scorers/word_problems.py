"""
WP (Word Problems) difficulty scorer — WP01 through WP10.

Scoring profiles:
    Motion          WP01 (basic), WP02 (meeting/opposite), WP03 (water current)
    Work            WP04 (productivity), WP05 (joint work)
    Harvest         WP06
    Mean            WP07
    Cuts            WP08
    Page numbering  WP09
    Days of week    WP10
"""

from __future__ import annotations

import math
import re

WP_TOPICS = {
    'WP01', 'WP02', 'WP03', 'WP04', 'WP05',
    'WP06', 'WP07', 'WP08', 'WP09', 'WP10',
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


def _sentence_count(text: str) -> int:
    return max(1, len(re.findall(r'[.?!]\s', text)) + 1)


def _multi_step(text: str) -> int:
    tl = text.lower()
    markers = [
        'сначала', 'потом', 'затем', 'после этого', 'подключился',
        'остальн', 'оставш', 'на обратном пути',
        'первый час', 'второй час', 'первый день', 'второй день',
    ]
    return sum(1 for m in markers if m in tl)


def _entity_count(text: str) -> int:
    tl = text.lower()
    entities = [
        'первый', 'второй', 'третий', 'рабочий', 'труба',
        'бассейн', 'пешеход', 'велосипед', 'поезд', 'катер',
        'лодк', 'автобус', 'машин',
    ]
    return sum(1 for e in entities if e in tl)


def _has_fraction(text: str) -> bool:
    return bool(re.search(r'\d+/\d+', text))


def _has_percent(text: str) -> bool:
    return '%' in text or 'процент' in text.lower()


# ── scoring profiles ──────────────────────────────────────────────────

def _score_motion(text: str, topic: str) -> float:
    """WP01 (basic), WP02 (meeting), WP03 (water current)."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)
    ms = _multi_step(text)
    ec = _entity_count(text)
    frac = 1 if _has_fraction(text) else 0
    pct = 1 if _has_percent(text) else 0

    base = (0.3 * math.log2(max(mn, 2)) + 1.0 * nc + 0.02 * tl +
            2.0 * ms + 1.5 * ec + 2.0 * frac + 2.0 * pct)

    if topic == 'WP02':
        base += 1.0
    elif topic == 'WP03':
        base += 0.5

    return round(base, 2)


def _score_work(text: str, topic: str) -> float:
    """WP04 (productivity), WP05 (joint work)."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)
    ms = _multi_step(text)
    ec = _entity_count(text)
    frac = 1 if _has_fraction(text) else 0

    base = (0.3 * math.log2(max(mn, 2)) + 1.2 * nc + 0.02 * tl +
            2.5 * ms + 1.5 * ec + 2.5 * frac)

    if topic == 'WP05':
        three_workers = bool(re.search(r'третий|трое|три\s+рабочи', text.lower()))
        base += 1.5 * three_workers

    return round(base, 2)


def _score_harvest(text: str) -> float:
    """WP06 — harvest / yield."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)
    ms = _multi_step(text)
    pct = 1 if _has_percent(text) else 0

    base = (0.3 * math.log2(max(mn, 2)) + 1.0 * nc + 0.02 * tl +
            2.0 * ms + 2.5 * pct)
    return round(base, 2)


def _score_mean(text: str) -> float:
    """WP07 — arithmetic mean."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)
    sc = _sentence_count(text)
    frac = 1 if _has_fraction(text) else 0

    base = (0.2 * math.log2(max(mn, 2)) + 1.5 * nc + 0.02 * tl +
            1.0 * sc + 2.0 * frac)
    return round(base, 2)


def _score_cuts(text: str) -> float:
    """WP08 — cuts / splits."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)

    is_3d = bool(re.search(r'куб|парал', text.lower()))
    time_element = bool(re.search(r'минут|секунд|час', text.lower()))

    base = (0.3 * math.log2(max(mn, 2)) + 1.0 * nc + 0.02 * tl +
            3.0 * is_3d + 1.5 * time_element)
    return round(base, 2)


def _score_pages(text: str) -> float:
    """WP09 — page numbering / digit counting."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)

    reverse = bool(re.search(r'использова.*цифр|сколько страниц', text.lower()))

    base = (0.5 * math.log2(max(mn, 2)) + 1.0 * nc + 0.02 * tl +
            2.0 * reverse)
    return round(base, 2)


def _score_days(text: str) -> float:
    """WP10 — days of week (cyclic)."""
    mn = _max_number(text)
    nc = _num_count(text)
    tl = _text_len(text)

    backward = bool(re.search(r'назад', text.lower()))
    year_context = bool(re.search(r'високосн|январ|феврал|март|декабр|год', text.lower()))
    large_num = 1 if mn > 100 else 0

    base = (0.3 * math.log2(max(mn, 2)) + 1.0 * nc + 0.02 * tl +
            1.5 * backward + 2.5 * year_context + 1.5 * large_num)
    return round(base, 2)


# ── routing ───────────────────────────────────────────────────────────

_MOTION = {'WP01', 'WP02', 'WP03'}
_WORK = {'WP04', 'WP05'}


def score_problem(text: str, topic: str) -> float:
    if topic in _MOTION:
        return _score_motion(text, topic)
    if topic in _WORK:
        return _score_work(text, topic)
    if topic == 'WP06':
        return _score_harvest(text)
    if topic == 'WP07':
        return _score_mean(text)
    if topic == 'WP08':
        return _score_cuts(text)
    if topic == 'WP09':
        return _score_pages(text)
    if topic == 'WP10':
        return _score_days(text)
    return 0.0
