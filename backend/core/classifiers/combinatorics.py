"""
CB (Combinatorics) topic classifier — CB01 through CB07.

CB01: Multiplication/addition principle (how many combos of soup+salad)
CB02: Permutations without repetition / grid paths
CB03: Permutations with repetition / anagrams
CB04: Counting with constraints (digit constraints, divisibility)
CB05: Permutations (n!)
CB06: Factorials (compute n!, n!/m!)
CB07: Basic probability
"""

from __future__ import annotations

import re

from .base import ClassifyResult


def _lower(text: str) -> str:
    return text.lower().strip()


def classify_cb(text: str) -> ClassifyResult:
    """Classify a problem into CB01–CB07."""
    tl = _lower(text)

    # CB07: probability
    if re.search(r'вероятност', tl):
        return ClassifyResult('CB07', 0.95, 'вероятность')
    if re.search(r'наугад\s+бер|случайн\w+\s+выбир', tl):
        return ClassifyResult('CB07', 0.85, 'random selection')

    # CB06: factorials
    if re.search(r'факториал', tl):
        return ClassifyResult('CB06', 0.95, 'факториал')
    if re.search(r'\d+\s*!\s*[/÷]|вычислите.*\d+\s*!', tl):
        return ClassifyResult('CB06', 0.90, 'n! expression')
    if re.search(r'P\s*\(\s*\d+\s*\)', text) and re.search(r'n\s*!|P\s*\(', text):
        return ClassifyResult('CB06', 0.85, 'P(n) = n!')

    # CB05: permutations
    if re.search(r'перестанов', tl):
        return ClassifyResult('CB05', 0.95, 'перестановка')
    if re.search(r'расставить.*на\s+полк|расположить.*в\s+ряд', tl):
        return ClassifyResult('CB05', 0.85, 'arrange on shelf/row')
    if re.search(r'сесть\s+за.*стол|за\s+круглый\s+стол', tl):
        return ClassifyResult('CB05', 0.85, 'circular permutation')
    if re.search(r'встать\s+в\s+очередь', tl):
        return ClassifyResult('CB05', 0.85, 'queue permutation')

    # CB03: permutations with repetition / anagrams
    if re.search(r'с\s+повторени', tl):
        return ClassifyResult('CB03', 0.95, 'с повторениями')
    if re.search(r'из\s+букв\s+слова|различных\s+слов\s+из\s+букв', tl):
        return ClassifyResult('CB03', 0.90, 'anagram from word')
    if re.search(r'из\s+цифр\s+\{?\d+\s*,\s*\d+\s*,\s*\d+\}?.*повтор', tl):
        return ClassifyResult('CB03', 0.85, 'digits with repetition')
    if re.search(r'повторения\s+разрешен', tl):
        return ClassifyResult('CB03', 0.90, 'repetitions allowed')

    # CB04: counting with constraints (digit constraints, divisibility)
    if re.search(r'различными\s+цифрами.*дел\w+\s+на|кратн\w+\s+\d+', tl):
        return ClassifyResult('CB04', 0.90, 'digits + divisibility')
    if re.search(r'различными\s+цифрами|все\s+цифры\s+нечётн', tl):
        return ClassifyResult('CB04', 0.85, 'digit constraints')
    if re.search(r'из\s+цифр.*без\s+повтор.*кратн|из\s+цифр.*без\s+повтор.*делится', tl):
        return ClassifyResult('CB04', 0.85, 'no repeat + divisibility')
    if re.search(r'сколько\s+\w*значных\s+чисел.*из\s+цифр', tl) and re.search(r'без\s+повтор', tl):
        has_constraint = bool(re.search(r'нечётн|чётн|кратн|делится|первая\s+цифра|больше|меньше', tl))
        if has_constraint:
            return ClassifyResult('CB04', 0.85, 'digit count + constraint')

    # CB02: permutations without repetition / grid paths
    if re.search(r'без\s+повторени', tl):
        return ClassifyResult('CB02', 0.85, 'без повторения')
    if re.search(r'вправо.*вверх|клеток\s+сетки|сетк\w+.*шаг', tl):
        return ClassifyResult('CB02', 0.85, 'grid path')

    # CB01: multiplication/addition principle
    if re.search(r'комбинаци|нарядов|сколько\s+\w*\s*вариантов', tl):
        return ClassifyResult('CB01', 0.85, 'combination/outfit')
    if re.search(r'вид\w+\s+суп\w*.*вид\w+\s+салат|вид\w+\s+\w+\s+и\s+\d+\s+вид', tl):
        return ClassifyResult('CB01', 0.90, 'soup+salad combos')
    if re.search(r'из\s+города.*дорог|маршрут\w*\s+из\s+A', tl):
        return ClassifyResult('CB01', 0.85, 'route counting')
    if re.search(r'рубаш\w+.*брюк|юбк\w+.*блуз', tl):
        return ClassifyResult('CB01', 0.85, 'clothing combos')
    if re.search(r'сколько\s+способов', tl):
        return ClassifyResult('CB01', 0.75, 'сколько способов fallback')

    return ClassifyResult('NONE', 0.0, 'no CB match')
