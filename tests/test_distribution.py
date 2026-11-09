"""Test modes/distribution.py — PYTHONPATH=src python tests/test_distribution.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fila_bot.modes.distribution import DistributionMode  # noqa: E402


def ok(n):
    print(f"[PASS] {n}")


BTN = {"accept": (10, 10), "decline": (20, 10), "complete": (30, 10)}
COURIER = {"type": "courier", "cargo_m3": 2.0, "buttons": BTN}


def world(**kw):
    w = {"docked": True, "station": "AGT", "agent_station": "AGT", "pickup": "AGT",
         "dropoff": "DST", "offer": None, "mission_active": False, "cargo_loaded": False,
         "cargo_free": 400.0, "route_hisec": True, "popup": None, "travel": {}}
    w.update(kw)
    return w


clock = {"t": 0.0}


def mk(**kw):
    return DistributionMode(clock=lambda: clock["t"], **kw)


# 1. vong courier day du
m = mk()
assert m.tick(world())[0]["do"] == "open_agent"
a = m.tick(world(offer=COURIER))
assert a[0] == {"do": "click", "at": (10, 10), "why": a[0]["why"]} and m.phase == "LOAD"
assert m.tick(world(mission_active=True))[0]["do"] == "load_cargo"
m.tick(world(mission_active=True, cargo_loaded=True))
assert m.phase == "TO_DROPOFF"
m.tick(world(mission_active=True, cargo_loaded=True, station="DST"))
assert m.phase == "COMPLETE"
a = m.tick(world(mission_active=True, station="DST", offer=COURIER))
assert a[0]["at"] == (30, 10)
m.tick(world(station="DST"))
assert m.phase == "TO_AGENT" and m.done == 1
m.tick(world())
assert m.phase == "AGENT" and m.at_safe_point
ok("courier: open agent -> accept -> load -> dropoff -> complete -> ve agent")

# 2. encounter -> decline, quay lai AGENT
m = mk()
a = m.tick(world(offer={"type": "encounter", "cargo_m3": None, "buttons": BTN}))
assert a[0]["at"] == (20, 10) and m.phase == "AGENT" and m.declined == 1
ok("encounter -> decline")

# 3. thieu du kien -> BLOCKED, khong bam
m = mk()
assert m.tick(world(offer={"type": None, "buttons": BTN}))[0]["do"] == "blocked"
assert m.tick(world(offer=COURIER)) == []
m = mk()
a = m.tick(world(offer={"type": "courier", "cargo_m3": 2.0, "buttons": {}}))
assert a[0]["do"] == "blocked" and "G2" in a[0]["why"]
m = mk()
m.tick(world(offer=COURIER))
assert m.tick(world(mission_active=True, cargo_loaded=None))[0]["do"] == "blocked"
ok("loai/nut/cargo khong doc duoc -> BLOCKED, dung han")

# 4. popup la -> BLOCKED
m = mk()
a = m.tick(world(popup="You are missing cargo"))
assert a[0]["do"] == "blocked" and m.phase == "BLOCKED"
ok("popup khong nhan ra -> BLOCKED")

# 5. travel: set_destination roi open_menu tren marker
m = mk()
m.tick(world(offer=COURIER)); m.tick(world(mission_active=True, cargo_loaded=True))
assert m.phase == "TO_DROPOFF"
assert m.tick(world(docked=False, station=None))[0] == {"do": "set_destination", "to": "DST"}
tw = {"system": "A", "docked": False, "markers": [(5, 5)], "warping": False,
      "menu": [], "route_panel": True}
a = m.tick(world(docked=False, station=None, travel=tw))
assert a[0]["do"] == "open_menu" and a[0]["at"] == (5, 5)
ok("travel: set_destination -> open_menu marker route")

# 6. STOP / max_missions -> dung o safe point
m = mk()
m.request_safe_stop()
assert m.tick(world()) == [] and m.phase == "IDLE_DONE" and m.at_safe_point
m = mk(max_missions=0)
m.tick(world())
assert m.phase == "IDLE_DONE"
ok("STOP / max_missions -> IDLE_DONE (docked)")

# 7. world None -> blocked
assert mk().tick(None)[0]["do"] == "blocked"
ok("khong co snapshot -> BLOCKED")

print("ALL OK test_distribution")
