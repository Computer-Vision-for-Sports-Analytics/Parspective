"""End-to-end smoke tests that run MediaPipe. Skipped when the model isn't downloaded."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from parspective.config import PoseConfig
from parspective.pose import resolve_model_path

try:
    resolve_model_path(PoseConfig().model)
    HAVE_MODEL = True
except FileNotFoundError:
    HAVE_MODEL = False

pytestmark = [
    pytest.mark.model,
    pytest.mark.skipif(not HAVE_MODEL, reason="run scripts/download_models.py first"),
]

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "putt.mp4"


def _blank_video(path: Path, frames: int = 20) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 30, (320, 240))
    assert writer.isOpened()
    for i in range(frames):
        frame = np.full((240, 320, 3), 40 + i, dtype=np.uint8)
        writer.write(frame)
    writer.release()


def test_video_without_a_person(tmp_path):
    from parspective import analyze

    video = tmp_path / "empty.avi"
    _blank_video(video)
    overlay, csv_path = tmp_path / "overlay.mp4", tmp_path / "landmarks.csv"
    result = analyze(video, overlay_path=overlay, landmarks_csv=csv_path)

    assert result.video.frame_count == 20
    assert result.pose.frames_with_pose == 0
    assert result.strokes == []
    assert result.tempo_summary.stroke_count == 0
    assert overlay.stat().st_size > 0
    assert csv_path.read_text(encoding="utf-8").startswith("frame,timestamp_ms")


@pytest.mark.skipif(not SAMPLE.is_file(), reason="samples/putt.mp4 is git-ignored; local only")
def test_local_sample_putt():
    from parspective import analyze

    result = analyze(SAMPLE, hand="right")
    assert result.pose.detection_rate > 0.9
    assert result.tempo_summary.stroke_count >= 1
    for s in result.strokes:
        assert 1.0 < s.tempo.ratio < 3.5
