"""End-to-end pipeline: video -> pose -> trajectory -> phases -> metrics -> result."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from . import SCHEMA_VERSION, __version__
from .config import AnalysisConfig, load_config
from .metrics import stroke_tempo, tempo_summary, tempo_target
from .phases import StrokePhases, detect_strokes
from .pose import PoseSequence
from .result import (
    AnalysisResult,
    PhaseEvent,
    PoseInfo,
    Stroke,
    StrokePhasesOut,
    VideoInfo,
)
from .trajectory import Hand, build_trajectory


def _event(timestamps_ms: np.ndarray, time_ms: float) -> PhaseEvent:
    frame = int(np.argmin(np.abs(timestamps_ms - time_ms)))
    return PhaseEvent(frame=frame, time_ms=round(time_ms, 1))


def _phases_out(ts: np.ndarray, s: StrokePhases) -> StrokePhasesOut:
    return StrokePhasesOut(
        address=_event(ts, s.address_ms),
        takeaway=_event(ts, s.takeaway_ms),
        top=_event(ts, s.top_ms),
        impact=_event(ts, s.impact_ms),
        finish=_event(ts, s.finish_ms) if s.finish_ms is not None else None,
    )


def analyze_pose(
    seq: PoseSequence,
    hand: Hand = "right",
    config: AnalysisConfig | None = None,
    filename: str = "",
) -> AnalysisResult:
    """Everything after pose extraction. Pure numpy, so it's testable without MediaPipe."""
    config = config or load_config()
    ts = seq.timestamps_ms
    warnings: list[str] = []

    n_detected = int(seq.detected.sum())
    frame_interval = float(np.median(np.diff(ts))) if len(ts) > 1 else None

    strokes: list[Stroke] = []
    traj = build_trajectory(ts, seq.landmarks, hand, config.signal)
    if traj is None:
        warnings.append(
            "The golfer's hands couldn't be tracked. Make sure the whole body and the putter "
            "are in frame, face-on, with good lighting."
        )
    else:
        detection = detect_strokes(traj, config.phases)
        warnings.extend(detection.warnings)
        for i, s in enumerate(detection.strokes, start=1):
            strokes.append(
                Stroke(
                    index=i,
                    phases=_phases_out(ts, s),
                    backswing_length_sw=round(s.backswing_length_sw, 3),
                    tempo=stroke_tempo(s, config.tempo),
                )
            )

    fps_for_warning = 1000.0 / frame_interval if frame_interval else seq.fps
    if strokes and fps_for_warning < config.tempo.low_fps_warning:
        warnings.append(
            f"The video is about {fps_for_warning:.0f} fps, so each frame is "
            f"{1000 / fps_for_warning:.0f} ms apart. Event times are interpolated between "
            f"frames, but recording at 60 fps or more gives more reliable tempo."
        )

    return AnalysisResult(
        schema_version=SCHEMA_VERSION,
        analysis_version=__version__,
        config_version=config.config_version,
        hand=hand,
        video=VideoInfo(
            filename=filename,
            frame_count=seq.frame_count,
            duration_ms=round(float(ts[-1]), 1) if len(ts) else 0.0,
            fps=round(seq.fps, 3),
            frame_interval_ms=round(frame_interval, 3) if frame_interval else None,
            width=seq.width,
            height=seq.height,
        ),
        pose=PoseInfo(
            model=seq.model,
            frames_with_pose=n_detected,
            detection_rate=round(n_detected / seq.frame_count, 3) if seq.frame_count else 0.0,
        ),
        strokes=strokes,
        tempo_summary=tempo_summary([s.tempo for s in strokes], config.tempo),
        tempo_target=tempo_target(config.tempo),
        warnings=warnings,
    )


def analyze(
    video_path: str | Path,
    hand: Hand = "right",
    config: AnalysisConfig | None = None,
    overlay_path: str | Path | None = None,
    landmarks_csv: str | Path | None = None,
    model_path: str | Path | None = None,
) -> AnalysisResult:
    """Analyze one putting video. Optionally writes an overlay video and a landmark CSV."""
    from .pose import extract_pose, write_landmarks_csv

    config = config or load_config()
    seq = extract_pose(video_path, config.pose, model_path=model_path)
    result = analyze_pose(seq, hand, config, filename=Path(video_path).name)
    if landmarks_csv:
        write_landmarks_csv(seq, landmarks_csv)
    if overlay_path:
        from .overlay import render_overlay

        render_overlay(video_path, seq, result, overlay_path)
    return result
