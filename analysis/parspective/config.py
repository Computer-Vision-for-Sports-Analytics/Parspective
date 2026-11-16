"""Analysis configuration, loaded from ``metrics.yaml``.

The defaults below mirror ``analysis/config/metrics.yaml``. All of them are provisional
(see ``docs/open-questions.md``).
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class _Section(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PoseConfig(_Section):
    model: Literal["lite", "full", "heavy"] = "full"
    min_pose_detection_confidence: float = Field(0.5, ge=0, le=1)
    min_pose_presence_confidence: float = Field(0.5, ge=0, le=1)
    min_tracking_confidence: float = Field(0.5, ge=0, le=1)


class SignalConfig(_Section):
    min_visibility: float = Field(0.5, ge=0, le=1)
    max_gap_ms: float = Field(200, gt=0)
    smoothing_window_ms: float = Field(250, gt=0)
    smoothing_polyorder: int = Field(2, ge=1, le=5)


class PhasesConfig(_Section):
    min_backswing_length_sw: float = Field(0.2, gt=0)
    takeaway_velocity_fraction: float = Field(0.10, gt=0, lt=1)
    top_velocity_fraction: float = Field(0.20, gt=0, lt=1)
    finish_velocity_fraction: float = Field(0.10, gt=0, lt=1)
    address_window_ms: float = Field(300, gt=0)
    min_backswing_ms: float = Field(200, ge=0)
    max_backswing_ms: float = Field(3000, gt=0)
    min_forward_swing_ms: float = Field(100, ge=0)
    max_forward_swing_ms: float = Field(2000, gt=0)


class AnalysisConfig(_Section):
    config_version: int = 1
    pose: PoseConfig = PoseConfig()
    signal: SignalConfig = SignalConfig()
    phases: PhasesConfig = PhasesConfig()


def default_config_path() -> Path:
    """Path of the bundled ``metrics.yaml``.

    Installed wheels ship it as ``parspective/_default_config/metrics.yaml``; an editable
    install reads ``analysis/config/metrics.yaml`` directly.
    """
    bundled = resources.files("parspective") / "_default_config" / "metrics.yaml"
    if bundled.is_file():
        return Path(str(bundled))
    return Path(__file__).resolve().parents[1] / "config" / "metrics.yaml"


def load_config(path: str | Path | None = None) -> AnalysisConfig:
    """Load a config file (the bundled default when ``path`` is None)."""
    path = Path(path) if path is not None else default_config_path()
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return AnalysisConfig.model_validate(data)
