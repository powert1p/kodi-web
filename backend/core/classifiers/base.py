"""Shared types for classifiers."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ClassifyResult:
    predicted: str
    confidence: float  # 0.0–1.0
    reason: str
    alternatives: list[str] = field(default_factory=list)
