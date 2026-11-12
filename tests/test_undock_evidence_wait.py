"""Regression: Undock thanh cong nhung bot tu BLOCKED sau 3 click (live 11-11).

Live trace that: AUTO.bat 20:29:59 / 20:30:02 / 20:30:05 bam Undock 3 lan,
`ok=True` ca 3, bot BLOCKED luc 20:30:09. Probe doc lai ngay sau do:
`docked: False | location: IN_SPACE` — Undock DA CO TAC DUNG, EVE doi session
lau hon cua so 9 giay. Dem click la sai; phai cho BANG CHUNG (world.docked=False)
voi timeout (EVE-Master "Wait while ship indicator", docs/EVEMASTER_ARCHITECTURE_2026-11-11.md).

Chay: PYTHONPATH=src python tests/test_undock_evidence_wait.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.modes.security import (  # noqa: E402
    SecurityMode, UNDOCK_EVIDENCE_TIMEOUT_S, UNDOCK_RETRY_INTERVAL_S,
    UNDOCK_MAX_CLICKS,
)

PASS = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} — {msg}")
        sys.exit(1)


class Clock:
    def __init__(self): self.t = 100.0
    def __call__(self): return self.t
    def advance(self, s): self.t += s


def docked_world():
    return {
        "docked": True, "agent_dialog_open": False, "mission_link_xy": None,
        "travel": {"markers": []}, "undock_xy": (889, 282),
        "offer": {"buttons": {}}, "modal": None, "connection_lost": False,
        "ship_health": {"shield": 1.0, "armor": 1.0, "structure": 1.0},
        "has_active_mission": True, "mission_panel_observed": True,
        "mission_travel_support": True, "hostiles": [], "gates": [],
        "beacons": [], "empty_xy": None, "mission_site_hint": None,
        "drones_out": False, "active_mission_title": "Poke (3 of 5)",
    }


clk = Clock()
m = SecurityMode(clock=clk)
m._destination_set = True          # da set destination -> giu che do travel
w = docked_world()

a = m._travel_actions(w)
ok("tick dau tien phat lenh undock", a[0]["do"] == "undock", str(a))
ok("undock co toa do that (889,282)", a[0]["at"] == (889, 282), str(a))

# Cu 3s sau (cu: click tiep / sau 3 click la BLOCKED) -> phai WAIT, khong block.
clk.advance(3)
a = m._travel_actions(w)
ok("3s sau khi bam: WAIT, KHONG bam lai, KHONG BLOCKED",
   a[0]["do"] == "wait" and "KHONG" in a[0]["why"], str(a))
ok("phase van UNDOCK (khong ket luan that bai)", m.phase == "UNDOCK", m.phase)

# 9s: van wait (tong 12s = retry interval)
clk.advance(9)
a = m._travel_actions(w)
ok("12s: cho phep bam lai 1 lan (co gian cach), khong spam moi tick",
   a[0]["do"] == "undock", str(a))
ok("dem click = 2", m._undock_attempts == 2, str(m._undock_attempts))

clk.advance(12)
a = m._travel_actions(w)
ok("24s: bam lan 3 (toi da)", a[0]["do"] == "undock" and m._undock_attempts == 3, str(a))

clk.advance(12)
a = m._travel_actions(w)
ok("36s: da het 3 click nhung VAN CHO bang chung, khong BLOCKED",
   a[0]["do"] == "wait" and "IN_SPACE" in a[0]["why"], str(a))

# Vuot timeout van DOCKED -> BLOCKED co ly do that.
clk.advance(10)
a = m._travel_actions(w)
ok("46s van DOCKED -> BLOCKED co ly do (sau khi cho du 45s)",
   a[0]["do"] == "blocked" and "45s" in a[0]["why"], str(a))

# === Bang chung IN_SPACE xuat hien TRUOC timeout -> khong duoc block, reset ===
clk2 = Clock()
m2 = SecurityMode(clock=clk2)
m2._destination_set = True
w2 = docked_world()
m2._travel_actions(w2)
clk2.advance(8)
w_space = dict(w2)
w_space.update({"docked": False, "hostiles": [], "gates": [], "beacons": [],
                "empty_xy": (320, 763), "travel": {"markers": []},
                "ship_health": {"shield": 1.0, "armor": 1.0, "structure": 1.0},
                "modal": None, "connection_lost": False,
                "has_active_mission": True, "mission_panel_observed": True,
                "mission_travel_support": True, "active_mission_title": "Poke (3 of 5)",
                "drones_out": False, "mission_site_hint": None,
                "maneuver": None, "speed_mps": 0.0, "cargo_loaded": False,
                "cargo_empty_now": True, "agents": [], "offer": {},
                "agent_dialog_open": False, "mission_link_xy": None,
                "undock_xy": None, "station": None, "system": "New Caldari",
                "security": 0.9, "home_station": None, "space_menu": [],
                "weapons_firing": False, "afterburner_on": False,
                "ship_panel_observed": False, "active_ship": None,
                "route": {}, "selected_name": None, "targets": 0,
                "overview_count": 0, "mission_is_courier": False,
                "mission_support": "combat", "drones_in_space": 0})
acts = m2.tick(w_space)
ok("IN_SPACE xuat hien -> tick khong tra blocked",
   not any(x.get("do") == "blocked" for x in acts), str(acts))
ok("IN_SPACE -> reset bo dem undock + dat _was_in_space",
   m2._was_in_space is True and m2._undock_attempts == 0
   and m2._undock_wait_since is None and m2._undock_sent_at is None,
   f"was={m2._was_in_space} n={m2._undock_attempts} "
   f"since={m2._undock_wait_since} sent={m2._undock_sent_at}")

ok("hang so hop ly: timeout > retry interval * max_clicks",
   UNDOCK_EVIDENCE_TIMEOUT_S > UNDOCK_RETRY_INTERVAL_S * UNDOCK_MAX_CLICKS,
   f"{UNDOCK_EVIDENCE_TIMEOUT_S} vs {UNDOCK_RETRY_INTERVAL_S * UNDOCK_MAX_CLICKS}")

print(f"\nKet qua: {PASS} PASS / 0 FAIL")
