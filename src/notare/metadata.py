"""Metadata inspection and editing utilities.

This module reports a concise, human-friendly summary with:
- Title, Subtitle, Composer, Arranger
- Number of Measures, Number of Parts
- For each part: Clefs present, Key Signatures (accidentals count), Musical Key, Tempos

It also supports simple metadata updates (e.g., title, composer) when requested.
"""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO
import xml.etree.ElementTree as ET

from music21 import metadata as m21_metadata
from music21 import stream as m21_stream
from music21 import key as m21_key
from music21 import clef as m21_clef
from music21 import tempo as m21_tempo

from .utils import infer_format_from_path, load_score, write_score


def metadata_summary(
    *,
    source: str | None = None,
    output: str | None = None,
    output_format: str | None = None,
    stdin_data: bytes | None = None,
    stdout_buffer: BinaryIO | None = None,
    fields: list[str] | None = None,
    updates: dict[str, str | None] | None = None,
) -> str:
    """Generate a comprehensive metadata summary and optionally update fields.

    The summary includes title/subtitle/composer/arranger, measure/part counts,
    and for each part: clefs, key signatures (accidentals count), musical key,
    and all tempos present in that part.
    """
    score = load_score(source, stdin_data=stdin_data)

    # If updates are provided, apply and write; return write message.
    update_payload = {k: v for k, v in (updates or {}).items() if v is not None}
    if update_payload and output is not None:
        _apply_metadata_updates(score, update_payload)
        return write_score(
            score,
            target_format=output_format,
            output=output,
            stdout_buffer=stdout_buffer,
        )

    # If specific fields are requested, output only those (single-value friendly).
    if fields:
        # Split requested fields into general vs part-related and print both when mixed
        part_related = {"key_signature", "musical_key", "tempo", "clef"}
        general_fields = [f for f in fields if f not in part_related]
        part_fields = [f for f in fields if f in part_related]

        lines: list[str] = []

        # Handle general fields
        if general_fields:
            values = _extract_single_fields(score, source_path=source, stdin_data=stdin_data)
            selected = {f: values.get(f) for f in general_fields if f in values}
            if len(selected) == 1 and not part_fields:
                return next(iter(selected.values())) or ""
            LABELS = {
                "title": "Title",
                "subtitle": "Subtitle",
                "author": "Author",
                "format": "Format",
                "rights": "Rights",
                "software": "Encoding Software",
                "composer": "Composer",
                "arranger": "Arranger",
                "number_parts": "Number of Parts",
                "number_measures": "Number of Measures",
            }
            for k in general_fields:
                if k in selected:
                    lines.append(f"{LABELS.get(k, k.title())}: {selected[k] or ''}")

        # Handle part-related fields
        if part_fields:
            part_output = _print_part_fields(score, requested_fields=part_fields)
            if part_output:
                if lines:
                    lines.append("")
                lines.append(part_output)

        return "\n".join(lines)

    # Otherwise, produce the new detailed summary for stdout.
    return _build_detailed_summary(score, source_path=source, stdin_data=stdin_data)


def set_metadata(
    *,
    source: str | None = None,
    output: str | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    author: str | None = None,
    format: str | None = None,
    rights: str | None = None,
    composer: str | None = None,
    arranger: str | None = None,
    stdin_data: bytes | None = None,
    stdout_buffer: BinaryIO | None = None,
) -> str:
    """Set a single general metadata attribute and write the score.

    Allowed fields: title, subtitle, author, format, rights, composer, arranger.
    Exactly one of these must be provided.
    """
    score = load_score(source, stdin_data=stdin_data)
    provided = {
        k: v
        for k, v in {
            "title": title,
            "subtitle": subtitle,
            "author": author,
            "format": format,
            "rights": rights,
            "composer": composer,
            "arranger": arranger,
        }.items()
        if v is not None
    }
    if len(provided) != 1:
        raise ValueError(
            "Provide exactly one field to set: one of --title, --subtitle, --author, --format, --rights, --composer, --arranger"
        )

    field, value = next(iter(provided.items()))

    if score.metadata is None:
        score.metadata = m21_metadata.Metadata()
    meta = score.metadata

    if field == "title":
        meta.title = str(value)
    elif field == "subtitle":
        # Prefer movementName; also mirror to subtitle if present
        try:
            meta.movementName = str(value)
        except Exception:
            pass
        try:
            setattr(meta, "subtitle", str(value))
        except Exception:
            pass
    elif field == "author":
        _set_custom_value(meta, "Author", str(value))
    elif field == "format":
        meta.fileFormat = str(value)
    elif field == "rights":
        try:
            meta.rights = str(value)
        except Exception:
            _set_custom_value(meta, "Rights", str(value))
    elif field == "composer":
        meta.composer = str(value)
    elif field == "arranger":
        meta.arranger = str(value)
    else:
        raise ValueError(f"Unsupported field: {field}")

    return write_score(
        score,
        target_format=None,
        output=output,
        stdout_buffer=stdout_buffer,
    )


