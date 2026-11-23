"""Result JSON schema (version ``SCHEMA_VERSION``).

This is the contract between the analysis core, the server and the mobile app.
Bump ``parspective.SCHEMA_VERSION`` on any breaking change.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TempoRating = Literal["in_range", "low", "high"]
ConsistencyRating = Literal["consistent", "variable"]


class PhaseEvent(BaseModel):
    frame: int = Field(description="Nearest video frame index (0-based).")
    time_ms: float = Field(description="Interpolated time from the start of the video.")


class StrokePhasesOut(BaseModel):
    address: PhaseEvent
    takeaway: PhaseEvent
    top: PhaseEvent
    impact: PhaseEvent
    finish: PhaseEvent | None = None


class Tempo(BaseModel):
    backswing_ms: float = Field(description="Takeaway -> top.")
    forward_swing_ms: float = Field(description="Top -> impact.")
    total_ms: float = Field(description="Takeaway -> impact.")
    transition_ms: float = Field(
        description="Pause at the top: backswing stops -> forward swing starts."
    )
    ratio: float = Field(description="backswing_ms / forward_swing_ms (e.g. 2.0 means 2:1).")
    rating: TempoRating
    message: str


class Stroke(BaseModel):
    index: int = Field(description="1-based stroke number within the video.")
    phases: StrokePhasesOut
    backswing_length_sw: float = Field(description="Address -> top, in shoulder widths.")
    tempo: Tempo


class Stat(BaseModel):
    mean: float
    sd: float | None = Field(None, description="Sample standard deviation; null for 1 stroke.")
    min: float
    max: float


class TempoSummary(BaseModel):
    stroke_count: int
    ratio: Stat | None = None
    backswing_ms: Stat | None = None
    forward_swing_ms: Stat | None = None
    total_ms: Stat | None = None
    consistency: ConsistencyRating | None = Field(
        None, description="Needs at least 2 strokes; null otherwise."
    )
    message: str


class TempoTarget(BaseModel):
    ratio: float
    tolerance: float
    consistency_max_ratio_sd: float


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
    tempo_summary: TempoSummary
    tempo_target: TempoTarget
    warnings: list[str]
