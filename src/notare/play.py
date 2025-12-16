"""Play scores by rendering to MIDI and opening the default player."""

from __future__ import annotations

import os
import platform
import subprocess
import tempfile
from pathlib import Path
from typing import BinaryIO

from music21 import stream as m21_stream

from .utils import load_score


def play_score(
    *,
    source: str | None = None,
    stdin_data: bytes | None = None,
) -> str:
    """Load a score and open it in the system's default MIDI player.

    - Reads from `--source` or stdin (when omitted or set to '-')
    - Writes a temporary `.mid` file and opens it with the OS default app
    - Does not write to stdout
    """
    score = load_score(source, stdin_data=stdin_data)

    with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as tmp:
        midi_path = Path(tmp.name)

    try:
        score.write("midi", fp=str(midi_path))
    except Exception as exc:  # pragma: no cover - best effort
        # Clean up if write failed
        try:
            midi_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise RuntimeError(f"Failed to render MIDI: {exc}")

    _open_file_with_default_app(midi_path)
    return f"Opened MIDI player: {midi_path}"


def _open_file_with_default_app(path: Path) -> None:
    sysname = platform.system().lower()
    try:
        if sysname.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sysname == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception:
        # As a last resort, do nothing; caller already returns the path
        pass
