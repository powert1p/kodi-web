"""MD (Absolute Value) scorer — MD01–MD03."""
from __future__ import annotations
import math, re

MD_TOPICS = {'MD01', 'MD02', 'MD03'}

def _numbers(t):
    return [float(r.replace(',','.')) for r in re.findall(r'\d+(?:[.,]\d+)?', t) if r.replace(',','.').replace('.','',1).isdigit()]

def _max_num(t): nums = _numbers(t); return max(nums) if nums else 0
def _nc(t): return len(_numbers(t))

def _score_compute(t):
    nc = _nc(t)
    pipes = t.count('|')
    nested = 1 if re.search(r'\|\||\|\s*\|', t) else 0
    return round(0.5*nc + 0.5*pipes + 2.0*nested + 0.3*math.log2(max(_max_num(t),2)), 2)

def _score_equation(t):
    nc = _nc(t)
    tl = len(t)
    multi = 1 if re.search(r'\+\s*\||\|\s*\+', t) else 0
    return round(0.5*nc + 0.02*tl + 2.0*multi + 0.3*math.log2(max(_max_num(t),2)), 2)

def _score_inequality(t):
    nc = _nc(t)
    tl = len(t)
    return round(0.5*nc + 0.02*tl + 0.3*math.log2(max(_max_num(t),2)), 2)

_MAP = {'MD01': _score_compute, 'MD02': _score_equation, 'MD03': _score_inequality}

def score_problem(text: str, topic: str) -> float:
    fn = _MAP.get(topic)
    return fn(text) if fn else 0.0
