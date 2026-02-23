"""
Topic classifier registry.
Each block (FR, AR, EQ, ...) has its own module with a classify() function.
"""

from __future__ import annotations

import re

from .base import ClassifyResult
from .fractions import classify_fr
from .arithmetic import classify_ar
from .word_problems import classify_wp
from .geometry import classify_ge
from .equations import classify_eq
from .divisibility import classify_dv
from .percent import classify_pc
from .logic import classify_lg
from .proportion import classify_pr
from .conversion import classify_cv
from .combinatorics import classify_cb
from .decimals import classify_dc
from .roman_numerals import classify_rn
from .algebra import classify_al
from .modular import classify_md
from .number_theory import classify_nm
from .data_analysis import classify_da
from .statistics import classify_st
from .algorithms import classify_alg


_GROUP_CLASSIFIERS = {
    'FR': classify_fr,
    'AR': classify_ar,
    'WP': classify_wp,
    'GE': classify_ge,
    'EQ': classify_eq,
    'DV': classify_dv,
    'PC': classify_pc,
    'LG': classify_lg,
    'PR': classify_pr,
    'CV': classify_cv,
    'CB': classify_cb,
    'DC': classify_dc,
    'RN': classify_rn,
    'AL': classify_al,
    'MD': classify_md,
    'NM': classify_nm,
    'DA': classify_da,
    'ST': classify_st,
    'ALG': classify_alg,
}


def classify(text_ru: str, current_node_id: str) -> ClassifyResult:
    prefix = re.match(r'[A-Z]+', current_node_id)
    group = prefix.group() if prefix else ''
    classifier = _GROUP_CLASSIFIERS.get(group)
    if classifier:
        return classifier(text_ru)
    return ClassifyResult(current_node_id, 0.0, 'no classifier for this group')


# Boundary topics that need higher confidence to reclassify
_HIGH_CONF_PAIRS: list[set[str]] = [
    {'FR12', 'FR09'},
    {'FR12', 'FR06'},
    {'FR09', 'FR06'},
    {'FR04', 'FR05'},
    {'AR08', 'AR09'},
    {'AR05', 'AR09'},
    {'AR08', 'AR05'},
    {'AR08', 'AR06'},
    {'AR01', 'AR06'},
    {'AR01', 'WP01'},
    {'AR05', 'WP01'},
    {'AR04', 'AR10'},
    {'WP01', 'WP02'},
    {'WP01', 'WP03'},
    {'WP04', 'WP05'},
    {'GE05', 'GE06'},
    {'GE05', 'GE07'},
    {'GE06', 'GE07'},
    {'GE02', 'GE03'},
    {'GE01', 'GE02'},
    {'GE01', 'GE03'},
    {'GE03', 'GE06'},
    {'GE10', 'GE11'},
    {'EQ04', 'EQ07'},
    {'EQ06', 'EQ07'},
    {'EQ04', 'EQ06'},
    {'EQ01', 'EQ02'},
    {'DV01', 'DV02'},
    {'DV03', 'DV04'},
    {'DV05', 'DV06'},
    {'PC02', 'PC05'},
    {'PC03', 'PC05'},
    {'PC04', 'PC05'},
    {'LG01', 'LG02'},
    {'LG06', 'LG07'},
    {'PR02', 'PR03'},
    {'PR04', 'PR05'},
    {'PR05', 'PR06'},
    {'CB02', 'CB03'},
    {'CB02', 'CB04'},
    {'CB03', 'CB04'},
    {'CB05', 'CB06'},
    {'DC01', 'DC04'},
    {'DC03', 'DC05'},
    {'RN01', 'RN02'},
    {'AL01', 'AL02'},
    {'AL03', 'AL04'},
    {'MD01', 'MD02'},
    {'NM01', 'NM02'},
]


def _min_confidence(current: str, predicted: str) -> float:
    pair = {current, predicted}
    if pair in _HIGH_CONF_PAIRS:
        return 0.92
    return 0.80


def validate_problems(problems: list[dict], group_filter: str | None = None) -> list[dict]:
    mismatches = []
    for i, p in enumerate(problems):
        if not isinstance(p, dict):
            continue
        nid = p.get('node_id', '')
        if group_filter and not nid.startswith(group_filter):
            continue
        text = p.get('text_ru', '')
        result = classify(text, nid)
        if result.predicted == nid or result.predicted == 'NONE':
            continue
        if result.confidence >= _min_confidence(nid, result.predicted):
            mismatches.append({
                'idx': i,
                'current': nid,
                'predicted': result.predicted,
                'confidence': result.confidence,
                'reason': result.reason,
                'text': text[:80],
            })
    return mismatches
