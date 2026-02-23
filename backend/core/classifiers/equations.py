"""
EQ (Equations) topic classifier — EQ01 through EQ08.

EQ01: One-step equations (x + a = b, ax = b, x/a = b)
EQ02: Multi-step equations (brackets, two+ operations, both sides)
EQ03: Equations with fractions (x/a + x/b, (x+a)/b = c)
EQ04: Word problems → single equation (age, ratio, consecutive)
EQ05: Systems of equations (two+ equations with two+ unknowns)
EQ06: Word problems → system (pricing, quantity with two unknowns)
EQ07: Sum/difference problems + inequalities
EQ08: Missing operator / number puzzles (◻, ☐)
"""

from __future__ import annotations

import re

from .base import ClassifyResult


def _lower(text: str) -> str:
    return text.lower().strip()


def _is_word_problem(text: str) -> bool:
    tl = text.lower()
    if re.search(r'решите|уравнени|систем|неравенств', tl) and not re.search(
            r'возраст|старше|младше|стоит|стоят|тенге|корзин|яблок|книг|полк|мешк|ученик|рабоч', tl):
        return False
    markers = [
        'возраст', 'старше', 'младше', 'лет.*сумм',
        'стоит', 'стоят', 'купил', 'тенге',
        'полк', 'корзин', 'яблок', 'книг', 'мешк',
        'собрал', 'деталей', 'рабоч',
        'ученик', 'задач', 'мальчик', 'девочек',
        'наклеек', 'баурсак', 'марк', 'украшен',
        'куры', 'зайц', 'кошк', 'собак',
        'последовательн.*числ',
        'периметр.*прямоугольник',
        'в двух', 'в классе', 'в магазине',
        'дешевле', 'дороже',
        r'сколько\s+(лет|стоит|решил|яблок|книг|ученик|задач|деталей|зайц|кур)',
    ]
    return any(re.search(m, tl) for m in markers)


def _has_fraction_eq(text: str) -> bool:
    """Detect fraction equations like x/3 + x/6, (x+1)/4, 2/(x-1), etc.
    Requires at least a complex fraction pattern, not just x/a = b."""
    tl = text.lower()
    frac_patterns = [
        re.search(r'\([^)]*[xхy][^)]*\)\s*/\s*[\d(]', tl),  # (x+1)/4 or (x+1)/(...)
        re.search(r'[\d)]\s*/\s*\([^)]*[xхy]', tl),          # 2/(x-1) or )/(x-1)
        re.search(r'\d\s*/\s*[xхy](?!\s*=)', tl),             # 3/x (not simple d/x = b)
    ]
    if any(frac_patterns):
        return True
    x_frac_count = len(re.findall(r'[xхy]\s*/\s*\d', tl))
    return x_frac_count >= 2


def _has_system(text: str) -> bool:
    """Detect system of equations patterns."""
    tl = text.lower()
    if 'систем' in tl:
        return True
    if re.search(r'[xх]\s*[+\-]\s*[yу]\s*=', tl) and re.search(r'[xх]\s*[+\-=]', tl):
        xy_eqs = re.findall(r'[yу]', tl)
        if len(xy_eqs) >= 2:
            return True
    if re.search(r'\{', text):
        return True
    if 'даны три уравнения' in tl or 'даны два уравнения' in tl:
        return True
    return False


def _has_inequality(text: str) -> bool:
    return bool(re.search(r'неравенств|[<>≤≥]', text.lower()))


def _is_simple_equation(text: str) -> bool:
    """Check if equation is one-step: ax = b, x + a = b, x/a = b."""
    tl = text.lower().strip()
    cleaned = re.sub(r'решите\s*(уравнение)?:?\s*', '', tl).strip()
    if re.match(r'^[xх]\s*[+\-]\s*\d+\s*=\s*\d+\.?$', cleaned):
        return True
    if re.match(r'^\d+\s*[+\-]\s*[xх]\s*=\s*\d+\.?$', cleaned):
        return True
    if re.match(r'^\d*[xх]\s*=\s*\d+\.?$', cleaned):
        return True
    if re.match(r'^[xх]\s*/\s*\d+\s*=\s*\d+\.?$', cleaned):
        return True
    if re.match(r'^\d+\s*/\s*[xх]\s*=\s*\d+\.?$', cleaned):
        return True
    return False


def _count_operations(text: str) -> int:
    """Count distinct math operations in equation text."""
    ops = 0
    if re.search(r'[+]', text):
        ops += 1
    if re.search(r'[−\-]', text):
        ops += 1
    if re.search(r'[×\*]|(?<!\w)\d+[xх]', text):
        ops += 1
    if re.search(r'[÷/:]', text):
        ops += 1
    return ops


def _has_brackets(text: str) -> bool:
    return '(' in text and ')' in text


# ── classifier ─────────────────────────────────────────────────────────

def classify_eq(text: str) -> ClassifyResult:
    """Classify a problem into EQ01–EQ08."""
    tl = _lower(text)

    # EQ08: missing operator / number puzzles
    if '◻' in text or '☐' in text or 'пропущенн' in tl:
        return ClassifyResult('EQ08', 0.95, 'missing operator puzzle')
    if re.search(r'вставьте число|найдите число.*[☐◻]|расставьте скобк|расставьте знак', tl):
        return ClassifyResult('EQ08', 0.90, 'insert number/bracket puzzle')

    # EQ07 inequalities BEFORE system check (system of inequalities != EQ05)
    if _has_inequality(text):
        return ClassifyResult('EQ07', 0.90, 'inequality')

    # EQ05: systems of equations
    if _has_system(text):
        if _is_word_problem(text):
            return ClassifyResult('EQ06', 0.85, 'word problem + system')
        return ClassifyResult('EQ05', 0.90, 'system of equations')

    word = _is_word_problem(text)
    frac = _has_fraction_eq(text)
    brackets = _has_brackets(text)
    ops = _count_operations(text)

    # Word problem branch
    if word:
        has_sum_diff = bool(re.search(r'сумм\w*.*разност|разност\w*.*сумм', tl))
        has_two_qty = bool(re.search(
            r'(больше|меньше|тяжелее|легче|длиннее|короче|старше|младше).*на\s+\d+.*всего|'
            r'всего.*\d+.*(больше|меньше|на\s+\d+)', tl))
        has_pricing = bool(re.search(
            r'\d+\s*(тетрад|ручк|яблок|груш|кг|штук).*стоят?\s*\d+.*тенге', tl))
        has_two_price = len(re.findall(r'стоят?\s*\d+', tl)) >= 2

        if has_pricing and has_two_price:
            return ClassifyResult('EQ06', 0.90, 'two pricing equations')
        if has_sum_diff:
            return ClassifyResult('EQ07', 0.85, 'sum/difference word problem')
        if has_two_qty:
            return ClassifyResult('EQ07', 0.80, 'sum + difference pattern')

        return ClassifyResult('EQ04', 0.85, 'word problem → equation')

    # Pure equation branch
    if frac:
        return ClassifyResult('EQ03', 0.90, 'fraction equation')

    if brackets and ops >= 2:
        return ClassifyResult('EQ02', 0.90, 'multi-step with brackets')

    if _is_simple_equation(text):
        return ClassifyResult('EQ01', 0.90, 'simple one-step equation')

    if ops >= 2 or brackets:
        return ClassifyResult('EQ02', 0.85, 'multi-step equation')

    # Fallback: any "решите" equation
    if re.search(r'решите|найдите.*[xх]|уравнени', tl):
        return ClassifyResult('EQ01', 0.75, 'equation fallback')

    return ClassifyResult('NONE', 0.0, 'no EQ match')
