"""Tests for metadata reporting and updates."""

from __future__ import annotations

from pathlib import Path

from music21 import converter as m21_converter

from notare.metadata import metadata_summary

DATA_DIR = Path(__file__).parent / "data"


def test_metadata_summary_basic_fields() -> None:
    summary = metadata_summary(source=str(DATA_DIR / "c_scale.musicxml"))
    assert "Title:" in summary
    assert "Composer:" in summary
    assert "Subtitle:" in summary
    assert "Arranger:" in summary
    assert "Number of Parts:" in summary
    assert "Number of Measures:" in summary
    assert "Main Musical Key:" in summary
    assert "Time Signatures:" in summary
    assert "Encoding Software:" in summary
    assert "Rights:" in summary
    assert "Tempos:" in summary


def test_metadata_summary_includes_parts_section() -> None:
    summary = metadata_summary(source=str(DATA_DIR / "c_scale.musicxml"))
    assert "Part 1:" in summary
    assert "- Clefs:" in summary
    assert "- Key Signatures:" in summary



def test_metadata_update_title(tmp_path) -> None:
    source = DATA_DIR / "c_scale.musicxml"
    output = tmp_path / "updated.musicxml"

    metadata_summary(
        source=str(source),
        output=str(output),
        updates={"title": "My New Title"},
    )

    refreshed = m21_converter.parse(str(output))
    assert refreshed.metadata is not None
    assert refreshed.metadata.title == "My New Title"
