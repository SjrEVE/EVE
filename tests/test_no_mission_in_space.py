"""No mission panel in space means no objective — go re-read, never warp blind.

Ground LIVE 2026-11-12 15:45 (run15): after the previous mission ended the job
panel was gone (`mission_panel_observed False`, no objective text) while the ship
was still in space. The generic branch then clicked 'Warp to Location' 173 times
(a tracker button that does not exist without a mission) and finally blocked with
"Warp tới mission site không hiệu lực sau 3 lần". Missing evidence must send the
ship back to a station, not into a blind warp loop.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.modes.security import NO_MISSION_GRACE_S, SecurityMode

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


def lost_mission(**kw):
    w = {"docked": False, "location_known": True, "snapshot_valid": True,
         "connection_lost": False,
         "ship_health": {"shield": 1.0, "armor": 1.0, "structure": 1.0},
         "hostiles": [], "gates": [], "beacons": [], "empty_xy": (396, 720),
         "missions": None, "active_mission_title": None,
         "mission_panel_observed": False, "mission_type_label": None,
         "mission_support": None, "has_active_mission": None,
         "mission_objective_text": None, "mission_target": None,
         "drones_out": False, "afterburner_on": True,
         "weapons_active": None, "modules_observed": True,
         "propulsion_slot": 1, "propulsion_observed": None, "defense_modules": []}
    w.update(kw)
    return w


clock = {"t": 4000.0}
m = SecurityMode(clock=lambda: clock["t"])
acts = m.tick(lost_mission())
ok("no panel in space waits instead of warping",
   acts[0]["do"] == "wait" and m.phase != "BLOCKED", f"{m.phase} {acts}")

clock["t"] += NO_MISSION_GRACE_S + 1.0
acts = m.tick(lost_mission())
ok("grace expires -> return to a station to re-read",
   acts[0]["do"] == "warp_home", str(acts))
ok("status explains there was no mission evidence",
   "panel mission" in (m.status().get("detail") or ""), str(m.status().get("detail")))

# Objective text present -> normal travel behaviour is untouched.
m2 = SecurityMode(clock=lambda: clock["t"])
acts = m2.tick(lost_mission(
    mission_panel_observed=True, missions=["Furrier Fiasco"],
    active_mission_title="Furrier Fiasco", has_active_mission=True,
    mission_type_label="Encounter (Deadspace)",
    mission_objective_text="You need to warp to the mission location"))
ok("a readable objective still drives the normal warp",
   acts[0]["do"] in ("warp_to_mission", "wait"), str(acts))

print(f"\nKet qua: {PASS} PASS / {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
