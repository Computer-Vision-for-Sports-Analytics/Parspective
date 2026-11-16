"""Overlay video: skeleton + stroke phase label (+ per-stroke metrics once added)."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .pose import CONNECTIONS, LEFT_WRIST, RIGHT_WRIST, PoseSequence
from .result import AnalysisResult, Stroke

# BGR colours
_GREEN = (0, 200, 0)
_RED = (0, 0, 255)
_YELLOW = (0, 220, 255)
_WHITE = (255, 255, 255)
_AMBER = (0, 165, 255)
_PANEL = (32, 32, 32)

_FONT = cv2.FONT_HERSHEY_SIMPLEX


def _phase_label(stroke: Stroke, t_ms: float) -> str | None:
    p = stroke.phases
    if p.takeaway.time_ms <= t_ms < p.top.time_ms:
        return "Backswing"
    if p.top.time_ms <= t_ms < p.impact.time_ms:
        return "Forward swing"
    end = p.finish.time_ms if p.finish else p.impact.time_ms + 300
    if p.impact.time_ms <= t_ms < end:
        return "Follow-through"
    if p.address.time_ms <= t_ms < p.takeaway.time_ms:
        return "Address"
    return None


def _draw_skeleton(frame: np.ndarray, lms: np.ndarray, scale: float) -> None:
    h, w = frame.shape[:2]
    if np.isnan(lms[0, 0]):
        return
    pts = {i: (int(lms[i, 0] * w), int(lms[i, 1] * h)) for i in range(11, 29)}
    thick = max(2, int(4 * scale))
    for a, b in CONNECTIONS:
        cv2.line(frame, pts[a], pts[b], _GREEN, thick, cv2.LINE_AA)
    for pt in pts.values():
        cv2.circle(frame, pt, max(3, int(7 * scale)), _RED, -1, cv2.LINE_AA)
    mid = (
        (pts[LEFT_WRIST][0] + pts[RIGHT_WRIST][0]) // 2,
        (pts[LEFT_WRIST][1] + pts[RIGHT_WRIST][1]) // 2,
    )
    cv2.circle(frame, mid, max(4, int(9 * scale)), _YELLOW, -1, cv2.LINE_AA)


def _draw_panel(frame: np.ndarray, lines: list[tuple[str, tuple]], scale: float) -> None:
    if not lines:
        return
    fs, th = 0.9 * scale, max(1, int(2 * scale))
    pad, gap = int(14 * scale), int(12 * scale)
    sizes = [cv2.getTextSize(text, _FONT, fs, th)[0] for text, _ in lines]
    line_h = max(s[1] for s in sizes) + gap
    w = max(s[0] for s in sizes) + 2 * pad
    h = line_h * len(lines) + pad
    overlay = frame.copy()
    cv2.rectangle(overlay, (pad, pad), (pad + w, pad + h), _PANEL, -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, dst=frame)
    y = pad + line_h
    for text, colour in lines:
        cv2.putText(frame, text, (2 * pad, y), _FONT, fs, colour, th, cv2.LINE_AA)
        y += line_h


def _hud_lines(result: AnalysisResult, t_ms: float) -> list[tuple[str, tuple]]:
    lines: list[tuple[str, tuple]] = []
    for s in result.strokes:
        label = _phase_label(s, t_ms)
        if label:
            lines.append((f"Stroke {s.index}: {label}", _WHITE))
    # Per-stroke metric lines (shown after each stroke's impact) are added here.
    return lines


def render_overlay(
    video_path: str | Path,
    seq: PoseSequence,
    result: AnalysisResult,
    out_path: str | Path,
) -> None:
    """Re-decode the video and write an H.264 MP4 with skeleton and phase annotations."""
    import imageio_ffmpeg

    video = cv2.VideoCapture(str(video_path))
    if not video.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    writer = None
    try:
        idx = 0
        while True:
            ok, frame = video.read()
            if not ok:
                break
            if writer is None:
                h, w = frame.shape[:2]
                writer = imageio_ffmpeg.write_frames(
                    str(out_path),
                    (w, h),
                    pix_fmt_in="bgr24",
                    pix_fmt_out="yuv420p",
                    fps=seq.fps,
                    codec="libx264",
                    macro_block_size=2,
                    output_params=["-movflags", "+faststart"],
                )
                writer.send(None)  # start the generator
            scale = frame.shape[0] / 1080
            if idx < seq.frame_count:
                _draw_skeleton(frame, seq.landmarks[idx], scale)
                _draw_panel(frame, _hud_lines(result, float(seq.timestamps_ms[idx])), scale)
            writer.send(np.ascontiguousarray(frame))
            idx += 1
    finally:
        video.release()
        if writer is not None:
            writer.close()
