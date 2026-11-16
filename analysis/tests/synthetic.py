"""Synthetic putting strokes with known timing, for testing without a model or a video.

The hand trajectory per stroke (positions in shoulder widths, backswing positive):

    address hold -> backswing (half-cosine, ``backswing_ms``) -> optional pause at the top
    -> forward swing (quarter-cosine to impact at ``forward_ms``, then on to the finish)
    -> finish hold -> return to address

The backswing starts and ends at zero speed; the forward swing starts at zero speed and is
fastest at impact, like a real putt.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from parspective.pose import (
    LEFT_SHOULDER,
    LEFT_WRIST,
    NUM_LANDMARKS,
    RIGHT_SHOULDER,
    RIGHT_WRIST,
    PoseSequence,
)

SHOULDER_WIDTH = 0.07  # normalized image units, like a golfer ~3 m from a 1080p phone
X0 = 0.5


@dataclass
class StrokeSpec:
    backswing_ms: float = 900.0
    forward_ms: float = 450.0
    pause_ms: float = 0.0
    amplitude_sw: float = 0.6


@dataclass
class StrokeTruth:
    takeaway_ms: float
    top_ms: float  #: middle of the pause at the top (or the reversal itself)
    impact_ms: float

    @property
    def backswing_ms(self) -> float:
        return self.top_ms - self.takeaway_ms

    @property
    def forward_ms(self) -> float:
        return self.impact_ms - self.top_ms

    @property
    def ratio(self) -> float:
        return self.backswing_ms / self.forward_ms


def stroke_position(
    strokes: list[StrokeSpec],
    lead_ms: float = 800.0,
    hold_ms: float = 500.0,
    return_ms: float = 700.0,
    tail_ms: float = 800.0,
) -> tuple[callable, float, list[StrokeTruth]]:
    """Return (position(t_ms) function, total duration, ground truth per stroke)."""
    segments: list[tuple[float, float, callable]] = []  # (start, end, f(local_t))
    truths = []
    t = 0.0

    def add(duration, f):
        nonlocal t
        segments.append((t, t + duration, f))
        t += duration

    add(lead_ms, lambda u: 0.0)
    for s in strokes:
        a, b, f, p = s.amplitude_sw, s.backswing_ms, s.forward_ms, s.pause_ms
        takeaway = t
        add(b, lambda u, a=a, b=b: a * (1 - np.cos(np.pi * u / b)) / 2)
        top = t + p / 2
        if p:
            add(p, lambda u, a=a: a)
        add(2 * f, lambda u, a=a, f=f: a * np.cos(np.pi * u / (2 * f)))
        truths.append(StrokeTruth(takeaway, top, top + p / 2 + f))
        add(hold_ms, lambda u, a=a: -a)
        add(return_ms, lambda u, a=a, r=return_ms: -a * (1 + np.cos(np.pi * u / r)) / 2)
        add(hold_ms, lambda u: 0.0)
    add(tail_ms, lambda u: 0.0)

    def position(times):
        out = np.zeros_like(times, dtype=float)
        for start, end, fn in segments:
            mask = (times >= start) & (times < end)
            out[mask] = [fn(x - start) for x in times[mask]]
        return out

    return position, t, truths


def make_sequence(
    strokes: list[StrokeSpec],
    fps: float = 60.0,
    hand: str = "right",
    noise_sw: float = 0.0,
    seed: int = 0,
    jitter_ms: float = 0.0,
    **timing,
) -> tuple[PoseSequence, list[StrokeTruth]]:
    """Fake MediaPipe output for the given strokes, sampled at ``fps``."""
    position, duration, truths = stroke_position(strokes, **timing)
    rng = np.random.default_rng(seed)
    ts = np.arange(0.0, duration, 1000.0 / fps)
    if jitter_ms:
        ts = np.sort(ts + rng.uniform(-jitter_ms, jitter_ms, len(ts)))
        ts -= ts[0]
    d = position(ts) + rng.normal(0.0, noise_sw, len(ts))
    sign = -1.0 if hand == "right" else 1.0  # right-handed backswing moves image-left
    x_hands = X0 + sign * d * SHOULDER_WIDTH

    lms = np.zeros((len(ts), NUM_LANDMARKS, 4))
    lms[:, :, 1] = 0.5
    lms[:, :, 3] = 0.95
    lms[:, :, 0] = X0
    lms[:, LEFT_SHOULDER, 0] = X0 + SHOULDER_WIDTH / 2
    lms[:, RIGHT_SHOULDER, 0] = X0 - SHOULDER_WIDTH / 2
    lms[:, LEFT_WRIST, 0] = x_hands + 0.005
    lms[:, RIGHT_WRIST, 0] = x_hands - 0.005
    seq = PoseSequence(
        timestamps_ms=ts, landmarks=lms, fps=fps, width=1920, height=1080, model="synthetic"
    )
    return seq, truths
