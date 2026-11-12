"""Production objective pipeline: approach branch and turn-in gating."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.modes.security import SecurityMode

TEXT = ('You need to approach <a href= showinfo:10131//9002321446000117567 >'
        'Fire Cloud</a>')

def space_world(**kw):
    w = {"docked": False, "location_known": True, "snapshot_valid": True,
         "connection_lost": False, "ship_health": {"shield": 1.0, "armor": 1.0,
         "hull": 1.0}, "hostiles": [], "gates": [], "beacons": [],
         "empty_xy": (320, 763), "has_active_mission": True,
         "mission_panel_observed": True, "missions": ["Foreign Investment"],
         "mission_objective_text": TEXT,
         "mission_target": {"label": "Fire Cloud", "center": (10, 20),
                            "item_id": 9002321446000117567,
                            "distance_m": 12000.0},
         "drones_out": False, "afterburner_on": True}
    w.update(kw)
    return w

m = SecurityMode()
acts = m.tick(space_world())
assert acts and acts[0]["do"] == "approach_target", acts
assert acts[0]["at"] == (10, 20), acts
print('[PASS] observed approach objective emits approach_target, not warp_to_mission')

m2 = SecurityMode()
acts = m2.tick(space_world(mission_target=None))
assert acts and acts[0]["do"] != "warp_to_mission", acts
print('[PASS] unresolved approach objective never falls through to blind warp')

# Turn-in: explicit objective-not-complete evidence forbids Complete.
m3 = SecurityMode(); m3._was_in_space = True
docked = {"docked": True, "location_known": True, "snapshot_valid": True,
          "connection_lost": False, "has_active_mission": True,
          "mission_panel_observed": True, "missions": ["Foreign Investment"],
          "objective_complete": False,
          "offer": {"title": "Foreign Investment", "buttons": {"complete": (5, 6)}},
          "agent_dialog_open": True, "agents": []}
acts = m3.tick(docked)
assert all(a.get("do") != "complete_mission" for a in acts), acts
print('[PASS] incomplete objective does not click Complete')

# Grounded tracker header allows the turn-in click (read-back still required).
m4 = SecurityMode(); m4._was_in_space = True
acts = m4.tick({**docked, "objective_complete": True})
assert acts and acts[0]["do"] == "complete_mission" and acts[0]["at"] == (5, 6), acts
assert m4._await_turnin is True
print('[PASS] tracker AllObjectivesComplete authorizes Complete, read-back still pending')

print('\nKet qua: 4 PASS / 0 FAIL')
