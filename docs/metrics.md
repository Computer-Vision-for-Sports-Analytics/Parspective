# Metric definitions

> **Status: every metric is PROVISIONAL.** We don't have the original Parspective formulas yet (spike SP 01). These are definitions the student team chose so the pipeline can be built and tested. They are **assumptions**, not descriptions of how Parspective works. All formulas live in [`analysis/parspective/metrics.py`](../analysis/parspective/metrics.py), and all thresholds live in [`analysis/config/metrics.yaml`](../analysis/config/metrics.yaml).

## Camera assumptions
- One phone, fixed, **face-on view**: the camera faces the golfer's chest, perpendicular to the target line, with the whole body and putter in frame.
- In this view, the target line runs horizontally across the image. For a right-handed golfer, the target is to the **image right**, the lead (left) shoulder appears on the image right, and the backswing moves the hands toward the image left.
- MediaPipe tracks the **body only**. The **wrist midpoint stands in for the putter** (a proxy).

## Coordinate conventions
- MediaPipe landmarks are normalized image coordinates: `x` from 0 (left edge) to 1 (right edge), `y` from 0 (top) to 1 (bottom).
- **Hand position** = horizontal position of the wrist midpoint (landmarks 15 and 16). Both wrists must have visibility of at least `signal.min_visibility`, otherwise that frame counts as missing.
- Distances are in **shoulder widths (sw)**: they're divided by the median horizontal distance between the shoulders (landmarks 11 and 12) over the whole clip. This makes thresholds independent of camera distance. A per-frame width isn't used because the apparent shoulder width changes as the shoulders rock.
- The signal is **signed so the backswing is positive** for both hands (right-handed: hands moving image-left = positive).
- **Time** comes from the video container's per-frame timestamps, not `frame / fps`, because phone video is often variable-frame-rate. The signal is resampled to an even grid at the median frame interval, then smoothed with a Savitzky–Golay filter (`signal.smoothing_window_ms`). Velocity is the filter's derivative, in sw/s.

## Metrics

| Metric | User story | Units | View needed | Status |
|--------|-----------|-------|-------------|--------|
| Stroke phases | foundation | frame index, ms | face-on | provisional |
| Shoulder tilt | US 05 | degrees | face-on | provisional |
| Tempo | US 06 | ratio, ms | any (face-on used) | provisional |
| Stroke length ratio | — | ratio (shoulder widths) | face-on | provisional |
| Head movement | Iteration 3 groundwork | shoulder widths | face-on (lateral only) | provisional |
| Combined score | US 04 | 0–100 | — | **placeholder** |

_Shoulder tilt, stroke length ratio, head movement and the combined score are defined in later phases._

### Stroke phases
Code: [`analysis/parspective/phases.py`](../analysis/parspective/phases.py). A video can contain several strokes; each one is detected separately. Every speed threshold is a fraction of **that stroke's own peak speed**, so the rules work for short and long putts.

| Event | Definition | Config key |
|-------|-----------|------------|
| Candidate stroke | A peak in hand position (backswing direction) with prominence ≥ 0.2 sw. Smaller motions (waggles) are ignored. | `phases.min_backswing_length_sw` |
| Takeaway | Walking back from the top: the moment speed first falls below 10% of peak backswing speed. | `phases.takeaway_velocity_fraction` |
| Address | Start of the still period before takeaway. The address *position* is the median hand position over the 300 ms before takeaway. | `phases.address_window_ms` |
| Top | Midpoint between the backswing stopping (speed < 20% of peak backswing speed) and the forward swing starting (speed > 20% of peak forward speed). | `phases.top_velocity_fraction` |
| Impact | The hands return to the address position during the forward swing. **Proxy**: no ball or putter tracking yet (open question Q3). | — |
| Finish | After impact, speed drops below 10% of peak forward speed. | `phases.finish_velocity_fraction` |

All event times are **interpolated between frames** (linear interpolation of the threshold crossing). At 30 fps a frame is 33 ms, which is about 7% of a typical forward swing, so whole-frame events would be too coarse.

**Why the top is a midpoint.** Many golfers pause briefly at the top. During a pause the furthest-back frame is essentially random: on the sample video, the MediaPipe *lite* and *full* models picked frames 200 ms apart for the same stroke, which moved the tempo ratio from 2.3 to 1.4. The midpoint of the pause is stable. On a smooth 2:1 stroke with no pause it lands exactly on the reversal.

A stroke is **rejected with a warning** (not silently dropped) if: it starts before the recording, it never returns to address, its backswing or forward swing is outside the plausible range (`phases.min/max_*_ms`), or the hands were untracked for more than `signal.max_gap_ms` between takeaway and impact.

### Tempo (US 06)
Code: [`analysis/parspective/metrics.py`](../analysis/parspective/metrics.py).

| Field | Definition |
|-------|-----------|
| `backswing_ms` | takeaway → top |
| `forward_swing_ms` | top → impact |
| `total_ms` | takeaway → impact |
| `ratio` | `backswing_ms / forward_swing_ms` (2.0 means 2:1) |
| `transition_ms` | backswing stops → forward swing starts (the pause at the top, plus the slow motion on either side of it) |
| `rating` | `in_range` if `ratio` is within `tempo.target_ratio ± tempo.target_tolerance` (2.0 ± 0.2), otherwise `low` (backswing quick relative to the forward swing) or `high` |

**Consistency** (`tempo_summary`), across all strokes in one video: mean, sample SD, min and max of each field. With 2 or more strokes, the verdict is `consistent` if the ratio's SD is ≤ `tempo.consistency_max_ratio_sd` (0.15), else `variable`. With one stroke there's no verdict, and the user is told to record several strokes in a row.

**Known biases and accuracy** (from `analysis/tests/test_phases.py` and the sample video):
- The 10% takeaway threshold starts the clock slightly after the hands first move: about 3% of the backswing on a smooth stroke. This lowers the ratio by about 0.06 at 2:1. The bias is the same for every stroke, so it doesn't affect consistency, but it does matter when comparing with Parspective (SP 02).
- On synthetic strokes with realistic landmark noise, the ratio error averages about 0.07.
- On the sample video (29.5 fps), the lite and full models give ratios that differ by about 0.04 on average and by up to 0.1 on a single stroke. Treat differences between strokes smaller than about 0.1 as noise. **Record at 60 fps or more** where possible. Below `tempo.low_fps_warning` (50 fps) the result carries a warning.

## What the face-on view cannot measure well
_(Expanded in Phase 6, `docs/limitations.md`.)_
- True putter path in depth (inside/outside the target line). That needs a down-the-line view.
- Putter face angle and wrist rotation (the face isn't visible; MediaPipe has no putter).
- Forward/backward (depth) sway. One camera can't measure depth reliably.
