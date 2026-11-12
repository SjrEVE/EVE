"""After clearing the pocket the GAME says where to go next — obey it.

Ground LIVE 2026-11-12 14:40 (Piak/Elonaya, 'The Guristas Spies'): once the
pocket was clear the tracker changed to "You need to travel to Piak 0.7" with a
'Set Destination' button, while the ship sat in Elonaya. The old code ignored
that sentence, called warp_home and stalled for 120 s because the home station is
not in the current system's overview ("home station ... không có đúng một entry
(0)"). Rule: follow the game's travel objective first; only warp home when the
objective no longer asks for a different place.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.modes.security import WARP_COOLDOWN_S, SecurityMode

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


TRAVEL_TEXT = ('You need to travel to <a href= showinfo:5//30001403 >Piak</a> '
               '<color=#ff61dba4>0.7</color>')


def clear_pocket(**kw):
    w = {"docked": False, "location_known": True, "snapshot_valid": True,
         "connection_lost": False,
         "ship_health": {"shield": 1.0, "armor": 1.0, "structure": 1.0},
         "hostiles": [], "gates": [], "beacons": [], "empty_xy": (396, 720),
         "missions": ["The Guristas Spies"],
         "active_mission_title": "The Guristas Spies",
         "mission_type_label": "Encounter (Deadspace)", "mission_support": "combat",
         "has_active_mission": True, "mission_panel_observed": True,
         "mission_objective_text": TRAVEL_TEXT, "mission_target": None,
         "drones_out": False, "afterburner_on": True,
         "weapons_active": None, "modules_observed": True,
         "propulsion_slot": 1, "propulsion_observed": None, "defense_modules": []}
    w.update(kw)
    return w


clock = {"t": 2000.0}
m = SecurityMode(clock=lambda: clock["t"])
m._site_visited = True          # đã vào site và clear
m.tick(clear_pocket())          # tick đầu chỉ mở đồng hồ wave-wait 18 s
clock["t"] += 20.0
acts = m.tick(clear_pocket())
ok("after clear, a travel objective drives the route instead of warp_home",
   acts[0]["do"] == "warp_to_mission", str(acts))
ok("phase reflects following the route", m.phase == "TRAVEL_ROUTE", m.phase)

clock["t"] += 5.0
acts = m.tick(clear_pocket())
ok("route command is not spammed every tick",
   acts[0]["do"] == "wait", str(acts))
ok("detail states the destination the game asked for",
   "Piak" in (m.status().get("detail") or ""), str(m.status().get("detail")))

# Without a travel objective the previous behaviour (go home) must stay.
m2 = SecurityMode(clock=lambda: clock["t"])
m2._site_visited = True
m2.tick(clear_pocket(mission_objective_text=None))
clock["t"] += 20.0
acts = m2.tick(clear_pocket(mission_objective_text=None))
ok("no travel objective -> warp home as before", acts[0]["do"] == "warp_home", str(acts))

# An approach objective must not be mistaken for travel.
m3 = SecurityMode(clock=lambda: clock["t"])
m3._site_visited = True
acts = m3.tick(clear_pocket(
    mission_objective_text=('You need to approach <a href= showinfo:10131'
                            '//9002321446000117567 >Fire Cloud</a>')))
ok("approach objective is not treated as travel-to-system",
   acts[0]["do"] != "warp_home" or "Fire Cloud" not in str(acts), str(acts))

print(f"\nKet qua: {PASS} PASS / {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
