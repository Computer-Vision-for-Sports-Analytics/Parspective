"""Pipeline after pose extraction, result schema, config and CLI (no model needed)."""

import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError
from synthetic import StrokeSpec, make_sequence
from typer.testing import CliRunner

import parspective
from parspective.cli import app, format_report
from parspective.config import AnalysisConfig, default_config_path, load_config
from parspective.pipeline import analyze_pose
from parspective.result import AnalysisResult


def test_bundled_yaml_matches_code_defaults():
    # Keeps metrics.yaml and the pydantic defaults from drifting apart.
    assert load_config() == AnalysisConfig()


def test_unknown_config_key_is_rejected(tmp_path):
    data = yaml.safe_load(default_config_path().read_text(encoding="utf-8"))
    data["phases"]["takeaway_velocity_fracton"] = 0.1  # typo
    bad = tmp_path / "metrics.yaml"
    bad.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_config(bad)


def test_result_shape_and_json_round_trip():
    specs = [StrokeSpec(900, 450), StrokeSpec(850, 440), StrokeSpec(920, 450)]
    seq, _ = make_sequence(specs, fps=60)
    result = analyze_pose(seq, "right", filename="synthetic.mp4")

    assert result.schema_version == parspective.SCHEMA_VERSION
    assert result.provisional is True
    assert [s.index for s in result.strokes] == [1, 2, 3]
    for s in result.strokes:
        p = s.phases
        assert p.address.time_ms <= p.takeaway.time_ms < p.top.time_ms < p.impact.time_ms
        assert p.takeaway.frame < p.top.frame < p.impact.frame
        assert s.backswing_length_sw == pytest.approx(0.6, abs=0.05)
    assert result.warnings == []

    data = json.loads(result.model_dump_json())
    assert AnalysisResult.model_validate(data) == result


def test_report_lists_each_stroke():
    seq, _ = make_sequence([StrokeSpec(900, 450), StrokeSpec(700, 500)], fps=60)
    report = format_report(analyze_pose(seq, "right", filename="x.mp4"))
    assert "x.mp4" in report
    assert "2 stroke(s) found" in report
    assert "Takeaway" in report


def _fake_run(calls):
    seq, _ = make_sequence([StrokeSpec(900, 450)], fps=60)

    def run(video, **kwargs):
        calls.append(kwargs)
        return analyze_pose(seq, "right", filename=video.name)

    return run


def test_cli_writes_to_results_folder_by_default(tmp_path, monkeypatch):
    video = tmp_path / "alex_right_01.mp4"
    video.write_bytes(b"")
    calls = []
    monkeypatch.setattr("parspective.pipeline.analyze", _fake_run(calls))
    monkeypatch.chdir(tmp_path)

    out = CliRunner().invoke(app, ["analyze", str(video)])

    assert out.exit_code == 0, out.output
    folder = tmp_path / "results" / "alex_right_01"
    assert AnalysisResult.model_validate_json((folder / "result.json").read_text()).strokes
    assert calls[0]["overlay_path"] == Path("results") / "alex_right_01" / "overlay.mp4"


def test_cli_no_overlay_and_custom_out_dir(tmp_path, monkeypatch):
    video = tmp_path / "putt.mp4"
    video.write_bytes(b"")
    calls = []
    monkeypatch.setattr("parspective.pipeline.analyze", _fake_run(calls))

    out_dir = tmp_path / "elsewhere"
    result = CliRunner().invoke(
        app, ["analyze", str(video), "--out-dir", str(out_dir), "--no-overlay"]
    )

    assert result.exit_code == 0, result.output
    assert (out_dir / "result.json").is_file()
    assert calls[0]["overlay_path"] is None


def test_cli_help_lists_analyze():
    out = CliRunner().invoke(app, ["--help"])
    assert out.exit_code == 0
    assert "analyze" in out.output
