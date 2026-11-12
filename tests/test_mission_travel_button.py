"""Regression: warp toi DUNG mission site, khong warp vao 'Celestial Beacon' bat ky.

Ground 11-11:
- Loi that: 'Derelict Ruins | Celestial Beacon' la cosmic anomaly, bot da warp
  vao do thay vi pocket mission (Boss: 'warp den cho lam mission sai me roi').
- NUT THAT trong mission tracker: StatefulButton
  _name='missionObjective_button_location_<id>', label doi theo trang thai:
    'Undock'          (docked)        -> dumps/g10_turnin_dialog.json
    'Set Destination' (chua dung he)  -> dumps/g11_docked_fresh.json
    'Warp to Location'(dung he)       -> CCP/community, chua co dump TQ
- docs/MISSION_TRAVEL_RESEARCH_2026-11-11.md + eve-master free / ISXEVE EVEBot.

Chay: PYTHONPATH=src python tests/test_mission_travel_button.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.eye import Eye  # noqa: E402
from fila_bot.mission import MissionEye  # noqa: E402
from fila_bot.modes.live_security import LiveSecurityRunner  # noqa: E402

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


def load(p: str) -> dict:
    return json.loads((ROOT / p).read_text(encoding="utf-8"))


# ---- 1. Nút Location ground từ dump TQ thật --------------------------------
g11 = eye_from(load("dumps/g11_docked_fresh.json"))
b11 = g11.mission_location_button()
ok("dump g11: tim thay nut missionObjective_button_location_*", b11 is not None, str(b11))
ok("dump g11: label = 'Set Destination' (chua o dung he)",
   b11["label"] == "Set Destination", str(b11))
ok("dump g11: center la toa do nguyen hop le",
   isinstance(b11["center"], tuple) and all(isinstance(v, int) for v in b11["center"]),
   str(b11["center"]))
ok("dump g11: name bat dau bang prefix da ground",
   str(b11["name"]).startswith("missionObjective_button_location_"), str(b11["name"]))

g10 = eye_from(load("dumps/g10_turnin_dialog.json"))
b10 = g10.mission_location_button()
ok("dump g10 (docked): label = 'Undock'", b10 is not None and b10["label"] == "Undock", str(b10))

g8 = eye_from(load("dumps/g8_opportunities_open.json"))
ok("dump g8 (Opportunities, khong co nut Location): tra None",
   g8.mission_location_button() is None)

fx06 = eye_from(load("tests/fixtures/ui_tree_e2e_06_live_cannot_complete.json"))
ok("fixture live Cannot Complete: label = 'Undock'",
   fx06.mission_location_button()["label"] == "Undock")


# ---- 2. Label 'Warp to Location' (state dung he) ---------------------------
warp_tree = {
    "type": "UIRoot",
    "attrs": {},
    "children": [{
        "type": "StatefulButton",
        "attrs": {"_name": "missionObjective_button_location_999",
                  "_displayX": 10, "_displayY": 20,
                  "_displayWidth": 240, "_displayHeight": 24},
        "children": [
            {"type": "Sprite", "attrs": {"_name": "icon"}, "children": []},
            {"type": "EveLabelMedium",
             "attrs": {"_name": "label", "_setText": "Warp to Location"},
             "children": []},
        ],
    }],
}
bw = eye_from(warp_tree).mission_location_button()
ok("state dung he: doc duoc label 'Warp to Location'", bw is not None and bw["label"] == "Warp to Location", str(bw))


# ---- 3. KHONG warp vao Celestial Beacon bat ky -----------------------------
class OvEye:
    def __init__(self, entries): self.entries = entries
    def overview_entries(self): return self.entries


beacon = [{"Name": "Derelict Ruins", "Type": "Celestial Beacon",
           "center": (813, 444), "Distance": "0.6 AU"}]
me = MissionEye(OvEye(beacon))
ok("khong co site_hint -> mission_beacons() = [] (fail-closed)",
   me.mission_beacons() == [], str(me.mission_beacons()))
ok("chi co site_hint khop TEN moi tra entry",
   me.mission_beacons("Derelict Ruins")[0]["name"] == "Derelict Ruins")
ok("site_hint khong khop -> [] (khong lay beacon dau tien)",
   me.mission_beacons("Gallente Broadcast Tower") == [])


# ---- 4. apply(warp_to_mission) chon dung hanh dong theo label --------------
class FakeEye:
    def __init__(self, button, menu=None):
        self.button = button
        self.menu = menu or []
        self.clicked = []
        self.dll = None

    def mission_location_button(self): return self.button
    def empty_point(self): return (320, 763)
    def context_menus(self): return self.menu
    def wait_menu(self, timeout_s=5.0): return False
    def overview_entries(self): return []
    def send_click(self, *a, **kw): self.clicked.append(a)


def apply_warp(button, menu=None):
    fe = FakeEye(button, menu)
    runner = LiveSecurityRunner(fe, dry=True)
    res = runner.apply([{"do": "warp_to_mission"}])
    return res[0], fe


r1, _ = apply_warp({"center": (100, 200), "label": "Warp to Location",
                    "name": "missionObjective_button_location_999"})
ok("label 'Warp to Location' -> ok=True, note noi ro tracker",
   r1["ok"] is True and "tracker" in r1["note"], str(r1))

r2, _ = apply_warp({"center": (100, 200), "label": "Set Destination",
                    "name": "missionObjective_button_location_999"})
ok("label 'Set Destination' -> dat route, KHONG warp pocket",
   r2["ok"] is True and "KHONG warp pocket" in r2["note"], str(r2))

r3, _ = apply_warp({"center": (100, 200), "label": "Undock",
                    "name": "missionObjective_button_location_999"})
ok("label 'Undock' (docked) -> KHONG warp, khong bam nham",
   r3["ok"] is True and "KHONG warp" in r3["note"], str(r3))

r4, _ = apply_warp(None, [{"center": (1, 1), "entries": [
    {"text": "Show Info", "center": (2, 2)},
    {"text": "Approach Location", "center": (3, 3)}]}])
ok("khong co nut + menu khong co 'Warp to Location' -> ok=False, KHONG warp beacon",
   r4["ok"] is False and "KHONG warp beacon" in r4["note"], str(r4))

print(f"\nKet qua: {PASS} PASS / 0 FAIL")
