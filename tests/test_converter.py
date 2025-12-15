"""Tests for the converter helpers."""

from __future__ import annotations

from pathlib import Path
import io
import shutil

import pytest
from music21 import converter as m21_converter

from notare.converter import convert_score, list_output_formats

DATA_DIR = Path(__file__).parent / "data"
HAS_LILYPOND = shutil.which("lilypond") is not None


def _assert_c_scale(score_path: Path) -> None:
    """Parse the score and assert it contains the expected C scale."""
    score = m21_converter.parse(str(score_path))
    notes = list(score.recurse().notes)
    assert len(notes) == 8
    assert notes[0].pitch.step == "C"
    assert notes[-1].pitch.step == "C"


def test_list_output_formats_includes_musicxml_and_midi() -> None:
    formats = list_output_formats()
    assert isinstance(formats, list)
    assert formats, "Format list should not be empty"
    assert "musicxml" in formats
    assert "midi" in formats


@pytest.mark.parametrize(
    "filename",
    [
        "c_scale.musicxml",
        "c_scale_basic.musicxml",
        "c_scale.abc"
    ],
)
def test_convert_preserves_c_scale(filename: str, tmp_path) -> None:
    source = DATA_DIR / filename
    assert source.exists(), f"Missing fixture {filename}"

    _assert_c_scale(source)

    output_path = tmp_path / f"{source.stem}_out.musicxml"
    convert_score(source=str(source), target_format="musicxml", output=str(output_path))

    assert output_path.exists()
    _assert_c_scale(output_path)


def test_convert_supports_stdin_and_stdout() -> None:
    source_bytes = (DATA_DIR / "c_scale.abc").read_bytes()
    buffer = io.BytesIO()

    convert_score(
        target_format="musicxml",
        stdin_data=source_bytes,
        stdout_buffer=buffer,
    )

    score = m21_converter.parseData(buffer.getvalue())
    notes = list(score.recurse().notes)
    assert notes[0].pitch.step == "C"
    assert notes[-1].pitch.step == "C"
