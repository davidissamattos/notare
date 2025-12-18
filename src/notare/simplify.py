"""Score simplification utilities.

This module provides a flexible framework to apply one or more simplification
algorithms to a score. Algorithms are toggled via flags and run in the order
they appear in the CLI invocation. Each algorithm can accept its own specific
parameters using a namespaced flag style (e.g., `--ornament-removal-duration`).

Currently implemented algorithms
- ornament-removal: removes grace notes, turns/trills components, and very
  short-duration neighbors using a heuristic.

Heuristic for `ornament-removal`
- Remove a note if ALL conditions are met:
  - Duration < X beats (default X = 1/8 of the local beat)
  - It is stepwise between two longer notes (neighbors exist and both longer)
  - It occurs on a weak beat (beatStrength < 0.5)

Usage examples
- Programmatic: `simplify_score(algorithms=[["ornament_removal", {"duration": "1/8"}]])`
- CLI: `notare simplify --source in.musicxml --ornament-removal --output out.musicxml`
- CLI with parameter: `notare simplify --ornament-removal --ornament-removal-duration "1/8"`

Notes
- "Beat" refers to the metric beat as determined by the local time signature.
  In 4/4, a beat is a quarter note (quarterLength = 1.0). In compound meters
  like 6/8, a beat is typically a dotted quarter (quarterLength = 1.5).
- The duration threshold is computed as (local beat duration) * (ratio), where
  ratio is parsed from strings like "1/8", "0.25", etc.
"""

from __future__ import annotations

from typing import BinaryIO, Callable, Dict, Iterable, List, Tuple

from music21 import interval as m21_interval
from music21 import meter as m21_meter
from music21 import note as m21_note
from music21 import stream as m21_stream
from music21 import expressions as m21_expr
from music21 import spanner as m21_spanner

from .utils import load_score, write_score, _parse_measure_spec, _select_parts


# --- Public API ---

def simplify_score(
	*,
	source: str | None = None,
	output: str | None = None,
	output_format: str | None = None,
	algorithms: List[Tuple[str, Dict[str, str]]] | None = None,
	measures: str | None = None,
	part_names: str | None = None,
	part_numbers: str | None = None,
	stdin_data: bytes | None = None,
	stdout_buffer: BinaryIO | None = None,
) -> str:
	"""Apply simplification algorithms to the input score and persist the result.

	Args
	- source: Path to input file. Omit to read from stdin (pipe).
	- output: Path to write the result. Omit to stream to stdout.
	- output_format: Explicit output format when writing (e.g., `musicxml`).
	- algorithms: Ordered list of (algorithm_name, params) to apply.
	  Example: `[('ornament_removal', {'duration': '1/8'})]`.
	- measures / part_names / part_numbers: Scoping options; when omitted, algorithms apply to the entire score.
	- stdin_data / stdout_buffer: Raw data buffers for piping.

	Returns
	- Message from `write_score` if writing to a file, otherwise empty string when streaming to stdout.
	"""
	score = load_score(source, stdin_data=stdin_data)

	# Determine selection scopes
	ranges = _parse_measure_spec(measures)
	try:
		selected_parts = _select_parts(score, part_names=part_names, part_numbers=part_numbers)
	except ValueError:
		# If explicit selection did not match any part, apply to none
		selected_parts = []

	# Resolve algorithms (defaults to no-op if none provided)
	for name, params in _normalize_algorithms(algorithms or []):
		func = _ALGORITHM_REGISTRY.get(name)
		if func is None:
			# Unknown algorithm: skip safely
			continue
		# Inject selection context into params so algorithms can scope their work
		full_params = dict(params or {})
		full_params["_ranges"] = ranges
		full_params["_parts"] = selected_parts
		func(score, **full_params)

	# Normalize notational representation for safe export
	try:
		score.makeNotation()
	except Exception:
		pass

	message = write_score(
		score,
		target_format=output_format,
		output=output,
		stdout_buffer=stdout_buffer,
	)
	return message


# --- Algorithm registration ---

AlgorithmFunc = Callable[[m21_stream.Score], None]


def _normalize_algorithms(
	items: Iterable[Tuple[str, Dict[str, str]]],
) -> List[Tuple[str, Dict[str, str]]]:
	"""Validate and normalize the incoming algorithms list.

	Lower-cases names and ensures params are dicts with string keys/values.
	"""
	normalized: List[Tuple[str, Dict[str, str]]] = []
	for name, params in items:
		key = str(name).strip().lower().replace("-", "_")
		clean_params: Dict[str, str] = {}
		for pkey, pval in (params or {}).items():
			clean_params[str(pkey)] = str(pval)
		normalized.append((key, clean_params))
	return normalized


_ALGORITHM_REGISTRY: Dict[str, Callable[[m21_stream.Score], None]] = {}


def register_algorithm(name: str, func: Callable[[m21_stream.Score], None]) -> None:
	"""Register an algorithm function under a normalized name."""
	key = str(name).strip().lower().replace("-", "_")
	_ALGORITHM_REGISTRY[key] = func


# --- Ornament removal implementation ---

def _parse_ratio(value: str | None, default: float = 1.0 / 8.0) -> float:
	"""Parse ratio strings like '1/8' or decimals like '0.125' into floats."""
	if not value:
		return float(default)
	text = str(value).strip()
	if "/" in text:
		num_str, den_str = text.split("/", 1)
		try:
			num = float(num_str.strip())
			den = float(den_str.strip())
			if den == 0:
				return float(default)
			return float(num / den)
		except Exception:
			return float(default)
	try:
		return float(text)
	except Exception:
		return float(default)


