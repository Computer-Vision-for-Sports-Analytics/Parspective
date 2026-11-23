# Program flow: the big picture

How a recorded putting video moves through Parspective Mobile: where it goes, what each stage turns it into, and what that output means. Every metric goes through the same flow; only the metrics step changes from one metric to the next.

Legend: **[built]** is working now · **[planned]** is designed but not built yet · **[prototype]** exists separately and is not connected yet

## 1. The whole system

```
 ┌───────────────────────────────────────────────────────────────────────┐
 │ PHONE   mobile/  (Expo app)                                [planned]  │
 │   Home → Capture (camera guide, countdown, record)                    │
 │        → Processing (upload, wait) → Results (overlay, stats, email)  │
 └───────────────────────────────────────────────────────────────────────┘
        │ video file + handedness                ▲ result JSON + overlay
        ▼                                        │
 ┌───────────────────────────────────────────────────────────────────────┐
 │ SERVER   server/  (FastAPI)                                           │
 │   GET  /health              → is the server up? versions     [built]  │
 │   POST /analyze             → save video, queue a job      [planned]  │
 │   worker thread             → calls parspective.analyze()  [planned]  │
 │   GET  /results/{id}        → phone polls until it's done  [planned]  │
 │   POST /results/{id}/email  → send results (with consent)  [planned]  │
 │   job store on disk         → deleted after 24 h           [planned]  │
 └───────────────────────────────────────────────────────────────────────┘
        │ video path                             ▲ AnalysisResult
        ▼                                        │
 ┌───────────────────────────────────────────────────────────────────────┐
 │ ANALYSIS CORE   analysis/parspective/  (Python library)      [built]  │
 │   video ─► body points ─► hand wave ─► strokes ─► metrics ─► result   │
 │   (detailed in section 2)                                             │
 │                                                                       │
 │   Used today from the command line:                                   │
 │   python -m parspective analyze putt.mp4 --hand right                 │
 └───────────────────────────────────────────────────────────────────────┘
        │
        ▼
 ┌───────────────────────────────────────────────────────────────────────┐
 │ EMAIL SHARE   emailShare/  (Flet screen + Resend API)    [prototype]  │
 │   asks for an email address, checks it, sends the stats JSON and      │
 │   the video. Will become the server's /email route.                   │
 └───────────────────────────────────────────────────────────────────────┘
```

Until the server and app are built, the analysis core is run from the command line, and its output goes to `results/<video name>/`.

## 2. Inside the analysis core

