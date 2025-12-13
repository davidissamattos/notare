"""Tests for transpose functionality."""

from __future__ import annotations

from pathlib import Path
import io

import pytest
from music21 import converter as m21_converter
from music21 import key as m21_key
from music21 import note
from music21 import stream

from music_score_sk.transpose import transpose_score

DATA_DIR = Path(__file__).parent / "data"


def _notes(part: stream.Stream) -> list[str]:
    return [n.pitch.step for n in part.recurse().notes]


def _first_key_signature(part: stream.Stream) -> m21_key.KeySignature:
    return part.recurse().getElementsByClass(m21_key.KeySignature)[0]


def _multi_part_score(tmp_path: Path) -> Path:
    """Create a temporary score with two parts for selection tests."""
    score = stream.Score()
    flute = stream.Part()
    flute.partName = "Flute"
    oboe = stream.Part()
    oboe.partName = "Oboe"

    for part in (flute, oboe):
        part.append(m21_key.KeySignature(0))
        scale_notes = ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5"]
        for name in scale_notes:
            part.append(note.Note(name, quarterLength=1))
        score.insert(0, part)

    output = tmp_path / "multi.musicxml"
    score.write("musicxml", fp=str(output))
    return output


def test_transpose_one_tone_updates_scale_and_key(tmp_path):
    source = DATA_DIR / "c_scale.musicxml"
    output = tmp_path / "c_scale_d.musicxml"

    transpose_score(source=str(source), output=str(output), steps=1.0)

    score = m21_converter.parse(str(output))
    part = score.parts[0] if score.parts else score
    assert _notes(part)[0] == "D"
    assert _notes(part)[-1] == "D"
    assert _first_key_signature(part).sharps == 2  # D major


def test_transpose_manual_key_signature_override(tmp_path):
    source = DATA_DIR / "c_scale_basic.musicxml"
    output = tmp_path / "c_scale_override.musicxml"

    transpose_score(
        source=str(source),
        output=str(output),
        steps=1.0,
        key_sharps=0,
    )

    score = m21_converter.parse(str(output))
    part = score.parts[0] if score.parts else score
    assert _notes(part)[0] == "D"
    assert _first_key_signature(part).sharps == 0  # Forced back to C


def test_transpose_specific_part_by_number(tmp_path):
    source = _multi_part_score(tmp_path)
    output = tmp_path / "multi_part_number.musicxml"

    transpose_score(
        source=str(source),
        output=str(output),
        steps=1.0,
        part_number=2,
    )

    score = m21_converter.parse(str(output))
    flute, oboe = score.parts
    assert _notes(flute)[0] == "C"
    assert _notes(oboe)[0] == "D"
    assert _first_key_signature(oboe).sharps == 2


def test_transpose_specific_part_by_name(tmp_path):
    source = _multi_part_score(tmp_path)
    output = tmp_path / "multi_part_name.musicxml"

    transpose_score(
        source=str(source),
        output=str(output),
        steps=-0.5,
        part_name="Flute",
        key_sharps=-2,
    )

    score = m21_converter.parse(str(output))
    flute, oboe = score.parts
    assert _notes(flute)[0] == "B"
    assert _first_key_signature(flute).sharps == -2
    assert _notes(oboe)[0] == "C"  # untouched


def test_transpose_rejects_invalid_part_reference(tmp_path):
    source = DATA_DIR / "c_scale.musicxml"
    output = tmp_path / "invalid.musicxml"

    with pytest.raises(ValueError):
        transpose_score(
            source=str(source),
            output=str(output),
            steps=1.0,
            part_name="Unknown",
        )


def test_transpose_rejects_invalid_step_increment(tmp_path):
    source = DATA_DIR / "c_scale.musicxml"
    output = tmp_path / "invalid_step.musicxml"

    with pytest.raises(ValueError):
        transpose_score(source=str(source), output=str(output), steps=0.3)


def test_transpose_supports_piping() -> None:
    source_bytes = (DATA_DIR / "c_scale.musicxml").read_bytes()
    buffer = io.BytesIO()

    transpose_score(
        steps=1.0,
        stdin_data=source_bytes,
        stdout_buffer=buffer,
    )

    score = m21_converter.parseData(buffer.getvalue())
    part = score.parts[0] if score.parts else score
    assert _notes(part)[0] == "D"
    assert _first_key_signature(part).sharps == 2