def _build_detailed_summary(score: m21_stream.Score, source_path: str | None, stdin_data: bytes | None) -> str:
    meta = score.metadata or m21_metadata.Metadata()

    title = (
        _safe_meta_attr(meta, "title")
        or _safe_meta_attr(meta, "workTitle")
        or _get_custom_value(meta, "Title")
        or _get_custom_value(meta, "Work Title")
        or _get_custom_value(meta, "work-title")
        or "Unknown"
    )
    subtitle = (
        _safe_meta_attr(meta, "movementName")
        or _safe_meta_attr(meta, "subtitle")
        or _get_custom_value(meta, "Subtitle")
        or ""
    )
    composer = _safe_meta_attr(meta, "composer") or "Unknown"
    arranger = _safe_meta_attr(meta, "arranger") or "Unknown"
    

    parts = list(score.parts)
    num_parts = len(parts) if parts else 0
    num_measures = _estimate_measure_count(score, parts)

    lines: list[str] = []
    lines.append(f"Title: {title}")
    lines.append(f"Subtitle: {subtitle}")
    lines.append(f"Composer: {composer}")
    lines.append(f"Arranger: {arranger}")
    lines.append(f"Number of Measures: {num_measures}")
    lines.append(f"Number of Parts: {num_parts}")

    musical_key = _analyze_musical_key(score)
    lines.append(f"Main musical Key: {musical_key}")

    rights = _collect_rights(meta, source_path=source_path, stdin_data=stdin_data)
    softwares = _collect_encoding_software(meta, source_path=source_path, stdin_data=stdin_data)
    lines.append(f"Rights: {rights if rights else 'Unknown'}")
    lines.append(f"Encoding Software: {', '.join(softwares) if softwares else 'Unknown'}")

    targets = parts if parts else [score]
    for idx, part in enumerate(targets, start=1):
        part_label = getattr(part, "partName", None) or getattr(part, "id", None) or f"Part {idx}"
        lines.append("")
        lines.append(f"Part {idx}: {part_label}")

        clefs = _collect_clefs(part)
        ksigs = _collect_key_signatures(part)
        tempos = _collect_tempos(part)

        lines.append(f"- Clefs: {', '.join(clefs) if clefs else 'Unknown'}")
        lines.append(f"- Key Signatures: {', '.join(ksigs) if ksigs else 'Unknown'}")
        
        lines.append(f"- Tempos: {', '.join(tempos) if tempos else 'Unknown'}")

    return "\n".join(lines)


def _extract_single_fields(
    score: m21_stream.Score,
    *,
    source_path: str | None,
    stdin_data: bytes | None,
) -> dict[str, str]:
    meta = score.metadata or m21_metadata.Metadata()

    title = _safe_meta_attr(meta, "title") or _get_custom_value(meta, "Title") or ""
    subtitle = (
        _safe_meta_attr(meta, "movementName")
        or _safe_meta_attr(meta, "subtitle")
        or _get_custom_value(meta, "Subtitle")
        or ""
    )
    author = _get_custom_value(meta, "Author") or ""
    fmt = getattr(meta, "fileFormat", None) or infer_format_from_path(source_path, default="musicxml")
    rights = _collect_rights(meta, source_path=source_path, stdin_data=stdin_data)
    softwares_list = _collect_encoding_software(meta, source_path=source_path, stdin_data=stdin_data)
    softwares = ", ".join(softwares_list)
    composer = _safe_meta_attr(meta, "composer") or ""
    arranger = _safe_meta_attr(meta, "arranger") or ""

    parts = list(score.parts)
    num_parts = len(parts) if parts else 0
    num_measures = _estimate_measure_count(score, parts)

    # Score-wide key signature (accidentals) aggregated across parts
    ksigs = set()
    targets = parts if parts else [score]
    for p in targets:
        for token in _collect_key_signatures(p):
            ksigs.add(token)
    key_signature = ", ".join(sorted(ksigs))

    # Musical key detected on the full score
    musical_key = _analyze_musical_key(score)

    # Aggregate tempos across score
    tempo_values = set()
    try:
        for mm in score.recurse().getElementsByClass(m21_tempo.MetronomeMark):
            number = getattr(mm, "number", None)
            text = getattr(mm, "text", None)
            if number is not None:
                try:
                    tempo_values.add(f"{int(number)} BPM")
                except Exception:
                    tempo_values.add(f"{number} BPM")
            elif text:
                tempo_values.add(str(text))
    except Exception:
        pass
    tempo = ", ".join(sorted(tempo_values))

    return {
        "title": title,
        "subtitle": subtitle,
        "author": author,
        "format": fmt,
        "rights": rights,
        "software": softwares,
        "composer": composer,
        "arranger": arranger,
        "number_parts": str(num_parts),
        "number_measures": str(num_measures),
        "key_signature": key_signature,
        "musical_key": musical_key,
        "tempo": tempo,
    }


