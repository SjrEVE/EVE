"""Guards UX + mechanic: tham so khong bi bo qua, 'khong biet' khong bi bia, CLI dung that.

Moi test o day tuong ung 1 loi THAT phat hien khi ra soat toan bo UI/UX + mechanic:
- CLI in filament ra man hinh nhung AbyssMode van dung default
- Supervisor khong co trang thai STOPPED/BLOCKED -> vong lap CLI khong bao gio dung
- LiveDistributionRunner bia cargo_free=400.0 va route_hisec=True
- load_cargo keo items[0] (item dau tien) thay vi item mission
- GUI khong truyen filament/max, khong hoi xac nhan khi bam that

PYTHONPATH=src python tests/test_ux_guards.py
"""
from __future__ import annotations

import sys
import tempfile
import time
import queue
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fila_bot.cli as cli  # noqa: E402
from fila_bot.bus import FileBus  # noqa: E402
from fila_bot.config import Config  # noqa: E402
from fila_bot.modes.abyss import AbyssMode, DemoSim  # noqa: E402
from fila_bot.modes.distribution import CARGO_RETRY, DistributionMode  # noqa: E402
from fila_bot.modes.live_distribution import pick_item_xy, route_hisec_value  # noqa: E402
from fila_bot.reflex import Bot  # noqa: E402
from fila_bot.runner import Supervisor  # noqa: E402
from fila_bot.ui_model import UiModel, build_supervisor  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="fila_ux_"))


def ok(name: str) -> None:
    print(f"[PASS] {name}")


def offer_world(**kw):
    w = {
        "docked": True, "station": "AGT", "agent_station": "AGT", "pickup": "AGT",
        "dropoff": "DST",
        "offer": {"type": "courier", "cargo_m3": 1.0,
                  "buttons": {"accept": (10, 10), "decline": (20, 10)}},
        "mission_active": False, "cargo_loaded": False, "cargo_free": 100.0,
        "route_hisec": True, "popup": None,
        "travel": {"system": "S0", "station": "AGT", "docked": True, "markers": [],
                   "warping": False, "menu": [], "route_panel": True},
    }
    w.update(kw)
    return w


# 1. build_supervisor phai truyen filament/max_runs/engine xuong AbyssMode.
sup = build_supervisor("abyss", filament="Cataclysmic Dark Filament", max_runs=2,
                       engine="bt", runs_dir=TMP, bus_dir=TMP / "bus1")
assert sup.mode.filament == "Cataclysmic Dark Filament", sup.mode.filament
assert sup.mode.max_runs == 2 and sup.mode.engine == "bt"
sup.shutdown()
ok("build_supervisor: filament/max_runs/engine khong bi bo qua")

# 2. max_missions truyen xuong DistributionMode va mode dung dung so mission.
sup = build_supervisor("distribution", max_missions=2, runs_dir=TMP)
assert sup.mode.max_missions == 2
sup.send("START")
for _ in range(600):
    sup.step()
    if sup.mode.phase == "IDLE_DONE":
        break
assert sup.mode.phase == "IDLE_DONE", sup.mode.phase
assert sup.mode.done == 2, sup.mode.done
sup.shutdown()
ok("DistributionMode: max_missions=2 -> chay dung 2 mission roi IDLE_DONE")

# 3. cargo_free None: mo Inventory roi thu lai, KHONG block ngay tick dau.
m = DistributionMode()
acts = m.tick(offer_world(cargo_free=None))
assert acts and acts[0]["do"] == "open_inventory", acts
for _ in range(CARGO_RETRY + 2):
    m.tick(offer_world(cargo_free=None))
assert m.phase == "BLOCKED", m.phase
assert "Inventory" in (m.blocked or ""), m.blocked
ok(f"OFFER thieu cargo_free: open_inventory {CARGO_RETRY} lan roi moi block")

# 4. route_hisec None: block ngay va co chi dan --allow-unknown-sec (khong doan hisec).
m = DistributionMode()
m.tick(offer_world(route_hisec=None))
assert m.phase == "BLOCKED", m.phase
assert "--allow-unknown-sec" in (m.blocked or ""), m.blocked
ok("OFFER thieu sec route: block (fail-closed) + huong dan --allow-unknown-sec")

# 5. load_cargo chi keo item mission, khong keo item dau tien.
items = [{"name": "Ammo", "center": (1, 2)}, {"name": "Encoded Data Chip", "center": (9, 9)}]
assert pick_item_xy(items, "Encoded Data Chip") == (9, 9)
assert pick_item_xy(items, "encoded data chip") == (9, 9)
assert pick_item_xy(items, "") is None
assert pick_item_xy(items, "Nanite Repair Paste") is None
ok("pick_item_xy: khop ten mission, khong biet ten -> None (khong keo bua)")

