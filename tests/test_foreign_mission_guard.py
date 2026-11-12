"""V1 is one agent/level: never run a mission that belongs to another agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.modes.security import SecurityMode

base = {"docked": False, "location_known": True, "snapshot_valid": True,
        "connection_lost": False, "has_active_mission": True,
        "mission_panel_observed": True, "active_mission_title": "The Blockade",
        "mission_agent_id": "3016214", "profile_agent_id": "3016216",
        "hostiles": [], "beacons": [], "gates": [], "drones_out": True,
        "afterburner_on": True, "mission_support": "combat"}

m = SecurityMode()
a = m.tick(base)
assert a and a[0]["do"] == "blocked", a
assert m.phase == "FOREIGN_MISSION" and "3016214" in m.blocked
print('[PASS] active mission from another agent is blocked, no travel/combat')

base2 = dict(base, mission_agent_id="3016216")
m2 = SecurityMode()
a = m2.tick(base2)
assert not (a and a[0]["do"] == "blocked" and m2.phase == "FOREIGN_MISSION"), a
print('[PASS] matching profile agent proceeds normally')

base3 = dict(base)
base3.pop("profile_agent_id")
m3 = SecurityMode()
m3.tick(base3)
assert m3.phase != "FOREIGN_MISSION"
print('[PASS] no profile pin (sim/tests) keeps legacy behavior')

print('\nKet qua: 3 PASS / 0 FAIL')
