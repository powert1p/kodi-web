"""ALG (Algebra General) scorer — ALG01 only."""
from __future__ import annotations
import math, re

ALG_TOPICS = {'ALG01'}

def _numbers(t):
    return [float(r.replace(',','.')) for r in re.findall(r'\d+(?:[.,]\d+)?', t) if r.replace(',','.').replace('.','',1).isdigit()]

def _max_num(t): nums = _numbers(t); return max(nums) if nums else 0
def _nc(t): return len(_numbers(t))

def _score_general(t):
    nc = _nc(t)
    tl = len(t)
    has_sq = 1 if '²' in t or '^2' in t else 0
    terms = len(re.findall(r'[a-z]\w*', t.lower()))
    return round(0.5*nc + 0.5*min(terms,6) + 1.5*has_sq + 0.02*tl + 0.3*math.log2(max(_max_num(t),2)), 2)

_MAP = {'ALG01': _score_general}

def score_problem(text: str, topic: str) -> float:
    fn = _MAP.get(topic)
    return fn(text) if fn else 0.0
