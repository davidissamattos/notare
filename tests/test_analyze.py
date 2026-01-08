"""Tests for the analyze module."""

from __future__ import annotations

from pathlib import Path

from notare.analyze import analyze_score
from notare.extract import extract_sections

DATA_DIR = Path(__file__).parent / "data"


def test_analyze_key_npvi_and_miv() -> None:
    result = analyze_score(
        source=str(DATA_DIR / "c_scale.musicxml"),
        metrics=["key", "npvi", "miv"],
    )
    assert "Key:" in result
    assert "nPVI:" in result
    assert "MIV:" in result


def test_analyze_subset_via_extract(tmp_path) -> None:
    subset = tmp_path / "subset.musicxml"
    extract_sections(
        source=str(DATA_DIR / "c_scale.musicxml"),
        output=str(subset),
        measures="1-1",
    )
    result = analyze_score(source=str(subset), metrics=["key"])
    assert "Key:" in result


def test_analyze_performance_and_difficulty() -> None:
    result = analyze_score(
        source=str(DATA_DIR / "c_scale.musicxml"),
        metrics=["pitch_range", "difficulty_categories"],
    )
    assert "Pitch Range:" in result
    assert "Difficulty Categories:" in result
