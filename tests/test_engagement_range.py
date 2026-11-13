"""A target outside weapon range must be flown to, not waited on.

Ground LIVE 2026-11-12 14:26 ('The Guristas Spies', Piak): the ship sat at the
site with speed 0 m/s while four Pithi frigates orbited at 60-65 km. The bot had
locked, fired and launched drones, then did nothing — no step ever closed the
distance, so the mission could not finish and the pocket never cleared.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.modes.security import (ENGAGE_MAX_ATTEMPTS, ENGAGE_RANGE_M, ENGAGE_STALL_S,
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


def battle(distance, **kw):
    w = {"docked": False, "location_known": True, "snapshot_valid": True,
         "connection_lost": False,
         "ship_health": {"shield": 1.0, "armor": 1.0, "structure": 1.0},
         "hostiles": [{"name": "Pithi Invader", "object_id": 101,
                       "faction": "Guristas", "hull": "Pithi",
                       "priority": 1, "skip": False, "center": (1365, 457),
                       "distance": distance}],
         "missions": ["The Guristas Spies"], "active_mission_title": "The Guristas Spies",
         "mission_type_label": "Encounter (Deadspace)", "mission_support": "combat",
         "has_active_mission": True, "mission_panel_observed": True,
         "gates": [], "beacons": [], "drones_out": True, "afterburner_on": True,
         "weapons_active": None, "modules_observed": True,
         "propulsion_slot": 1, "propulsion_observed": None, "defense_modules": [],
         "target_bar_supported": True,
         "locked_target": {"object_id": 101, "is_active": True,
                           "texts": ["Pithi Invader"]}}
    w.update(kw)
    return w


clock = {"t": 500.0}
m = SecurityMode(clock=lambda: clock["t"])
acts = m.tick(battle("65 km"))
kinds = [a["do"] for a in acts]
ok("target beyond weapon range is approached before offense",
   "close_distance" in kinds and acts[[a["do"] for a in acts].index("close_distance")]["at"]
   == (1365, 457), str(acts))
close_action = next(a for a in acts if a["do"] == "close_distance")
ok("distance-closing action carries the selected itemID",
   close_action.get("target_id") == 101
   and close_action.get("target_name") == "Pithi Invader", str(close_action))
m_unverified = SecurityMode(clock=lambda: clock["t"])
unverified_kinds = [a["do"] for a in m_unverified.tick(
    battle("12 km", locked_target=None))]
ok("unverified target lock withholds weapons and drone engagement",
   "fire_weapons" not in unverified_kinds
   and "engage_drones" not in unverified_kinds, str(unverified_kinds))

# Same distance, still flying: no repeat command inside the stall window.
clock["t"] += 5.0
kinds2 = [a["do"] for a in m.tick(battle("64 km"))]
ok("no re-issued approach while the ship is closing", "close_distance" not in kinds2, str(kinds2))

# Distance stops decreasing -> command is re-issued.
clock["t"] += ENGAGE_STALL_S + 1.0
kinds3 = [a["do"] for a in m.tick(battle("64 km"))]
ok("stalled approach is re-issued", "close_distance" in kinds3, str(kinds3))

# Inside engagement range -> no flying, keep shooting.
m2 = SecurityMode(clock=lambda: clock["t"])
kinds = [a["do"] for a in m2.tick(battle(
    "12 km", target_bar_supported=True,
    locked_target={"object_id": 101, "is_active": True,
                   "texts": ["Pithi Invader"]}))]
ok("matching active target inside range enables weapons, without approach",
   "close_distance" not in kinds and "fire_weapons" in kinds, str(kinds))

# Never closes -> blocks with the real distance, bounded attempts.
m3 = SecurityMode(clock=lambda: clock["t"])
seen = []
for _ in range(ENGAGE_MAX_ATTEMPTS + 12):
    out = m3.tick(battle("65 km"))[0]["do"]
    seen.append(out)
    clock["t"] += ENGAGE_STALL_S + 1.0
    if m3.phase == "BLOCKED":
        break
ok("unreachable target eventually blocks", m3.phase == "BLOCKED", m3.phase)
ok("attempts stay bounded", seen.count("close_distance") <= ENGAGE_MAX_ATTEMPTS + 1,
   str(seen.count("close_distance")))
ok("block reason names the range it could not reach",
   str(int(ENGAGE_RANGE_M / 1000)) in (m3.blocked or ""), m3.blocked or "")

print(f"\nKet qua: {PASS} PASS / {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
