"""Phase detection and tempo against synthetic strokes with known timing."""

import numpy as np
import pytest
from synthetic import StrokeSpec, make_sequence

from parspective.config import AnalysisConfig
from parspective.phases import detect_strokes
from parspective.pipeline import analyze_pose
from parspective.trajectory import build_trajectory

CFG = AnalysisConfig()


def detect(seq, hand="right", config=CFG):
    traj = build_trajectory(seq.timestamps_ms, seq.landmarks, hand, config.signal)
    assert traj is not None
    return detect_strokes(traj, config.phases)


@pytest.mark.parametrize("fps", [30, 60, 120])
def test_single_two_to_one_stroke(fps):
    seq, (truth,) = make_sequence([StrokeSpec(900, 450)], fps=fps)
    (s,) = detect(seq).strokes
    # Takeaway is the 10%-of-peak-speed onset, which is ~3% of the backswing after true
    # motion onset on this smooth profile; top and impact should be close to exact.
    assert s.takeaway_ms == pytest.approx(truth.takeaway_ms, abs=60)
    assert s.top_ms == pytest.approx(truth.top_ms, abs=25)
    assert s.impact_ms == pytest.approx(truth.impact_ms, abs=10)
    assert s.backswing_ms / s.forward_swing_ms == pytest.approx(2.0, abs=0.15)
    assert s.finish_ms is not None and s.finish_ms > s.impact_ms


def test_pause_at_top_is_split_evenly_and_reported():
    paused, (truth,) = make_sequence([StrokeSpec(800, 450, pause_ms=250)], fps=60)
    smooth, _ = make_sequence([StrokeSpec(800, 450)], fps=60)
    (s,) = detect(paused).strokes
    (s0,) = detect(smooth).strokes
    assert s.top_ms == pytest.approx(truth.top_ms, abs=25)
    # transition_ms also includes the slow (<20% speed) motion either side of the top, so
    # compare with the same stroke without a pause.
    assert s.transition_ms - s0.transition_ms == pytest.approx(250, abs=30)


def test_several_strokes_are_all_found_in_order():
    specs = [StrokeSpec(900, 450), StrokeSpec(800, 500, 150), StrokeSpec(1000, 400, 50)]
    seq, truths = make_sequence(specs, fps=60)
    strokes = detect(seq).strokes
    assert len(strokes) == 3
    for s, t in zip(strokes, truths, strict=True):
        assert s.backswing_ms / s.forward_swing_ms == pytest.approx(t.ratio, abs=0.15)
        assert s.impact_ms == pytest.approx(t.impact_ms, abs=10)


def test_left_handed_mirror_gives_same_timing():
    specs = [StrokeSpec(900, 450), StrokeSpec(750, 400)]
    right, _ = make_sequence(specs, fps=60, hand="right")
    left, _ = make_sequence(specs, fps=60, hand="left")
    r, lft = detect(right, "right").strokes, detect(left, "left").strokes
    assert len(r) == len(lft) == 2
    for a, b in zip(r, lft, strict=True):
        assert a.top_ms == pytest.approx(b.top_ms, abs=1e-6)
        assert a.impact_ms == pytest.approx(b.impact_ms, abs=1e-6)


def test_wrong_handedness_finds_no_backswing_first():
    # Mirrored, a right-hander's follow-through looks like a backswing that never returns
    # to address in the right way. The key thing is no crash and no confident nonsense.
    seq, _ = make_sequence([StrokeSpec(900, 450)], fps=60)
    strokes = detect(seq, "left").strokes
    for s in strokes:
        assert s.backswing_ms > 0 and s.forward_swing_ms > 0


@pytest.mark.parametrize("seed", range(5))
def test_robust_to_landmark_noise(seed):
    specs = [StrokeSpec(900, 450), StrokeSpec(800, 520)]
    seq, truths = make_sequence(specs, fps=60, noise_sw=0.01, seed=seed)
    strokes = detect(seq).strokes
    assert len(strokes) == 2
    for s, t in zip(strokes, truths, strict=True):
        assert s.backswing_ms / s.forward_swing_ms == pytest.approx(t.ratio, abs=0.25)


def test_variable_frame_rate_timestamps():
    seq, (truth,) = make_sequence([StrokeSpec(900, 450)], fps=30, jitter_ms=6)
    (s,) = detect(seq).strokes
    assert s.backswing_ms / s.forward_swing_ms == pytest.approx(2.0, abs=0.2)


def test_no_motion_means_no_strokes():
    seq, _ = make_sequence([], fps=30)
    result = detect(seq)
    assert result.strokes == []


def test_small_waggle_is_ignored():
    seq, _ = make_sequence([StrokeSpec(400, 300, amplitude_sw=0.1)], fps=60)
    assert detect(seq).strokes == []


def test_stroke_cut_off_before_impact_is_skipped_with_warning():
    seq, _ = make_sequence([StrokeSpec(900, 450)], fps=60)
    cut = seq.timestamps_ms < 800 + 900 + 400  # ends 50 ms before impact
    seq.timestamps_ms, seq.landmarks = seq.timestamps_ms[cut], seq.landmarks[cut]
    result = detect(seq)
    assert result.strokes == []
    assert any("never return to address" in w for w in result.warnings)


def test_short_tracking_gap_is_interpolated():
    seq, (truth,) = make_sequence([StrokeSpec(900, 450)], fps=60)
    gap = (seq.timestamps_ms > 1200) & (seq.timestamps_ms < 1300)  # 100 ms mid-backswing
    seq.landmarks[gap] = np.nan
    (s,) = detect(seq).strokes
    assert s.impact_ms == pytest.approx(truth.impact_ms, abs=10)


def test_long_tracking_gap_rejects_the_stroke():
    seq, _ = make_sequence([StrokeSpec(900, 450)], fps=60)
    gap = (seq.timestamps_ms > 1100) & (seq.timestamps_ms < 1500)  # 400 ms mid-backswing
    seq.landmarks[gap] = np.nan
    result = detect(seq)
    assert result.strokes == []
    assert any("not tracked" in w for w in result.warnings)


def test_low_visibility_wrists_count_as_missing():
    seq, _ = make_sequence([StrokeSpec(900, 450)], fps=60)
    seq.landmarks[:, 15, 3] = 0.1  # left wrist never visible
    result = analyze_pose(seq, "right", CFG)
    assert result.strokes == []
    assert any("couldn't be tracked" in w for w in result.warnings)
