"""Test main glue — RealExecutor với FakeEye: snapshot từ eye + action→keybind."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.main import RealExecutor  # noqa: E402

PASS = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} — {msg}")
        sys.exit(1)


# FakeEye từ helper (kế thừa Eye thật — logic find/health giữ nguyên, chỉ fake root)
from fake_eye import FakeEye  # noqa: E402

fe = FakeEye()
ex = RealExecutor(fe, input_dry=True)

# 1. snapshot từ eye: hp = min(0.9,0.55,1.0)=0.55; cap = 100%; overview 1; drones 2
ex.refresh_from_eye()
snap = ex.snapshot()
ok("hp_min_conservative", snap["hp"] == 0.55, str(snap))
ok("cap_percent", snap["cap"] == 1.0, str(snap))
ok("overview_count", snap["overview_count"] == 1, str(snap))
ok("drones_count", snap["drones_in_space"] == 2, str(snap))
ok("maneuver_read", snap["maneuver"] == "orbit", str(snap))

# 2. orbit action → keybind thật (dry log): click entry + W + số + Enter
ex.actions.append(("orbit", 12))
res = ex.process_actions()
r = res[0]
combos = [s.get("combo") for s in r["input_log"] if "combo" in s]
typed = [s.get("typed") for s in r["input_log"] if "typed" in s]
clicked = [s for s in r["input_log"] if "x" in s]
ok("orbit_glue_keys", combos == ["W", "ENTER"] and typed == ["12"] and clicked and clicked[0]["x"] == 125,
   str(r["input_log"]))
ok("orbit_ok_flag", r.get("ok") is True and r.get("action") == "orbit", str(r))

# 3. action chưa ground → SKIP rõ ràng, không đoán
ex.actions.append(("fila", "Chaotic Gamma"))
res = ex.process_actions()
ok("fila_not_groundable_skip", res[0].get("skipped") == "fila"
   and "chưa ground" in res[0]["reason"], str(res))

# 4. module/stop/reload/confirm qua keybind chuẩn
ex.actions.append(("activate", 1))
ex.actions.append(("stop",))
ex.actions.append(("reload",))
ex.actions.append(("confirm",))
res = ex.process_actions()
oks = [x for x in res if x.get("ok")]
combos_all = [s.get("combo") for x in res for s in x.get("input_log", []) if "combo" in s]
ok("module_stop_reload_confirm_keys", len(oks) == 4
   and combos_all == ["F1", "ctrl+SPACE", "ctrl+R", "ENTER"], str(combos_all))

# 5. Bot tích hợp với RealExecutor (chuỗi đúng như main.py: tick → process_actions)
from fila_bot.bus import FileBus      # noqa: E402
from fila_bot.config import Config    # noqa: E402
from fila_bot.reflex import Bot       # noqa: E402
import tempfile                       # noqa: E402

tmp = Path(tempfile.mkdtemp(prefix="fila_glue_"))
bus = FileBus(tmp)
ex2 = RealExecutor(FakeEye(), input_dry=True, bus=bus)   # main.py truyền bus vào executor
bot = Bot(bus, Config(escape_hp=0.25, unknown_timeout=0.25), ex2)
with (tmp / "fc_to_bot.jsonl").open("a", encoding="utf-8") as fh:
    fh.write('{"id":"g1","cmd":"ORBIT","arg":5}\n')
bot.run(max_ticks=1, tick_sleep=0.01)
ex2.refresh_from_eye()                       # main.py gọi trước mỗi tick
results = ex2.process_actions()              # main.py gọi sau tick
inputs = [e for e in bus.read_outbox(50) if e["type"] == "INPUT"]
ok("bot_live_glue_input_event", len(inputs) >= 1 and inputs[-1].get("action") == "orbit",
   f"results={results[-1:]} inputs={inputs[-2:]}")
ok("bot_state_from_eye", ex2.hp == 0.55, f"ex2.hp={ex2.hp}")

print(f"\n=> {PASS} test PASS (mọi [FAIL] exit(1) ngay)")
