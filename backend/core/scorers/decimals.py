"""DC (Decimal Fractions) scorer — DC01–DC05."""
from __future__ import annotations
import math, re

DC_TOPICS = {'DC01', 'DC02', 'DC03', 'DC04', 'DC05'}

def _numbers(t):
    return [float(r.replace(',','.')) for r in re.findall(r'\d+(?:[.,]\d+)?', t) if r.replace(',','.').replace('.','',1).isdigit()]

def _max_num(t): nums = _numbers(t); return max(nums) if nums else 0
def _nc(t): return len(_numbers(t))

def _score_write(t):
    return round(0.5*_nc(t) + 0.3*math.log2(max(_max_num(t),2)) + (1.5 if '/' in t else 0), 2)

def _score_compare(t):
    return round(0.8*_nc(t) + 0.3*math.log2(max(_max_num(t),2)) + (1.0 if re.search(r'не вычисляя', t.lower()) else 0), 2)

def _score_arith(t):
    ops = len(re.findall(r'[+−×·⋅÷]', t))
    return round(1.2*ops + 0.5*_nc(t) + 0.3*math.log2(max(_max_num(t),2)) + (1.0 if re.search(r'\(', t) else 0), 2)

def _score_convert(t):
    has_period = 1 if re.search(r'периодическ|\(\d+\)', t.lower()) else 0
    return round(0.5*_nc(t) + 0.3*math.log2(max(_max_num(t),2)) + 2.0*has_period + (1.0 if '/' in t else 0), 2)

def _score_period(t):
    nc = _nc(t)
    tl = len(t)
    ops = len(re.findall(r'[+−×·⋅÷]', t))
    return round(0.5*nc + 0.02*tl + 1.0*ops + 0.3*math.log2(max(_max_num(t),2)), 2)

_MAP = {'DC01': _score_write, 'DC02': _score_compare, 'DC03': _score_arith, 'DC04': _score_convert, 'DC05': _score_period}

def score_problem(text: str, topic: str) -> float:
    fn = _MAP.get(topic)
    return fn(text) if fn else 0.0
