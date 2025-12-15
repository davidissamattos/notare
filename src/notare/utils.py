"""Shared helpers for score IO operations."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
from typing import Any, BinaryIO

from music21 import converter as m21_converter
from music21 import stream as m21_stream
from music21 import metadata as m21_metadata


def _available_output_formats() -> tuple[str, ...]:
    """Return sorted output formats supported by music21."""
    formats: set[str] = set()
    for sub_converter in m21_converter.Converter.subConvertersList("output"):
        base_formats = (
            fmt.lower()
            for fmt in getattr(sub_converter, "registerFormats", ())
            if fmt
        )
        subformats = getattr(sub_converter, "registerOutputSubformatExtensions", {}) or {}
        for base in base_formats:
            formats.add(base)
            for sub in subformats:
                formats.add(f"{base}.{sub.lower()}")
    return tuple(sorted(formats))


def _available_input_formats() -> tuple[str, ...]:
    """Return sorted input formats supported by music21."""
    formats: set[str] = set()
    for sub_converter in m21_converter.Converter.subConvertersList("input"):
        base_formats = (
            fmt.lower()
            for fmt in getattr(sub_converter, "registerFormats", ())
            if fmt
        )
        for base in base_formats:
            formats.add(base)
    return tuple(sorted(formats))


def list_output_formats() -> list[str]:
    """Expose supported output formats."""
    return list(_available_output_formats())


def list_input_formats() -> list[str]:
    """Expose supported input formats."""
    return list(_available_input_formats())

def load_score(source: str | None, *, stdin_data: bytes | None = None) -> m21_stream.Score:
    """Load a score from disk or stdin and normalize empty fields.

    Ensures missing part names, title, and composer are empty strings.
    """
    # Treat '-' as stdin alias
    if source is None or (isinstance(source, str) and source.strip() == "-"):
        raw = stdin_data if stdin_data is not None else sys.stdin.buffer.read()
        if not raw:
            raise ValueError("No input data received from stdin.")
        try:
            data = raw.decode("utf-8")
        except (UnicodeDecodeError, AttributeError):
            data = raw
        score = m21_converter.parseData(data)
    else:
        source_path = Path(source).expanduser()
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        score = m21_converter.parse(str(source_path))

    # Normalize metadata: ensure metadata exists and set empty strings when missing
    if score.metadata is None:
        score.insert(0, m21_metadata.Metadata())
    # Helper to detect placeholder/missing strings
    def _is_missing(value: object, placeholders: set[str]) -> bool:
        if value is None:
            return True
        if not isinstance(value, str):
            return False
        stripped = value.strip()
        if stripped == "":
            return True
        return stripped.lower() in placeholders

    title_placeholders = {"music21", "untitled", "title"}
    composer_placeholders = {"unknown", "composer", "music21"}

    if _is_missing(getattr(score.metadata, "title", None), title_placeholders):
        score.metadata.title = ""
    if _is_missing(getattr(score.metadata, "composer", None), composer_placeholders):
        score.metadata.composer = ""

    # Normalize part names
    try:
        part_placeholders = {"part", "musicxml part"}
        for idx, part in enumerate(score.parts):
            name = getattr(part, "partName", None)
            if _is_missing(name, part_placeholders):
                part.partName = f"Part {idx + 1}"
    except Exception:
        # In case score has no parts iterable, ignore
        pass

    return score


def write_score(
    score: m21_stream.Score,
    target_format: str,
    *,
    output: str | None,
    stdout_buffer: BinaryIO | None = None,
    write_kwargs: dict[str, Any] | None = None,
) -> str:
    """Write the score either to stdout or to a file path."""
    if output is None:
        buffer = stdout_buffer or sys.stdout.buffer
        # If target_format is omitted or unsupported, fall back to musicxml for piping
        available = set(_available_output_formats())
        fmt = (target_format or "").strip().lower()
        if not fmt:
            effective_fmt = "musicxml"
        else:
            effective_fmt = fmt if fmt in available else "musicxml"
        _write_to_buffer(score, effective_fmt, buffer, write_kwargs=write_kwargs)
        return ""

    output_path = Path(output).expanduser()
    if output_path.parent and not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # Validate format for file output
    available = set(_available_output_formats())
    fmt = target_format.strip().lower()
    if fmt not in available:
        raise ValueError(
            f"Unsupported output format '{target_format}'. Choose from: {', '.join(sorted(available))}"
        )
    score.write(fmt, fp=str(output_path), **(write_kwargs or {}))
    return f"Created {output_path} using format '{target_format}'."


def infer_format_from_path(path: str | None, *, default: str = "musicxml") -> str:
    """Guess a format from a file path, falling back to the provided default."""
    if path:
        suffix = Path(path).suffix.lstrip(".")
        if suffix:
            return suffix.lower()
    return default


def _write_to_buffer(
    score: m21_stream.Score,
    fmt: str,
    buffer: BinaryIO,
    *,
    write_kwargs: dict[str, Any] | None,
) -> None:
    suffix = f".{fmt.split('.')[0]}"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        kwargs = write_kwargs or {}
        score.write(fmt, fp=str(tmp_path), **kwargs)
        with open(tmp_path, "rb") as handle:
            buffer.write(handle.read())
            buffer.flush()
    finally:
        tmp_path.unlink(missing_ok=True)
