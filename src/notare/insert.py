"""Insert measures and parts from one score into another.

Provides an `add_sections` function used by the CLI command `notare add`.

Behavior
- Match parts by name (case-insensitive). If a `to-add` part matches an existing
  part in the original score, insert all its measures at the requested position
  (before/after the given measure number).
- For original parts not present in `to-add`, insert the same number of measures
  filled with rests at the insertion position to keep parts aligned.
- For `to-add` parts not present in the original, create new parts in the result,
  placing their measures at the correct position, and fill the remaining measures
  (before/after) with rests to align with the other parts.

Notes
- Measure numbering is normalized on import and renumbered after insertion.
- Time signatures and key signatures are copied from neighboring measures where
  possible. Rest measure duration falls back to the local bar duration or 4/4.
"""

from __future__ import annotations

import copy
from typing import BinaryIO, Dict, List, Tuple

from music21 import meter as m21_meter
from music21 import note as m21_note
from music21 import stream as m21_stream

from .utils import load_score, write_score
from .utils import _renumber_measures_starting_at_one


def add_sections(
    *,
    original: str,
    to_add: str,
    measure: int,
    before: bool = True,
    output: str | None = None,
    output_format: str | None = None,
) -> str:
    """Insert all measures from `to_add` into `original` at the specified position.

    Args
    - original: Path to the base score to modify.
    - to_add: Path to the score whose measures/parts should be inserted.
    - measure: 1-based measure index in the original; insert before/after this.
    - before: When True, insert before `measure`; otherwise insert after it.
    - output, output_format: Where/how to write the resulting score.
    """
    if measure < 1:
        raise ValueError("measure must be >= 1")

    base = load_score(original)
    inc = load_score(to_add)

    base_parts = list(base.parts) or [base]
    inc_parts = list(inc.parts) or [inc]

    # Build name->part mapping (lowercase) using partName then id as fallback
    def part_key(p: m21_stream.Stream) -> str:
        name = (getattr(p, "partName", None) or "").strip() or (getattr(p, "id", None) or "").strip()
        return name.lower() or "part"

    base_map: Dict[str, m21_stream.Stream] = {part_key(p): p for p in base_parts}
    inc_map: Dict[str, m21_stream.Stream] = {part_key(p): p for p in inc_parts}

    # Determine number of measures in base and in each inc part
    def measures_list(p: m21_stream.Stream) -> List[m21_stream.Measure]:
        return list(p.getElementsByClass(m21_stream.Measure))

    base_meas_counts = {part_key(p): len(measures_list(p)) for p in base_parts}
    base_total_measures = max(base_meas_counts.values() or [0])

    inc_meas_counts = {part_key(p): len(measures_list(p)) for p in inc_parts}
    # Inserted block length is max measures among incoming parts
    insert_len = max(inc_meas_counts.values() or [0])

    # Compute insertion index (1-based in musical terms); convert to 0-based for list operations
    insert_at = measure if before else measure + 1
    if insert_at < 1:
        insert_at = 1

    # Insert into matched parts and prepare rest placeholders for non-matches
    for b_key, b_part in base_map.items():
        b_measures = measures_list(b_part)
        # Clamp insertion to current available range + 1
        pos = min(max(1, insert_at), len(b_measures) + 1) - 1  # 0-based

        # Determine measure duration for rest fill using the local bar duration near insertion
        bar_ql = _measure_bar_quarter_length_near_index(b_measures, pos)

        if b_key in inc_map:
            # Insert measures copied from corresponding part in `to_add`
            inc_measures = measures_list(inc_map[b_key])
            copied = [copy.deepcopy(m) for m in inc_measures]
            # If incoming part has fewer than insert_len, pad with rest measures
            if len(copied) < insert_len:
                copied.extend(_make_rest_measures(insert_len - len(copied), bar_ql))
            for idx, m in enumerate(copied):
                b_part.insert(pos + idx, m)
        else:
            # No incoming content for this part: insert rest measures as placeholder
            fillers = _make_rest_measures(insert_len, bar_ql)
            for idx, m in enumerate(fillers):
                b_part.insert(pos + idx, m)

    # Handle incoming parts that don't exist in base: create new parts
    for i_key, i_part in inc_map.items():
        if i_key in base_map:
            continue
        new_part = m21_stream.Part()
        try:
            new_part.partName = getattr(i_part, "partName", None) or getattr(i_part, "id", None) or "Part"
        except Exception:
            pass

        # Compose new_part measures: rests before insertion, then inc content, then rests after
        inc_measures = measures_list(i_part)
        # Determine bar duration from base (fallback 4.0 if unknown)
        bar_ql_base = _bar_quarter_length_from_base(base)

        # Number of base measures before the insertion point and after it
        before_count = max(0, insert_at - 1)
        # Remaining base measures after the insertion point
        after_count = max(0, base_total_measures - before_count)

        seq: List[m21_stream.Measure] = []
        seq.extend(_make_rest_measures(before_count, bar_ql_base))
        seq.extend([copy.deepcopy(m) for m in inc_measures])
        # If incoming is shorter than insert_len, pad inside the inserted block to align others
        if len(inc_measures) < insert_len:
            seq.extend(_make_rest_measures(insert_len - len(inc_measures), bar_ql_base))
        seq.extend(_make_rest_measures(after_count, bar_ql_base))

        for m in seq:
            new_part.append(m)
        base.insert(len(base.parts), new_part)

    # Renumber measures and normalize notation
    _renumber_measures_starting_at_one(base)
    try:
        base.makeNotation()
    except Exception:
        pass

    return write_score(
        base,
        target_format=output_format,
        output=output,
    )


def _measure_bar_quarter_length_near_index(
    measures: List[m21_stream.Measure], pos0: int
) -> float:
    """Return bar duration (quarterLength) near index in a measures list."""
    if measures:
        idx = min(max(0, pos0 if pos0 < len(measures) else len(measures) - 1), len(measures) - 1)
        ts = measures[idx].getContextByClass(m21_meter.TimeSignature)
        if ts is None and idx > 0:
            ts = measures[idx - 1].getContextByClass(m21_meter.TimeSignature)
        if ts is not None:
            bd = getattr(ts, "barDuration", None)
            ql = getattr(bd, "quarterLength", None)
            if ql:
                return float(ql)
    # Fallback to 4/4
    return 4.0


def _bar_quarter_length_from_base(base: m21_stream.Score) -> float:
    """Extract a representative barDuration from the base score (fallback 4.0)."""
    try:
        first_part = (list(base.parts) or [base])[0]
        first_meas = next(iter(first_part.getElementsByClass(m21_stream.Measure)), None)
        ts = None if first_meas is None else first_meas.getContextByClass(m21_meter.TimeSignature)
        if ts is not None:
            bd = getattr(ts, "barDuration", None)
            ql = getattr(bd, "quarterLength", None)
            if ql:
                return float(ql)
    except Exception:
        pass
    return 4.0


def _make_rest_measures(count: int, bar_ql: float) -> List[m21_stream.Measure]:
    out: List[m21_stream.Measure] = []
    for _ in range(max(0, int(count))):
        m = m21_stream.Measure()
        r = m21_note.Rest()
        r.quarterLength = float(bar_ql)
        m.append(r)
        out.append(m)
    return out
