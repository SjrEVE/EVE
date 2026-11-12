"""Regression: doc loai mission tu CHINH panel game, khong whitelist title.

Live 11-11 20:35: bot ACCEPTED_UNSUPPORTED voi "What s in a Name - Poke (3 of 5)"
vi title khong co trong catalog -> dung im (Boss ghet 'tu them bien do an toan').
Dump that `tests/fixtures/ui_tree_live_poke_jobboard.json` (1470 node, client TQ)
hien trong Opportunities / AgentMissionInfoPanelEntry:
  "What s in a Name  - Poke (3 of 5)"
  "Encounter (Deadspace)"
  "You need to travel to Josameto 0.6"
  "Set Destination"   (con cua StatefulButton missionObjective_button_location_3010986)

EVE-Master doc UI tree thay vi doan ten (docs/EVEMASTER_ARCHITECTURE_2026-11-11.md).
Day chi cap quyen DI CHUYEN; authorize_security_targets() van cham ban.

Chay: PYTHONPATH=src python tests/test_mission_panel_evidence.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.eye import Eye  # noqa: E402
from fila_bot.modes.live_security import LiveSecurityRunner  # noqa: E402
from fila_bot.modes.security import SecurityMode  # noqa: E402

PASS = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} — {msg}")
        sys.exit(1)


FIX = ROOT / "tests" / "fixtures" / "ui_tree_live_poke_jobboard.json"
root = json.loads(FIX.read_text(encoding="utf-8"))


def eye_from(r):
    e = Eye.__new__(Eye)
    e.root = r
    e._pos = None
    e._pos_root = None
    return e


e = eye_from(root)
obs = e.mission_panel_observation()
assert obs is not None, "fixture phai co AgentMissionInfoPanelEntry"
ok("panel duoc quan sat", obs["observed"] is True, str(obs))
ok("title doc tu panel = Poke (3 of 5)",
   obs["title"] == "What s in a Name  - Poke (3 of 5)", str(obs["title"]))
ok("loai mission = 'Encounter (Deadspace)' do GAME bao",
   obs["type_label"] == "Encounter (Deadspace)", str(obs["type_label"]))
ok("he can toi = Josameto 0.6 (khong doan)",
   "Josameto" in (obs["location_text"] or ""), str(obs["location_text"]))
ok("nut Location doc duoc label 'Set Destination'",
   obs["location_button"] == "Set Destination", str(obs["location_button"]))
ok("co toa do nut Location de click",
   isinstance(obs["location_button_xy"], tuple), str(obs["location_button_xy"]))

# Counter-example: cay khong co panel -> None (fail-closed, khong bi ra bang chung).
empty = {"type": "UIRoot", "attrs": {}, "children": []}
ok("khong co panel -> None (khong bi bang chung)",
   eye_from(empty).mission_panel_observation() is None)

# Runner.refresh() phai chuyen bang chung thanh quyen DI CHUYEN.
runner = LiveSecurityRunner(e, dry=True)
w = runner.refresh()
ok("refresh: mission_travel_support=True tu panel evidence",
   w.get("mission_travel_support") is True, str(w.get("mission_travel_support")))
ok("refresh: mission_type_label='Encounter (Deadspace)'",
   w.get("mission_type_label") == "Encounter (Deadspace)", str(w.get("mission_type_label")))
ok("refresh: mission_location_button='Set Destination'",
   w.get("mission_location_button") == "Set Destination", str(w.get("mission_location_button")))
ok("refresh: mission_panel_title = Poke (3 of 5)",
   "Poke" in str(w.get("mission_panel_title")), str(w.get("mission_panel_title")))

# SecurityMode khong duoc ket luan ACCEPTED_UNSUPPORTED nua.
m = SecurityMode()
acts = m.tick(w)
ok("tick khong tra blocked/ACCEPTED_UNSUPPORTED voi panel evidence",
   not any(a.get("do") == "blocked" for a in acts)
   and m.phase != "ACCEPTED_UNSUPPORTED", f"phase={m.phase} acts={acts}")

print(f"\nKet qua: {PASS} PASS / 0 FAIL")
