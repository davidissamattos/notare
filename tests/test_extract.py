"""Tests for the extract module."""

from __future__ import annotations

from pathlib import Path

from music21 import converter as m21_converter
from music21 import note
from music21 import stream
from music21 import chord as m21_chord

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


def test_extract_chords_only_preserves_only_chords(tmp_path: Path) -> None:
    score = stream.Score()
    part = stream.Part()
    meas1 = stream.Measure(number=1)
    meas1.append(m21_chord.Chord(["C4", "E4"]))
    meas1.append(note.Note("G4"))
    meas2 = stream.Measure(number=2)
    meas2.append(note.Note("F4"))
    part.append(meas1)
    part.append(meas2)
    score.insert(0, part)
    source = tmp_path / "chord_source.musicxml"
    score.write("musicxml", fp=str(source))

    output = tmp_path / "chords.musicxml"
    extract_sections(
        source=str(source),
        output=str(output),
        chords_only=True,
    )

    new_score = m21_converter.parse(str(output))
    out_part = new_score.parts[0]
    measures = list(out_part.getElementsByClass(stream.Measure))
    assert len(measures) == 2

    chords_m1 = list(measures[0].recurse().getElementsByClass(m21_chord.Chord))
    notes_m1 = [n for n in measures[0].recurse().notes if isinstance(n, note.Note)]
    assert len(chords_m1) == 1
    assert sorted(p.nameWithOctave for p in chords_m1[0].pitches) == ["C4", "E4"]
    assert notes_m1 == []

    # Measure 2 originally had only a single note; after chords-only it should be empty
    assert len(list(measures[1].recurse().getElementsByClass(m21_chord.Chord))) == 0
    assert len(list(measures[1].recurse().notes)) == 0


def test_extract_chords_only_handles_scores_without_chords(tmp_path: Path) -> None:
    source = _build_score(tmp_path)
    output = tmp_path / "chordless.musicxml"

    extract_sections(
        source=str(source),
        output=str(output),
        chords_only=True,
    )

    new_score = m21_converter.parse(str(output))
    part = new_score.parts[0]
    measures = list(part.getElementsByClass(stream.Measure))
    assert len(measures) == 4
    for measure in measures:
        assert len(list(measure.recurse().getElementsByClass(m21_chord.Chord))) == 0
        assert len(list(measure.recurse().notes)) == 0
