"""RN (Rational Numbers) scorer — RN01–RN04."""
from __future__ import annotations
import math, re

RN_TOPICS = {'RN01', 'RN02', 'RN03', 'RN04'}

def _numbers(t):
    return [float(r.replace(',','.')) for r in re.findall(r'\d+(?:[.,]\d+)?', t) if r.replace(',','.').replace('.','',1).isdigit()]

def _max_num(t): nums = _numbers(t); return max(nums) if nums else 0
def _nc(t): return len(_numbers(t))

def _score_line(t):
    nc = _nc(t)
    has_neg = 1 if re.search(r'[−-]\d', t) else 0
    return round(0.5*nc + 0.3*math.log2(max(_max_num(t),2)) + 1.0*has_neg + (1.5 if 'промежут' in t.lower() else 0), 2)

def _score_ops(t):
    ops = len(re.findall(r'[+−×·⋅÷]', t))
    has_frac = 1 if '/' in t else 0
    return round(1.2*ops + 0.5*_nc(t) + 0.3*math.log2(max(_max_num(t),2)) + 1.5*has_frac + (1.0 if re.search(r'\(', t) else 0), 2)

def _score_coord(t):
    nc = _nc(t)
    tl = len(t)
    return round(0.5*nc + 0.02*tl + 0.3*math.log2(max(_max_num(t),2)), 2)

def _score_class(t):
    nc = _nc(t)
    tl = len(t)
    return round(0.5*nc + 0.02*tl + 0.3*math.log2(max(_max_num(t),2)), 2)

_MAP = {'RN01': _score_line, 'RN02': _score_ops, 'RN03': _score_coord, 'RN04': _score_class}

def score_problem(text: str, topic: str) -> float:
    fn = _MAP.get(topic)
    return fn(text) if fn else 0.0
