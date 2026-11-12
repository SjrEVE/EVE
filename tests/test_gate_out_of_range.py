"""Gate out of activation range must be approached, not re-warped forever.

Ground LIVE 2026-11-12 13:32 (Piak, 'Furrier Fiasco'): the game said
'You need to activate the Acceleration Gate' while the overview showed the gate
at '18 km'. The old code only activated inside 2.5 km and otherwise fell into the
generic warp branch, which re-clicked 'Warp to Location' every 60 s because the
ship was already at the site — three attempts then BLOCKED, mission unfinished.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.modes.security import APPROACH_COOLDOWN_S, APPROACH_MAX_ATTEMPTS, SecurityMode

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


def space(distance="18 km", objective="You need to activate the Acceleration Gate", **kw):
    w = {"docked": False, "location_known": True, "snapshot_valid": True,
         "connection_lost": False, "ship_health": {"shield": 1.0, "armor": 1.0, "hull": 1.0},
         "hostiles": [], "beacons": [], "empty_xy": (396, 720),
         "gates": [{"name": "Acceleration Gate", "center": (1373, 505),
                    "distance": distance}],
         "has_active_mission": True, "mission_panel_observed": True,
         "missions": ["Furrier Fiasco"], "mission_type_label": "Encounter (Deadspace)",
         "mission_objective_text": objective, "mission_target": None,
         "mission_travel_support": True, "drones_out": False, "afterburner_on": True}
    w.update(kw)
    return w


clock = {"t": 500.0}
m = SecurityMode(clock=lambda: clock["t"])
acts = m.tick(space())
ok("gate at 18 km -> approach, never activate_gate",
   acts[0]["do"] == "approach_target" and acts[0]["at"] == (1373, 505), str(acts))
ok("approach is bounded, not a blind click on the gate",
   m._gate_approach_attempts == 1, str(m._gate_approach_attempts))

acts = m.tick(space())
ok("second tick inside cooldown waits instead of clicking again",
   acts[0]["do"] == "wait" and m._gate_approach_attempts == 1, str(acts))
ok("closing distance never triggers a repeat click",
   m._gate_approach_attempts == 1, str(m._gate_approach_attempts))

# Gate arrives in range -> activate, and the gate-approach counters reset.
clock["t"] += APPROACH_COOLDOWN_S + 1.0
acts = m.tick(space(distance="1,800 m"))
ok("in range -> activate_gate", acts[0]["do"] == "activate_gate", str(acts))
ok("counters reset on activation",
   m._gate_approach_sent is None and m._gate_approach_attempts == 0,
   f"{m._gate_approach_sent}/{m._gate_approach_attempts}")

# Never gets in range -> blocks with the real distance, no infinite warp loop.
m2 = SecurityMode(clock=lambda: clock["t"])
last = None
seen = []
for _ in range(120):
    last = m2.tick(space())
    seen.append(last[0]["do"])
    clock["t"] += 5.0
    if m2.phase == "BLOCKED":
        break
ok("unreachable gate blocks after the attempt budget",
   bool(m2.phase == "BLOCKED" and last and last[0]["do"] == "blocked"), f"{m2.phase} {last}")
ok("retries before giving up (never a single blind click)",
   seen.count("approach_target") >= 2, str(seen.count("approach_target")))
ok("block reason states the remaining distance",
   "18 km" in (m2.blocked or ""), m2.blocked or "")

print(f"\nKet qua: {PASS} PASS / {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
