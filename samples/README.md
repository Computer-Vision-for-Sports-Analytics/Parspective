# samples/

Put test putt videos here for `scripts/benchmark.py` and the end-to-end checks. Use **face-on view**, with the whole body and the putter in frame.

Everything in this folder except this README is **git-ignored** because these videos are recordings of real people. Share them through the team's private drive. Only record people who have agreed to be recorded.

Suggested naming: `<golfer>_<hand>_<n>.mp4`, e.g. `alex_right_01.mp4`. The benchmark reads `_left` / `_right` from the file name to set handedness. The default is right-handed.

For SP 02 (single-camera accuracy), if you have the Parspective reference value for a putt, put it in a sidecar file `<video>.reference.json`. The format is described in [../docs/spikes/SP02-single-camera.md](../docs/spikes/SP02-single-camera.md).