```
 putt.mp4
    │
    ▼
 ┌───────────────────────────────────────────────────────────────────────┐
 │ 0. SETUP           pipeline.analyze()   config.py                     │
 │   loads every threshold from config/metrics.yaml and checks them      │
 │   (a misspelled key is rejected)                                      │
 └───────────────────────────────────────────────────────────────────────┘
    │
    ▼
 ┌───────────────────────────────────────────────────────────────────────┐
 │ 1. POSE EXTRACTION              pose.py  extract_pose()               │
 │   OpenCV decodes each frame → MediaPipe finds 33 body points          │
 │   saves the real timestamp of each frame (phone frame rates vary)     │
 │                                                                       │
 │   BECOMES ► PoseSequence: (x, y, z, visibility) for each point,       │
 │             on every frame                                            │
 │   MEANS   ► "where every joint was, at every moment"                  │
 └───────────────────────────────────────────────────────────────────────┘
    │                                           │
    │                                           └────────────────────┐
    ▼                                                                │
 ┌───────────────────────────────────────────────────────────────┐   │
 │ 2. SIGNAL CLEANUP               trajectory.py                 │   │
 │   wrist midpoint = stand-in for the putter                    │   │
 │   side-to-side position only (along the target line)          │   │
 │   ÷ shoulder width     → camera distance doesn't matter       │   │
 │   sign flip for hand   → backswing is always +                │   │
 │   even time grid, gaps filled, smoothed, velocity worked out  │   │
 │                                                               │   │
 │   BECOMES ► HandTrajectory                                    │   │
 │       ╱╲        ╱╲        ╱╲                                  │   │
 │   ───╯  ╲──────╯  ╲──────╯  ╲───   one hill per stroke        │   │
 │   MEANS   ► "how far the hands are from address, over time"   │   │
 └───────────────────────────────────────────────────────────────┘   │
    │                                                                │
    ▼                                                                │
 ┌───────────────────────────────────────────────────────────────┐   │
 │ 3. STROKE PHASES                phases.py                     │   │
 │   each hill big enough to count = one stroke                  │   │
 │   events: address → takeaway → top → impact → finish (ms)     │   │
 │   implausible strokes are skipped, with a warning             │   │
 │                                                               │   │
 │   BECOMES ► list[StrokePhases]                                │   │
 │   MEANS   ► "when each part of each stroke happened"          │   │
 │             This is the shared timeline every metric uses.    │   │
 └───────────────────────────────────────────────────────────────┘   │
    │                                                                │
    ▼                                                                │
 ┌───────────────────────────────────────────────────────────────┐   │
 │ 4. METRICS                      metrics.py                    │   │
 │   Each metric reads the phase times and, where needed, the    │◄──┘
 │   body points at those moments. Every metric has two parts:   │ body points
 │   • per stroke: value + rating vs. target + coaching message  │ (for angle-
 │   • whole video: mean / SD / min / max, consistency verdict   │  based metrics)
 │   Targets and thresholds live in metrics.yaml, not the code.  │
 │                                                               │
 │   ┌─────────────────────┬──────────┬─────────────────────┐    │
 │   │ Metric              │ Story    │ Status              │    │
 │   ├─────────────────────┼──────────┼─────────────────────┤    │
 │   │ Tempo               │ US 06    │ [built]             │    │
 │   │ Shoulder tilt       │ US 05    │ [planned]           │    │
 │   │ Stroke length ratio │ —        │ [planned]           │    │
 │   │ Head movement       │ Iter. 3  │ [planned]           │    │
 │   │ Combined score      │ US 04    │ [planned] (0–100)   │    │
 │   └─────────────────────┴──────────┴─────────────────────┘    │
 │                                                               │
 │   BECOMES ► one model per metric, e.g. Tempo, TempoSummary    │
 │   MEANS   ► "how good / how repeatable the stroke was"        │
 └───────────────────────────────────────────────────────────────┘
    │
    ▼
 ┌───────────────────────────────────────────────────────────────────────┐
 │ 5. RESULT            pipeline.analyze_pose()  →  result.py            │
 │   AnalysisResult  (the contract with the server and the app)          │
 │    ├─ video       filename, fps, frame count, duration                │
 │    ├─ pose        how often a body was found                          │
 │    ├─ strokes[]   phases + one field per metric, for each stroke      │
 │    ├─ <metric>_summary / <metric>_target   across the whole video     │
 │    └─ warnings    skipped strokes, low fps, ...                       │
 └───────────────────────────────────────────────────────────────────────┘
    │
    ├──────────────────────┬──────────────────────┬───────────────────────┐
    ▼                      ▼                      ▼                       ▼
 ┌────────────────┐ ┌────────────────┐ ┌────────────────────┐ ┌──────────────────┐
 │ TERMINAL       │ │ result.json    │ │ overlay.mp4        │ │ landmarks.csv    │
 │ cli.py         │ │                │ │ overlay.py         │ │ (optional)       │
 │ a table for    │ │ read by the    │ │ decodes the video  │ │ raw body points  │
 │ each stroke    │ │ server and app │ │ again and draws:   │ │ for each frame,  │
 │ + summary      │ │                │ │ skeleton, current  │ │ for debugging    │
 │ + warnings     │ │                │ │ phase, metric      │ │                  │
 │                │ │                │ │ lines after impact │ │                  │
 └────────────────┘ └────────────────┘ └────────────────────┘ └──────────────────┘
```

## 3. The idea in one line

**Video → where the body is → where the hands are → when each stroke happens → how good each stroke is → feedback.**

Stages 1–3 are the same for every metric. A new metric only touches step 4 and the files around it:
1. **Compute it:** write a function in `metrics.py`.
2. **Settings:** add its thresholds to `config/metrics.yaml` and a matching model in `config.py`.
3. **Schema:** add its fields to `result.py`.
4. **Wire it in:** call it in `pipeline.analyze_pose()`.
5. **Show it:** add a line to `cli.py` and `overlay.py`.
6. **Test it:** write tests on synthetic strokes (`tests/synthetic.py`), whose timing is known.

The overlay is the only output that reads the original video a second time. Every other stage works only on the numbers produced by the stage before it.

Metric definitions and known biases: [`docs/metrics.md`](../docs/metrics.md). Planned server and app design: the root [`README.md`](../README.md).