def _print_part_fields(score: m21_stream.Score, *, requested_fields: list[str]) -> str:
    parts = list(score.parts) or [score]
    lines: list[str] = []
    # For each requested part-related field, print values per part
    for field in requested_fields:
        if field not in {"key_signature", "musical_key", "tempo", "clef"}:
            continue
        # Header for the field
        header = {
            "key_signature": "Key Signature",
            "musical_key": "Musical Key",
            "tempo": "Tempo",
            "clef": "Clefs",
        }[field]
        lines.append(f"{header}:")
        for idx, part in enumerate(parts, start=1):
            part_label = getattr(part, "partName", None) or getattr(part, "id", None) or f"Part {idx}"
            if field == "key_signature":
                vals = ", ".join(_collect_key_signatures(part)) or ""
            elif field == "musical_key":
                vals = _analyze_musical_key(part)
            elif field == "tempo":
                vals = ", ".join(_collect_tempos(part)) or ""
            else:  # clef
                vals = ", ".join(_collect_clefs(part)) or ""
            lines.append(f"- {part_label}: {vals}")
        lines.append("")
    return "\n".join(lines).strip()


def _estimate_measure_count(score: m21_stream.Score, parts: list[m21_stream.Stream]) -> int:
    if parts:
        return max(
            (
                len(list(part.getElementsByClass(m21_stream.Measure)))
                for part in parts
            ),
            default=0,
        )
    return len(list(score.getElementsByClass(m21_stream.Measure)))


def _analyze_musical_key(stream_obj: m21_stream.Stream) -> str:
    try:
        k = stream_obj.analyze("key")
        return k.name
    except Exception:  # analysis is best-effort
        return "Unknown"


def _apply_metadata_updates(score: m21_stream.Score, updates: dict[str, str]) -> None:
    if not updates:
        return
    if score.metadata is None:
        score.metadata = m21_metadata.Metadata()
    meta = score.metadata

    for field, value in updates.items():
        text_value = str(value)
        if field in {"title", "author", "composer", "arranger"}:
            if field == "author":
                _set_custom_value(meta, "Author", text_value)
            else:
                setattr(meta, field, text_value)
        elif field == "format":
            meta.fileFormat = text_value
        else:
            label = field.replace("_", " ").title()
            _set_custom_value(meta, label, text_value)


def _safe_meta_attr(meta: m21_metadata.Metadata, attribute: str) -> str | None:
    try:
        return getattr(meta, attribute)
    except AttributeError:
        return None


def _get_custom_value(meta: m21_metadata.Metadata, label: str) -> str | None:
    try:
        entries = list(meta.all())
    except Exception:
        return None
    for entry in reversed(entries):
        name = getattr(entry, "name", None)
        value = getattr(entry, "value", None)
        if name is None and isinstance(entry, tuple) and len(entry) >= 2:
            name, value = entry[0], entry[1]
        if name and name.lower() == label.lower():
            return "" if value is None else str(value)
    return None


def _set_custom_value(meta: m21_metadata.Metadata, label: str, value: str) -> None:
    meta.add(label, value)


def _collect_clefs(part: m21_stream.Stream) -> list[str]:
    names: list[str] = []
    try:
        seen = set()
        for c in part.recurse().getElementsByClass(m21_clef.Clef):
            label = getattr(c, "name", None) or getattr(c, "sign", None) or str(c)
            if not label:
                continue
            if label not in seen:
                seen.add(label)
                names.append(str(label))
    except Exception:
        pass
    return names


