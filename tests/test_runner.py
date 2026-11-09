"""Test Supervisor (runner.py) + input.release_all — chạy: PYTHONPATH=src python tests/test_runner.py"""
from __future__ import annotations

import queue
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fila_bot.input import release_all          # noqa: E402
from fila_bot.modes import Mode                 # noqa: E402
from fila_bot.runner import Supervisor          # noqa: E402


def ok(name: str) -> None:
    print(f"[PASS] {name}")


class FakeMode(Mode):
    name = "fake"

    def __init__(self) -> None:
        super().__init__()
        self.ticks = 0
        self.safe = False
        self.no_escape = False
        self.boom = False
        self.safe_after_ticks: int | None = None

    def tick(self, world):
        if self.boom:
            raise RuntimeError("boom")
        self.ticks += 1
        if self.stop_requested and self.safe_after_ticks is not None:
            self.safe_after_ticks -= 1
            if self.safe_after_ticks <= 0:
                self.safe = True
        return [("noop",)]

    @property
    def at_safe_point(self):
        return self.safe

    @property
    def in_no_escape(self):
        return self.no_escape


def drain(sup):
    out = []
    while True:
        try:
            out.append(sup.evt_q.get_nowait())
        except queue.Empty:
            return out


class Counter:
    def __init__(self):
        self.n = 0

    def __call__(self):
        self.n += 1


def make(**kw):
    m = FakeMode()
    rel = Counter()
    sup = Supervisor(m, release_all=rel, **kw)
    return m, sup, rel


# 1. START -> RUNNING, tick + execute
m, sup, rel = make(execute=lambda acts: [{"ok": True} for _ in acts])
sup.step()
assert sup.state == "IDLE" and m.ticks == 0
sup.send("START"); sup.step()
assert sup.state == "RUNNING" and m.ticks == 1, (sup.state, m.ticks)
ticks = [e for e in drain(sup) if e["type"] == "TICK"]
assert ticks and ticks[-1]["results"] == [{"ok": True}]
ok("START -> RUNNING, tick + execute chay")

# 2. PAUSE / RESUME
sup.send("PAUSE"); sup.step(); sup.step()
assert sup.state == "PAUSED" and m.ticks == 1 and rel.n == 1
ok("PAUSE dung tick + release_all")
sup.send("RESUME"); sup.step()
assert sup.state == "RUNNING" and m.ticks == 2
ok("RESUME tick lai")

# 3. STOP an toan -> safe point -> IDLE
m.safe_after_ticks = 2
sup.send("STOP"); sup.step()
assert sup.state == "STOPPING" and m.stop_requested
sup.step()
assert sup.state == "IDLE", sup.state
ok("STOP chay toi safe point roi IDLE")

# 4. E-STOP
m, sup, rel = make()
sup.send("START"); sup.step()
sup.send("ESTOP"); sup.step()
assert sup.state == "IDLE" and rel.n == 1 and m.ticks == 1
assert any(e["type"] == "ESTOP" for e in drain(sup))
ok("E-STOP -> IDLE trong 1 step + release_all")

# 5. crash -> PAUSED + CRASH
m, sup, rel = make()
sup.send("START"); sup.step()
m.boom = True; sup.step()
assert sup.state == "PAUSED" and rel.n == 1
assert any(e["type"] == "CRASH" for e in drain(sup))
ok("exception -> PAUSED + CRASH event")

# 6. kill-switch
ks = {"on": False}
m, sup, rel = make(kill_switch=lambda: ks["on"])
sup.send("START"); sup.step()
ks["on"] = True; sup.step()
assert sup.state == "IDLE" and rel.n == 1 and m.ticks == 1
ok("kill-switch -> IDLE khong tick them")

# 7. kill-switch loi khong giet bot
m, sup, rel = make(kill_switch=lambda: 1 / 0)
sup.send("START"); sup.step()
assert sup.state == "RUNNING" and m.ticks == 1
ok("kill-switch loi -> bo qua, van chay")

# 8. max_session
now = {"t": 0.0}
m, sup, rel = make(max_session_s=10, clock=lambda: now["t"])
sup.send("START"); sup.step()
now["t"] = 11; sup.step()
assert sup.state == "STOPPING" and m.stop_requested
ok("het max_session -> STOP an toan")

# 9. abyss warn
m, sup, rel = make()
m.no_escape = True
sup.send("START"); sup.step(); drain(sup)
sup.send("PAUSE"); sup.step()
assert any(e["type"] == "WARN" for e in drain(sup))
sup.send("STOP"); sup.step()
assert sup.state == "STOPPING"
assert any(e["type"] == "WARN" for e in drain(sup))
ok("PAUSE/STOP trong abyss -> canh bao timer")

# 10. lenh la
m, sup, rel = make()
sup.send("FLY"); sup.step()
assert sup.state == "IDLE" and any(e["type"] == "REJECT" for e in drain(sup))
ok("lenh la -> REJECT")

# 11. START lai sau STOP
m, sup, rel = make()
m.safe_after_ticks = 1
sup.send("START"); sup.step(); sup.send("STOP"); sup.step(); sup.step()
assert sup.state == "IDLE"
m.safe = False
sup.send("START"); sup.step()
assert sup.state == "RUNNING" and not m.stop_requested
ok("START lai sau STOP reset co stop")


# 12. release_all
class FakeUser32:
    def __init__(self, held):
        self.held = set(held)
        self.kb, self.ms = [], []

    def GetAsyncKeyState(self, vk):
        return 0x8000 if vk in self.held else 0

    def keybd_event(self, vk, scan, flags, extra):
        self.kb.append((vk, flags))

    def mouse_event(self, flags, x, y, d, e):
        self.ms.append(flags)


u = FakeUser32({0x11, 0x01})
r = release_all(user32=u)
assert r["released"] == ["ctrl", "lmb"], r
assert u.kb == [(0x11, 2)] and u.ms == [0x0004]
ok("release_all nha dung Ctrl + LMB dang giu")
u = FakeUser32(set())
assert release_all(user32=u)["released"] == [] and not u.kb and not u.ms
ok("release_all khong ban phim thua")
assert release_all(dry_run=True)["dry"] is True
ok("release_all dry")

# 13. thread that
m, sup, rel = make()
sup.start_thread(tick_interval=0.01)
sup.send("START")
t0 = time.time()
while m.ticks < 3 and time.time() - t0 < 2:
    time.sleep(0.01)
sup.shutdown()
assert m.ticks >= 3 and sup.state == "IDLE" and not sup._thread.is_alive()
ok("thread chay + shutdown sach")

print("ALL OK test_runner")