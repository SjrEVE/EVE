"""Inventory (M3 task 3.2) — đọc cửa sổ inventory: dung tích + item. READ-ONLY.

Schema ỨNG VIÊN từ Viir ParseUserInterface.elm 2097-2262 (docs/VIIR_FRAMEWORK_NOTES.md §2).
CHƯA ground trên client Photon (G4) → mọi hàm trả None khi không thấy node, KHÔNG đoán.
Kéo thả item (move_to_cargo) cố ý chưa có: chỉ viết sau khi có dump G4 thật.
"""
from __future__ import annotations

import re
from typing import Any

WINDOW_TYPES = ("InventoryPrimary", "ActiveShipCargo")
CONTAINER_TYPES = ("ShipCargo", "ShipDroneBay", "ShipGeneralMiningHold", "StationItems",
                   "ShipFleetHangar", "StructureItemHangar")
_NUM = r"([0-9][0-9.,\s]*)"
TREE_TYPES = ("TreeViewEntryWithTag", "TreeViewEntryInventoryCargo", "TreeViewEntryInventory")


def _text(n: dict[str, Any]) -> str | None:
    a = n.get("attrs") or {}
    t = a.get("_setText") or a.get("_text")
    return t if isinstance(t, str) and t.strip() else None


def _num(s: str) -> float | None:
    s = re.sub(r"\s", "", s)
    if s.count(",") and s.count("."):
        s = s.replace(",", "")             # 1,234.5
    elif s.count(",") == 1 and len(s.split(",")[1]) <= 2:
        s = s.replace(",", ".")            # 12,5 (locale)
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def parse_capacity(text: str) -> dict[str, float | None] | None:
    """'12.5/400.0 m³' → {used, max}. '(3.0) 12.5/400 m³' → thêm selected. Sai format → None."""
    clean = re.sub(r"<[^>]*>", "", str(text))
    sel = None
    m = re.match(rf"\s*\(\s*{_NUM}\)\s*(.*)", clean)
    if m:
        sel, clean = _num(m.group(1)), m.group(2)
    m = re.search(rf"{_NUM}\s*/\s*{_NUM}", clean)
    if not m:
        return None
    used, mx = _num(m.group(1)), _num(m.group(2))
    if used is None:
        return None
    return {"used": used, "max": mx, "selected": sel}


class InventoryEye:
    def __init__(self, eye: Any) -> None:
        self.eye = eye

    def window(self) -> dict[str, Any] | None:
        for t in WINDOW_TYPES:
            found = self.eye._find_by_type(t, select_many=True) or []
            if found:
                return found[0]
        return None

    def capacity(self) -> dict[str, float | None] | None:
        w = self.window()
        if w is None:
            return None
        for n in self.eye.walk(w):
            if "CapacityGauge" in str(n.get("type", "")):
                texts = [t for t in (_text(x) for x in self.eye.walk(n)) if t]
                texts.sort(key=len, reverse=True)
                return parse_capacity(texts[0]) if texts else None
        return None

    def selected_container(self) -> str | None:
        w = self.window()
        if w is None:
            return None
        for n in self.eye.walk(w):
            if n.get("type") in CONTAINER_TYPES:
                return n.get("type")
        return None

    def items(self) -> list[dict[str, Any]] | None:
        """[{name, texts, center}] — None nếu không có window (khác list rỗng = window trống)."""
        w = self.window()
        if w is None:
            return None
        out = []
        for n in self.eye.walk(w):
            t = str(n.get("type", ""))
            if t == "Item" or "InvItem" in t:
                texts = [x for x in (_text(c) for c in self.eye.walk(n)) if x]
                if texts:
                    out.append({"name": re.sub(r"<[^>]*>", "", texts[0]).strip(),
                                "texts": texts, "center": self.eye.abs_center(n)})
        return out

    def has_item(self, name: str) -> bool | None:
        items = self.items()
        if items is None:
            return None
        want = name.strip().lower()
        return any(want in i["name"].lower() for i in items)

    def fits(self, volume_m3: float) -> bool | None:
        cap = self.capacity()
        if not cap or cap.get("max") is None:
            return None
        return cap["max"] - cap["used"] >= volume_m3

    def tree_entries(self) -> list[dict[str, Any]] | None:
        """Cay hangar ben trai: [{name, label, center}]. Catalog g4_inventory_171356:
        TreeViewEntryWithTag (ItemHangar/StationShips), TreeViewEntryInventoryCargo (ShipHangar
        = tau dang lai), TreeViewEntryInventory (ShipDroneBay...). center = topCont_<name>
        (node cha cao ca phan childCont nen KHONG dung tam node cha)."""
        w = self.window()
        if w is None:
            return None
        out: list[dict[str, Any]] = []
        for n in self.eye.walk(w):
            if n.get("type") not in TREE_TYPES:
                continue
            name = (n.get("attrs") or {}).get("_name")
            top = next((c for c in (n.get("children") or [])
                        if (c.get("attrs") or {}).get("_name") == f"topCont_{name}"), None)
            if not name or top is None:
                continue
            label = next((t for t in (_text(x) for x in self.eye.walk(top)) if t), None)
            out.append({"name": name, "label": label, "center": self.eye.abs_center(top)})
        return out

    def tree_entry_xy(self, name: str) -> tuple[int, int] | None:
        """Toa do entry theo _name dung (vd 'ItemHangar', 'ShipHangar'). Khong thay -> None."""
        for e in self.tree_entries() or []:
            if e["name"] == name:
                return e["center"]
        return None
