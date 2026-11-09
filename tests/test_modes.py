"""Test modes/abyss.py + Supervisor — chạy: PYTHONPATH=src python tests/test_modes.py"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fila_bot.bus import FileBus                 # noqa: E402
from fila_bot.config import Config               # noqa: E402
from fila_bot.modes.abyss import AbyssMode       # noqa: E402
from fila_bot.reflex import Bot, SimExecutor     # noqa: E402
from fila_bot.runner import Supervisor           # noqa: E402


def ok(name: str) -> None:
    print(f"[PASS] {name}")


class ClearingSim(SimExecutor):
    """Sim: mỗi room có quái 2 tick đầu rồi sạch."""

    def __init__(self):
        super().__init__()
        self.sim_confirm = True
        self._fight_ticks = 0
        self._room_key = None

    def overview_texts(self):
        key = (self.phase, self.room)
        if key != self._room_key:
            self._room_key, self._fight_ticks = key, 0
        self._fight_ticks += 1
        return super().overview_texts() if self._fight_ticks <= 2 else []


def make(max_runs=None, ex=None):
    bus = FileBus(tempfile.mkdtemp(prefix="fila_modes_"))
    ex = ex or ClearingSim()
    bot = Bot(bus, Config(), ex)
    return AbyssMode(bot, max_runs=max_runs), bus


def run_ticks(mode, n, stop_at=None):
    seen = set()
    for _ in range(n):
        if mode.phase == "FILA_SPOOL" and mode.bot.fila_started is not None:
            mode.bot.fila_started = time.time() - 16      # tua spool 15s trong sim
        mode.tick(None)
        seen.add(mode.phase)
        if stop_at and stop_at(mode):
            break
    return seen


# 1. sim chạy đủ 2 run rồi đứng ở DOCKED (hết max_runs)
m, bus = make(max_runs=2)
seen = run_ticks(m, 300)
assert m.runs == 2, (m.runs, m.phase)
assert m.phase == "DOCKED" and m.at_safe_point
for ph in ("ROOM1_FIGHT", "ROOM2_FIGHT", "ROOM3_FIGHT", "WARP_HOME"):
    assert ph in seen, (ph, seen)
ok("abyss sim: 2 run end-to-end, dừng ở DOCKED")

# 2. hết filament → không undock nữa
assert m.ex.filaments == 0
n_before = len(m.ex.actions)
run_ticks(m, 5)
assert m.phase == "DOCKED" and not any(a[0] == "undock" for a in m.ex.actions[n_before:])
ok("hết filament → đứng yên ở DOCKED")

# 3. in_no_escape đúng trong room
m, bus = make(max_runs=1)
run_ticks(m, 50, stop_at=lambda x: x.phase == "ROOM1_FIGHT")
assert m.in_no_escape and not m.at_safe_point
ok("trong room: in_no_escape=True, không phải safe point")

# 4. STOP khi đang ở TRAVEL_ENTRY → dock, không bật filament
m, bus = make()
m.tick(None)                       # DOCKED → UNDOCK → TRAVEL_ENTRY
assert m.phase == "TRAVEL_ENTRY", m.phase
m.request_safe_stop()
m.tick(None)
assert m.phase == "DOCKED" and m.ex.filaments == 2
ok("STOP trước filament → dock, giữ filament")

# 5. STOP trong abyss → chạy nốt run rồi mới về dock
m, bus = make()
run_ticks(m, 50, stop_at=lambda x: x.phase == "ROOM2_FIGHT")
m.request_safe_stop()
run_ticks(m, 100, stop_at=lambda x: x.at_safe_point)
assert m.phase == "DOCKED" and m.runs == 1 and m.ex.filaments == 1
ok("STOP trong abyss → chạy nốt run, dock, không bật run mới")


# 6. executor live (không phải sim) → BLOCKED, không tự tiến phase
class FakeLive:
    def __init__(self):
        self.phase = "DOCKED"; self.room = 0; self.hp = 1.0; self.cap = 1.0
        self.shield = self.armor = self.hull = 1.0
        self.dist_gate = 0; self.targets = 0; self.ammo = 1.0; self.weather = None
        self.filaments = 3; self.actions = []

    def snapshot(self):
        return {"phase": self.phase, "room": self.room, "hp": self.hp, "cap": self.cap,
                "shield": 1.0, "armor": 1.0, "hull": 1.0, "dist_gate": 0,
                "targets": 0, "ammo": 1.0, "weather": None}


m, bus = make(ex=FakeLive())
for _ in range(5):
    m.tick(None)
assert m.phase == "DOCKED" and m.blocked and "chưa ground" in m.blocked
assert not any(a[0] in ("undock", "fila") for a in m.ex.actions)
ok("live chưa ground → BLOCKED, không bấm undock/filament")

# 7. Supervisor + AbyssMode: START → chạy → STOP → về IDLE ở safe point
m, bus = make()
sup = Supervisor(m, release_all=lambda: None)
sup.send("START")
for _ in range(40):
    if m.phase == "FILA_SPOOL" and m.bot.fila_started is not None:
        m.bot.fila_started = time.time() - 16
    sup.step()
    if m.phase == "ROOM2_FIGHT":
        break
assert sup.state == "RUNNING" and m.in_no_escape
sup.send("STOP")
for _ in range(200):
    if m.phase == "FILA_SPOOL" and m.bot.fila_started is not None:
        m.bot.fila_started = time.time() - 16
    sup.step()
    if sup.state == "IDLE":
        break
assert sup.state == "IDLE" and m.phase == "DOCKED" and m.runs == 1, (sup.state, m.phase, m.runs)
ok("Supervisor + AbyssMode: STOP trong abyss -> chay not run -> IDLE o DOCKED")

print("ALL OK test_modes")
