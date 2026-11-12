"""Test control layer — ActionSpec chạy dry-run, verify logic, retry policy.

Không cần EVE: dry=True không bấm phím thật; verify functions test trên fake eye.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.control import (  # noqa: E402
    ActionSpec, act_confirm, act_drones_engage, act_drones_return, act_launch_drones,
    act_module, act_orbit, act_overheat, execute,
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


# 1. dry-run: không bấm thật, log combo đúng keybind UniWiki
r = execute(act_module(1, "high"), dry=True)
ok("module_f1_dry", r["ok"] and r["input_log"][0]["combo"] == "F1", str(r["input_log"]))

r = execute(act_module(2, "mid"), dry=True)
ok("module_alt_f2", r["input_log"][0]["combo"] == "alt+F2", str(r["input_log"]))

r = execute(act_module(3, "low"), dry=True)
ok("module_ctrl_f3", r["input_log"][0]["combo"] == "ctrl+F3", str(r["input_log"]))

r = execute(act_overheat(1, "high"), dry=True)
ok("overheat_shift_f1", r["input_log"][0]["combo"] == "shift+F1", str(r["input_log"]))

r = execute(act_launch_drones(), dry=True)
ok("drones_shift_f", r["input_log"][0]["combo"] == "shift+F", str(r["input_log"]))

r = execute(act_drones_engage(), dry=True)
ok("drones_f_engage", r["input_log"][0]["combo"] == "F", str(r["input_log"]))

r = execute(act_drones_return(), dry=True)
ok("drones_shift_r", r["input_log"][0]["combo"] == "shift+R", str(r["input_log"]))

r = execute(act_confirm(), dry=True)
ok("confirm_enter", r["input_log"][0]["combo"] == "ENTER", str(r["input_log"]))

# 2. orbit: click chọn với W GIỮ (hold w_down → click → hold w_up) — ground
#    eve-hotkeys-and-widgets §1 + live 13-11: 'W type 25 Enter' KHÔNG phải cơ chế EVE
r = execute(act_orbit((100, 200), 25), dry=True)
holds = [s.get("hold") for s in r["input_log"] if "hold" in s]
clicked = [s for s in r["input_log"] if "x" in s]
ok("orbit_sequence", holds == ["w_down", "w_up"] and clicked and clicked[0]["x"] == 100,
   str(r["input_log"]))

# 3. verify-fail → retry rồi fail sạch
calls = {"n": 0}


def never_ok(eye) -> bool:
    calls["n"] += 1
    return False


spec = ActionSpec("test_retry", [{"do": "combo", "mods": [], "key": "F1"}],
                  verify=never_ok, retry_max=2, verify_wait=0)
r = execute(spec, eye=object(), dry=True)
# loop: attempts 1..retry_max+1 = 3; verify gọi mỗi attempt (3 lần), fail hết → ok=False
ok("retry_then_fail", (not r["ok"]) and r["attempts"] == 3 and calls["n"] == 3, str(r))

# 4. verify-pass ngay → 1 attempt
calls2 = {"n": 0}


def always_ok(eye) -> bool:
    calls2["n"] += 1
    return True


spec2 = ActionSpec("test_pass", [{"do": "combo", "mods": [], "key": "F1"}],
                   verify=always_ok, retry_max=2, verify_wait=0)
r = execute(spec2, eye=object(), dry=True)
ok("verify_pass_one_attempt", r["ok"] and r["attempts"] == 1 and calls2["n"] == 1, str(r))

print(f"\n=> {PASS} test PASS (mọi [FAIL] exit(1) ngay)")
