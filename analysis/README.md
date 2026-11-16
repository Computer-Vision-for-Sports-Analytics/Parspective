# parspective (analysis core)

A platform-independent Python library for single-camera putting analysis. It takes a video file and returns pose landmarks, stroke phases, metrics and a versioned JSON result. It can also render a skeleton overlay video.

There is no web or mobile code in this package, so it can be tested on its own.

```bash
pip install -e ".[dev]"
python ../scripts/download_models.py          # fetches the MediaPipe pose model
python -m parspective analyze putt.mp4 --hand right   # -> results/putt/result.json + overlay.mp4
pytest
```

The command finds every putting stroke in the video and prints its phase times (address, takeaway, top, impact, finish). Options:

| Option | What it does |
|--------|-------------|
| `--hand right\|left` | Golfer's handedness (default `right`) |
| `--out-dir DIR` | Folder for `result.json` and `overlay.mp4` (default `results/<video name>/`) |
| `--out file.json` | Write the result JSON here instead (schema in `parspective/result.py`) |
| `--overlay file.mp4` | Write the H.264 overlay (skeleton, current phase) here instead |
| `--no-overlay` | Skip the overlay video (faster) |
| `--landmarks-csv lm.csv` | Write raw per-frame landmarks |
| `--config my.yaml` | Use a different `metrics.yaml` |

From Python:

```python
from parspective import analyze
result = analyze("putt.mp4", hand="right")
print(len(result.strokes), "strokes")
```

| Module | Role |
|--------|------|
| `pose.py` | Video → MediaPipe landmarks per frame (with real frame timestamps) |
| `trajectory.py` | Landmarks → clean, smoothed hand position along the target line |
| `phases.py` | Hand trajectory → address / takeaway / top / impact / finish per stroke |
| `metrics.py` | Phases + landmarks → per-stroke metrics (shoulder tilt, stroke length, …: to be added) |
| `result.py` | Result JSON schema (pydantic) |
| `pipeline.py` | Wires it together (`analyze`, `analyze_pose`) |
| `overlay.py`, `cli.py` | Overlay video, command line |

Tests in `tests/` use synthetic strokes with known timing (`tests/synthetic.py`), so they don't need a model or a video. Tests marked `model` run MediaPipe and are skipped if the model isn't downloaded.

See [../docs/metrics.md](../docs/metrics.md) for metric definitions. All of them are **provisional**, and all thresholds are in [config/metrics.yaml](config/metrics.yaml).
