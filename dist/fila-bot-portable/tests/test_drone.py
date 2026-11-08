"""Test drone.py — aggro rules theo cơ chế thật."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.drone import DroneManager  # noqa: E402

PASS = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} — {msg}")
        sys.exit(1)


d = DroneManager(max_drones=5)

# launch khi chưa redbox = CHẶN (UniWiki Tips: launch sớm = nuke)
allow, why = d.can_launch(redboxed=False)
ok("no_redbox_block", allow is False and "redbox" in why, why)

# redbox rồi → launch ok
allow, why = d.can_launch(redboxed=True)
ok("redbox_ok", allow is True, why)
d.on_launch()
ok("state_engaged", d.state == "ENGAGED" and d.in_space == 5, str(d.state))

# drone bị đánh → hp rơi < 40% → recall
r = d.update({"drones_in_space": 5, "drones_hp_avg": 0.3})
ok("hp_recall", r is not None and r["action"] == "recall" and d.state == "RECALLING", str(r))

# target ra ngoài leash 25km → return_orbit (không để idle trôi)
d.state = "ENGAGED"
d.hp_avg = 0.9
r = d.update({"drones_in_space": 5, "drones_hp_avg": 0.9, "dist_to_drone_target_km": 40})
ok("leash_return_orbit", r is not None and r["action"] == "return_orbit", str(r))

# drone về hết → HIDDEN
r = d.update({"drones_in_space": 0, "drones_hp_avg": 1.0})
ok("all_home_hidden", d.state == "HIDDEN", str(d.state))

# gate ready chỉ khi 0 drone ngoài
ok("gate_ready", d.gate_ready() is True, "")
d.in_space = 2
ok("gate_not_ready", d.gate_ready() is False, "")

print(f"\n=> {PASS} test PASS (mọi [FAIL] exit(1) ngay)")
