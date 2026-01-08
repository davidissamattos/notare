from __future__ import annotations

from pathlib import Path
import io

from music21 import converter as m21_converter
from music21 import duration as m21_duration
from music21 import meter as m21_meter
from music21 import note as m21_note
from music21 import stream as m21_stream
from music21 import expressions as m21_expr
from music21 import chord as m21_chord

from notare.simplify import simplify_score

def test_ornament_removal_scoped_to_part_name(tmp_path: Path) -> None:
    # Two parts: Flute and Oboe; apply simplify only to Flute via part-name
    flute = m21_stream.Part()
    flute.partName = "Flute"
    m1 = m21_stream.Measure(number=1)
    m1.insert(0, m21_meter.TimeSignature("4/4"))
    n1 = m21_note.Note("C4"); n1.duration = m21_duration.Duration(0.5)
    n2 = m21_note.Note("D4"); n2.duration = m21_duration.Duration(0.0625)
    n3 = m21_note.Note("C4"); n3.duration = m21_duration.Duration(1.0)
    for n in (n1, n2, n3): m1.append(n)
    flute.append(m1)

    oboe = m21_stream.Part(); oboe.partName = "Oboe"
    m2 = m21_stream.Measure(number=1)
    m2.insert(0, m21_meter.TimeSignature("4/4"))
    o1 = m21_note.Note("C4"); o1.duration = m21_duration.Duration(0.5)
    o2 = m21_note.Note("D4"); o2.duration = m21_duration.Duration(0.0625)
    o3 = m21_note.Note("C4"); o3.duration = m21_duration.Duration(1.0)
    for n in (o1, o2, o3): m2.append(n)
    oboe.append(m2)

    score = m21_stream.Score()
    score.insert(0, flute)
    score.insert(0, oboe)
    in_path = tmp_path / "multi.musicxml"
    out_path = tmp_path / "out.musicxml"
    score.write("musicxml", fp=str(in_path))

    # Simplify only Flute
    simplify_score(
        algorithms=[("ornament_removal", {"duration": "1/4"})],
        source=str(in_path),
        output=str(out_path),
        part_names="Flute",
    )

    out = m21_converter.parse(str(out_path))
    out_flute, out_oboe = out.parts
    names_flute = [n.pitch.nameWithOctave for n in out_flute.recurse().notes]
    names_oboe = [n.pitch.nameWithOctave for n in out_oboe.recurse().notes]
    assert names_flute == ["C4", "C4"]
    assert names_oboe == ["C4", "D4", "C4"]


def test_ornament_removal_scoped_to_measures(tmp_path: Path) -> None:
    # One part, two measures; apply to measure 1 only
    part = m21_stream.Part(); part.partName = "Solo"
    m1 = m21_stream.Measure(number=1)
    m1.insert(0, m21_meter.TimeSignature("4/4"))
    a1 = m21_note.Note("C4"); a1.duration = m21_duration.Duration(0.5)
    a2 = m21_note.Note("D4"); a2.duration = m21_duration.Duration(0.0625)
    a3 = m21_note.Note("C4"); a3.duration = m21_duration.Duration(1.0)
    for n in (a1, a2, a3): m1.append(n)

    m2 = m21_stream.Measure(number=2)
    b1 = m21_note.Note("C4"); b1.duration = m21_duration.Duration(0.5)
    b2 = m21_note.Note("D4"); b2.duration = m21_duration.Duration(0.0625)
    b3 = m21_note.Note("C4"); b3.duration = m21_duration.Duration(1.0)
    for n in (b1, b2, b3): m2.append(n)

    part.append(m1); part.append(m2)
    score = m21_stream.Score(); score.insert(0, part)
    in_path = tmp_path / "measures.musicxml"
    out_path = tmp_path / "out_measures.musicxml"
    score.write("musicxml", fp=str(in_path))

    simplify_score(
        algorithms=[("ornament_removal", {"duration": "1/4"})],
        source=str(in_path),
        output=str(out_path),
        measures="1",
    )

    out = m21_converter.parse(str(out_path))
    out_part = out.parts[0] if out.parts else out
    # Expected: measure 1 simplified -> [C, C]; measure 2 unchanged -> [C, D, C]
    names = [n.pitch.nameWithOctave for n in out_part.recurse().notes]
    assert names == ["C4", "C4", "C4", "D4", "C4"]
"""Tests for simplify module and ornament removal algorithm."""


def _make_score_with_notes(notes: list[m21_note.Note]) -> m21_stream.Score:
    score = m21_stream.Score()
    part = m21_stream.Part()
    meas = m21_stream.Measure(number=1)
    meas.insert(0, m21_meter.TimeSignature("4/4"))
    for n in notes:
        meas.append(n)
    part.append(meas)
    score.insert(0, part)
    return score


def _musicxml_bytes(score: m21_stream.Score) -> bytes:
    tmp = Path.cwd() / "_tmp_test_simplify.musicxml"
    try:
        score.write("musicxml", fp=str(tmp))
        return tmp.read_bytes()
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass


def test_ornament_removal_grace_neighbor_removed() -> None:
    # C8th, grace D, Cquarter — grace should be removed
    n1 = m21_note.Note("C4")
    n1.duration = m21_duration.Duration(0.5)

    n2 = m21_note.Note("D4")
    # Simulate a grace-like very short neighbor by small duration
    n2.duration = m21_duration.Duration(0.0625)

    n3 = m21_note.Note("C4")
    n3.duration = m21_duration.Duration(1.0)

    score = _make_score_with_notes([n1, n2, n3])
    source_bytes = _musicxml_bytes(score)

    buffer = io.BytesIO()
    simplify_score(
        algorithms=[("ornament_removal", {"duration": "1/8"})],
        stdin_data=source_bytes,
        stdout_buffer=buffer,
    )

    out = m21_converter.parseData(buffer.getvalue())
    part = out.parts[0] if out.parts else out
    names = [n.pitch.nameWithOctave for n in part.recurse().notes]
    assert names == ["C4", "C4"]


