"""NM (Number Sets) scorer — NM01–NM03."""
from __future__ import annotations
import math, re

NM_TOPICS = {'NM01', 'NM02', 'NM03'}

def _numbers(t):
    return [float(r.replace(',','.')) for r in re.findall(r'\d+(?:[.,]\d+)?', t) if r.replace(',','.').replace('.','',1).isdigit()]

def _max_num(t): nums = _numbers(t); return max(nums) if nums else 0
def _nc(t): return len(_numbers(t))

def _score_order(t):
    nc = _nc(t)
    has_neg = 1 if re.search(r'[−-]\d', t) else 0
    return round(0.5*nc + 1.0*has_neg + 0.3*math.log2(max(_max_num(t),2)), 2)

def _score_arith(t):
    ops = len(re.findall(r'[+−×·⋅÷]', t))
    nc = _nc(t)
    brackets = t.count('(')
    return round(1.0*ops + 0.5*nc + 0.5*brackets + 0.3*math.log2(max(_max_num(t),2)), 2)

def _score_line(t):
    nc = _nc(t)
    tl = len(t)
    return round(0.5*nc + 0.02*tl + 0.3*math.log2(max(_max_num(t),2)), 2)

_MAP = {'NM01': _score_order, 'NM02': _score_arith, 'NM03': _score_line}

def score_problem(text: str, topic: str) -> float:
    fn = _MAP.get(topic)
    return fn(text) if fn else 0.0
