"""Test eye.py — chỉ test phần chắc chắn (không cần EVE): find/walk/center_xy.

DLL read thật cần EVE client chạy → nếu load được DLL mà không có client thì
refresh() trả None (không fail). Ship_health chưa ground → NotImplemented.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.eye import Eye  # noqa: E402

PASS = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} — {msg}")
        sys.exit(1)


# fake tree — shape giống UI tree thật (type/attrs/children/_displayX..)
FAKE = {
    "address": 1, "type": "Root", "attrs": {"_displayX": 0, "_displayY": 0,
                                            "_displayWidth": 1920, "_displayHeight": 1080},
    "children": [
        {"address": 2, "type": "ShipUI", "attrs": {"_displayX": 100, "_displayY": 200}, "children": []},
        {"address": 3, "type": "Label", "attrs": {"_setText": "Cargo bay is full",
                                                  "_displayX": 50, "_displayY": 60}, "children": []},
        {"address": 4, "type": "Label", "attrs": {"_setText": "Overview: Kikimora",
                                                  "_displayX": 500, "_displayY": 300}, "children": []},
    ],
}


def fake_eye() -> Eye:
    e = Eye.__new__(Eye)   # bỏ __init__ (không cần DLL thật cho test logic)
    e.root = FAKE
    return e


e = fake_eye()
labels = e.find(type="Label", select_many=True)
ok("find_type_all", len(labels) == 2, str(len(labels)))

full = e.find(type="Label", _setText="Cargo bay is full")
ok("find_exact", len(full) == 1 and full[0]["address"] == 3, str(full))

cargo = e.find(type="Label", _setText="Cargo", contains=True)
ok("find_contains", len(cargo) == 1 and cargo[0]["address"] == 3, str(cargo))

kik = e.find(_setText="Kikimora", contains=True)
ok("find_by_text_only", len(kik) == 1 and kik[0]["type"] == "Label", str(kik))

none_ = e.find(type="ShipUI", _setText="nope")
ok("find_none", none_ == [], str(none_))

x, y = Eye.center_xy(labels[0])
ok("center_xy", (x, y) == (50 + 0, 60 + 0) or (x, y) == (50, 60), f"{x},{y}")

x2, y2 = Eye.center_xy(e.find(type="ShipUI")[0])
ok("center_xy_shipui", (x2, y2) == (100, 200), f"{x2},{y2}")

# walk đếm đúng tổng node
ok("walk_total", len(list(Eye.walk(FAKE))) == 4, str(len(list(Eye.walk(FAKE)))))

# ship_health giờ là IMPL THẬT (schema Sanderling) — test ở block dưới với fake tree;

# DLL chưa build nếu thiếu file → FileNotFoundError rõ ràng
try:
    Eye(dll_path="Z:/khong ton tai.dll")
    ok("dll_missing_clear_error", False, "không raise")
except FileNotFoundError as ex:
    ok("dll_missing_clear_error", "chưa build" in str(ex), str(ex))

# DLL build có thật → load (không có EVE client thì initialize có thể fail → skip, không fail test)
dll_exists = (ROOT / "vendor/eve-memory-reader/x64/Release/eve-memory-reader.dll").exists()
ok("dll_built_present", dll_exists, "DLL chưa có — build lại")

# ---------- game data trên fake tree theo schema Sanderling đã ground ----------
SHIP_FAKE = {
    "address": 100, "type": "Root", "attrs": {},
    "children": [{
        "address": 101, "type": "ShipUI", "attrs": {"_displayX": 0, "_displayY": 700},
        "children": [
            {"address": 110, "type": "Gauge", "attrs": {"_name": "shieldGauge", "_lastValue": 0.87}, "children": []},
            {"address": 111, "type": "Gauge", "attrs": {"_name": "armorGauge", "_lastValue": 0.55}, "children": []},
            {"address": 112, "type": "Gauge", "attrs": {"_name": "structureGauge", "_lastValue": 1.0}, "children": []},
            {"address": 113, "type": "CapacitorContainer", "attrs": {}, "children": [
                {"address": 114, "type": "Sprite", "attrs": {"_name": "pmark", "color": {"r": 1, "g": 1, "b": 1, "a": 10}}, "children": []},
                {"address": 115, "type": "Sprite", "attrs": {"_name": "pmark", "color": {"r": 1, "g": 1, "b": 1, "a": 10}}, "children": []},
                {"address": 116, "type": "Sprite", "attrs": {"_name": "pmark", "color": {"r": 1, "g": 1, "b": 1, "a": 200}}, "children": []},
                {"address": 117, "type": "Sprite", "attrs": {"_name": "pmark", "color": {"r": 1, "g": 1, "b": 1, "a": 200}}, "children": []},
            ]},
            {"address": 118, "type": "ShipSlot", "attrs": {}, "children": [
                {"address": 119, "type": "ModuleButton", "attrs": {"isActive": True, "_displayX": 900, "_displayY": 1000, "_displayWidth": 40, "_displayHeight": 40}, "children": []},
            ]},
            {"address": 120, "type": "X", "attrs": {"_name": "indicationcontainer", "maneuverType": "Approach"}, "children": []},
        ],
    }, {
        "address": 130, "type": "OverviewWindow",
        "attrs": {"_name": "overview", "_displayX": 0, "_displayY": 500,
                  "_displayWidth": 460, "_displayHeight": 300}, "children": [
            {"address": 131, "type": "EveLabelSmall", "attrs": {"_setText": "Distance", "_displayX": 20, "_displayY": 0, "_displayWidth": 60, "_displayHeight": 18}, "children": []},
            {"address": 132, "type": "EveLabelSmall", "attrs": {"_setText": "Name", "_displayX": 90, "_displayY": 0, "_displayWidth": 60, "_displayHeight": 18}, "children": []},
            {"address": 133, "type": "EveLabelSmall", "attrs": {"_setText": "Type", "_displayX": 200, "_displayY": 0, "_displayWidth": 80, "_displayHeight": 18}, "children": []},
            {"address": 135, "type": "OverviewScrollEntry", "attrs": {"_displayX": 0, "_displayY": 24, "_displayWidth": 428, "_displayHeight": 24}, "children": [
                {"address": 136, "type": "OverviewLabel", "attrs": {"_text": "12 km", "_displayX": 20, "_displayY": 3, "_displayWidth": 60, "_displayHeight": 18}, "children": []},
                {"address": 137, "type": "OverviewLabel", "attrs": {"_text": "Kikimora", "_displayX": 90, "_displayY": 3, "_displayWidth": 60, "_displayHeight": 18}, "children": []},
                {"address": 138, "type": "OverviewLabel", "attrs": {"_text": "Triglavian", "_displayX": 200, "_displayY": 3, "_displayWidth": 80, "_displayHeight": 18}, "children": []},
            ]},
            {"address": 139, "type": "OverviewScrollEntry", "attrs": {"_displayX": 0, "_displayY": 48, "_displayWidth": 428, "_displayHeight": 24}, "children": [
                {"address": 140, "type": "OverviewLabel", "attrs": {"_text": "1 km", "_displayX": 20, "_displayY": 3, "_displayWidth": 60, "_displayHeight": 18}, "children": []},
                {"address": 141, "type": "OverviewLabel", "attrs": {"_text": "Bioadaptive Cache", "_displayX": 90, "_displayY": 3, "_displayWidth": 120, "_displayHeight": 18}, "children": []},
                {"address": 142, "type": "OverviewLabel", "attrs": {"_text": "Container", "_displayX": 200, "_displayY": 3, "_displayWidth": 80, "_displayHeight": 18}, "children": []},
            ]},
        ],
    }, {
        "address": 150, "type": "KeyActivationWindow", "attrs": {}, "children": [
            {"address": 151, "type": "Label", "attrs": {"_setText": "Do you want to travel?"}, "children": []},
            {"address": 152, "type": "Button", "attrs": {"_setText": "Confirm", "_displayX": 500, "_displayY": 400, "_displayWidth": 80, "_displayHeight": 30}, "children": []},
        ],
    }],
}


def ship_eye() -> Eye:
    e2 = Eye.__new__(Eye)
    e2.root = SHIP_FAKE
    return e2


e2 = ship_eye()

hp = e2.ship_health()
ok("ship_health_read", hp == {"shield": 0.87, "armor": 0.55, "structure": 1.0}, str(hp))

cap = e2.capacitor_percent()
ok("capacitor_pmarks", cap == 50.0, str(cap))   # 2/4 pmark alpha<20

mods = e2.module_buttons()
ok("module_buttons", len(mods) == 1 and mods[0]["is_active"] is True and mods[0]["center"] == (920, 1720), str(mods))

mv = e2.maneuver()
ok("maneuver_read", mv == "approach", str(mv))

ov = e2.overview_entries()
ok("overview_headers_mapped", len(ov) == 2 and ov[0].get("Name") == "Kikimora"
   and ov[0].get("Distance") == "12 km", str(ov[:1]))
ok("overview_cache_entry", ov[1].get("Name") == "Bioadaptive Cache", str(ov[1] if len(ov) > 1 else None))

dlg = e2.confirm_dialog()
ok("confirm_dialog_found", dlg is not None and dlg["type"] == "KeyActivationWindow"
   and "Confirm" in " ".join(dlg["texts"]), str(dlg))

# không có ShipUI → ship_health None, overview rỗng
e3 = Eye.__new__(Eye)
e3.root = {"address": 1, "type": "Root", "attrs": {}, "children": []}
ok("no_shipui_none", e3.ship_health() is None and e3.overview_entries() == []
   and e3.capacitor_percent() is None and e3.module_buttons() == [], "đáng lẽ None/[]")

print(f"\n=> {PASS} test PASS (mọi [FAIL] exit(1) ngay)")
