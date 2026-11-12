"""Going home from another system: jump the gate the game names, never a random one.

Ground LIVE 2026-11-12 16:05: after the mission the ship was in Elonaya while the
home station is in Piak. The overview listed "Piak | Stargate (Caldari System)"
at 12 km, and ESI route 30001399 -> 30001403 is a single hop — so going home
means jumping THAT gate. Before this, `warp_home` found no matching station and
looped for minutes.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.modes.live_security import resolve_home_travel
from fila_bot.modes.security import (HOME_TRANSITION_GRACE_S, NO_MISSION_GRACE_S,
                                     SecurityMode)

PASS = 0
FAIL = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name} {msg}")


HOME_STATION = "Piak III - Moon 6 - Poksu Mineral Group Mineral Reserve"

ELONAYA = [
    {"Name": "Elonaya - 2% T2 Ice Refinery & Clone", "Type": "Athanor",
     "Distance": "6.6 AU", "center": (1373, 265)},
    {"Name": "Litiura", "Type": "Stargate (Caldari System)", "Distance": "24.4 AU",
     "center": (1373, 625)},
    {"Name": "Nonni", "Type": "Stargate (Caldari System)", "Distance": "24.4 AU",
     "center": (1373, 649)},
    {"Name": "Piak", "Type": "Stargate (Caldari System)", "Distance": "12 km",
     "center": (1373, 673)},
]
IN_PIAK = ELONAYA + [
    {"Name": HOME_STATION, "Type": "Caldari Mining Station", "Distance": "11 AU",
     "center": (1373, 289)},
]


class Eye:
    dll = None

    def __init__(self, entries):
        self._entries = entries

    def overview_entries(self):
        return list(self._entries)


w_other_in, w_other_gate = resolve_home_travel(ELONAYA, False, HOME_STATION, "Piak")
ok("ship in another system is detected from the profile home system",
   w_other_in is False, str(w_other_in))
ok("the gate named after the home system is the only one used",
   w_other_gate == (1373, 673), str(w_other_gate))

w_home_in, w_home_gate = resolve_home_travel(IN_PIAK, False, HOME_STATION, "Piak")
ok("in the home system with the home station visible, no jump is needed",
   w_home_in is True and w_home_gate == (1373, 673), f"{w_home_in} {w_home_gate}")

ok("docked always counts as being at home",
   resolve_home_travel([], True, HOME_STATION, "Piak") == (True, None),
   str(resolve_home_travel([], True, HOME_STATION, "Piak")))

# Unknown state when there is no profile system pinned (SIM/legacy behaviour).
ok("without a pinned home system nothing is guessed",
   resolve_home_travel(ELONAYA, False, HOME_STATION, None) == (None, None),
   str(resolve_home_travel(ELONAYA, False, HOME_STATION, None)))

# A neighbouring gate must never be used as "the way home".
ok("a differently-named stargate is never selected",
   resolve_home_travel([{"Name": "Litiura", "Type": "Stargate (Caldari System)",
                         "center": (1, 2)}], False, HOME_STATION, "Piak")
   == (False, None),
   str(resolve_home_travel([{"Name": "Litiura", "Type": "Stargate (Caldari System)",
                             "center": (1, 2)}], False, HOME_STATION, "Piak")))

# FSM: no mission + wrong system -> jump that gate, not warp_home.
clock = {"t": 5000.0}
m = SecurityMode(clock=lambda: clock["t"])
base = {"docked": False, "location_known": True, "snapshot_valid": True,
        "connection_lost": False,
        "ship_health": {"shield": 1.0, "armor": 1.0, "structure": 1.0},
        "hostiles": [], "gates": [], "beacons": [], "empty_xy": (396, 720),
        "missions": None, "active_mission_title": None,
        "mission_panel_observed": False, "mission_type_label": None,
        "has_active_mission": None, "mission_objective_text": None,
        "mission_target": None, "drones_out": False, "afterburner_on": True,
        "weapons_active": None, "modules_observed": True,
        "propulsion_slot": 1, "propulsion_observed": None, "defense_modules": [],
        "home_system": "Piak", "home_in_system": False, "home_gate_xy": (1373, 673)}
m.tick(dict(base))
clock["t"] += NO_MISSION_GRACE_S + 1.0
acts = m.tick(dict(base))
ok("wrong system + no mission -> jump the named gate",
   acts[0]["do"] == "jump_to_system" and acts[0]["at"] == (1373, 673), str(acts))
ok("phase names the home-system travel",
   m.phase == "TRAVEL_HOME_SYSTEM", m.phase)

# In the home system, the same state falls back to docking.
m2 = SecurityMode(clock=lambda: clock["t"])
base_home = dict(base, home_in_system=True)
m2.tick(base_home)
clock["t"] += NO_MISSION_GRACE_S + 1.0
acts = m2.tick(base_home)
ok("already in the home system -> dock instead of jumping",
   acts[0]["do"] == "warp_home", str(acts))

# No gate with the home system's name -> block, never jump a different gate.
m3 = SecurityMode(clock=lambda: clock["t"])
no_gate = dict(base, home_gate_xy=None)
m3.tick(no_gate)
clock["t"] += NO_MISSION_GRACE_S + 1.0
acts = m3.tick(no_gate)
ok("a fresh transition wastes no jump but does not block instantly",
   acts[0]["do"] == "wait", f"{m3.phase} {acts}")
clock["t"] += HOME_TRANSITION_GRACE_S + 1.0
acts = m3.tick(no_gate)
ok("no exact gate after the transition grace -> block instead of jumping",
   acts[0]["do"] == "blocked" and m3.phase == "BLOCKED", f"{m3.phase} {acts}")

# One jump command, then wait for the system change — never click the same gate
# every tick (live 16:37 spammed click+D because the overview re-sorted).
m4 = SecurityMode(clock=lambda: clock["t"])
m4.tick(dict(base))
clock["t"] += NO_MISSION_GRACE_S + 1.0
first = m4.tick(dict(base))
second = m4.tick(dict(base, home_gate_xy=(1373, 481)))
ok("first tick jumps the named gate", first[0]["do"] == "jump_to_system", str(first))
ok("second tick waits instead of clicking again",
   second[0]["do"] == "wait", str(second))

print(f"\nKet qua: {PASS} PASS / {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
