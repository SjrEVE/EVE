"""Session counters require objective-complete evidence; no duplicate count."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.mission_session import MissionSession
from fila_bot.modes.security import SecurityMode

s = MissionSession(character="Pilot", agent_id="3016214", home_station="Exact Base")
m = SecurityMode(session=s)
m._was_in_space = True
docked = {"docked": True, "location_known": True, "snapshot_valid": True,
          "connection_lost": False, "has_active_mission": True,
          "mission_panel_observed": True, "missions": ["Chain (1 of 5)"],
          "objective_complete": True, "agent_dialog_open": True,
          "offer": {"title": "Chain (1 of 5)", "buttons": {"complete": (5, 6)}},
          "agents": []}
a = m.tick(docked)
assert a and a[0]["do"] == "complete_mission", a
assert s.active_key is not None
key = s.active_key

readback = dict(docked, has_active_mission=False, offer=None, agent_dialog_open=False,
                objective_complete=True)
a = m.tick(readback)
assert m.completed_missions == 1 and s.completed == 1, (m.completed_missions, s.completed)
assert s.active_key is None
print('[PASS] verified turn-in counts once and clears the exact mission key')

a = m.tick(readback)
assert m.completed_missions == 1 and s.completed == 1
print('[PASS] repeated panel-absent tick cannot double-count')

# A different title while a mission is active is an identity conflict.
s2 = MissionSession(character="Pilot", agent_id="3016214", home_station="Exact Base")
m2 = SecurityMode(session=s2)
s2.bind("Chain (1 of 5)")
blocked = m2.tick(dict(docked, offer={"title": "Chain (2 of 5)",
                                      "buttons": {"complete": (5, 6)}},
                       missions=["Chain (2 of 5)"]))
assert blocked and blocked[0]["do"] == "blocked", blocked
print('[PASS] unconfirmed title switch blocks instead of overwriting the active mission')

print('\nKet qua: 3 PASS / 0 FAIL')
