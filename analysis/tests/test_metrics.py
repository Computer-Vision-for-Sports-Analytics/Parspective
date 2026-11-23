import pytest

from parspective.config import TempoConfig
from parspective.metrics import stroke_tempo, tempo_summary
from parspective.phases import StrokePhases

CFG = TempoConfig()


def phases(backswing_ms: float, forward_ms: float, transition_ms: float = 0.0) -> StrokePhases:
    return StrokePhases(
        address_ms=0,
        takeaway_ms=500,
        top_ms=500 + backswing_ms,
        impact_ms=500 + backswing_ms + forward_ms,
        finish_ms=None,
        transition_ms=transition_ms,
        address_position_sw=0,
        backswing_length_sw=0.6,
    )


def test_tempo_fields():
    t = stroke_tempo(phases(900, 450, 120), CFG)
    assert t.backswing_ms == 900
    assert t.forward_swing_ms == 450
    assert t.total_ms == 1350
    assert t.transition_ms == 120
    assert t.ratio == pytest.approx(2.0)
    assert t.rating == "in_range"


@pytest.mark.parametrize(
    ("back", "fwd", "rating"),
    [(900, 450, "in_range"), (800, 600, "low"), (1000, 400, "high"), (880, 400, "in_range")],
)
def test_rating_against_target_band(back, fwd, rating):
    assert stroke_tempo(phases(back, fwd), CFG).rating == rating


def test_summary_no_strokes():
    s = tempo_summary([], CFG)
    assert s.stroke_count == 0 and s.ratio is None and s.consistency is None


def test_summary_single_stroke_has_no_consistency_verdict():
    s = tempo_summary([stroke_tempo(phases(900, 450), CFG)], CFG)
    assert s.stroke_count == 1
    assert s.ratio.sd is None
    assert s.consistency is None
    assert "several strokes" in s.message


def test_summary_consistent():
    tempos = [stroke_tempo(phases(b, f), CFG) for b, f in [(900, 450), (880, 450), (920, 455)]]
    s = tempo_summary(tempos, CFG)
    assert s.consistency == "consistent"
    assert s.ratio.mean == pytest.approx(2.0, abs=0.05)
    assert s.ratio.sd <= CFG.consistency_max_ratio_sd


def test_summary_variable():
    tempos = [stroke_tempo(phases(b, f), CFG) for b, f in [(900, 450), (700, 520), (1000, 380)]]
    s = tempo_summary(tempos, CFG)
    assert s.consistency == "variable"
    assert s.ratio.min < 1.5 < 2.5 < s.ratio.max
