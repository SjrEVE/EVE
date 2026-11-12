"""Resolve an approach objective to ONE visible overview entry.

The objective label comes from the game's own showinfo link; the overview entry
must match that label exactly (case-insensitive) and be unique. Substring,
suffix, or "first entry" selection is rejected: an exercise vessel with a
similar name is not the mission target.
"""
from __future__ import annotations

from numbers import Real
from typing import Any

from .objective_ref import APPROACH, objective_reference


def _distance_m(raw: Any) -> float | None:
    if not isinstance(raw, str):
        return None
    text = raw.strip().lower().replace(",", "")
    try:
        if text.endswith(" km"):
            return float(text[:-3].strip()) * 1000.0
        if text.endswith(" m"):
            return float(text[:-2].strip())
    except ValueError:
        return None
    return None


def _center(value: Any) -> tuple[int, int] | None:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        return None
    if not all(isinstance(v, Real) and not isinstance(v, bool) for v in value):
        return None
    return int(value[0]), int(value[1])


def resolve_objective_target(objective_text: str | None,
                             entries: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    ref = objective_reference(objective_text)
    if not ref or ref.get("verb") != APPROACH or not ref.get("label"):
        return None
    want = str(ref["label"]).strip().casefold()
    matches = [e for e in (entries or [])
               if isinstance(e, dict) and isinstance(e.get("Name"), str)
               and e["Name"].strip().casefold() == want]
    if len(matches) != 1:
        return None
    entry = matches[0]
    center = _center(entry.get("center"))
    if center is None:
        return None
    return {
        "label": entry["Name"].strip(),
        "name": entry["Name"].strip(),
        "type_id": ref.get("type_id"),
        "item_id": ref.get("item_id"),
        "center": center,
        "distance_m": _distance_m(entry.get("Distance")),
    }
