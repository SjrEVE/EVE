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
    """Parse chuỗi Distance của overview thành mét.

    Ground LIVE 2026-11-13 (Boss: 'đọc toàn nhầm'): EVE overview Distance có
    3 dạng — '2,5 km' / '500 m' / '1.5 AU'. 'AU' là HÀNG CHỤC TRIỆU km:
    1 AU = 149.597.870.7 m. Bản cũ trả None cho AU → mọi logic 'in range'
    coi như không biết khoảng cách → orbit/lock/approach quyết sai.
    AU parse đúng đơn vị; giá trị > 1e12 m là AU thật, không phải m.
    """
    if not isinstance(raw, str):
        return None
    # EVE client luôn render locale EN-US: ',' = ngăn ngàn ('1,200 m' = 1200 m),
    # '.' = thập phân. Ground 13-11: bản cũ replace(',','') đúng cho ngàn nhưng
    # không xử AU; bản thử replace(',','.') sai '1,200 m' thành 1.2 m (x1000!).
    text = raw.strip().lower().replace(",", "")
    try:
        if text.endswith(" km"):
            return float(text[:-3].strip()) * 1000.0
        if text.endswith(" m"):
            return float(text[:-2].strip())
        if text.endswith(" au"):
            return float(text[:-3].strip()) * 149_597_870_700.0
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
