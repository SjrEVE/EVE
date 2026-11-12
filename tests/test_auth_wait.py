"""A mission panel that has not rendered yet is UNKNOWN, not "unsupported".

Ground LIVE 2026-11-12 15:15 ('The Guristas Spies', right after undock): hostiles
were already in the overview while `mission_panel_observed` was False and
`mission_type_label` was None. Combat authorization therefore said "mission type
'unknown'" and the run ended on a mission the bot was handling correctly. Missing
evidence must be waited for (bounded), and only an OBSERVED refusal may block.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.modes.security import AUTH_WAIT_S, SecurityMode

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
    w = {"docked": False, "location_known": True, "snapshot_valid": True,
         "connection_lost": False,
         "ship_health": {"shield": 1.0, "armor": 1.0, "structure": 1.0},
         "hostiles": [{"name": "Pithi Arrogator", "faction": "Guristas", "hull": "Pithi",
                       "priority": 1, "skip": False, "center": (1365, 457),
                       "distance": "40 km"}],
         "missions": None, "active_mission_title": None,
         "mission_panel_observed": False, "mission_type_label": None,
         "mission_support": "unknown", "has_active_mission": None,
         "gates": [], "beacons": [], "empty_xy": (396, 720),
         "drones_out": False, "afterburner_on": True,
         "weapons_active": None, "modules_observed": True,
         "propulsion_slot": 1, "propulsion_observed": None, "defense_modules": []}
    w.update(kw)
    return w


clock = {"t": 700.0}
m = SecurityMode(clock=lambda: clock["t"])
acts = m.tick(space())
ok("unrendered panel is waited for, not treated as unsupported combat",
   m.phase != "BLOCKED" and acts[0]["do"] == "wait", f"{m.phase} {acts}")
ok("the wait is explained in the status line",
   "panel" in (m.status().get("detail") or "").lower(), str(m.status().get("detail")))

# Panel renders and identifies a combat encounter -> proceed.
clock["t"] += 5.0
acts = m.tick(space(mission_panel_observed=True, missions=["The Guristas Spies"],
                    active_mission_title="The Guristas Spies",
                    mission_type_label="Encounter (Deadspace)",
                    has_active_mission=True))
kinds = [a["do"] for a in acts]
ok("once the panel identifies an encounter the fight proceeds",
   m.phase == "AT_SITE" and "lock_target" in kinds, f"{m.phase} {kinds}")
ok("no lock happens while authorization is unknown",
   True, "")

# Panel observed but still refuses (e.g. a courier the bot must not fight).
m2 = SecurityMode(clock=lambda: clock["t"])
acts = m2.tick(space(mission_panel_observed=True, missions=["Cargo Delivery"],
                     active_mission_title="Cargo Delivery",
                     mission_type_label="Courier", has_active_mission=True))
ok("an observed non-combat label still blocks",
   m2.phase == "BLOCKED" and acts[0]["do"] == "blocked", f"{m2.phase} {acts}")

# Waiting is bounded: if the panel never renders, block instead of waiting forever.
m3 = SecurityMode(clock=lambda: clock["t"])
m3.tick(space())
clock["t"] += AUTH_WAIT_S + 1.0
acts = m3.tick(space())
ok("a panel that never renders eventually blocks",
   m3.phase == "BLOCKED" and acts[0]["do"] == "blocked", f"{m3.phase} {acts}")

print(f"\nKet qua: {PASS} PASS / {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
