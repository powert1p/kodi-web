"""
AR (Arithmetic) topic classifier — AR01 through AR11.

Also detects when an AR-labeled problem actually belongs to a different group
(WP, CB, EQ, PR, ST, etc.) — common in AR06 where word problems were dumped.
"""

from __future__ import annotations

import re

from .base import ClassifyResult


def _lower(text: str) -> str:
    return text.lower().strip()


def _max_number(text: str) -> int:
    nums = re.findall(r'\b\d+\b', text)
    return max((int(n) for n in nums), default=0)


def _digit_count(text: str) -> int:
    nums = re.findall(r'\b\d+\b', text)
    return max((len(n) for n in nums), default=0)


def _get_ops(text: str) -> set[str]:
    expr = text
    m = re.match(r'^[А-Яа-яA-Za-z\s,]+:\s*', text)
    if m and len(m.group()) < 40:
        expr = text[m.end():]
    ops = set()
    if '+' in expr:
        ops.add('add')
    if re.search(r'[\u2212−]', expr):
        ops.add('sub')
    if re.search(r'[×·⋅∙]|\*', expr):
        ops.add('mul')
    if '÷' in expr:
        ops.add('div')
    if re.search(r'\)\s*:\s*[\d(]|\d\s*:\s*\d', expr):
        ops.add('div')
    if '²' in expr or '³' in expr or '^' in expr:
        ops.add('pow')
    return ops


def _bracket_depth(text: str) -> int:
    expr = text.split(':', 1)[-1] if ':' in text and len(text.split(':', 1)[0]) < 30 else text
    d = mx = 0
    for ch in expr:
        if ch == '(':
            d += 1; mx = max(mx, d)
        elif ch == ')':
            d -= 1
    return mx


def _is_short_compute(text: str) -> bool:
    """Short expression after 'Вычислите:' — pure arithmetic."""
    tl = _lower(text)
    if not re.match(r'вычислите', tl):
        return False
    expr = text.split(':', 1)[-1].strip() if ':' in text else ''
    return len(expr) < 60 and not re.search(r'[а-яА-Я]{3,}', expr)


# ---------------------------------------------------------------------------
# Word-problem detectors (for AR06 misclassification cleanup)
# ---------------------------------------------------------------------------

_WP_WORK_KEYWORDS = [
    'работник', 'рабочи', 'мастер', 'оператор', 'станок', 'кран',
    'бригад', 'токар', 'столяр', 'маляр', 'плотник',
    'вместе за', 'вместе –', 'вместе—', 'совместн',
    'производительн', 'выполня', 'изготов',
]

_WP_MOTION_KEYWORDS = [
    'скорость', 'расстояни', 'километр', 'путь', 'ехал', 'шёл', 'шел',
    'поезд', 'автобус', 'велосипед', 'машин', 'катер', 'лодк', 'течени',
    'навстречу', 'одновременно выехал', 'пешеход',
]

_CB_KEYWORDS = [
    'сколько вариант', 'сколько способ', 'сколько.*можно составить',
    'сколько.*различных', 'комбинаци', 'перестанов',
    'слов можно', 'чисел можно составить',
]

_ST_KEYWORDS = [
    'круги эйлера', 'диаграмм.*венн', 'пересечен.*множеств',
    'человек.*из них', 'из них.*человек',
    'знают.*знают', 'занимаются.*занимаются',
    'предпочитают.*предпочитают',
]

_EQ_KEYWORDS = [
    'найдите x', 'найди x', 'решите уравнен',
    'если каждому.*раздать.*если каждому', 'если раздат.*не хват.*если раздат',
]

_PR_KEYWORDS = [
    'пропорц', 'прямо пропорц', 'обратно пропорц',
]


def _detect_word_problem(tl: str) -> tuple[str, float, str] | None:
    """If this is a word problem, return (target_group, confidence, reason)."""
    for kw in _WP_WORK_KEYWORDS:
        if kw in tl:
            return ('WP05', 0.85, f'work problem: {kw}')
    for kw in _WP_MOTION_KEYWORDS:
        if kw in tl:
            return ('WP01', 0.85, f'motion problem: {kw}')
    for pat in _CB_KEYWORDS:
        if re.search(pat, tl):
            return ('CB01', 0.85, f'combinatorics: {pat}')
    for pat in _ST_KEYWORDS:
        if re.search(pat, tl):
            return ('ST01', 0.85, f'sets/Euler: {pat}')
    for pat in _EQ_KEYWORDS:
        if re.search(pat, tl):
            return ('EQ04', 0.80, f'equation word problem: {pat}')
    for kw in _PR_KEYWORDS:
        if kw in tl:
            return ('PR02', 0.80, f'proportion: {kw}')
    return None


