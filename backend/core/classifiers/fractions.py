"""
FR (Fractions) topic classifier — FR01 through FR13.
"""

from __future__ import annotations

import re

from .base import ClassifyResult


def _lower(text: str) -> str:
    return text.lower().strip()


def _has_fraction(text: str) -> bool:
    return bool(re.search(r'\d+/\d+', text))


def _frac_count(text: str) -> int:
    return len(re.findall(r'\d+/\d+', text))


def _has_mixed(text: str) -> bool:
    return bool(re.search(r'\d+\s+\d+/\d+', text))


def _has_decimal(text: str) -> bool:
    return bool(re.search(r'\d+[.,]\d+', text))


def _get_operations(text: str) -> set[str]:
    expr = text
    m = re.match(r'^[А-Яа-яA-Za-z\s,]+:\s*', text)
    if m and len(m.group()) < 40:
        expr = text[m.end():]
    ops = set()
    if re.search(r'[+]', expr):
        ops.add('add')
    if re.search(r'[\u2212−]', expr):
        ops.add('sub')
    if re.search(r'[×·⋅∙]|\*', expr):
        ops.add('mul')
    if '÷' in expr:
        ops.add('div')
    if re.search(r'\)\s*:\s*[\d(]', expr):
        ops.add('div')
    if re.search(r'\d\s*:\s*\d', expr):
        if re.search(r'\d\s*:\s*\d+\s*/\s*\d+|\d+\s*/\s*\d+\s*:\s*\d', expr):
            ops.add('div')
    if '²' in expr or '³' in expr or '^' in expr:
        ops.add('pow')
    return ops


def _bracket_depth(text: str) -> int:
    expr = text.split(':', 1)[-1] if ':' in text and len(text.split(':', 1)[0]) < 30 else text
    d = mx = 0
    for ch in expr:
        if ch == '(':
            d += 1
            mx = max(mx, d)
        elif ch == ')':
            d -= 1
    return mx


def _is_compute_task(tl: str) -> bool:
    return bool(re.search(r'вычисл|упрост|найдите значен|найди значен', tl))


