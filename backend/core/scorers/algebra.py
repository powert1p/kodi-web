"""AL (Algebraic Expressions) scorer — AL01–AL04."""
from __future__ import annotations
import math, re

AL_TOPICS = {'AL01', 'AL02', 'AL03', 'AL04'}

def _numbers(t):
    return [float(r.replace(',','.')) for r in re.findall(r'\d+(?:[.,]\d+)?', t) if r.replace(',','.').replace('.','',1).isdigit()]

def _max_num(t): nums = _numbers(t); return max(nums) if nums else 0
def _nc(t): return len(_numbers(t))

def _score_eval(t):
    nc = _nc(t)
    has_sq = 1 if '²' in t or '^2' in t else 0
    terms = len(re.findall(r'[a-z]\w*', t.lower()))
    return round(0.5*nc + 0.5*min(terms,6) + 1.5*has_sq + 0.3*math.log2(max(_max_num(t),2)), 2)

def _score_expand(t):
    nc = _nc(t)
    brackets = t.count('(')
    has_frac = 1 if '/' in t else 0
    return round(0.5*nc + 1.0*brackets + 1.5*has_frac + 0.3*math.log2(max(_max_num(t),2)), 2)

def _score_ineq(t):
    nc = _nc(t)
    mn = _max_num(t)
    tl = len(t)
    return round(0.5*nc + 0.02*tl + 0.3*math.log2(max(mn,2)), 2)

def _score_system(t):
    nc = _nc(t)
    mn = _max_num(t)
    tl = len(t)
    constraints = len(re.findall(r'[<>≤≥]', t))
    return round(0.5*nc + 0.02*tl + 0.5*constraints + 0.3*math.log2(max(mn,2)), 2)

_MAP = {'AL01': _score_eval, 'AL02': _score_expand, 'AL03': _score_ineq, 'AL04': _score_system}

def score_problem(text: str, topic: str) -> float:
    fn = _MAP.get(topic)
    return fn(text) if fn else 0.0
