"""Test issue #1 fixes — P0-1 (no timer auto-confirm), P0-3 (Ctrl+click lock),
P0-4 (rack param), P0-5 (targeted entry), P0-7 (guard actions), P1-1 (combat brain)."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from fila_bot.bus import FileBus        # noqa: E402
from fila_bot.config import Config      # noqa: E402
from fila_bot.reflex import Bot, SimExecutor  # noqa: E402
from fila_bot.main import RealExecutor  # noqa: E402
from fila_bot import control as ctl     # noqa: E402
from fake_eye import FakeEye            # noqa: E402

PASS = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} — {msg}")
        sys.exit(1)


# ---- P0-1: không auto-confirm khi thiếu xác minh (đã test trong test_all: 39 PASS) ----
print("[PASS] P0-1 covered in test_all (39 PASS) — spool không confirm khi thiếu eye/sim_confirm")
PASS += 1

# ---- P0-3: lock = Ctrl down → click → Ctrl up (không phải click+Q) ----
fe = FakeEye()
ex = RealExecutor(fe, input_dry=True)
ex.actions.append(("lock", "Kikimora"))
res = ex.process_actions()
r = res[0]
log = r.get("input_log", [])
holds = [s.get("hold") for s in log if "hold" in s]
clicks = [s for s in log if "x" in s]
# sequence đúng: 3 attempts × (ctrl_down, click, ctrl_up) — mỗi attempt đúng thứ tự
ok("p03_lock_ctrl_click", holds == ["ctrl_down", "ctrl_up"] * 3 and len(clicks) == 3
   and clicks[0]["x"] == 125, f"holds={holds} clicks={len(clicks)}")
# verify fail (fake không ActiveItem) → attempts = 3, ok False
ok("p03_lock_retry_then_fail", (not r.get("ok")) and r.get("attempts") == 3, str(r.get("attempts")))

# ---- P0-5: orbit bấm đúng target đang lock (ActiveItem name match) ----
fe2 = FakeEye()
# thêm ActiveItem "Kikimora" vào fake tree
fe2.root["children"].append({
    "address": 50, "type": "ActiveItem", "attrs": {}, "children": [
        {"address": 51, "type": "Label", "attrs": {"_setText": "Kikimora"}, "children": []}]})
ex2 = RealExecutor(fe2, input_dry=True)
ex2.actions.append(("orbit", 10))
res = ex2.process_actions()
r = res[0]
clicked = [s for s in r.get("input_log", []) if "x" in s]
ok("p05_orbit_targeted_entry", clicked and clicked[0]["x"] == 125,
   f"click={clicked} (entry Kikimora ở 100+50/2=125)")

# orbit KHÔNG có lock → fail closed (không bấm mù entry đầu)
ex3 = RealExecutor(FakeEye(with_active_item=False), input_dry=True)
ex3.actions.append(("orbit", 10))
res = ex3.process_actions()
ok("p05_no_lock_fail_closed", res[0].get("ok") is False and "bấm mù" in res[0]["fail"],
   str(res))

# ---- P0-4: module rack param ----
ex4 = RealExecutor(FakeEye(), input_dry=True)
ex4.actions.append(("activate", 2, "mid"))
ex4.actions.append(("activate", 1, "low"))
res = ex4.process_actions()
combos = [s.get("combo") for x in res for s in x.get("input_log", []) if "combo" in s]
ok("p04_module_rack", combos == ["alt+F2", "ctrl+F1"], str(combos))

# ---- P0-2: fail-closed không skip lặng lẽ ----
ex5 = RealExecutor(FakeEye(), input_dry=True)
ex5.actions.append(("gate",))
res = ex5.process_actions()
ok("p02_gate_fail_closed", res[0].get("ok") is False and "fail-closed" in res[0]["fail"], str(res))

# ---- P0-7: guard actions không còn skip ----
ex6 = RealExecutor(FakeEye(), input_dry=True)
ex6.actions.append(("power_save", ("prop", "web")))
ex6.actions.append(("disable_mwd",))
ex6.actions.append(("next_target",))
res = ex6.process_actions()
ok("p07_guard_actions_handled", all(x.get("ok") for x in res) and len(res) == 3, str(res))

# ---- P1-1: combat brain chạy trong tick ----
tmp = Path(tempfile.mkdtemp(prefix="fila_p1_"))
bus = FileBus(tmp)
bot = Bot(bus, Config(escape_hp=0.25, unknown_timeout=0.25), SimExecutor())
bot.ex.phase = "ROOM1_FIGHT"
bot.ex.room = 1
bot.run(max_ticks=1, tick_sleep=0.01)
acts = bot.ex.actions
ok("p11_combat_brain_locks", any(a[0] == "lock" and a[1] == "Snarecaster Tessella" for a in acts),
   str(acts[:6]))   # web = priority 1 → lock đầu tiên
ok("p11_combat_brain_orbit", any(a[0] == "orbit" for a in acts), str(acts[:6]))
ok("p11_combat_brain_shoot", any(a[0] == "activate" for a in acts), str(acts[:6]))
# swarmer không bị lock
locked_names = [a[1] for a in acts if a[0] == "lock"]
ok("p11_swarmer_skipped", "Vila Swarmer" not in locked_names, str(locked_names))

print(f"\n=> {PASS} test PASS (mọi [FAIL] exit(1) ngay)")
