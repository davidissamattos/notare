"""Score analysis utilities."""

from __future__ import annotations

from collections import OrderedDict
from typing import BinaryIO

from music21 import analysis, note

from .utils import load_score


def analyze_score(
    *,
    source: str | None = None,
    stdin_data: bytes | None = None,
    metrics: list[str] | None = None,
) -> str:
    """Return requested analysis metrics for a score."""
    score = load_score(source, stdin_data=stdin_data)
    requested = metrics or list(_METRIC_FUNCTIONS.keys())

    results: list[str] = []
    for metric in requested:
        func = _METRIC_FUNCTIONS.get(metric)
        if func is None:
            raise ValueError(f"Unsupported metric '{metric}'. Available: {', '.join(_METRIC_FUNCTIONS)}")
        try:
            value = func(score)
        except Exception:
            value = "N/A"
        results.append(f"{_METRIC_LABELS.get(metric, metric.title())}: {value}")
    return "\n".join(results)


def _compute_key(score) -> str:
    analyzed_key = score.analyze("key")
    return f"{analyzed_key.tonic.name} {analyzed_key.mode}".replace("-", "b")


def _compute_npvi(score) -> float:
    durations = [n.quarterLength for n in score.recurse().notes if isinstance(n, note.Note)]
    pairs = list(zip(durations[:-1], durations[1:]))
    if not pairs:
        return 0.0
    diffs = [abs(d1 - d2) / ((d1 + d2) / 2) for d1, d2 in pairs if (d1 + d2)]
    return round(100 * (sum(diffs) / len(diffs)), 2) if diffs else 0.0


_METRIC_FUNCTIONS = {
    "key": _compute_key,
    "npvi": _compute_npvi,
}

_METRIC_LABELS = OrderedDict(
    [
        ("key", "Key"),
        ("npvi", "nPVI"),
    ]
)
