"""Test inventory.py — PYTHONPATH=src python tests/test_inventory.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fila_bot.inventory import InventoryEye, parse_capacity  # noqa: E402


def ok(n):
    print(f"[PASS] {n}")


def node(t, text=None, children=()):
    return {"type": t, "attrs": {"_setText": text} if text else {}, "children": list(children)}


class FakeEye:
    def __init__(self, root):
        self.root = root

    def walk(self, n):
        yield n
        for c in n.get("children", []):
            yield from self.walk(c)

    def _find_by_type(self, t, select_many=True):
        return [n for n in self.walk(self.root)] and [n for n in self.walk(self.root) if n["type"] == t]

    def abs_center(self, n):
        return (1, 2)


# 1. parse_capacity
assert parse_capacity("12.5/400.0 m³") == {"used": 12.5, "max": 400.0, "selected": None}
assert parse_capacity("1,234.5/8,000.0 m³")["max"] == 8000.0
assert parse_capacity("(3.0) 12,5/400 m³") == {"used": 12.5, "max": 400.0, "selected": 3.0}
assert parse_capacity("<color=red>0/450</color>")["max"] == 450.0
assert parse_capacity("Cargo Hold") is None
ok("parse_capacity: thường, nghìn, locale, selected, markup, sai format")

# 2. không có window → None (không đoán)
inv = InventoryEye(FakeEye(node("UIRoot")))
assert inv.window() is None and inv.capacity() is None and inv.items() is None
assert inv.has_item("x") is None and inv.fits(1) is None
ok("không có InventoryPrimary → mọi hàm None")

# 3. window đủ
tree = node("UIRoot", children=[node("InventoryPrimary", children=[
    node("InvContViewCapacityGauge", children=[node("Label", "m³"), node("Label", "120.0/400.0 m³")]),
    node("ShipCargo", children=[
        node("Item", children=[node("Label", "Encrypted Data Cache"), node("Label", "1")]),
        node("Item", children=[node("Label", "Scourge Light Missile")]),
    ])])])
inv = InventoryEye(FakeEye(tree))
assert inv.capacity() == {"used": 120.0, "max": 400.0, "selected": None}
assert inv.selected_container() == "ShipCargo"
assert [i["name"] for i in inv.items()] == ["Encrypted Data Cache", "Scourge Light Missile"]
assert inv.has_item("data cache") is True and inv.has_item("tritanium") is False
assert inv.fits(280) is True and inv.fits(281) is False
ok("window đủ: capacity, container, items, has_item, fits")

# 4. window trống → [] (khác None)
inv = InventoryEye(FakeEye(node("UIRoot", children=[node("ActiveShipCargo")])))
assert inv.items() == [] and inv.capacity() is None
ok("window trống → items [] , capacity None")

# 5. G4 GROUND: InventoryPrimary tren dump client that (TQ 2026-11-09, g4_inventory_171356)
#    capacityText '0/932.7 m ' (DLL bien m³ thanh 'm '), ShipCargo rong ('Nothing Found').
import json  # noqa: E402
from fila_bot.eye import Eye  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures" / "ui_tree_inventory_cargo.json"
real = Eye.__new__(Eye)
for _k in ("root", "_pos", "_pos_root"):
    setattr(real, _k, None)
real.root = json.loads(FIX.read_text(encoding="utf-8"))
inv = InventoryEye(real)
assert inv.window() is not None and inv.window()["type"] == "InventoryPrimary"
assert inv.capacity() == {"used": 0.0, "max": 932.7, "selected": None}, inv.capacity()
assert inv.selected_container() == "ShipCargo", inv.selected_container()
assert inv.items() == [], inv.items()
assert inv.has_item("Encoded Data Chip") is False
assert inv.fits(0.1) is True and inv.fits(933) is False
ok("G4 ground: InventoryPrimary that -> capacity 0/932.7, ShipCargo rong, fits dung")

print("ALL OK test_inventory")