def _local_beat_quarter_length(n: m21_note.Note) -> float:
	"""Return the local beat duration in quarterLength units for the note context."""
	try:
		ts = n.getContextByClass(m21_meter.TimeSignature)
		if ts is None:
			return 1.0
		# music21 represents beat duration as a Duration object
		bd = getattr(ts, "beatDuration", None)
		ql = getattr(bd, "quarterLength", None)
		return float(ql) if ql is not None else 1.0
	except Exception:
		return 1.0


def _is_stepwise(n1: m21_note.Note, n2: m21_note.Note) -> bool:
	"""Return True if the interval between notes is a step (M2 or m2)."""
	try:
		itv = m21_interval.Interval(n1, n2)
		semis = abs(int(round(itv.semitones)))
		return semis in (1, 2)
	except Exception:
		return False


def _is_weak_beat(n: m21_note.Note) -> bool:
	"""Return True if the note occurs on a weak beat (beatStrength < 0.5)."""
	try:
		strength = float(getattr(n, "beatStrength", 0.0))
		return strength < 0.5
	except Exception:
		return True


def _number_in_ranges(num: int, ranges: List[Tuple[int, int]]) -> bool:
	if not ranges:
		return True
	for start, end in ranges:
		if start <= num <= end:
			return True
	return False


def _ornament_removal(
	score: m21_stream.Score,
	*,
	duration: str | None = None,
	_ranges: List[Tuple[int, int]] | None = None,
	_parts: List[m21_stream.Stream] | None = None,
) -> None:
	"""Remove candidate ornament notes based on duration, context, and metric position.

	Parameters
	- duration: Ratio of the beat to use as the maximum ornament length (e.g., '1/8').
	  Defaults to '1/8'. The actual threshold in quarterLength is: localBeatQL * ratio.
	- _ranges: Optional measure ranges to limit application.
	- _parts: Optional list of parts/streams to limit application.
	"""
	ratio = _parse_ratio(duration, default=1.0 / 8.0)

	parts = _parts if (_parts is not None and len(_parts) > 0) else (list(score.parts) or [score])
	for part in parts:
		# First remove ornament mark objects (trills, turns, mordents, etc.) and trill extensions
		_remove_ornament_objects(part)
		notes: List[m21_note.Note] = [n for n in part.recurse().notes if isinstance(n, m21_note.Note)]
		to_remove: List[m21_note.Note] = []

		# Pass 1: remove all grace notes unconditionally (including first/last notes)
		for n in notes:
			is_grace_any = bool(getattr(getattr(n, "duration", None), "isGrace", False)) or (
				float(getattr(getattr(n, "duration", None), "quarterLength", 0.0) or 0.0) == 0.0
			)
			in_selected_measures_any = True
			if _ranges:
				meas_any = n.getContextByClass(m21_stream.Measure)
				try:
					num_any = int(getattr(meas_any, "number", 0) or 0) if meas_any is not None else 0
				except Exception:
					num_any = 0
				in_selected_measures_any = _number_in_ranges(num_any, _ranges)
			if is_grace_any and in_selected_measures_any:
				to_remove.append(n)
		for i in range(1, len(notes) - 1):
			n_prev = notes[i - 1]
			n = notes[i]
			n_next = notes[i + 1]

			beat_ql = _local_beat_quarter_length(n)
			threshold = beat_ql * ratio
			ql = float(getattr(n.duration, "quarterLength", 0.0) or 0.0)
			# Detect grace via duration attribute or zero-length duration
			is_grace = bool(getattr(getattr(n, "duration", None), "isGrace", False)) or (
				float(getattr(getattr(n, "duration", None), "quarterLength", 0.0) or 0.0) == 0.0
			)

			cond_duration = (ql < threshold)
			prev_longer = float(getattr(n_prev.duration, "quarterLength", 0.0) or 0.0) >= threshold
			next_longer = float(getattr(n_next.duration, "quarterLength", 0.0) or 0.0) >= threshold
			cond_neighbors = prev_longer and next_longer
			cond_stepwise = _is_stepwise(n_prev, n) and _is_stepwise(n, n_next)
			cond_weak = _is_weak_beat(n)

			# Scope to selected measure ranges when provided
			in_selected_measures = True
			if _ranges:
				meas = n.getContextByClass(m21_stream.Measure)
				try:
					num = int(getattr(meas, "number", 0) or 0) if meas is not None else 0
				except Exception:
					num = 0
				in_selected_measures = _number_in_ranges(num, _ranges)

			if in_selected_measures and cond_duration and cond_neighbors and cond_stepwise and cond_weak:
				to_remove.append(n)

		# Remove in a separate pass to avoid messing with iteration
		for n in to_remove:
			try:
				site = n.activeSite
				if site is not None:
					site.remove(n)
			except Exception:
				pass


def _remove_ornament_objects(target: m21_stream.Stream) -> None:
	"""Remove ornament markings like trills, turns, mordents and trill spanners."""
	# Remove expression ornaments attached to notes/streams
	try:
		for expr in list(target.recurse().getElementsByClass(m21_expr.Ornament)):
			site = expr.activeSite
			if site is not None:
				site.remove(expr)
	except Exception:
		pass

	# Remove trill extensions (spanners)
	try:
		for sp in list(target.recurse().getElementsByClass(m21_spanner.Spanner)):
			if isinstance(sp, m21_spanner.TrillExtension):
				for site in list(sp.getSites() or []):
					try:
						site.remove(sp)
					except Exception:
						pass
	except Exception:
		pass


# Register algorithms with context-aware wrapper
_ALGORITHM_REGISTRY["ornament_removal"] = lambda s, **p: _ornament_removal(
	s,
	duration=p.get("duration"),
	_ranges=p.get("_ranges"),
	_parts=p.get("_parts"),
)


