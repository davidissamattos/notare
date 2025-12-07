# music-score-sk

A swiss knife utility for handling music score files in the command line.

## Installation

```bash
pip install -e .
```

## Usage

The CLI uses [Google's Python Fire](https://github.com/google/python-fire) so every
method on the `ScoreTool` object becomes a command.

```bash
# Print the current version
music-score-sk version

# List available output formats reported by music21
music-score-sk formats

# Convert a score by specifying source, format, and output
music-score-sk convert --source score.musicxml --format midi --output score.mid

# You can also request subformats exposed by music21
music-score-sk convert --source score.musicxml --format musicxml.pdf --output score.pdf
```
