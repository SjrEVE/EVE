"""Test trio.py — role FSM cho 2DPS+1Logi theo ngưỡng Gustav."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.trio import TrioRole  # noqa: E402

PASS = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} — {msg}")
        sys.exit(1)


# role sai → ValueError
try:
    TrioRole("sniper")
    ok("role_validate", False, "không raise")
except ValueError:
    ok("role_validate", True)

# TANK: entry approach cache
t = TrioRole("tank")
acts = t.tick({"room_entry": True, "moved_this_room": False, "hp": 1.0})
ok("tank_entry_approach", acts and acts[0]["do"] == "approach_cache", str(acts))
# hp rơi → signal logi
acts = t.tick({"room_entry": False, "hp": 0.5})
ok("tank_signal_logi", any(a["do"] == "signal_logi_all_reps" for a in acts), str(acts))

# DPS: giữ orbit tank
d = TrioRole("dps")
acts = d.tick({"dist_to_tank_km": 12.0})
ok("dps_orbit_tank", acts and acts[0]["do"] == "orbit_tank", str(acts))
# switch target đồng bộ
acts = d.tick({"dist_to_tank_km": 2.0, "current_target": "X", "want_target": "Y"})
ok("dps_switch_target", any(a["do"] == "switch_target" and a["to"] == "Y" for a in acts), str(acts))

# LOGI: >6 kiki → all reps
l = TrioRole("logi")
acts = l.tick({"kikimora_count": 13, "tank_hp": 1.0, "cap": 0.9})
ok("logi_kiki_threshold", acts and acts[0]["do"] == "all_reps_on_tank" and l.reps_open, str(acts))
# tank hp <60% → all reps
l2 = TrioRole("logi")
acts = l2.tick({"kikimora_count": 2, "tank_hp": 0.5, "cap": 0.9})
ok("logi_hp_threshold", acts and acts[0]["do"] == "all_reps_on_tank", str(acts))
# tank ổn → close reps tiết kiệm cap
acts = l2.tick({"kikimora_count": 2, "tank_hp": 0.9, "cap": 0.9})
ok("logi_close_reps", acts and acts[0]["do"] == "close_extra_reps" and not l2.reps_open, str(acts))
# cap <20% → mayday
acts = l2.tick({"kikimora_count": 2, "tank_hp": 0.9, "cap": 0.15})
ok("logi_mayday_cap", any(a["do"] == "mayday" for a in acts), str(acts))
# new room reset
l2.new_room()
ok("logi_room_reset", l2.reps_open is False, "")

print(f"\n=> {PASS} test PASS (mọi [FAIL] exit(1) ngay)")
