"""ALG (Algebra General) classifier — ALG01 only."""
from __future__ import annotations
from .base import ClassifyResult

def classify_alg(text: str) -> ClassifyResult:
    return ClassifyResult('ALG01', 0.90, 'single topic block')
