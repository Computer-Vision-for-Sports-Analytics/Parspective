"""Stroke phase segmentation: find every putting stroke in a hand trajectory.

Provisional event definitions (team assumptions; see docs/metrics.md and open-questions Q3).
"Speed" is the hand speed along the target line; each threshold is a fraction of that
stroke's own peak speed, so the rules don't depend on stroke length or camera distance.

* **takeaway**: hand speed first rises above ``takeaway_velocity_fraction`` of the peak
  backswing speed.
* **address**: start of the still period before takeaway. The address *position* is the
  median hand position over ``address_window_ms`` before takeaway.
* **top**: midpoint between the backswing stopping (speed falls below
  ``top_velocity_fraction`` of peak backswing speed) and the forward swing starting (speed
  rises above the same fraction of peak forward speed). Many golfers pause at the top, and
  then the single furthest-back frame is essentially random; the midpoint is stable. The pause
  itself is reported as ``transition_ms``.
* **impact**: the hands return to the address position during the forward swing. There's no
  ball or putter tracking yet, so this stands in for ball contact.
* **finish**: after impact, hand speed drops below ``finish_velocity_fraction`` of the peak
  forward-swing speed (end of the follow-through).

Event times are interpolated between frames: at 30 fps a frame is ~33 ms, which is large
compared with a ~300-500 ms forward swing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.signal import find_peaks

from .config import PhasesConfig
from .trajectory import HandTrajectory


@dataclass
class StrokePhases:
    """Event times (ms from the start of the video) for one stroke."""

    address_ms: float
    takeaway_ms: float
    top_ms: float
    impact_ms: float
    finish_ms: float | None
    transition_ms: float
    address_position_sw: float
    backswing_length_sw: float

    @property
    def backswing_ms(self) -> float:
        return self.top_ms - self.takeaway_ms

    @property
    def forward_swing_ms(self) -> float:
        return self.impact_ms - self.top_ms


@dataclass
class PhaseDetection:
    strokes: list[StrokePhases] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _crossing_ms(t: np.ndarray, y: np.ndarray, i: int, level: float) -> float:
    """Time where y crosses ``level`` between samples i and i+1 (linear interpolation)."""
    y0, y1 = y[i], y[i + 1]
    if y1 == y0:
        return float(t[i])
    frac = float(np.clip((level - y0) / (y1 - y0), 0.0, 1.0))
    return float(t[i] + frac * (t[i + 1] - t[i]))


class _SkipStrokeError(Exception):
    """A peak that doesn't form a complete, plausible stroke."""


