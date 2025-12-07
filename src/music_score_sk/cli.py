"""Command line interface for the music-score-sk package."""

from __future__ import annotations

from collections.abc import Sequence
import sys

import fire

from . import __version__
from .converter import convert_score, list_output_formats


class ScoreTool:
    """Swiss-knife commands for manipulating score files."""

    def version(self) -> str:
        """Return the package version."""
        return __version__

    def formats(self) -> list[str]:
        """List supported output formats."""
        return list_output_formats()

    def convert(self, *, source: str, format: str, output: str) -> str:
        """Convert a score to the requested format."""
        return convert_score(source=source, target_format=format, output=output)


def main(argv: Sequence[str] | None = None) -> None:
    """Entrypoint used by the console script."""
    command = list(argv) if argv is not None else sys.argv[1:]
    fire.Fire(ScoreTool, command=command)


if __name__ == "__main__":
    main()