def test_ornament_removal_duration_parameter_controls_threshold(tmp_path: Path) -> None:
    # C8th, D16th, Cquarter — remove only when threshold >= 1/8 beat
    n1 = m21_note.Note("C4")
    n1.duration = m21_duration.Duration(0.5)

    n2 = m21_note.Note("D4")
    n2.duration = m21_duration.Duration(0.125)  # Sixteenth relative to quarter beat

    n3 = m21_note.Note("C4")
    n3.duration = m21_duration.Duration(1.0)

    score = _make_score_with_notes([n1, n2, n3])

    # Write input once
    in_path = tmp_path / "in.musicxml"
    score.write("musicxml", fp=str(in_path))

    # With 1/16 threshold (0.0625 of beat), D16th is NOT removed
    out1 = tmp_path / "out1.musicxml"
    simplify_score(
        algorithms=[("ornament_removal", {"duration": "1/16"})],
        source=str(in_path),
        output=str(out1),
    )
    out_score1 = m21_converter.parse(str(out1))
    part1 = out_score1.parts[0] if out_score1.parts else out_score1
    names1 = [n.pitch.nameWithOctave for n in part1.recurse().notes]
    assert names1 == ["C4", "D4", "C4"]

    # With 1/4 threshold (0.25 of beat), D16th IS removed
    out2 = tmp_path / "out2.musicxml"
    simplify_score(
        algorithms=[("ornament_removal", {"duration": "1/4"})],
        source=str(in_path),
        output=str(out2),
    )

    out_score2 = m21_converter.parse(str(out2))
    part2 = out_score2.parts[0] if out_score2.parts else out_score2
    names2 = [n.pitch.nameWithOctave for n in part2.recurse().notes]
    assert names2 == ["C4", "C4"]


def test_simplify_supports_piping() -> None:
    # Create a score with a remove-worthy ornament and use stdin/stdout
    n1 = m21_note.Note("C4")
    n1.duration = m21_duration.Duration(0.5)
    n2 = m21_note.Note("D4")
    n2.duration = m21_duration.Duration(0.125)
    n3 = m21_note.Note("C4")
    n3.duration = m21_duration.Duration(1.0)
    score = _make_score_with_notes([n1, n2, n3])
    source_bytes = _musicxml_bytes(score)

    buffer = io.BytesIO()
    simplify_score(
        algorithms=[("ornament_removal", {"duration": "1/4"})],
        stdin_data=source_bytes,
        stdout_buffer=buffer,
    )

    out = m21_converter.parseData(buffer.getvalue())
    part = out.parts[0] if out.parts else out
    names = [n.pitch.nameWithOctave for n in part.recurse().notes]
    assert names == ["C4", "C4"]


def test_ornament_markings_are_removed(tmp_path: Path) -> None:
    # Create a note with an explicit trill marking
    part = m21_stream.Part()
    meas = m21_stream.Measure(number=1)
    meas.insert(0, m21_meter.TimeSignature("4/4"))
    n = m21_note.Note("C4")
    n.duration = m21_duration.Duration(1.0)
    n.expressions.append(m21_expr.Trill())
    meas.append(n)
    part.append(meas)
    score = m21_stream.Score(); score.insert(0, part)

    in_path = tmp_path / "orn_mark.musicxml"
    out_path = tmp_path / "orn_mark_out.musicxml"
    score.write("musicxml", fp=str(in_path))

    simplify_score(
        algorithms=[("ornament_removal", {"duration": "1/8"})],
        source=str(in_path),
        output=str(out_path),
    )

    out = m21_converter.parse(str(out_path))
    # Ensure no Ornament expressions remain
    orns = list(out.recurse().getElementsByClass(m21_expr.Ornament))
    assert len(orns) == 0


def test_chordify_collapses_all_parts_into_chords() -> None:
    # Two parts sounding simultaneously -> expect a single chord containing both pitches.
    part_a = m21_stream.Part()
    part_b = m21_stream.Part()
    meas_a = m21_stream.Measure(number=1)
    meas_b = m21_stream.Measure(number=1)
    meas_a.insert(0, m21_meter.TimeSignature("4/4"))
    meas_b.insert(0, m21_meter.TimeSignature("4/4"))
    n_a = m21_note.Note("C4"); n_a.duration = m21_duration.Duration(1.0)
    n_b = m21_note.Note("E4"); n_b.duration = m21_duration.Duration(1.0)
    meas_a.append(n_a); meas_b.append(n_b)
    part_a.append(meas_a); part_b.append(meas_b)
    score = m21_stream.Score()
    score.insert(0, part_a)
    score.insert(0, part_b)

    buffer = io.BytesIO()
    simplify_score(
        algorithms=[("chordify", {})],
        stdin_data=_musicxml_bytes(score),
        stdout_buffer=buffer,
    )

    out = m21_converter.parseData(buffer.getvalue())
    out_part = out.parts[0] if out.parts else out
    chords = list(out_part.recurse().getElementsByClass(m21_chord.Chord))
    assert len(chords) == 1
    names = sorted(p.nameWithOctave for p in chords[0].pitches)
    assert names == ["C4", "E4"]