# 6. route_hisec chi True khi CHAC CHAN.
assert route_hisec_value(False, 0.9, 0) is True
assert route_hisec_value(False, 0.9, 3) is None
assert route_hisec_value(False, 0.4, 0) is None
assert route_hisec_value(False, None, 0) is None
assert route_hisec_value(True, 0.4, 5) is True
ok("route_hisec_value: chi ket luan hisec khi cung he + sec>=0.5 + 0 jump")

# 7. engine=bt chay duoc run sim giong fsm.
def run_abyss(engine: str):
    ex = DemoSim(fight_ticks=1)
    ex.filaments = 3
    bot = Bot(FileBus(TMP / f"bus_{engine}"), Config(), ex)
    mode = AbyssMode(bot, engine=engine, max_runs=1)
    for _ in range(300):
        mode.tick(None)
        if mode.runs >= 1:
            break
    return mode


fsm, bt = run_abyss("fsm"), run_abyss("bt")
assert fsm.runs == 1, f"fsm runs={fsm.runs}"
assert bt.runs == 1, f"bt runs={bt.runs}"
ok("Abyss: engine=bt va engine=fsm deu hoan tat 1 run sim")

# 8. engine la -> ValueError (khong am tham chay fsm).
try:
    AbyssMode(Bot(FileBus(TMP / "bus_bad"), Config(), DemoSim()), engine="x")
except ValueError:
    ok("AbyssMode: engine la -> ValueError")
else:
    raise AssertionError("engine la khong bi tu choi")


# 9. _watch phai DUNG khi mode blocked / IDLE_DONE (truoc day lap vo han).
class StubMode:
    name = "stub"
    phase = "AGENT"
    stop_requested = False
    at_safe_point = True
    in_no_escape = False

    def __init__(self, phase: str, blocked: str | None = None) -> None:
        self.phase = phase
        self._blocked = blocked

    def status(self):
        return {"blocked": self._blocked, "runs": 1 if self.phase == "IDLE_DONE" else 0,
                "declined": 0}

    def tick(self, _w):
        return []

    def request_safe_stop(self) -> None:
        pass


t0 = time.time()
rc_blocked = cli._watch(Supervisor(StubMode("AGENT", "test block"), execute=lambda a: [],
                                   refresh=lambda: None), abyss=False, tick=0.01)
assert rc_blocked == 3, rc_blocked
rc_done = cli._watch(Supervisor(StubMode("IDLE_DONE"), execute=lambda a: [],
                                refresh=lambda: None), abyss=False, tick=0.01)
assert rc_done == 0, rc_done
ok(f"_watch: tra 3 khi blocked, 0 khi IDLE_DONE ({time.time() - t0:.1f}s)")

# 10. UiModel: factory cu (khong nhan filament) van chay nho fallback TypeError.
def old_factory(mode, sim=True, dry=True, max_hours=4.0):
    return build_supervisor(mode, sim=True, dry=True, runs_dir=TMP)


m = UiModel(factory=old_factory, tick=0.01, runs_dir=TMP)
m.filament = "Cataclysmic Dark Filament"
m.max_missions = 1
m.start()
assert m.sup is not None and m.error is None, m.error
m.poll()
v = m.view()
assert "declined" in v and v["can_estop"] is False
m.close()
ok("UiModel: factory cu van chay, view() co 'declined', can_estop dung o IDLE")

# 11. TypeError that trong factory KHONG bi fallback che mat.
def bad_factory(mode, **kw):
    raise TypeError("boom that su")


m = UiModel(factory=bad_factory, tick=0.01, runs_dir=TMP)
m.start()
assert m.error and "boom that su" in m.error, m.error
ok("UiModel: TypeError that -> hien FATAL, khong retry mu")

# Live runner must terminate and release ownership when its acquired client window vanishes.
class WatchSup:
    mode = StubMode("AGENT")
    state = "IDLE"
    ticks = 0
    evt_q = queue.Queue()
    def start_thread(self, tick_interval): self.started = True
    def send(self, event): self.event = event
    def shutdown(self): self.stopped = True

watch_sup = WatchSup()
with mock.patch.object(cli, "find_client_window", return_value=None) as find_window, \
     mock.patch.object(cli.time, "sleep", return_value=None):
    rc_closed = cli._watch(watch_sup, abyss=False, client_pid=4242)
assert rc_closed == 2 and watch_sup.stopped and not getattr(watch_sup, "started", False), \
    (rc_closed, getattr(watch_sup, "stopped", False), getattr(watch_sup, "started", False))
find_window.assert_called_with(pid=4242)
ok("_watch refuses to start when acquired EVE window is already gone")

watch_mid_close = WatchSup()
with mock.patch.object(cli, "find_client_window", side_effect=[{"pid": 4242}, None]) as find_window, \
     mock.patch.object(cli.time, "sleep", return_value=None):
    rc_mid_close = cli._watch(watch_mid_close, abyss=False, client_pid=4242)
assert rc_mid_close == 2 and watch_mid_close.stopped and watch_mid_close.started
assert find_window.call_count == 2
ok("_watch shuts down the worker when EVE window disappears mid-session")

print("\nTat ca guard UX/mechanic: PASS")
