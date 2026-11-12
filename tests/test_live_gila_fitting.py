"""Regression: doc active hull tu FittingWindow that, KHONG tu nut lobby.

Ground 11-11 tren client live `EVE - Kompi Yaken`: `nameCaption` = "Gila - Kompi
Yaken", trong khi LobbyWnd van hien "Board my Corvette". Doc nut lobby thanh
"corvette" la suy luan sai (da bi Boss bat). Cham dut bang cach chi tin panel
duoc quan sat that.

Chay: PYTHONPATH=src python tests/test_live_gila_fitting.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.eye import Eye  # noqa: E402
from fila_bot.world_snapshot import parse_world  # noqa: E402

PASS = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} — {msg}")
        sys.exit(1)


def eye_from(root: dict) -> Eye:
    e = Eye.__new__(Eye)
    e.root = root
    e._pos = None
    e._pos_root = None
    return e


FIX = ROOT / "tests" / "fixtures" / "ui_tree_live_gila_fitting.json"
live = json.loads(FIX.read_text(encoding="utf-8"))
e = eye_from(live)

observed, ship = e.active_ship_observation()
assert observed is True and ship == {"name": "Gila - Kompi Yaken", "hull": "Gila"}, (observed, ship)
ok("FittingWindow live: active hull = Gila - Kompi Yaken (khong phai corvette)", True)

s = parse_world(e)
assert s.ship_panel_observed is True and s.active_ship and s.active_ship["hull"] == "Gila", s.active_ship
ok("parse_world -> ship_panel_observed=True, active_ship.hull=Gila", True)

# Nut "Board my Corvette" chi la candidate: khong duoc phep thanh active hull.
lobby_only = {
    "type": "UIRoot",
    "children": [{
        "type": "LobbyWnd",
        "attrs": {"_name": "lobbyWnd"},
        "children": [{"type": "EveLabelMedium",
                      "attrs": {"_name": "label", "_setText": "Board my Corvette"}}],
    }],
}
o2, s2 = eye_from(lobby_only).active_ship_observation()
assert (o2, s2) == (False, None), (o2, s2)
ok("nut lobby 'Board my Corvette' KHONG duoc dung lam bang chung hull", True)

# FittingWindow dang load (chua co nameCaption) -> observed nhung UNKNOWN, khong doan.
loading = {
    "type": "UIRoot",
    "children": [{
        "type": "FittingWindow",
        "attrs": {"_name": "fittingWnd"},
        "children": [{"type": "LoadingWheel", "attrs": {"_name": "myLoadingWheel"}}],
    }],
}
o3, s3 = eye_from(loading).active_ship_observation()
assert (o3, s3) == (True, None), (o3, s3)
ok("FittingWindow dang load -> observed=True nhung active_ship=None (khong biạ)", True)

# Khong co panel nao -> (False, None), phan biet ro "khong quan sat duoc".
o4, s4 = eye_from({"type": "UIRoot", "children": []}).active_ship_observation()
assert (o4, s4) == (False, None)
ok("khong co panel -> (False, None), khong nham voi 'quan sat thay nhung rong'", True)

print(f"\n[PASS] test_live_gila_fitting: {PASS} pass")
