"""PUTTR camera: record a putt with your laptop's webcam.

User story: As a PUTTR user, I want to be able to allow the app to access my camera
so that I can record the data from my putt.

Run it from the repo root:
    python analysis/parspective/camera.py

What happens:
  1. It asks you to allow camera access
  2. A preview window opens, stand so your whole body and the putter are in view.
  3. Press SPACE, a 3-second countdown, then it records 6 seconds
  4. The video is saved to samples/my_putt.mp4, ready for pose.py to build the skeleton
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "samples" / "my_putt.mp4"
COUNTDOWN_SECONDS = 3
RECORD_SECONDS = 6
WINDOW_NAME = "PUTTR camera (SPACE = record, Q = quit)"


def ask_permission() -> bool:
    """Ask the user to allow camera access. Returns True if they said yes."""
    answer = input("PUTTR would like to use your camera to record your putt. Allow? [y/n] ")
    return answer.strip().lower() in ("y", "yes")

# Asks for 720p, if the camera can't do it OpenCV uses the closest size it can.
def open_camera(index: int = 0) -> cv2.VideoCapture:
    """Open the webcam. Camera 0 is usually the laptop's built-in one."""
    camera = cv2.VideoCapture(index)
    if not camera.isOpened():
        camera.release()
        raise RuntimeError(
            f"Could not open camera {index}. Things to check:\n"
            "  - Close other apps using the camera (Zoom, Teams, a browser tab).\n"
            "  - Windows: Settings > Privacy & security > Camera > turn on\n"
            "    'Let desktop apps access your camera'.\n"
            "  - Mac: System Settings > Privacy & Security > Camera > turn on your terminal app.\n"
            "  - Try another camera with --camera 1."
        )
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    return camera

# draw on a copy so the text never ends up in the saved video
def show_frame(frame, text: str = "", color=(0, 255, 255)) -> int:
    """Show a frame in the preview window, with optional text. Returns the key pressed."""
    if text:
        frame = frame.copy()
        cv2.putText(frame, text, (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, color, 3)
    cv2.imshow(WINDOW_NAME, frame)
    return cv2.waitKey(1) & 0xFF


def read_frame(camera):
    ok, frame = camera.read()
    if not ok:
        raise RuntimeError("The camera stopped sending video.")
    return frame


def record_putt(
    camera,
    output_path: Path,
    countdown_seconds: float = COUNTDOWN_SECONDS,
    record_seconds: float = RECORD_SECONDS,
    show=show_frame,
) -> Path | None:
    """Preview until SPACE is pressed, count down, then record and save the putt.

    Returns the saved video's path, or None if the user pressed Q.
    """
    # 1) Preview: wait for SPACE.
    while True:
        key = show(read_frame(camera), "Press SPACE to record")
        if key == ord("q"):
            return None
        if key == ord(" "):
            break

    # 2) Countdown. Counts frames here to measure the camera's real frame rate
    start = time.monotonic()
    frames = 0
    while (elapsed := time.monotonic() - start) < countdown_seconds:
        frame = read_frame(camera)
        frames += 1
        if show(frame, f"Get ready... {int(countdown_seconds - elapsed) + 1}") == ord("q"):
            return None
    elapsed = time.monotonic() - start
    fps = frames / elapsed if frames > 1 and elapsed > 0 else 30.0

    # 3) Record.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame = read_frame(camera)
    height, width = frame.shape[:2]
    writer = cv2.VideoWriter(
        str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
    )
    start = time.monotonic()
    try:
        while (elapsed := time.monotonic() - start) < record_seconds:
            writer.write(frame)
            if show(frame, f"REC {elapsed:.1f}s", (0, 0, 255)) == ord("q"):
                break
            frame = read_frame(camera)
    finally:
        writer.release()
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a putt with your webcam.")
    parser.add_argument("--camera", type=int, default=0, help="camera number (default: 0)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT, help="where to save the video")
    args = parser.parse_args()

    if not ask_permission():
        print("Camera access not allowed. Nothing was recorded.")
        return 0

    try:
        camera = open_camera(args.camera)
    except RuntimeError as error:
        print(error)
        return 1

    try:
        saved = record_putt(camera, args.out)
    except RuntimeError as error:
        print(error)
        return 1
    finally:
        camera.release()
        cv2.destroyAllWindows()

    if saved is None:
        print("Quit. Nothing was saved.")
    else:
        print(f"Saved your putt to {saved}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
