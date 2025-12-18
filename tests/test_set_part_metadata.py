"""Tests for part-specific metadata updates (rename and reorder)."""

from __future__ import annotations

from pathlib import Path

from music21 import duration as m21_duration
from music21 import meter as m21_meter
from music21 import note as m21_note
from music21 import stream as m21_stream
from music21 import converter as m21_converter

from notare.metadata import set_part_metadata


def _score_two_parts() -> m21_stream.Score:
    score = m21_stream.Score()
    ts = m21_meter.TimeSignature("4/4")

    flute = m21_stream.Part(); flute.partName = "Flute"
    m1 = m21_stream.Measure(number=1)
    m1.insert(0, ts)
    n1 = m21_note.Note("C4"); n1.duration.quarterLength = 4.0
    m1.append(n1)
    flute.append(m1)

    oboe = m21_stream.Part(); oboe.partName = "Oboe"
    m2 = m21_stream.Measure(number=1)
    m2.insert(0, ts)
    n2 = m21_note.Note("D4"); n2.duration.quarterLength = 4.0
    m2.append(n2)
    oboe.append(m2)

    score.insert(0, flute)
    score.insert(0, oboe)
    return score


def _write_tmp(score: m21_stream.Score, path: Path) -> None:
    score.write("musicxml", fp=str(path))


def test_set_part_metadata_rename_by_name(tmp_path: Path) -> None:
    s = _score_two_parts()
    in_path = tmp_path / "rename_in.musicxml"
    out_path = tmp_path / "rename_out.musicxml"
    _write_tmp(s, in_path)

    set_part_metadata(
        source=str(in_path),
        output=str(out_path),
        part_name="Flute",
        name="Solo Flute",
    )

    out = m21_converter.parse(str(out_path))
    parts = list(out.parts)
    assert parts[0].partName == "Solo Flute" or parts[1].partName == "Solo Flute"


def test_set_part_metadata_reorder_by_number(tmp_path: Path) -> None:
    s = _score_two_parts()
    in_path = tmp_path / "reorder_in.musicxml"
    out_path = tmp_path / "reorder_out.musicxml"
    _write_tmp(s, in_path)

    # Move second part (Oboe) to first position
    set_part_metadata(
        source=str(in_path),
        output=str(out_path),
        part_number=2,
        order=1,
    )

    out = m21_converter.parse(str(out_path))
    parts = list(out.parts)
    assert (parts[0].partName or "").lower() == "oboe"


def test_set_part_metadata_rename_and_reorder(tmp_path: Path) -> None:
    s = _score_two_parts()
    in_path = tmp_path / "both_in.musicxml"
    out_path = tmp_path / "both_out.musicxml"
    _write_tmp(s, in_path)

    set_part_metadata(
        source=str(in_path),
        output=str(out_path),
        part_number=1,
        name="Lead",
        order=2,
    )

    out = m21_converter.parse(str(out_path))
    parts = list(out.parts)
    # New order places previously first part at index 1 (second position)
    assert (parts[1].partName or "").lower() == "lead"
