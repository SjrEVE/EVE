"""Adapter refuses to send input when the EVE window lost foreground."""
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.modes.live_security import LiveSecurityRunner

class FakeEye:
    dll = None
    def empty_point(self): return (1, 2)

runner = LiveSecurityRunner(FakeEye(), dry=False)
runner.win = {"hwnd": 7, "pid": 10}
with patch('fila_bot.modes.live_security.is_foreground', return_value=False):
    r = runner.apply([{"do": "click_start"}])[0]
assert r['ok'] is False and r['verified'] is False
assert r['status'] == 'INPUT_NOT_OWNED', r
print('[PASS] lost foreground -> INPUT_NOT_OWNED, no click sent')

from fila_bot.modes.security import INPUT_LOST_GIVE_UP_S, SecurityMode
clock = {"t": 1000.0}
m = SecurityMode(clock=lambda: clock["t"])
m.on_action_results([{"status": "INPUT_NOT_OWNED"}])
# Ground LIVE 2026-11-12 13:20: losing foreground is the owner taking the mouse,
# NOT a bot failure. One tick must not end an accepted mission mid-warp; the FSM
# keeps the session alive, tells the owner, and resumes when focus returns.
assert m.phase != 'BLOCKED' and not m.blocked, (m.blocked, m.phase)
assert "foreground" in (m.status().get("detail") or ""), m.status()
print('[PASS] one lost-focus tick waits for the owner instead of blocking')

SPACE = {"docked": False, "location_known": True, "snapshot_valid": True,
         "connection_lost": False, "ship_health": {"shield": 1.0, "armor": 1.0, "hull": 1.0},
         "hostiles": [], "gates": [], "beacons": [], "empty_xy": (320, 763),
         "has_active_mission": True, "mission_panel_observed": True,
         "missions": ["Furrier Fiasco"], "mission_objective_text": None,
         "mission_target": None, "drones_out": False, "afterburner_on": True,
         "mission_travel_support": True}
acts = m.tick(dict(SPACE))
assert acts and m.blocked is None, acts
m.on_action_results([{"status": "SENT"}])
assert m._input_lost_since is None, m._input_lost_since
print('[PASS] mission loop continues after focus returns')

m2 = SecurityMode(clock=lambda: clock["t"])
m2.on_action_results([{"status": "INPUT_NOT_OWNED"}])
clock["t"] += INPUT_LOST_GIVE_UP_S + 1.0
acts = m2.tick(dict(SPACE))
assert m2.phase == 'BLOCKED' and acts and acts[0]["do"] == "blocked", (m2.phase, acts)
print('[PASS] sustained focus loss still blocks, so a forgotten bot never types elsewhere')

print('\nKet qua: 3 PASS / 0 FAIL')
