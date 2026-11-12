"""Entering the site must turn the tank on — observed OFF only, never blind.

Ground LIVE 2026-11-12 (Gila, Piak, real HUD via module_buttons()):
  High 2-5 = Rapid Light Missile Launcher II  -> is_active false
  High 1   = Drone Link Augmentor I           -> null
  Med 1    = 10MN Afterburner II              -> null
  Med 2,6  = Multispectrum Shield Hardener II -> true/null
  Med 3-5  = Caldari Navy Large Shield Extender (passive), Low 1-3 = DDA II

Two defects that this test pins:
1. The old code used `not world["afterburner_on"]`, so an UNKNOWN (None) counted
   as "off" and pressed Alt-F1 every 10 s — toggling a running AB back off.
2. Nothing ever pressed the hardeners, so a null-reading tank stayed off while
   the ship sat in the pocket.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.modes.security import SecurityMode

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
         "connection_lost": False, "ship_health": {"shield": 1.0, "armor": 1.0, "hull": 1.0},
         "hostiles": [{"name": "Pithi Arrogator", "faction": "Guristas", "hull": "Pithi",
                       "priority": 1, "skip": False, "center": (1373, 649),
                       "distance": "10 km"}],
         "gates": [], "beacons": [], "empty_xy": (396, 720),
         "has_active_mission": True, "mission_panel_observed": True,
         "missions": ["Seek and Destroy"], "mission_type_label": "Encounter (Deadspace)",
         "mission_objective_text": None, "mission_target": None,
         "mission_travel_support": True, "drones_out": False,
         "weapons_active": False, "modules_observed": True,
         "module_state": {"high": {1: None, 2: False, 3: False, 4: False, 5: False},
                          "med": {1: None, 2: True, 6: True}, "low": {}},
         "propulsion_slot": 1, "propulsion_observed": None,
         "defense_modules": [{"slot": 2, "observed": None}, {"slot": 6, "observed": None}],
         "afterburner_on": None}
    w.update(kw)
    return w


clock = {"t": 100.0}
m = SecurityMode(clock=lambda: clock["t"])
kinds = [a["do"] for a in m.tick(space())]
# In-space HUD exports NO module state (client source: ramp_active only while
# the ramp animation runs). Waiting for that flag left the ship standing at the
# site with guns cold, so the rule is "act once per mission".
ok("unreadable module state still turns the tank and guns on",
   "toggle_defense" in kinds and "toggle_ab" in kinds and "fire_weapons" in kinds, str(kinds))
ok("hardeners observed ON are not toggled again",
   [a["slot"] for a in m.tick(space()) if a["do"] == "toggle_defense"] == [], "re-pressed")

# Hardeners read OFF -> must be turned on before the ship eats damage.
m2 = SecurityMode(clock=lambda: clock["t"])
acts = m2.tick(space(defense_modules=[{"slot": 2, "observed": False},
                                      {"slot": 6, "observed": False}]))
kinds = [a["do"] for a in acts]
ok("hardeners observed OFF are turned on",
   kinds.count("toggle_defense") == 2, str(kinds))
ok("each defense command carries its slot",
   sorted(a["slot"] for a in acts if a["do"] == "toggle_defense") == [2, 6], str(acts))

# Afterburner observed OFF -> turn it on (this one IS grounded evidence).
m3 = SecurityMode(clock=lambda: clock["t"])
kinds = [a["do"] for a in m3.tick(space(propulsion_observed=False, afterburner_on=False))]
ok("afterburner observed OFF is switched on", "toggle_ab" in kinds, str(kinds))

# Unknown hardener state is still activated once per mission (never a blind
# repeat): the second call in the same mission must stay silent.
m4 = SecurityMode(clock=lambda: clock["t"])
first = [a["do"] for a in m4.tick(space(defense_modules=[{"slot": 2, "observed": None}]))]
second = [a["do"] for a in m4.tick(space(defense_modules=[{"slot": 2, "observed": None}]))]
ok("unknown hardener state is activated once, never re-pressed",
   "toggle_defense" in first and "toggle_defense" not in second,
   f"{first} / {second}")

# Same tick twice inside the cooldown must not re-press.
m5 = SecurityMode(clock=lambda: clock["t"])
m5.tick(space(propulsion_observed=False, afterburner_on=False))
clock["t"] += 1.0
kinds = [a["do"] for a in m5.tick(space(propulsion_observed=False, afterburner_on=False))]
ok("no double toggle inside the 10s cooldown", "toggle_ab" not in kinds, str(kinds))

print(f"\nKet qua: {PASS} PASS / {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
