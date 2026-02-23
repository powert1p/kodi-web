"""DA (Data Analysis) scorer — DA01–DA03."""
from __future__ import annotations
import math, re

DA_TOPICS = {'DA01', 'DA02', 'DA03'}

def _numbers(t):
    return [float(r.replace(',','.')) for r in re.findall(r'\d+(?:[.,]\d+)?', t) if r.replace(',','.').replace('.','',1).isdigit()]

def _max_num(t): nums = _numbers(t); return max(nums) if nums else 0
def _nc(t): return len(_numbers(t))

def _score_diagram(t):
    nc = _nc(t)
    tl = len(t)
    return round(0.5*nc + 0.02*tl + 0.3*math.log2(max(_max_num(t),2)), 2)

def _score_graph(t):
    nc = _nc(t)
    tl = len(t)
    multi = 1 if re.search(r'автомобиль.*автомобиль|поезд.*автобус', t.lower()) else 0
    return round(0.5*nc + 0.02*tl + 1.5*multi + 0.3*math.log2(max(_max_num(t),2)), 2)

def _score_stats(t):
    nc = _nc(t)
    mn = _max_num(t)
    has_neg = 1 if re.search(r'[−-]\d', t) else 0
    return round(0.5*nc + 1.0*has_neg + 0.3*math.log2(max(mn,2)), 2)

_MAP = {'DA01': _score_diagram, 'DA02': _score_graph, 'DA03': _score_stats}

def score_problem(text: str, topic: str) -> float:
    fn = _MAP.get(topic)
    return fn(text) if fn else 0.0
