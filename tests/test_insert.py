"""Tests for insert/add module."""

from __future__ import annotations

from pathlib import Path

from music21 import duration as m21_duration
from music21 import meter as m21_meter
from music21 import note as m21_note
from music21 import stream as m21_stream
from music21 import converter as m21_converter

from notare.insert import add_sections


def _score_with_part(name: str, measures: int) -> m21_stream.Score:
    score = m21_stream.Score()
    part = m21_stream.Part()
    part.partName = name
    ts = m21_meter.TimeSignature("4/4")
    for i in range(measures):
        m = m21_stream.Measure(number=i + 1)
        if i == 0:
            m.insert(0, ts)
        n = m21_note.Note("C4")
        n.duration = m21_duration.Duration(4.0)
        m.append(n)
        part.append(m)
    score.insert(0, part)
    return score


def _write_temp(score: m21_stream.Score, path: Path) -> None:
    score.write("musicxml", fp=str(path))


def test_add_inserts_measures_before_position(tmp_path: Path) -> None:
    a = _score_with_part("Flute", 4)
    b = _score_with_part("Flute", 2)
    a_path = tmp_path / "a.musicxml"
    b_path = tmp_path / "b.musicxml"
    out_path = tmp_path / "out.musicxml"
    _write_temp(a, a_path)
    _write_temp(b, b_path)

    add_sections(original=str(a_path), to_add=str(b_path), measure=2, before=True, output=str(out_path))

    out = m21_converter.parse(str(out_path))
    part = out.parts[0] if out.parts else out
    meas_nums = [m.number for m in part.getElementsByClass(m21_stream.Measure)]
    assert len(meas_nums) == 6


def test_add_fills_other_parts_with_rests(tmp_path: Path) -> None:
    # Base has Flute and Oboe, inc has only Flute -> Oboe gets rest measures in inserted block
    score = m21_stream.Score()
    flute = _score_with_part("Flute", 3).parts[0]
    oboe = _score_with_part("Oboe", 3).parts[0]
    score.insert(0, flute)
    score.insert(0, oboe)
    a_path = tmp_path / "a2.musicxml"
    _write_temp(score, a_path)

    inc = _score_with_part("Flute", 2)
    b_path = tmp_path / "b2.musicxml"
    _write_temp(inc, b_path)

    out_path = tmp_path / "out2.musicxml"
    add_sections(original=str(a_path), to_add=str(b_path), measure=2, before=True, output=str(out_path))

    out = m21_converter.parse(str(out_path))
    parts = list(out.parts)
    assert len(parts) == 2
    # Total measures should be base 3 + inserted 2 = 5
    for p in parts:
        assert len(list(p.getElementsByClass(m21_stream.Measure))) == 5


def test_add_creates_new_parts_when_no_match(tmp_path: Path) -> None:
    a = _score_with_part("Flute", 2)
    b = _score_with_part("Oboe", 1)
    a_path = tmp_path / "a3.musicxml"
    b_path = tmp_path / "b3.musicxml"
    out_path = tmp_path / "out3.musicxml"
    _write_temp(a, a_path)
    _write_temp(b, b_path)

    add_sections(original=str(a_path), to_add=str(b_path), measure=1, before=False, output=str(out_path))

    out = m21_converter.parse(str(out_path))
    parts = list(out.parts)
    # Now should have both Flute and Oboe
    names = sorted([(p.partName or p.id) for p in parts])
    assert any("Flute" in (p.partName or "") for p in parts)
    assert any("Oboe" in (p.partName or "") for p in parts)
    # Total measures = base 2 + insert 1 = 3 in all parts
    for p in parts:
        assert len(list(p.getElementsByClass(m21_stream.Measure))) == 3
