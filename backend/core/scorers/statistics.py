"""ST (Sets) scorer — ST01–ST02."""
from __future__ import annotations
import math, re

ST_TOPICS = {'ST01', 'ST02'}

def _numbers(t):
    return [float(r.replace(',','.')) for r in re.findall(r'\d+(?:[.,]\d+)?', t) if r.replace(',','.').replace('.','',1).isdigit()]

def _max_num(t): nums = _numbers(t); return max(nums) if nums else 0
def _nc(t): return len(_numbers(t))

def _score_ops(t):
    nc = _nc(t)
    tl = len(t)
    symbols = len(re.findall(r'[∩∪\\]', t))
    return round(0.5*nc + 0.02*tl + 1.0*symbols + 0.3*math.log2(max(_max_num(t),2)), 2)

def _score_venn(t):
    nc = _nc(t)
    tl = len(t)
    groups = len(re.findall(r'математик|физик|хими|английск|немецк|французск|любят|знают|сдали', t.lower()))
    return round(0.5*nc + 0.02*tl + 0.5*min(groups,4) + 0.3*math.log2(max(_max_num(t),2)), 2)

_MAP = {'ST01': _score_ops, 'ST02': _score_venn}

def score_problem(text: str, topic: str) -> float:
    fn = _MAP.get(topic)
    return fn(text) if fn else 0.0
