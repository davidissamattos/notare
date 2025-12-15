"""Tests for the extract module."""

from __future__ import annotations

from pathlib import Path

from music21 import converter as m21_converter
from music21 import note
from music21 import stream

from notare.extract import extract_sections


def _build_score(tmp_path: Path) -> Path:
    score = stream.Score()
    for idx, part_name in enumerate(["Flute", "Oboe"], start=1):
        part = stream.Part(id=f"P{idx}")
        part.partName = part_name
        for measure_number in range(1, 5):
            measure = stream.Measure(number=measure_number)
            pitch_name = chr(ord("C") + measure_number - 1)
            measure.append(note.Note(pitch_name + "4"))
            part.append(measure)
        score.insert(idx - 1, part)
    source = tmp_path / "source.musicxml"
    score.write("musicxml", fp=str(source))
    return source


def test_extract_measures(tmp_path):
    source = _build_score(tmp_path)
    output = tmp_path / "measures.musicxml"

    extract_sections(
        source=str(source),
        output=str(output),
        measures="1-2",
    )

    new_score = m21_converter.parse(str(output))
    first_part = new_score.parts[0]
    assert len(list(first_part.getElementsByClass(stream.Measure))) == 2


def test_extract_specific_parts(tmp_path):
    source = _build_score(tmp_path)
    output = tmp_path / "parts.musicxml"

    extract_sections(
        source=str(source),
        output=str(output),
        part_names="Flute",
    )

    new_score = m21_converter.parse(str(output))
    assert len(new_score.parts) == 1
    assert new_score.parts[0].partName == "Flute"


def test_extract_combined_measures_and_part_numbers(tmp_path):
    source = _build_score(tmp_path)
    output = tmp_path / "combined.musicxml"

    extract_sections(
        source=str(source),
        output=str(output),
        part_numbers="2",
        measures="3-4",
    )

    new_score = m21_converter.parse(str(output))
    assert len(new_score.parts) == 1
    assert new_score.parts[0].partName == "Oboe"
    assert len(list(new_score.parts[0].getElementsByClass(stream.Measure))) == 2
