# parspective (analysis core)

A platform-independent Python library for single-camera putting analysis. It takes a video file and returns pose landmarks, stroke phases, metrics and a versioned JSON result. It can also render a skeleton overlay video.

There is no web or mobile code in this package, so it can be tested on its own.

```bash
pip install -e ".[dev]"
python ../scripts/download_models.py          # fetches the MediaPipe pose model
python -m parspective analyze putt.mp4 --hand right --out result.json --overlay out.mp4
pytest
```

See [../docs/metrics.md](../docs/metrics.md) for metric definitions. All of them are **provisional**.
