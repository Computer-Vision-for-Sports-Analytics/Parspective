# results/

`python -m parspective analyze <video>` writes its output here, one folder per video:

```
results/
  putt/
    result.json    # tempo per stroke, consistency summary, phases (schema: analysis/parspective/result.py)
    overlay.mp4    # skeleton + phase label + tempo, H.264
```

Running a video again overwrites its folder. Use `--out-dir`, `--out` or `--overlay` to write somewhere else, and `--no-overlay` to skip the video.

Everything here except this README is **git-ignored**. Overlays are recordings of real people, so share them through the team's private drive, the same as `samples/`.
