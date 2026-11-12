"""Regression: game bao 'activate the Acceleration Gate' -> bot phai BAM GATE.

Live 11-11 20:4x, client TQ 'EVE - Kompi Yaken':
- tau da toi dung he **Josameto 0.6** (overview toan 'Josameto ...')
- overview: 'Acceleration Gate | Acceleration Gate | 0 m' center (813,396)
- Opportunities / AgentMissionInfoPanelEntry: 'What s in a Name - Poke (3 of 5)',
  'Encounter (Deadspace)', **'You need to activate the Acceleration Gate'**
- Bot cu van phat `warp_to_mission` (TRAVEL_SITE 97 tick) thay vi vao pocket.

Sua: doc objective text tu CHINH game + gate trong tam -> `activate_gate`.
Fail-closed: thieu objective text hoac gate o xa (AU/km) -> KHONG bam.

Chay: PYTHONPATH=src python tests/test_activate_gate_evidence.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.eye import Eye  # noqa: E402
from fila_bot.modes.live_security import LiveSecurityRunner  # noqa: E402
from fila_bot.modes.security import SecurityMode, _gate_in_activation_range  # noqa: E402

PASS = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} — {msg}")
        sys.exit(1)


FIX = ROOT / "tests" / "fixtures" / "ui_tree_live_at_gate.json"
root = json.loads(FIX.read_text(encoding="utf-8"))


def eye_from(r):
    e = Eye.__new__(Eye)
    e.root = r
    e._pos = None
    e._pos_root = None
    return e


e = eye_from(root)
obs = e.mission_panel_observation()
assert obs is not None
ok("panel objective = 'You need to activate the Acceleration Gate'",
   obs["objective_text"] == "You need to activate the Acceleration Gate",
   str(obs["objective_text"]))

ok("'0 m' nam trong tam kich hoat", _gate_in_activation_range("0 m") is True)
ok("'12 AU' KHONG duoc kich hoat", _gate_in_activation_range("12 AU") is False)
ok("'30 km' KHONG duoc kich hoat", _gate_in_activation_range("30 km") is False)
ok("None KHONG duoc kich hoat", _gate_in_activation_range(None) is False)
ok("'1,200 m' van trong tam", _gate_in_activation_range("1,200 m") is True)
ok("'9.7 AU' KHONG duoc kich hoat", _gate_in_activation_range("9.7 AU") is False)

runner = LiveSecurityRunner(e, dry=True)
w = runner.refresh()
ok("refresh day objective_text vao world",
   w.get("mission_objective_text") == "You need to activate the Acceleration Gate",
   str(w.get("mission_objective_text")))
ok("refresh thay gate 0 m",
   bool(w.get("gates")) and w["gates"][0].get("distance") == "0 m", str(w.get("gates")))

m = SecurityMode()
acts = m.tick(w)
ok("tick phat activate_gate (KHONG con warp_to_mission)",
   any(a.get("do") == "activate_gate" for a in acts)
   and not any(a.get("do") == "warp_to_mission" for a in acts), str(acts))
act = [a for a in acts if a.get("do") == "activate_gate"][0]
ok("activate_gate dung toa do (813,396)", act.get("at") == (813, 396), str(act.get("at")))
ok("phase AT_GATE", m.phase == "AT_GATE", m.phase)

# Counter-example 1: gate o xa -> khong bam (fail-closed).
w_far = dict(w)
w_far["gates"] = [{"name": "Acceleration Gate", "center": (813, 396), "distance": "14 AU"}]
acts_far = SecurityMode().tick(w_far)
ok("gate o 14 AU -> KHONG activate_gate",
   not any(a.get("do") == "activate_gate" for a in acts_far), str(acts_far))

# Counter-example 2: thieu objective text -> khong bam (khong doan).
w_noobj = dict(w)
w_noobj["mission_objective_text"] = None
acts_no = SecurityMode().tick(w_noobj)
ok("thieu objective text -> KHONG activate_gate",
   not any(a.get("do") == "activate_gate" for a in acts_no), str(acts_no))

print(f"\nKet qua: {PASS} PASS / 0 FAIL")
