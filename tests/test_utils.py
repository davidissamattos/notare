"""Tests for utils.load_score normalization behavior."""

from __future__ import annotations

from pathlib import Path

from music21 import stream
from music21 import metadata as m21_metadata

from notare.utils import load_score


def _write_minimal_score(tmp_path: Path, *, with_meta: bool) -> Path:
    score = stream.Score()
    part = stream.Part()
    # Intentionally omit partName to test normalization
    score.insert(0, part)
    if with_meta:
        # Create metadata but omit title/composer values
        score.insert(0, m21_metadata.Metadata())
    out = tmp_path / "empty_fields.musicxml"
    score.write("musicxml", fp=str(out))
    return out


def test_load_score_normalizes_missing_fields_from_file(tmp_path) -> None:
    src = _write_minimal_score(tmp_path, with_meta=False)
    score = load_score(str(src))

    assert score.metadata is not None
    assert score.metadata.title == ""
    assert score.metadata.composer == ""

    # Ensure parts exist and names normalized
    assert score.parts
    for p in score.parts:
        assert getattr(p, "partName", "") == "Part 1"


def test_load_score_normalizes_missing_fields_from_stdin(tmp_path) -> None:
    src = _write_minimal_score(tmp_path, with_meta=True)
    raw = Path(src).read_bytes()
    score = load_score(None, stdin_data=raw)

    assert score.metadata is not None
    assert score.metadata.title == ""
    assert score.metadata.composer == ""
    for p in score.parts:
        assert getattr(p, "partName", "") == "Part 1" # Default name we assign