def _is_long_word_problem(text: str) -> bool:
    """Detect word problems by structure: long text with narrative."""
    if len(text) < 80:
        return False
    tl = _lower(text)
    narrative_markers = [
        'скольк', 'купил', 'привез', 'раздат', 'собрал', 'построи',
        'рабочи', 'ученик', 'класс', 'магазин', 'склад',
        'гуляют', 'яблок', 'конфет', 'билет', 'столов',
        'день', 'час ', 'минут', 'кг ', 'литр',
        'каждый', 'поровну', 'остал', 'раз больш', 'раз меньш',
        'вместе', 'всего', 'в первом', 'во втором',
    ]
    matches = sum(1 for m in narrative_markers if m in tl)
    return matches >= 2


# ---------------------------------------------------------------------------
# AR topic classification
# ---------------------------------------------------------------------------

def classify_ar(text: str) -> ClassifyResult:
    """Classify a problem into AR01–AR11 or detect misclassification."""
    tl = _lower(text)
    ops = _get_ops(text)
    depth = _bracket_depth(text)
    max_num = _max_number(text)
    digits = _digit_count(text)
    is_short = _is_short_compute(text)

    # --- Step 0: detect word problems that don't belong in AR ---
    wp = _detect_word_problem(tl)
    if wp:
        return ClassifyResult(wp[0], wp[1], wp[2])

    if _is_long_word_problem(text) and not is_short:
        if re.search(r'труб|бассейн|наполн|выкач', tl):
            return ClassifyResult('WP05', 0.80, 'word: pipes/pool → совместная работа')
        if re.search(r'коров|корм|съед|сено', tl):
            return ClassifyResult('WP04', 0.75, 'word: animals/feed → производительность')
        if re.search(r'куры.*зайцы|ног.*голов|голов.*ног', tl):
            return ClassifyResult('EQ04', 0.80, 'word: chicken-rabbit → equation')
        if re.search(r'яблок.*груш|разлож|ящик', tl):
            return ClassifyResult('AR06', 0.60, 'word: fruit/boxes — possibly AR06')
        return ClassifyResult('WP01', 0.65, 'long word problem, likely WP')

    # --- Step 1: high-confidence AR topic keywords ---

    # AR11: last digit of power/product
    if re.search(r'последн.*цифр|послед.*цифр', tl):
        return ClassifyResult('AR11', 0.95, 'keyword: последняя цифра')

    # AR09: powers
    if re.search(r'степен', tl):
        return ClassifyResult('AR09', 0.90, 'keyword: степень')
    if re.search(r'[²³⁴⁵⁶⁷⁸⁹]|\^\d+', text) and is_short:
        return ClassifyResult('AR09', 0.85, 'power notation in short expression')

    # AR10: digits/places (but not "разряд" in rounding context)
    if re.search(r'сколько цифр|количество цифр|цифры числа', tl):
        return ClassifyResult('AR10', 0.90, 'keyword: цифры числа')
    if 'разряд' in tl and 'округл' not in tl:
        return ClassifyResult('AR10', 0.85, 'keyword: разряд (not rounding)')
    if re.search(r'сумма цифр|произведение цифр', tl):
        return ClassifyResult('AR10', 0.85, 'keyword: сумма/произведение цифр')
    if re.search(r'двузначн|трёхзначн|трехзначн|четырёхзначн', tl):
        if 'последн' not in tl:
            return ClassifyResult('AR10', 0.80, 'keyword: двузначное/трёхзначное')

    # AR07: rounding (high priority — don't let power/digit detection override)
    if re.search(r'округли', tl):
        return ClassifyResult('AR07', 0.95, 'keyword: округлите')
    if re.search(r'до\s+(?:десятков|сотен|тысяч|единиц|десятых|сотых)', tl):
        return ClassifyResult('AR07', 0.90, 'keyword: до десятков/сотен/...')

    # AR08: clever computation
    if re.search(r'выгодн|удобн.*способ|рациональн.*способ', tl):
        return ClassifyResult('AR08', 0.95, 'keyword: выгодным/удобным способом')
    # Distributive/associative patterns: a×b + a×c, 25×n×4, near-100
    if is_short and re.search(r'(?:25|125)\s*[×·]\s*\d+\s*[×·]\s*(?:4|8)', text):
        return ClassifyResult('AR08', 0.80, 'pattern: 25×n×4')
    if is_short and re.search(r'(?:99|101|98|102)\s*[×·]', text):
        return ClassifyResult('AR08', 0.80, 'pattern: near-100 multiplication')
    # a²−(a-1)(a+1) = difference of squares trick
    if is_short and re.search(r'\d{3,}[²³]', text):
        if re.search(r'без\s+калькулятор|без\s+вычислен', tl):
            return ClassifyResult('AR08', 0.80, 'pattern: algebraic identity trick')
    # Factoring: a×b + a×c = a×(b+c), or cancellation: a×b×c÷b = a×c
    if is_short:
        expr_part = text.split(':', 1)[-1].strip() if ':' in text else text
        nums_in_expr = re.findall(r'\d+', expr_part)
        if len(nums_in_expr) >= 4:
            from collections import Counter as _C
            dups = [n for n, c in _C(nums_in_expr).items()
                    if c >= 2 and int(n) > 12]
            if dups:
                return ClassifyResult('AR08', 0.80, f'pattern: repeated factor {dups[0]}')

    # AR04: division with remainder
    if re.search(r'остаток.*делен|делен.*остат', tl):
        return ClassifyResult('AR04', 0.95, 'keyword: остаток от деления')
    if re.search(r'остаток', tl) and re.search(r'делен|разделит|÷', tl):
        return ClassifyResult('AR04', 0.85, 'keyword: остаток + деление')

    # AR05: order of operations — requires mixing ×/÷ with +/−, or brackets
    # Pure +/- is NOT order of operations (no priority needed)
    if is_short:
        actual_ops = ops - {'pow'}
        has_mul_div = bool(actual_ops & {'mul', 'div'})
        has_add_sub = bool(actual_ops & {'add', 'sub'})
        is_order_of_ops = (
            (has_mul_div and has_add_sub)
            or (depth >= 1 and len(actual_ops) >= 1 and has_mul_div)
        )
        if is_order_of_ops and max_num <= 1000:
            return ClassifyResult('AR05', 0.85, f'mixed ops: {actual_ops}, depth={depth}')

    # AR01: add/sub within 100
    if is_short and ops <= {'add', 'sub'} and max_num <= 100 and digits <= 2:
        return ClassifyResult('AR01', 0.80, 'add/sub, numbers ≤ 100')

    # AR02: multiplication table (single-digit × single-digit, or up to 12×12)
    if is_short and ops == {'mul'} and max_num <= 144:
        expr = text.split(':', 1)[-1].strip() if ':' in text else text
        factors = re.findall(r'\d+', expr)
        if all(int(f) <= 12 for f in factors if f.isdigit()):
            return ClassifyResult('AR02', 0.85, 'multiplication table (≤12×12)')
        if all(int(f) <= 20 for f in factors if f.isdigit()):
            return ClassifyResult('AR02', 0.70, 'extended multiplication (≤20)')

    # AR03: pure division
    if is_short and ops == {'div'} and 'остаток' not in tl:
        return ClassifyResult('AR03', 0.80, 'pure division')

    # AR06: multi-digit arithmetic (large numbers, pure computation)
    if is_short and digits >= 3:
        return ClassifyResult('AR06', 0.80, f'multi-digit computation ({digits} digits)')

    # AR02 for simple multiplication with larger numbers
    if is_short and ops == {'mul'}:
        return ClassifyResult('AR02', 0.65, 'multiplication (general)')

    # --- Fallback for short compute tasks ---
    if is_short:
        return ClassifyResult('AR06', 0.50, 'fallback: short compute → AR06')

    # --- Fallback for everything else ---
    if re.search(r'звёздочк|вместо\s*\*|вместо\s*☆', tl):
        return ClassifyResult('AR10', 0.70, 'missing digit problem')

    return ClassifyResult('AR06', 0.30, 'fallback: generic arithmetic')
