# SP 02: Single-camera accuracy

**Question:** Can one phone in face-on view measure each metric well enough to match the multi-camera Parspective reference within an agreed tolerance?

**Owner:** _name_ · **Timebox:** _x days_ · **Status:** Not started

## Method
1. Record putts with a phone in face-on view (setup per the in-app placement guide) **at the same time as** a Parspective capture, if SAS can provide one.
2. Save each video as `samples/<name>.mp4`. Put the reference values in `samples/<name>.reference.json`:
   ```json
   { "shoulder_tilt_change_deg": 1.8, "tempo_ratio": 2.1, "stroke_length_ratio": 0.95 }
   ```
3. Run `python scripts/benchmark.py --csv benchmark-results/sp02.csv`.
4. Fill in the tables below. Tolerances come from [open-questions.md](../open-questions.md) Q4 until SAS confirms them.

## Recording conditions
| Video | Device | Resolution / fps | Distance & height | Lighting | Golfer hand | Notes |
|-------|--------|------------------|-------------------|----------|-------------|-------|
| | | | | | | |

## Results per metric
| Metric | Video | Ours | Parspective ref | Abs. error | Tolerance | Within? |
|--------|-------|------|-----------------|------------|-----------|---------|
| Shoulder tilt change (°) | | | | | ±2° (TBC) | |
| Tempo ratio | | | | | ±0.2 (TBC) | |
| Stroke length ratio | | | | | ±0.15 (TBC) | |
| Head movement (shoulder widths) | | | | | TBC | |

## Summary
| Metric | n putts | Mean abs. error | Max abs. error | % within tolerance | Verdict (Go / No-go / Needs work) |
|--------|---------|-----------------|----------------|--------------------|-----------------------------------|
| Shoulder tilt change | | | | | |
| Tempo ratio | | | | | |
| Stroke length ratio | | | | | |
| Head movement | | | | | |

## Timing (US 16: results in ≤ 15 s)
| Video | Duration | decode | pose | smooth+phases+metrics | overlay | total | ≤ 15 s? |
|-------|----------|--------|------|-----------------------|---------|-------|---------|
| | | | | | | | |

## Conclusion & recommendation
_What can one camera measure reliably? What needs a second view or putter tracking?_
