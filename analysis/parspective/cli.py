"""Command-line interface: ``python -m parspective analyze putt.mp4 --hand right``."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Annotated

import typer

from .config import load_config
from .result import AnalysisResult

app = typer.Typer(add_completion=False, help="Parspective Mobile: single-camera putting analysis.")


class HandOption(str, Enum):
    right = "right"
    left = "left"


@app.callback()
def _main() -> None:
    """Parspective Mobile: single-camera putting analysis."""


def format_report(result: AnalysisResult) -> str:
    """Human-readable report for the terminal."""
    v = result.video
    lines = [
        f"{v.filename}: {result.hand}-handed, {v.frame_count} frames, "
        f"{v.duration_ms / 1000:.1f} s, {v.fps:.1f} fps "
        f"(pose found in {result.pose.detection_rate:.0%} of frames)",
        "",
        f"{len(result.strokes)} stroke(s) found.",
    ]
    if result.strokes:
        events = ("address", "takeaway", "top", "impact", "finish")
        lines.append(f"{'Stroke':<8}" + "".join(f"{e.capitalize():>10}" for e in events))
        for s in result.strokes:
            times = [getattr(s.phases, e) for e in events]
            cells = "".join(f"{t.time_ms / 1000:>9.2f}s" if t else f"{'-':>10}" for t in times)
            lines.append(f"{s.index:<8}{cells}")
        # Per-stroke metric lines are added here.
    if result.warnings:
        lines.append("")
        lines.extend(f"Warning: {w}" for w in result.warnings)
    return "\n".join(lines)


@app.command()
def analyze(
    video: Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="Putting video.")],
    hand: Annotated[HandOption, typer.Option(help="Golfer's handedness.")] = HandOption.right,
    out_dir: Annotated[
        Path | None,
        typer.Option(help="Folder for result.json and overlay.mp4 [default: results/<video name>]"),
    ] = None,
    out: Annotated[
        Path | None, typer.Option(help="Write the result JSON here instead of OUT_DIR.")
    ] = None,
    overlay: Annotated[
        Path | None, typer.Option(help="Write the overlay MP4 here instead of OUT_DIR.")
    ] = None,
    no_overlay: Annotated[
        bool, typer.Option("--no-overlay", help="Skip the overlay video (faster).")
    ] = False,
    landmarks_csv: Annotated[
        Path | None, typer.Option(help="Write per-frame pose landmarks as CSV here.")
    ] = None,
    config: Annotated[
        Path | None, typer.Option(exists=True, dir_okay=False, help="Alternative metrics.yaml.")
    ] = None,
    model: Annotated[
        Path | None, typer.Option(exists=True, dir_okay=False, help="Explicit .task model file.")
    ] = None,
) -> None:
    """Analyze one putting video: detect strokes and their phases.

    By default the result JSON and overlay video are written to results/<video name>/.
    """
    from .pipeline import analyze as run

    out_dir = out_dir or Path("results") / video.stem
    out = out or out_dir / "result.json"
    overlay = None if no_overlay else (overlay or out_dir / "overlay.mp4")
    for path in (out, overlay):
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)

    result = run(
        video,
        hand=hand.value,
        config=load_config(config),
        overlay_path=overlay,
        landmarks_csv=landmarks_csv,
        model_path=model,
    )
    out.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(format_report(result))
    typer.echo(f"\nResult JSON: {out}")
    if overlay:
        typer.echo(f"Overlay video: {overlay}")


if __name__ == "__main__":
    app()
