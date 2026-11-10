# Metric definitions

> **Status: every metric is PROVISIONAL.** We don't have the original Parspective formulas yet (spike SP 01). These are definitions the student team chose so the pipeline can be built and tested. They are **assumptions**, not descriptions of how Parspective works. All formulas live in [`analysis/parspective/metrics.py`](../analysis/parspective/metrics.py), and all thresholds live in [`analysis/config/metrics.yaml`](../analysis/config/metrics.yaml).

## Camera assumptions
- One phone, fixed, **face-on view**: the camera faces the golfer's chest, perpendicular to the target line, with the whole body and putter in frame.
- In this view, the target line runs horizontally across the image. For a right-handed golfer, the target is to the **image right**, the lead (left) shoulder appears on the image right, and the backswing moves the hands toward the image left.
- MediaPipe tracks the **body only**. The **wrist midpoint stands in for the putter** (a proxy).

## Coordinate conventions
_(Written in Phase 3.)_

## Metrics

| Metric | User story | Units | View needed | Status |
|--------|-----------|-------|-------------|--------|
| Stroke phases | foundation | frame index, ms | face-on | provisional |
| Shoulder tilt | US 05 | degrees | face-on | provisional |
| Tempo | US 06 | ratio, ms | any (face-on used) | provisional |
| Stroke length ratio | — | ratio (shoulder widths) | face-on | provisional |
| Head movement | Iteration 3 groundwork | shoulder widths | face-on (lateral only) | provisional |
| Combined score | US 04 | 0–100 | — | **placeholder** |

_Detailed definitions and formulas are added in Phase 3._

## What the face-on view cannot measure well
_(Expanded in Phase 6, `docs/limitations.md`.)_
- True putter path in depth (inside/outside the target line). That needs a down-the-line view.
- Putter face angle and wrist rotation (the face isn't visible; MediaPipe has no putter).
- Forward/backward (depth) sway. One camera can't measure depth reliably.
