"""Test guards — mỗi guard test với đúng kịch bản cái chết thật mà nó học từ."""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.guards import (  # noqa: E402
    CapStarveGuard, CloudSlingGuard, DroneOutGuard, GuardManager, LootGreedGuard,
    LoopWatchdog, MultiClientGuard, OverviewEmptyGuard, PassiveSafetyGuard, PreflightGuard,
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


# DEATH #1: overview empty 10s khi đang FIGHT
g = OverviewEmptyGuard(timeout_s=0.1)
st = {"phase": "ROOM2_FIGHT", "overview_count": 0}
g.check(st)
time.sleep(0.15)
r = g.check(st)
ok("death1_overview_empty", r is not None and "survival" in r["action"], str(r))
# overview sống lại → reset
st["overview_count"] = 3
ok("death1_reset", g.check(st) is None, "đáng lẽ None")

# DEATH #2: action lặp 5+ lần không đổi state
g = LoopWatchdog(max_same=5)
st = {"phase": "FILA_SPOOL", "last_action": "confirm"}
r = None
for _ in range(6):
    r = g.check(st)
ok("death2_loop_spam", r is not None and "mayday" in r["action"], str(r))
# đổi action → reset
st["last_action"] = "lock"
ok("death2_reset", g.check(st) is None, "đáng lẽ None")

# DEATH #3: GATE khi drone còn ngoài
allow, why = DroneOutGuard.allow_gate({"drones_in_space": 2})
ok("death3_drones_out_block", allow is False and "drone" in why, why)
allow, why = DroneOutGuard.allow_gate({"drones_in_space": 0})
ok("death3_drones_in_ok", allow is True, why)

# DEATH #4: Tachyon sling — speed spike
g = CloudSlingGuard(max_speed_mps=2500)
r = g.check({"speed_mps": 4200})
ok("death4_speed_spike_stop", r is not None and r["action"] == "stop", str(r))
r = g.check({"speed_mps": 1100, "weather": "Dark", "mwd_on": True})
ok("death4_dark_mwd", r is not None and r["action"] == "disable_mwd", str(r))
r = g.check({"speed_mps": 1100, "weather": "Dark", "mwd_on": False})
ok("death4_ok_ab", r is None, str(r))

# DEATH #5: cap cạn khi tank on
g = CapStarveGuard(cap_floor=0.25)
r = g.check({"cap": 0.15, "tank_on": True})
ok("death5_cap_starve", r is not None and r["action"] == "power_save"
   and "prop" in r["disable"], str(r))
r = g.check({"cap": 0.15, "tank_on": False})
ok("death5_tank_off_noop", r is None, str(r))

# DEATH #6: damp — lock fail 3 lần
g = Damping = __import__("fila_bot.guards", fromlist=["DampingGuard"]).DampingGuard(max_lock_fail=3)
g = __import__("fila_bot.guards", fromlist=["DampingGuard"]).DampingGuard(max_lock_fail=3)
st = {"last_lock_failed": True}
r = None
for _ in range(3):
    r = g.check(st)
ok("death6_damped_next_target", r is not None and r["action"] == "next_target", str(r))
st = {"last_lock_failed": False}
ok("death6_reset", g.check(st) is None, "đáng lẽ None")

# DEATH #7: loot can xa gate
g = LootGreedGuard(max_dist_for_loot_m=15000)
r = g.check({"want_loot": True, "dist_gate": 25000})
ok("death7_loot_greed_skip", r is not None and r["action"] == "skip_loot", str(r))
r = g.check({"want_loot": True, "dist_gate": 8000})
ok("death7_loot_close_ok", r is None, str(r))

# DEATH #8: precheck filament
allow, why = PreflightGuard.allow_fila({"ammo_loaded": False})
ok("death8_ammo_block", allow is False and "ammo" in why, why)
allow, why = PreflightGuard.allow_fila(
    {"ammo_loaded": True, "plan_fila": {"tier": "Chaotic", "weather": "Gamma"},
     "fila_name": "Raging Dark Filament"})
ok("death8_wrong_tier_block", allow is False and "tier" in why, why)
allow, why = PreflightGuard.allow_fila(
    {"ammo_loaded": True, "plan_fila": {"tier": "Chaotic", "weather": "Gamma"},
     "fila_name": "Chaotic Gamma Filament"})
ok("death8_correct_ok", allow is True, why)

# DEATH #9: đứng trơ 6s khi FIGHT
g = PassiveSafetyGuard(timeout_s=0.1)
st = {"phase": "ROOM1_FIGHT", "maneuver": None}
g.check(st)
time.sleep(0.15)
r = g.check(st)
ok("death9_drift_orbit", r is not None and r["action"] == "orbit_cache", str(r))
st["maneuver"] = "orbit"
ok("death9_orbit_ok", g.check(st) is None, "đáng lẽ None")

# DEATH #10: multibox chưa pin pid + nhiều client (Viir "UI changes 3/21/26" 2026-03)
g10 = MultiClientGuard()
r = g10.check({"client_windows_count": 2, "multibox_pinned": False})
ok("death10_multi_client_mayday", r is not None and r["action"] == "mayday", str(r))
ok("death10_warn_once", g10.check({"client_windows_count": 2,
                                   "multibox_pinned": False}) is None)
g10b = MultiClientGuard()
ok("death10_pinned_ok", g10b.check({"client_windows_count": 3,
                                    "multibox_pinned": True}) is None)
ok("death10_single_ok", g10b.check({"client_windows_count": 1}) is None)
ok("death10_default_ok", g10b.check({}) is None)
mgr2 = GuardManager()
acts2 = mgr2.check_all({"phase": "ROOM1_FIGHT", "client_windows_count": 2})
ok("death10_in_manager", any(a.get("guard") == "multi_client" for a in acts2), str(acts2))

# Manager: nhiều guard cùng bắn
mgr = GuardManager()
acts = mgr.check_all({"phase": "ROOM1_FIGHT", "overview_count": 0, "speed_mps": 900,
                      "cap": 0.8, "maneuver": "orbit"})
ok("manager_collects", isinstance(acts, list), str(acts))

print(f"\n=> {PASS} test PASS (mọi [FAIL] exit(1) ngay)")
