# music-score-sk

A swiss knife utility for handling music score files in the command line.

The CLI uses [Google's Python Fire](https://github.com/google/python-fire) so every
method on the `ScoreTool` object becomes a command.

Behind the scenes most of the calculations and transformations are done with the excelent music21 library

## Installation

```bash
pip install -e .
```

## Tests
```bash
pytest -q
```

## Usage

```bash
# Print the current version
music-score-sk version
```

### Convert

Tools for converting between different formats

```bash
# List available output formats reported by music21
music-score-sk formats

# Convert a score by specifying source, format, and optional output
music-score-sk convert --source score.musicxml --format midi --output score.mid

# When --output is omitted, data is streamed to stdout (great for pipelines)
music-score-sk convert --source score.abc --format musicxml > tmp.musicxml

# You can also request subformats exposed by music21
music-score-sk convert --source score.musicxml --format musicxml.pdf --output score.pdf
```

### Transpose module

```bash
# Transpose an input score by tones (use 0.5 for semitones) and write the result
# Transposition adjust the key signature by automatically identifying which is the new key and setting it appropriately
music-score-sk transpose 1 --source score.musicxml --output score_transposed.musicxml

# Limit transposition to a single part and control the resulting key signature
music-score-sk transpose -0.5 --source score.musicxml --output flute_down.musicxml --part-name Flute --key-sharps -2

# Parts can also be selected by number (1 == first part)
music-score-sk transpose 1.5 --source score.musicxml --output part2_up.mxl --part-number 2

# Stream results through pipes: omit --source to read stdin, omit --output for stdout
cat score.abc | music-score-sk convert --format musicxml | music-score-sk transpose 1 --output final.musicxml

# Emit transposed data directly to stdout in another format
music-score-sk transpose 2 --source score.musicxml --output-format midi > score.mid
```

You can also just change the key signature without transposing *in this case adding two flats

```bash
music-score-sk transpose 0 --source score.musicxml --output flute_down.musicxml --key-sharps -2
```

### Metadata module

Available metadata flags (--field or --new-field)

* title 
* author 
* format
* composer
* arranger
* number-parts
* number-measures
* key-signature
* tempo

If you add --new-field this means it is expected a new value

```bash
# Inspect metadata (all fields by default, or pick specific fields)
music-score-sk metadata --source score.musicxml
music-score-sk metadata --source score.musicxml --title --composer

# Update metadata and write to a new file (supports piping like other commands)
music-score-sk metadata --source score.musicxml --new-title "My new title" --output updated.musicxml
```

### Extract module

```bash
# Extract specific measures and/or parts (supports comma-separated ranges)
music-score-sk extract --source score.musicxml --measures 1-4 --part-name Flute,Oboe --output excerpt.musicxml

# Keep all parts but only select specific measures
music-score-sk extract --source score.musicxml --measures 1,3,5-8 --output highlights.musicxml

# Combine part number selection with output piping
music-score-sk extract --source score.musicxml --part-number 1 --measures 2-4 --output-format musicxml > flute_excerpt.musicxml

# Analyze entire piece or pipeline with extracts
music-score-sk analyze --source score.musicxml --key --npvi
music-score-sk extract --source score.musicxml --measures 1-4 --output - | music-score-sk analyze --key
```
