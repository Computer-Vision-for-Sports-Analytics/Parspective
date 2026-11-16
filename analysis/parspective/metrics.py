"""Stroke metrics.

Each metric is a small pure function computed per stroke from the detected phases
(``phases.StrokePhases``: event times in ms) and, where needed, the pose landmarks
(``pose.PoseSequence``) or the hand trajectory (``trajectory.HandTrajectory``).

Conventions (see docs/metrics.md):

* Distances in shoulder widths, angles in degrees, times in ms.
* Thresholds and targets go in ``config/metrics.yaml`` under their own section, with a
  matching pydantic model in ``config.py``. Never hard-code them here.
* To look up landmarks at a phase event, map its time to the nearest frame, e.g.
  ``frame = int(np.argmin(np.abs(seq.timestamps_ms - stroke.top_ms)))``.
* Wire the metric into ``pipeline.analyze_pose`` and the result schema in ``result.py``.
* Test it on synthetic strokes (``tests/synthetic.py``), which have known timing.
"""
