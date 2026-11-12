"""A warp click must be followed by a re-read, not by another click.

Ground LIVE 2026-11-12 18:27 (Piak -> Elonaya, 'Eliminate the Pirate Campers'):
the mission is in Elonaya 0.7 while the ship was in Piak. The tracker correctly
said 'Warp to Location'; clicking it starts a session change, the UI tree stops
parsing for ~10 s (`location_state` UNKNOWN, mission panel None), the FSM read
that as "no mission" and fell into the generic warp branch, which clicked the
same button again. The log shows the same command repeating for minutes.

Rules pinned here:
1. While the client is settling after a warp click, wait — do not click again.
2. The number of warp clicks is bounded; running out is an honest BLOCKED that
   says the ship may not be in the mission's system.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.modes.security import (WARP_MAX_ATTEMPTS, WARP_SETTLE_S, SecurityMode)

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


def space(**kw):
    w = {"docked": False, "location_known": False, "snapshot_valid": False,
         "connection_lost": False,
         "ship_health": {"shield": 1.0, "armor": 1.0, "structure": 1.0},
         "hostiles": [], "gates": [], "beacons": [], "empty_xy": (396, 720),
         "missions": None, "active_mission_title": None,
         "mission_panel_observed": False, "mission_type_label": None,
         "has_active_mission": None, "mission_objective_text": None,
         "mission_target": None, "drones_out": False, "afterburner_on": True,
         "weapons_active": None, "modules_observed": True,
         "propulsion_slot": 1, "propulsion_observed": None, "defense_modules": [],
         "mission_location_button": "Warp to Location"}
    w.update(kw)
    return w


clock = {"t": 1000.0}

# 1. Right after a warp click: the client is settling -> wait, never click again.
m = SecurityMode(clock=lambda: clock["t"])
m._warp_sent = clock["t"]
m._warp_attempts = 1
acts = m.tick(space())
ok("during the warp settle window the bot waits",
   acts[0]["do"] == "wait", str(acts))
ok("the wait says it is waiting for the client to change scene",
   "đổi cảnh" in (acts[0].get("why") or ""), acts[0].get("why") or "")

# 2. Still unreadable after the settle window and the click budget is spent.
clock["t"] += WARP_SETTLE_S + 1.0
m._warp_attempts = WARP_MAX_ATTEMPTS
acts = m.tick(space())
ok("exhausted warp attempts block instead of looping",
   acts[0]["do"] == "blocked" and m.phase == "BLOCKED", f"{m.phase} {acts}")
ok("the block names the real possibility (wrong system)",
   "hệ" in (m.blocked or "").lower(), m.blocked or "")

# 3. A fresh session with no warp click and no panel waits the normal grace,
#    then heads home / to the mission system instead of clicking warp blindly.
m2 = SecurityMode(clock=lambda: clock["t"])
acts = m2.tick(space())
ok("no warp click and no panel -> bounded wait first",
   acts[0]["do"] == "wait", str(acts))

print(f"\nKet qua: {PASS} PASS / {FAIL} FAIL")
sys.exit(1 if FAIL else 0)