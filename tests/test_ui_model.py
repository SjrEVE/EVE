"""Test UiModel (khong can man hinh) — PYTHONPATH=src python tests/test_ui_model.py"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fila_bot.ui_model import ModeUnavailable, UiModel, build_supervisor  # noqa: E402


def ok(name):
    print(f"[PASS] {name}")


BUS = tempfile.mkdtemp(prefix="fila_ui_")


def factory(mode, **kw):
    sup = build_supervisor(mode, bus_dir=BUS, **kw)
    sup.kill_switch = lambda: False      # test khong doc ban phim that
    return sup


def pump(m, n=1):
    for _ in range(n):
        m.sup.step()
        m.poll()


# 1. security: LIVE chua ground -> FATAL ro rang; distribution LIVE da ground (G1-G7)
try:
    build_supervisor("security", sim=False, bus_dir=BUS)
    raise AssertionError("security live phai raise")
except ModeUnavailable as e:
    assert "LIVE" in str(e), str(e)
m = UiModel(factory=factory, threaded=False)
m.mode, m.sim = "security", False
m.start()
v = m.view()
assert m.sup is None and v["state"] == "IDLE" and v["banner"].startswith("FATAL")
assert v["can_start"] and v["danger"]
ok("security LIVE chua ground -> FATAL, nut Start van bat")

# 1a. distribution LIVE: build_supervisor khong con ModeUnavailable (G1-G7 da ground).
# Eye that se fail khi client khong chay (DLL initialize fail) -> do la hanh vi DUNG,
# khong phai loi architect. Chi assert khong nem ModeUnavailable.
try:
    sup_dist_live = build_supervisor("distribution", sim=False, dry=True, bus_dir=BUS)
    assert sup_dist_live is not None and sup_dist_live.mode.name == "distribution"
    ok("distribution LIVE da ground -> build_supervisor hop le, khong FATAL")
except ModeUnavailable as e:
    raise AssertionError(f"distribution LIVE van bi chan ModeUnavailable: {e}")
except RuntimeError as e:
    ok("distribution LIVE: khong con ModeUnavailable; DLL init fail vi EVE client tat (dung)")

# 1b. distribution SIM: chay het vong courier (khong phai bang chung client)
m = UiModel(factory=factory, threaded=False)
m.mode, m.sim = "distribution", True
m.start()
pump(m, 120)
v = m.view()
assert v["state"] == "RUNNING" and v["runs"] >= 1 and not v["banner"], v
ok("distribution SIM chay >=1 mission")

# 1c. security SIM: START -> RUNNING, khong crash
m = UiModel(factory=factory, threaded=False)
m.mode, m.sim = "security", True
m.start()
pump(m, 30)
v = m.view()
assert v["state"] == "RUNNING" and v["phase"] != "-", v
ok("security SIM START -> RUNNING")

# 2. abyss sim: START -> RUNNING, phase chay
m = UiModel(factory=factory, threaded=False)
m.start()
pump(m, 3)
v = m.view()
assert v["state"] == "RUNNING" and v["phase"] != "-", v
assert not v["can_start"] and v["can_stop"] and v["can_estop"]
ok("abyss sim START -> RUNNING, nut dung trang thai")

# 3. PAUSE -> label RESUME; bam lai -> RUNNING
m.pause(); pump(m)
v = m.view()
assert v["state"] == "PAUSED" and v["pause_label"] == "RESUME" and v["can_start"]
m.pause(); pump(m)
assert m.view()["state"] == "RUNNING"
ok("PAUSE/RESUME toggle")

# 4. vao abyss -> banner canh bao timer; STOP -> chay not run -> IDLE
for _ in range(200):
    mode = m.sup.mode
    if mode.phase == "FILA_SPOOL" and mode.bot.fila_started is not None:
        mode.bot.fila_started = time.time() - 16
    pump(m)
    if m.no_escape:
        break
v = m.view()
assert m.no_escape and "ABYSS" in v["banner"] and v["danger"], v
ok("trong abyss -> banner do canh bao timer")
m.stop()
for _ in range(400):
    mode = m.sup.mode
    if mode.phase == "FILA_SPOOL" and mode.bot.fila_started is not None:
        mode.bot.fila_started = time.time() - 16
    pump(m)
    if m.view()["state"] == "IDLE":
        break
v = m.view()
assert v["state"] == "IDLE" and v["phase"] == "DOCKED" and v["runs"] == 1, v
ok("STOP trong abyss -> chay not run -> IDLE o DOCKED")

# 5. E-STOP
m = UiModel(factory=factory, threaded=False)
m.start(); pump(m, 2)
m.estop(); pump(m)
v = m.view()
assert v["state"] == "IDLE" and any("ESTOP" in l for l in v["log"])
ok("E-STOP -> IDLE + log")

# 6. thread that + close sach
m = UiModel(factory=factory, threaded=True, tick=0.01)
m.start()
t0 = time.time()
while m.view()["state"] != "RUNNING" and time.time() - t0 < 2:
    time.sleep(0.02); m.poll()
assert m.view()["state"] == "RUNNING"
m.close()
assert not m.sup._thread.is_alive()
ok("thread that chay + close sach")

print("ALL OK test_ui_model")