def classify_fr(text: str) -> ClassifyResult:
    """Classify a problem into FR01–FR13."""
    tl = _lower(text)
    has_frac = _has_fraction(text)
    ops = _get_operations(text)
    fc = _frac_count(text)
    depth = _bracket_depth(text)
    is_compute = _is_compute_task(tl)

    if not has_frac and not _has_mixed(text) and not _has_decimal(text):
        if 'дроб' not in tl and 'часть' not in tl:
            return ClassifyResult('NONE', 0.95, 'no fraction markers at all')

    # --- Phase 1: high-confidence keyword matches ---

    if re.search(r'закрашен|заштрихован', tl):
        return ClassifyResult('FR13', 0.95, 'visual: закрашен/заштрихован')
    if re.search(r'разделён.*равн.*част|разделен.*равн.*част', tl) and 'закрашен' not in tl:
        if not is_compute:
            return ClassifyResult('FR13', 0.85, 'visual: разделён на равные части')

    if re.search(r'сравни', tl):
        return ClassifyResult('FR05', 0.90, 'comparison: сравни')
    if re.search(r'какая.*(?:дробь|из дробей).*больш|какое.*(?:чисел|из чисел).*больш', tl):
        if 'знаменател' not in tl:
            return ClassifyResult('FR05', 0.90, 'comparison: какая дробь/число больше')
    if re.search(r'расположите.*(?:возраст|убыван)', tl):
        return ClassifyResult('FR05', 0.85, 'comparison: расположите')
    if re.search(r'упорядоч', tl):
        return ClassifyResult('FR05', 0.80, 'comparison: упорядочить')
    if re.search(r'(?:больше|меньше)\s*[:?]', tl) and not is_compute:
        return ClassifyResult('FR05', 0.80, 'comparison: больше/меньше?')
    if re.search(r'дальше\s+от|ближе\s+к', tl) and re.search(r'какая|какое|определите', tl):
        return ClassifyResult('FR05', 0.80, 'comparison: дальше от / ближе к')
    if re.search(r'(?:наибольш|наименьш)', tl):
        if 'знаменател' not in tl and 'натуральн' not in tl:
            return ClassifyResult('FR05', 0.85, 'comparison: наибольш/наименьш')

    has_kakuyu_chast = bool(re.search(r'какую\s+часть', tl))
    if re.search(r'найд.*дроб.*от\s+числ', tl):
        return ClassifyResult('FR10', 0.90, 'найди дробь от числа')
    if re.search(r'\d+/\d+\s+от\s+\d+', tl) and not has_kakuyu_chast:
        return ClassifyResult('FR10', 0.85, 'X/Y от Z')
    if re.search(r'(?:составляет|равна?)\s+\d+/\d+\s+от', tl) and not has_kakuyu_chast:
        return ClassifyResult('FR10', 0.80, 'составляет X/Y от')

    if re.search(r'найд.*числ.*по.*дроб', tl):
        return ClassifyResult('FR11', 0.90, 'найди число по дроби')
    if re.search(r'\d+/\d+\s+числа\s+(?:равн|состав)', tl):
        return ClassifyResult('FR11', 0.85, 'X/Y числа равно')
    if re.search(r'(?:потратил|израсходовал).*остал', tl):
        return ClassifyResult('FR11', 0.80, 'потратили...осталось')

    if re.search(r'(?:общ|наименьш).*знаменател', tl) and 'между' not in tl:
        return ClassifyResult('FR04', 0.90, 'общий/наименьший знаменатель')
    if re.search(r'привед.*к.*знаменател', tl):
        return ClassifyResult('FR04', 0.85, 'привести к знаменателю')
    if 'НОЗ' in text:
        return ClassifyResult('FR04', 0.80, 'НОЗ')

    if re.search(r'сократ', tl) and not re.search(r'предварительно\s+сократ', tl):
        if not is_compute:
            return ClassifyResult('FR03', 0.90, 'сократить (primary task)')
    if re.search(r'несократим', tl) and not is_compute:
        return ClassifyResult('FR03', 0.85, 'несократимая дробь')

    if not is_compute:
        if re.search(r'(?:переведи|перевод|запиши).*(?:смешанн|неправильн|десятичн)', tl):
            return ClassifyResult('FR02', 0.85, 'conversion: переведите/запишите')
        if re.search(r'(?:правильн|неправильн).*дроб', tl):
            return ClassifyResult('FR02', 0.80, 'conversion: правильная/неправильная')
        if re.search(r'(?:смешанн).*(?:числ|дроб)', tl):
            return ClassifyResult('FR02', 0.75, 'conversion: смешанное число')
        if re.search(r'(?:целая|дробная)\s+часть', tl):
            return ClassifyResult('FR02', 0.70, 'conversion: целая/дробная часть')

    if re.search(r'какую\s+часть', tl):
        return ClassifyResult('FR01', 0.85, 'concept: какую часть')
    if re.search(r'понятие.*дроб', tl):
        return ClassifyResult('FR01', 0.80, 'concept: понятие дроби')

    # --- Phase 2: structural analysis ---

    if re.search(r'\d+\s*/\s*\(\d+\s*[+−\u2212]\s*\d+\s*/', text):
        return ClassifyResult('FR12', 0.90, 'nested: a/(b ± c/...)')
    if re.search(r'\d+\s*/\s*\(\d+/\d+\)', text):
        return ClassifyResult('FR12', 0.85, 'nested: a/(b/c)')
    if re.search(r'этажн|многоэтажн', tl):
        return ClassifyResult('FR12', 0.85, 'keyword: этажная/многоэтажная')

    actual_ops = ops - {'pow'}
    has_pow = 'pow' in ops

    if is_compute or re.search(r'^вычислите', tl):
        has_nested_frac = bool(re.search(
            r'\d+\s*/\s*\(.*\d+/\d+|'
            r'\(\d+/\d+\)\s*[²³^]',
            text
        ))
        is_combined = (
            len(actual_ops) >= 2
            or (has_pow and actual_ops)
            or (_has_decimal(text) and has_frac and actual_ops)
            or has_nested_frac
        )
        if is_combined:
            return ClassifyResult('FR09', 0.80, f'combined ops: {actual_ops | ({"pow"} if has_pow else set())}')
        if actual_ops:
            if 'mul' in actual_ops:
                return ClassifyResult('FR07', 0.75, '× only')
            if 'div' in actual_ops:
                return ClassifyResult('FR08', 0.75, '÷ only')
            if 'add' in actual_ops or 'sub' in actual_ops:
                return ClassifyResult('FR06', 0.75, '+/- only')

    # --- Fallbacks ---
    if has_frac and fc >= 2 and actual_ops:
        if len(actual_ops) >= 2:
            return ClassifyResult('FR09', 0.50, 'fallback: multi-op with fractions')
        return ClassifyResult('FR06', 0.40, 'fallback: fractions with operations')

    return ClassifyResult('FR01', 0.30, 'fallback: generic fraction')