def _measure_stroke(
    traj: HandTrajectory, p: int, lo: int, hi: int, config: PhasesConfig
) -> StrokePhases:
    t, pos, vel = traj.t_ms, traj.position, traj.velocity
    n = len(t)

    # --- backswing + takeaway: walk back from the top, tracking the peak backswing speed so
    # far, until speed falls below takeaway_velocity_fraction of it. That stops in the still
    # address period, never in an earlier motion (e.g. the previous stroke's return to
    # address). The stop only counts once we're at least halfway down the backswing, so
    # noise near the (slow) top can't end the walk early. Step over a flat top first.
    run_end = p
    while run_end > lo and vel[run_end] <= 0:
        run_end -= 1
    i_vmax, v_back = run_end, float(vel[run_end])
    frac = config.takeaway_velocity_fraction
    half_way = 0.5 * config.min_backswing_length_sw
    i = run_end
    while i > lo:
        v = vel[i - 1]
        if v > v_back:
            i_vmax, v_back = i - 1, float(v)
        if pos[p] - pos[i - 1] >= half_way and v < frac * v_back:
            break
        i -= 1
    else:
        raise _SkipStrokeError("the backswing starts before the recording")
    if v_back <= 0 or pos[p] - pos[i] < half_way:
        raise _SkipStrokeError("no backswing motion found")
    thresh = frac * v_back
    takeaway_ms = _crossing_ms(t, vel, i - 1, thresh)

    # --- address: still period before takeaway, and the hand position there.
    a = i - 1
    while a > lo and abs(vel[a - 1]) < thresh:
        a -= 1
    window = (t >= takeaway_ms - config.address_window_ms) & (t <= takeaway_ms)
    window[:a] = False
    address_pos = float(np.median(pos[window])) if window.any() else float(pos[i - 1])
    length = float(pos[p] - address_pos)
    if length < config.min_backswing_length_sw:
        raise _SkipStrokeError(f"backswing too short ({length:.2f} shoulder widths)")

    # --- impact: first return to the address position after the peak.
    below = np.flatnonzero(pos[p + 1 : hi] <= address_pos)
    if len(below) == 0:
        raise _SkipStrokeError("the hands never return to address before the video ends")
    j = int(p + 1 + below[0])
    impact_ms = _crossing_ms(t, pos, j - 1, address_pos)

    # --- forward swing: the run of negative velocity through impact (always mid-swing).
    m = j
    while m + 1 < n and vel[m + 1] < 0:
        m += 1
    q0 = j
    while q0 > p and vel[q0 - 1] < 0:
        q0 -= 1
    i_vmin = q0 + int(np.argmin(vel[q0 : m + 1]))
    v_fwd = -vel[i_vmin]

    # --- top: midpoint of [backswing stops, forward swing starts].
    top_thresh = config.top_velocity_fraction
    s = i_vmax
    while s + 1 < n and vel[s + 1] >= top_thresh * v_back:
        s += 1
    back_stop_ms = _crossing_ms(t, vel, s, top_thresh * v_back) if s + 1 < n else float(t[s])
    q = i_vmin
    while q - 1 > 0 and -vel[q - 1] >= top_thresh * v_fwd:
        q -= 1
    fwd_start_ms = _crossing_ms(t, -vel, q - 1, top_thresh * v_fwd)
    if fwd_start_ms < back_stop_ms:  # a sharp reversal: the two crossings can overlap
        back_stop_ms = fwd_start_ms = (back_stop_ms + fwd_start_ms) / 2
    top_ms = (back_stop_ms + fwd_start_ms) / 2
    transition_ms = fwd_start_ms - back_stop_ms

    # --- finish: forward speed decays after its peak (optional).
    f_thresh = config.finish_velocity_fraction * v_fwd
    f = max(i_vmin, j)
    while f + 1 <= m and -vel[f + 1] >= f_thresh:
        f += 1
    finish_ms = _crossing_ms(t, -vel, f, f_thresh) if f + 1 < n else None
    if finish_ms is not None and finish_ms < impact_ms:
        finish_ms = None

    # --- plausibility checks.
    backswing_ms, forward_ms = top_ms - takeaway_ms, impact_ms - top_ms
    problems = []
    if not config.min_backswing_ms <= backswing_ms <= config.max_backswing_ms:
        problems.append(f"backswing {backswing_ms:.0f} ms is outside the plausible range")
    if not config.min_forward_swing_ms <= forward_ms <= config.max_forward_swing_ms:
        problems.append(f"forward swing {forward_ms:.0f} ms is outside the plausible range")
    if not traj.valid[i - 1 : j + 1].all():
        problems.append("the hands were not tracked for part of the stroke")
    if problems:
        raise _SkipStrokeError("; ".join(problems))

    return StrokePhases(
        address_ms=float(t[a]),
        takeaway_ms=takeaway_ms,
        top_ms=top_ms,
        impact_ms=impact_ms,
        finish_ms=finish_ms,
        transition_ms=transition_ms,
        address_position_sw=address_pos,
        backswing_length_sw=length,
    )


def detect_strokes(traj: HandTrajectory, config: PhasesConfig) -> PhaseDetection:
    """Find every complete stroke (address -> takeaway -> top -> impact [-> finish])."""
    out = PhaseDetection()
    peaks, _ = find_peaks(traj.position, prominence=config.min_backswing_length_sw)
    for k, p in enumerate(peaks):
        lo = int(peaks[k - 1]) if k > 0 else 0
        hi = int(peaks[k + 1]) if k + 1 < len(peaks) else len(traj.t_ms)
        try:
            out.strokes.append(_measure_stroke(traj, int(p), lo, hi, config))
        except _SkipStrokeError as reason:
            out.warnings.append(
                f"Possible stroke at {traj.t_ms[p] / 1000:.1f} s was skipped: {reason}."
            )
    return out
