"""
Difficulty scorer registry.
Each block (FR, AR, EQ, ...) has its own module with a score_problem() function.
"""

from __future__ import annotations

import math
from collections import Counter

from .fractions import score_problem as score_fr, FR_TOPICS
from .arithmetic import score_problem as score_ar, AR_TOPICS
from .word_problems import score_problem as score_wp, WP_TOPICS
from .geometry import score_problem as score_ge, GE_TOPICS
from .equations import score_problem as score_eq, EQ_TOPICS
from .divisibility import score_problem as score_dv, DV_TOPICS
from .percent import score_problem as score_pc, PC_TOPICS
from .logic import score_problem as score_lg, LG_TOPICS
from .proportion import score_problem as score_pr, PR_TOPICS
from .conversion import score_problem as score_cv, CV_TOPICS
from .combinatorics import score_problem as score_cb, CB_TOPICS
from .decimals import score_problem as score_dc, DC_TOPICS
from .roman_numerals import score_problem as score_rn, RN_TOPICS
from .algebra import score_problem as score_al, AL_TOPICS
from .modular import score_problem as score_md, MD_TOPICS
from .number_theory import score_problem as score_nm, NM_TOPICS
from .data_analysis import score_problem as score_da, DA_TOPICS
from .statistics import score_problem as score_st, ST_TOPICS
from .algorithms import score_problem as score_alg, ALG_TOPICS


_TOPIC_SCORERS: dict[str, callable] = {}
for t in FR_TOPICS:
    _TOPIC_SCORERS[t] = score_fr
for t in AR_TOPICS:
    _TOPIC_SCORERS[t] = score_ar
for t in WP_TOPICS:
    _TOPIC_SCORERS[t] = score_wp
for t in GE_TOPICS:
    _TOPIC_SCORERS[t] = score_ge
for t in EQ_TOPICS:
    _TOPIC_SCORERS[t] = score_eq
for t in DV_TOPICS:
    _TOPIC_SCORERS[t] = score_dv
for t in PC_TOPICS:
    _TOPIC_SCORERS[t] = score_pc
for t in LG_TOPICS:
    _TOPIC_SCORERS[t] = score_lg
for t in PR_TOPICS:
    _TOPIC_SCORERS[t] = score_pr
for t in CV_TOPICS:
    _TOPIC_SCORERS[t] = score_cv
for t in CB_TOPICS:
    _TOPIC_SCORERS[t] = score_cb
for t in DC_TOPICS:
    _TOPIC_SCORERS[t] = score_dc
for t in RN_TOPICS:
    _TOPIC_SCORERS[t] = score_rn
for t in AL_TOPICS:
    _TOPIC_SCORERS[t] = score_al
for t in MD_TOPICS:
    _TOPIC_SCORERS[t] = score_md
for t in NM_TOPICS:
    _TOPIC_SCORERS[t] = score_nm
for t in DA_TOPICS:
    _TOPIC_SCORERS[t] = score_da
for t in ST_TOPICS:
    _TOPIC_SCORERS[t] = score_st
for t in ALG_TOPICS:
    _TOPIC_SCORERS[t] = score_alg


def score_problem(text: str, topic: str) -> float:
    scorer = _TOPIC_SCORERS.get(topic)
    if scorer:
        return scorer(text, topic)
    return 0.0


def has_scorer(topic: str) -> bool:
    return topic in _TOPIC_SCORERS


def calibrate_thresholds(scores: list[float]) -> tuple[float, float, float]:
    """Return (t12, t23, t34) thresholds for L1/L2/L3/L4 split.
    ~25% L1, ~25% L2, ~30% L3, ~20% L4.
    """
    if not scores:
        return (0.0, 0.0, 0.0)
    s = sorted(scores)
    n = len(s)
    i25 = max(1, int(n * 0.25)) - 1
    i50 = max(1, int(n * 0.50)) - 1
    i80 = max(1, int(n * 0.80)) - 1
    t12 = (s[i25] + s[min(i25 + 1, n - 1)]) / 2
    t23 = (s[i50] + s[min(i50 + 1, n - 1)]) / 2
    t34 = (s[i80] + s[min(i80 + 1, n - 1)]) / 2
    return (round(t12, 2), round(t23, 2), round(t34, 2))


def classify_level(raw: float, thresholds: tuple[float, float, float]) -> int:
    t12, t23, t34 = thresholds
    if raw <= t12:
        return 1
    if raw <= t23:
        return 2
    if raw <= t34:
        return 3
    return 4


def is_potential_l5(raw: float, scores: list[float]) -> bool:
    if not scores:
        return False
    s = sorted(scores)
    p90 = s[max(0, int(len(s) * 0.90) - 1)]
    return raw > p90
