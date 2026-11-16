"""Pose extraction: video file -> MediaPipe PoseLandmarker landmarks per frame."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .config import PoseConfig

#: MediaPipe landmark indices used by the analysis.
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
LEFT_WRIST, RIGHT_WRIST = 15, 16
NUM_LANDMARKS = 33

#: Pairs of landmarks drawn as the skeleton in the overlay.
CONNECTIONS = [
    (11, 12),  # Shoulders
    (11, 13),  # Left shoulder to elbow
    (13, 15),  # Left elbow to wrist
    (12, 14),  # Right shoulder to elbow
    (14, 16),  # Right elbow to wrist
    (11, 23),  # Left shoulder to hip
    (12, 24),  # Right shoulder to hip
    (23, 24),  # Hips
    (23, 25),  # Left hip to knee
    (25, 27),  # Left knee to ankle
    (24, 26),  # Right hip to knee
    (26, 28),  # Right knee to ankle
]

#: Default model folder (``analysis/models``); ``PARSPECTIVE_MODEL_DIR`` overrides it.
DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[1] / "models"


@dataclass
class PoseSequence:
    """Landmarks for every decoded frame of one video.

    ``landmarks`` has shape ``(n_frames, 33, 4)`` holding normalized ``x, y, z, visibility``.
    Frames where no person was detected are all-NaN.
    """

    timestamps_ms: np.ndarray
    landmarks: np.ndarray
    fps: float
    width: int
    height: int
    model: str

    @property
    def frame_count(self) -> int:
        return len(self.timestamps_ms)

    @property
    def detected(self) -> np.ndarray:
        """Boolean mask of frames where a pose was detected."""
        return ~np.isnan(self.landmarks[:, 0, 0])


def resolve_model_path(variant: str, model_dir: str | Path | None = None) -> Path:
    """Locate ``pose_landmarker_<variant>.task``, or explain how to download it."""
    folder = Path(model_dir or os.environ.get("PARSPECTIVE_MODEL_DIR", DEFAULT_MODEL_DIR))
    path = folder / f"pose_landmarker_{variant}.task"
    if not path.is_file():
        raise FileNotFoundError(
            f"MediaPipe model not found at {path}. "
            f"Run: python scripts/download_models.py {variant}"
        )
    return path


def _frame_timestamps(raw_ms: list[float], fps: float) -> np.ndarray:
    """Use the container's timestamps when they are usable, else derive them from fps.

    Phone videos are often variable-frame-rate, so ``frame_index / fps`` can drift.
    Some OpenCV backends report 0 for every frame, which is why there's a fallback.
    """
    ts = np.asarray(raw_ms, dtype=float)
    if len(ts) > 1 and np.all(np.diff(ts) > 0):
        return ts - ts[0]
    return np.arange(len(ts), dtype=float) * 1000.0 / fps


def extract_pose(
    video_path: str | Path,
    config: PoseConfig | None = None,
    model_path: str | Path | None = None,
) -> PoseSequence:
    """Run MediaPipe PoseLandmarker over every frame of ``video_path``."""
    import mediapipe as mp  # imported lazily: heavy, and not needed by the pure-math modules

    config = config or PoseConfig()
    model_path = Path(model_path) if model_path else resolve_model_path(config.model)

    video = cv2.VideoCapture(str(video_path))
    if not video.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = video.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0 or not np.isfinite(fps):
        fps = 30.0

    options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=config.min_pose_detection_confidence,
        min_pose_presence_confidence=config.min_pose_presence_confidence,
        min_tracking_confidence=config.min_tracking_confidence,
    )

    raw_ts: list[float] = []
    frames: list[np.ndarray] = []
    width = height = 0
    last_mp_ts = -1
    try:
        with mp.tasks.vision.PoseLandmarker.create_from_options(options) as landmarker:
            while True:
                ok, frame = video.read()
                if not ok:
                    break
                height, width = frame.shape[:2]
                ts = video.get(cv2.CAP_PROP_POS_MSEC)
                raw_ts.append(ts)

                # MediaPipe needs strictly increasing integer timestamps. Fall back to the
                # nominal frame time when the backend doesn't report one.
                if ts <= 0 and len(raw_ts) > 1:
                    ts = (len(raw_ts) - 1) * 1000.0 / fps
                mp_ts = max(last_mp_ts + 1, int(round(ts)))
                last_mp_ts = mp_ts

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result = landmarker.detect_for_video(image, mp_ts)

                values = np.full((NUM_LANDMARKS, 4), np.nan)
                if result.pose_landmarks:
                    for i, lm in enumerate(result.pose_landmarks[0]):
                        values[i] = (lm.x, lm.y, lm.z, lm.visibility)
                frames.append(values)
    finally:
        video.release()

    landmarks = np.stack(frames) if frames else np.empty((0, NUM_LANDMARKS, 4))
    return PoseSequence(
        timestamps_ms=_frame_timestamps(raw_ts, fps),
        landmarks=landmarks,
        fps=float(fps),
        width=width,
        height=height,
        model=config.model,
    )


def write_landmarks_csv(seq: PoseSequence, path: str | Path) -> None:
    """Write one row per (frame, landmark), for frames where a pose was detected."""
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["frame", "timestamp_ms", "landmark_id", "x", "y", "z", "visibility"])
        for frame_idx in np.flatnonzero(seq.detected):
            ts = round(float(seq.timestamps_ms[frame_idx]), 3)
            for lm_idx, (x, y, z, vis) in enumerate(seq.landmarks[frame_idx]):
                writer.writerow([int(frame_idx), ts, lm_idx, x, y, z, vis])
