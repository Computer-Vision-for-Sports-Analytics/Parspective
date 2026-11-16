"""Result JSON schema (version ``SCHEMA_VERSION``).

This is the contract between the analysis core, the server and the mobile app.
Bump ``parspective.SCHEMA_VERSION`` on any breaking change.

Adding a metric: add an optional field to ``Stroke`` (per-stroke value) and/or to
``AnalysisResult`` (whole-video summary), compute it in ``metrics.py`` and fill it in
``pipeline.analyze_pose``. Optional fields with a default are not a breaking change.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PhaseEvent(BaseModel):
    frame: int = Field(description="Nearest video frame index (0-based).")
    time_ms: float = Field(description="Interpolated time from the start of the video.")


class StrokePhasesOut(BaseModel):
    address: PhaseEvent
    takeaway: PhaseEvent
    top: PhaseEvent
    impact: PhaseEvent
    finish: PhaseEvent | None = None


class Stroke(BaseModel):
    index: int = Field(description="1-based stroke number within the video.")
    phases: StrokePhasesOut
    backswing_length_sw: float = Field(description="Address -> top, in shoulder widths.")


class VideoInfo(BaseModel):
    filename: str
    frame_count: int
    duration_ms: float
    fps: float = Field(description="Nominal frame rate reported by the container.")
    frame_interval_ms: float | None = Field(None, description="Median time between frames.")
    width: int
    height: int


class PoseInfo(BaseModel):
    model: str
    frames_with_pose: int
    detection_rate: float


class AnalysisResult(BaseModel):
    schema_version: str
    analysis_version: str
    config_version: int
    provisional: bool = Field(
        True, description="All metric definitions are team assumptions pending SAS (SP 01)."
    )
    hand: Literal["right", "left"]
    video: VideoInfo
    pose: PoseInfo
    strokes: list[Stroke]
    warnings: list[str]
