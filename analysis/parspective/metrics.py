"""Stroke metrics. Iteration 1: tempo (US 06).

Tempo ratio = backswing time (takeaway -> top) / forward-swing time (top -> impact).
A ratio near 2:1 is the commonly taught target. The target, the tolerance band and the
consistency threshold are provisional (open-questions Q4/Q5) and live in metrics.yaml.
"""

from __future__ import annotations

import numpy as np

from .config import TempoConfig
from .phases import StrokePhases
from .result import Stat, Tempo, TempoSummary, TempoTarget


def stroke_tempo(stroke: StrokePhases, config: TempoConfig) -> Tempo:
    backswing, forward = stroke.backswing_ms, stroke.forward_swing_ms
    ratio = backswing / forward
    lo = config.target_ratio - config.target_tolerance
    hi = config.target_ratio + config.target_tolerance
    target = f"target {config.target_ratio:.1f}:1"

    if ratio < lo:
        rating = "low"
        message = (
            f"Tempo {ratio:.1f}:1. The backswing is quick compared with the forward swing "
            f"({target}). Try a slower, smoother takeaway."
        )
    elif ratio > hi:
        rating = "high"
        message = (
            f"Tempo {ratio:.1f}:1. The forward swing is quick compared with the backswing "
            f"({target}). Try not to rush or hit at the ball."
        )
    else:
        rating = "in_range"
        message = f"Tempo {ratio:.1f}:1 is within the {lo:.1f}-{hi:.1f}:1 target band."

    return Tempo(
        backswing_ms=round(backswing, 1),
        forward_swing_ms=round(forward, 1),
        total_ms=round(backswing + forward, 1),
        transition_ms=round(stroke.transition_ms, 1),
        ratio=round(ratio, 3),
        rating=rating,
        message=message,
    )


def _stat(values: list[float], digits: int) -> Stat:
    arr = np.asarray(values, dtype=float)
    sd = round(float(arr.std(ddof=1)), digits) if len(arr) > 1 else None
    return Stat(
        mean=round(float(arr.mean()), digits),
        sd=sd,
        min=round(float(arr.min()), digits),
        max=round(float(arr.max()), digits),
    )


def tempo_summary(tempos: list[Tempo], config: TempoConfig) -> TempoSummary:
    """Consistency across all strokes in the video."""
    n = len(tempos)
    if n == 0:
        return TempoSummary(
            stroke_count=0,
            message="No complete putting stroke was found, so tempo couldn't be measured.",
        )

    ratio = _stat([t.ratio for t in tempos], 3)
    summary = TempoSummary(
        stroke_count=n,
        ratio=ratio,
        backswing_ms=_stat([t.backswing_ms for t in tempos], 1),
        forward_swing_ms=_stat([t.forward_swing_ms for t in tempos], 1),
        total_ms=_stat([t.total_ms for t in tempos], 1),
        message="",
    )
    if n == 1:
        summary.message = (
            "One stroke measured. Record several strokes in a row to see how repeatable "
            "your tempo is."
        )
    elif ratio.sd <= config.consistency_max_ratio_sd:
        summary.consistency = "consistent"
        summary.message = (
            f"Consistent: {n} strokes averaged {ratio.mean:.1f}:1 "
            f"(varied by +/-{ratio.sd:.2f})."
        )
    else:
        summary.consistency = "variable"
        summary.message = (
            f"Variable: {n} strokes ranged from {ratio.min:.1f}:1 to {ratio.max:.1f}:1 "
            f"(+/-{ratio.sd:.2f}). Aim to repeat the same rhythm every stroke."
        )
    return summary


def tempo_target(config: TempoConfig) -> TempoTarget:
    return TempoTarget(
        ratio=config.target_ratio,
        tolerance=config.target_tolerance,
        consistency_max_ratio_sd=config.consistency_max_ratio_sd,
    )
