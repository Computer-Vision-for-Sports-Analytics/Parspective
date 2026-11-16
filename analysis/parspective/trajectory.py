"""Landmarks -> a clean, evenly sampled 1-D hand trajectory along the target line.

Face-on view: the target line runs horizontally across the image, so the horizontal position
of the wrist midpoint (the putter proxy) is the stroke signal. It is expressed in shoulder
widths and signed so the backswing is always positive, whatever the golfer's handedness:

* right-handed: backswing moves the hands toward image-left (x decreasing)
* left-handed: backswing moves the hands toward image-right (x increasing)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy.signal import savgol_filter

from .config import SignalConfig
from .pose import LEFT_SHOULDER, LEFT_WRIST, RIGHT_SHOULDER, RIGHT_WRIST

Hand = Literal["right", "left"]


@dataclass
class HandTrajectory:
    """Hand position (shoulder widths, backswing positive) on a uniform time grid."""

    t_ms: np.ndarray  #: uniform sample times
    position: np.ndarray  #: smoothed position, shoulder widths
    velocity: np.ndarray  #: smoothed velocity, shoulder widths per second
    valid: np.ndarray  #: False where the sample lies inside a gap longer than max_gap_ms
    dt_ms: float  #: grid spacing (the video's median frame interval)
    shoulder_width: float  #: median shoulder width, normalized image units


def hand_signal(
    landmarks: np.ndarray, min_visibility: float
) -> tuple[np.ndarray, np.ndarray, float]:
    """Return (wrist-midpoint x per frame, NaN where unusable; valid mask; shoulder width).

    Both wrists must be visible. With only one, the midpoint would jump by half the
    wrist separation, which looks like hand motion.
    """
    if len(landmarks) == 0:
        return np.empty(0), np.zeros(0, dtype=bool), float("nan")

    lw, rw = landmarks[:, LEFT_WRIST], landmarks[:, RIGHT_WRIST]
    ok = (lw[:, 3] >= min_visibility) & (rw[:, 3] >= min_visibility)  # NaN compares False
    x_mid = np.where(ok, (lw[:, 0] + rw[:, 0]) / 2.0, np.nan)

    widths = np.abs(landmarks[:, LEFT_SHOULDER, 0] - landmarks[:, RIGHT_SHOULDER, 0])
    widths = widths[np.isfinite(widths)]
    shoulder_width = float(np.median(widths)) if len(widths) else float("nan")
    return x_mid, ok, shoulder_width


def _odd_window(window_ms: float, dt_ms: float, polyorder: int) -> int:
    n = max(int(round(window_ms / dt_ms)), polyorder + 2)
    return n if n % 2 == 1 else n + 1


def build_trajectory(
    timestamps_ms: np.ndarray,
    landmarks: np.ndarray,
    hand: Hand,
    config: SignalConfig,
) -> HandTrajectory | None:
    """Clean, resample and smooth the hand signal. Returns None if there's nothing usable."""
    x_mid, ok, shoulder_width = hand_signal(landmarks, config.min_visibility)
    return trajectory_from_x(timestamps_ms, x_mid, ok, shoulder_width, hand, config)


def trajectory_from_x(
    timestamps_ms: np.ndarray,
    x_mid: np.ndarray,
    ok: np.ndarray,
    shoulder_width: float,
    hand: Hand,
    config: SignalConfig,
) -> HandTrajectory | None:
    t = np.asarray(timestamps_ms, dtype=float)
    if ok.sum() < 2 or not np.isfinite(shoulder_width) or shoulder_width <= 1e-6:
        return None

    # Even grid at the video's typical frame interval: phone video is often variable-rate.
    dt_ms = float(np.median(np.diff(t)))
    if dt_ms <= 0:
        return None
    t_u = np.arange(t[0], t[-1] + dt_ms / 2, dt_ms)

    sign = -1.0 if hand == "right" else 1.0
    d_raw = sign * x_mid[ok] / shoulder_width
    t_ok = t[ok]
    d_u = np.interp(t_u, t_ok, d_raw)

    # A grid sample is trustworthy if a real measurement lies within half the max gap.
    idx = np.clip(np.searchsorted(t_ok, t_u), 1, len(t_ok) - 1)
    nearest = np.minimum(np.abs(t_u - t_ok[idx - 1]), np.abs(t_ok[idx] - t_u))
    valid = nearest <= config.max_gap_ms / 2

    window = _odd_window(config.smoothing_window_ms, dt_ms, config.smoothing_polyorder)
    if len(t_u) < window:
        return None
    pos = savgol_filter(d_u, window, config.smoothing_polyorder)
    vel = savgol_filter(d_u, window, config.smoothing_polyorder, deriv=1, delta=dt_ms / 1000)

    return HandTrajectory(
        t_ms=t_u,
        position=pos,
        velocity=vel,
        valid=valid,
        dt_ms=dt_ms,
        shoulder_width=shoulder_width,
    )
