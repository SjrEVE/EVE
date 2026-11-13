"""Weapons are activated from OBSERVED slot state, never self-confirmed."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.modes.security import SecurityMode
from fila_bot.modes.live_security import LiveSecurityRunner


def battle(**kw):
    w = {"docked": False, "location_known": True, "snapshot_valid": True,
         "connection_lost": False, "ship_health": {"shield": 1.0, "armor": 1.0,
         "structure": 1.0}, "hostiles": [{"name": "Guristas Frigate", "object_id": 101,
         "faction": "Guristas", "priority": 1, "distance": 1000,
         "center": (500, 500)}], "target_bar_supported": True,
         "locked_target": {"object_id": 101, "is_active": True,
                           "texts": ["Guristas Frigate"]}, "missions": ["The Blockade"],
         "active_mission_title": "The Blockade", "mission_support": "combat",
         "has_active_mission": True, "mission_panel_observed": True,
         "gates": [], "beacons": [], "drones_out": True,
         "afterburner_on": True, "weapons_active": None}
    w.update(kw)
    return w

m = SecurityMode()
a = m.tick(battle(weapons_active=True))
assert not any(x["do"] == "fire_weapons" for x in a), a
print('[PASS] observed-active weapons do not send F1-F4 again')

m2 = SecurityMode()
a = m2.tick(battle(weapons_active=False))
assert any(x["do"] == "fire_weapons" for x in a), a
print('[PASS] observed-inactive weapons trigger a bounded fire command')

m3 = SecurityMode()
a = m3.tick(battle(weapons_active=None, modules_observed=False))
assert any(x["do"] == "fire_weapons" for x in a), a
print('[PASS] no module data (sim) fires once, not every tick')

m4 = SecurityMode()
a = m4.tick(battle(weapons_active=None, modules_observed=True))
# Ground LIVE 2026-11-12: in space the HUD exports no module state at all
# (client `ramp_active` only exists while the ramp animation runs), so refusing
# to fire left the ship standing at the site with cold guns. Act once, then stop
# — a repeat press would toggle the launchers OFF.
assert any(x["do"] == "fire_weapons" for x in a), a
a2 = m4.tick(battle(weapons_active=None, modules_observed=True))
assert not any(x["do"] == "fire_weapons" for x in a2), a2
print('[PASS] unreadable live module state fires once, then honours the cooldown')

# A launcher can run dry mid-mission. Bounded re-arm keeps the fight alive
# without toggling a running launcher off every few seconds.
a3 = SecurityMode()
a3._weapons_sent = a3.clock() - 100.0   # last press long ago, fight still on
a3._engagement_id = "The Blockade"      # already fired once this engagement
a3._engagement_modules_on = True
re_arm = a3.tick(battle(weapons_active=None, modules_observed=True))
assert sum(1 for x in re_arm if x["do"] == "fire_weapons") == 1, re_arm
print('[PASS] a dry launcher is re-armed once after a long quiet stretch')

a4 = SecurityMode()
a4._weapons_sent = a4.clock() - 100.0
a4._engagement_id = "The Blockade"
a4._engagement_modules_on = True
a4._weapons_rearms = 3                  # budget spent
spent = a4.tick(battle(weapons_active=None, modules_observed=True))
assert not any(x["do"] == "fire_weapons" for x in spent), spent
print('[PASS] the re-arm budget is bounded')

# Adapter presses only slotted buttons observed inactive.
class FakeEye:
    dll = None
    def module_buttons(self):
        return [
            {"rack": "high", "index": 1, "is_active": True},
            {"rack": "high", "index": 2, "is_active": False},
            {"rack": "high", "index": 3, "is_active": None},
            {"rack": "high", "index": 4, "is_active": True},
        ]
    def empty_point(self): return (1, 2)

r = LiveSecurityRunner(FakeEye(), dry=True,
                       profile={"weapon_slots": [2, 3, 4]}).apply([{"do": "fire_weapons"}])[0]
keys = [s.get("combo") for s in r.get("input_log", []) if s.get("combo")]
assert keys == ["F2"], r
print('[PASS] adapter presses only configured slots observed inactive')

class UnknownEye:
    dll = None
    def module_buttons(self):
        return [{"rack": "high", "index": 1, "is_active": None},
                {"rack": "high", "index": 2, "is_active": None}]
    def empty_point(self): return (1, 2)

r = LiveSecurityRunner(UnknownEye(), dry=True).apply([{"do": "fire_weapons"}])[0]
assert r["status"] == "UNKNOWN_STATE" and not r.get("input_log"), r
print('[PASS] all-unknown module flags -> UNKNOWN_STATE, zero keys sent')