def _collect_key_signatures(part: m21_stream.Stream) -> list[str]:
    """Return unique key signatures in human-friendly form per part.

    Format examples:
    - "2 sharps" for +2
    - "1 flat" for -1
    - "0 (no accidentals)" for 0
    """
    tokens: list[str] = []
    try:
        seen = set()
        for ks in part.recurse().getElementsByClass(m21_key.KeySignature):
            sharps = getattr(ks, "sharps", None)
            if sharps is None:
                continue
            label: str
            if isinstance(sharps, int):
                if sharps > 0:
                    label = f"{sharps} sharp{'s' if sharps != 1 else ''}"
                elif sharps < 0:
                    n = abs(sharps)
                    label = f"{n} flat{'s' if n != 1 else ''}"
                else:
                    label = "0 (no accidentals)"
            else:
                label = str(sharps)
            if label not in seen:
                seen.add(label)
                tokens.append(label)
    except Exception:
        pass
    return tokens


def _collect_tempos(part: m21_stream.Stream) -> list[str]:
    values: list[str] = []
    try:
        seen = set()
        # Prefer MetronomeMark occurrences
        for mm in part.recurse().getElementsByClass(m21_tempo.MetronomeMark):
            label = None
            number = getattr(mm, "number", None)
            text = getattr(mm, "text", None)
            if number is not None:
                try:
                    label = f"{int(number)} BPM"
                except Exception:
                    label = f"{number} BPM"
            elif text:
                label = str(text)
            if label and label not in seen:
                seen.add(label)
                values.append(label)
    except Exception:
        pass
    return values


def _collect_rights(meta: m21_metadata.Metadata, *, source_path: str | None, stdin_data: bytes | None) -> str:
    # Prefer structured metadata
    try:
        rights = getattr(meta, "rights", None)
        if isinstance(rights, str) and rights.strip():
            return rights.strip()
        # Try custom label
        cv = _get_custom_value(meta, "Rights")
        if cv:
            return cv
    except Exception:
        pass

    # Try reading from the raw XML when available (MusicXML)
    xml_text = _read_xml_text(source_path=source_path, stdin_data=stdin_data)
    if xml_text:
        try:
            root = ET.fromstring(xml_text)
            ns = ""  # musicxml often has no namespace in many files
            for node in root.findall(".//identification/rights"):
                if node.text and node.text.strip():
                    return node.text.strip()
        except Exception:
            pass
    return ""


def _collect_encoding_software(meta: m21_metadata.Metadata, *, source_path: str | None, stdin_data: bytes | None) -> list[str]:
    softwares: list[str] = []
    seen: set[str] = set()
    # Try custom metadata entries first
    try:
        for label in ("Software", "Encoding Software", "Generator"):
            vals = _get_all_custom_values(meta, label)
            for v in vals:
                vv = v.strip()
                if vv and vv not in seen:
                    seen.add(vv)
                    softwares.append(vv)
    except Exception:
        pass

    # Fall back to parsing MusicXML identification/encoding/software
    xml_text = _read_xml_text(source_path=source_path, stdin_data=stdin_data)
    if xml_text:
        try:
            root = ET.fromstring(xml_text)
            for node in root.findall(".//identification/encoding/software"):
                if node.text:
                    vv = node.text.strip()
                    if vv and vv not in seen:
                        seen.add(vv)
                        softwares.append(vv)
        except Exception:
            pass
    return softwares


def _read_xml_text(*, source_path: str | None, stdin_data: bytes | None) -> str | None:
    # Only read plain MusicXML/XML text; ignore binary containers like .mxl here
    try:
        if source_path:
            p = Path(source_path)
            if p.exists() and p.suffix.lower() in {".xml", ".musicxml"}:
                return p.read_text(encoding="utf-8", errors="ignore")
        if stdin_data:
            try:
                return stdin_data.decode("utf-8", errors="ignore")
            except Exception:
                return None
    except Exception:
        return None
    return None


def _get_all_custom_values(meta: m21_metadata.Metadata, label: str) -> list[str]:
    values: list[str] = []
    try:
        entries = list(meta.all())
    except Exception:
        return values
    for entry in entries:
        name = getattr(entry, "name", None)
        value = getattr(entry, "value", None)
        if name is None and isinstance(entry, tuple) and len(entry) >= 2:
            name, value = entry[0], entry[1]
        if name and str(name).lower() == label.lower():
            if value is None:
                values.append("")
            else:
                values.append(str(value))
    return values
