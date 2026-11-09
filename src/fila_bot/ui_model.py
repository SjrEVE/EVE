"""UiModel — logic cửa sổ điều khiển, tách khỏi tkinter để test không cần màn hình.

UI chỉ gọi start/pause/stop/estop + poll()/view(). Bot chạy trong Supervisor thread.
"""
from __future__ import annotations

import queue
import time
from collections import deque
from pathlib import Path
from typing import Any, Callable

MODES = ("abyss", "distribution", "security")
MODE_LABELS = {"abyss": "Abyss", "distribution": "Distribution (courier)",
               "security": "Security mission"}


class ModeUnavailable(Exception):
    """Mode chưa làm xong — báo thẳng, không chạy giả."""


def build_supervisor(mode: str, sim: bool = True, dry: bool = True, dll: str | None = None,
                     max_hours: float | None = 4.0, bus_dir: str | None = None) -> Any:
    from . import input as inp
    from .bus import FileBus
    from .config import Config
    from .modes.abyss import AbyssMode, DemoSim
    from .reflex import Bot
    from .runner import Supervisor

    if mode not in MODES:
        raise ModeUnavailable(f"mode lạ: {mode}")
    rel = lambda: inp.release_all(dry_run=sim or dry)  # noqa: E731
    max_s = max_hours * 3600 if max_hours else None
    if mode != "abyss":
        if not sim:
            # Live distribution/security cần reader agent/inventory/jump/dock thật (G1–G7).
            # Chưa ground → từ chối thẳng, không chạy giả trên client.
            raise ModeUnavailable(
                f"{MODE_LABELS[mode]} LIVE: chưa ground agent/inventory/jump/dock "
                "trên client thật (G1–G7) — chỉ chạy được SIM")
        from .sim_worlds import DistSim, SecSim
        if mode == "distribution":
            from .modes.distribution import DistributionMode
            w = DistSim()
            mode_obj: Any = DistributionMode()
            refresh: Any = w.world
        else:
            from .modes.security import SecurityMode
            w = SecSim()
            mode_obj = SecurityMode(runner=w)
            refresh = None
        return Supervisor(mode_obj, execute=w.apply, refresh=refresh, release_all=rel,
                          kill_switch=inp.kill_switch_pressed, max_session_s=max_s)
    bus = FileBus(bus_dir or Path(__file__).resolve().parents[2] / "bus")
    if sim:
        ex: Any = DemoSim()
        execute: Callable = lambda acts: []
        refresh = None
    else:
        from .eye import Eye
        from .main import RealExecutor
        ex = RealExecutor(Eye(dll_path=dll), input_dry=dry, bus=bus)
        execute = lambda acts: ex.process_actions()
        refresh = ex.refresh_from_eye
    mode_obj = AbyssMode(Bot(bus, Config(), ex))
    return Supervisor(mode_obj, execute=execute, refresh=refresh,
                      release_all=lambda: inp.release_all(dry_run=sim or dry),
                      kill_switch=inp.kill_switch_pressed,
                      max_session_s=max_hours * 3600 if max_hours else None)


class UiModel:
    def __init__(self, factory: Callable = build_supervisor, threaded: bool = True,
                 tick: float = 0.3, log_max: int = 200) -> None:
        self.factory = factory
        self.threaded = threaded
        self.tick = tick
        self.mode = "abyss"
        self.sim = True
        self.dry = True
        self.max_hours: float | None = 4.0
        self.sup: Any = None
        self.state = "IDLE"
        self.phase: str | None = None
        self.status: dict[str, Any] = {}
        self.no_escape = False
        self.error: str | None = None
        self.started: float | None = None
        self.log: deque[str] = deque(maxlen=log_max)

    def _log(self, msg: str) -> None:
        self.log.append(time.strftime("%H:%M:%S ") + msg)

    # ---------------- buttons ----------------
    def start(self) -> None:
        if self.sup is not None and self.sup.state == "PAUSED":
            self.sup.send("RESUME")
            return
        if self.sup is not None and self.sup.state != "IDLE":
            return
        if self.sup is not None:
            self.sup.shutdown()
        self.error, self.phase, self.status = None, None, {}
        try:
            self.sup = self.factory(self.mode, sim=self.sim, dry=self.dry,
                                    max_hours=self.max_hours)
        except Exception as e:  # noqa: BLE001 — UI phải hiện lỗi, không crash
            self.sup = None
            self.state = "IDLE"
            self.error = f"FATAL: {e}"
            self._log(self.error)
            return
        if self.threaded:
            self.sup.start_thread(self.tick)
        self.sup.send("START")
        self.started = time.time()
        self._log(f"START {self.mode} sim={self.sim} dry={self.dry}")

    def pause(self) -> None:
        if self.sup is None:
            return
        if self.sup.state == "RUNNING":
            self.sup.send("PAUSE")
        elif self.sup.state == "PAUSED":
            self.sup.send("RESUME")

    def stop(self) -> None:
        if self.sup is not None:
            self.sup.send("STOP")

    def estop(self) -> None:
        if self.sup is not None:
            self.sup.send("ESTOP")

    def close(self) -> None:
        if self.sup is not None:
            self.sup.shutdown()

    # ---------------- events → state ----------------
    def poll(self) -> None:
        if self.sup is None:
            return
        while True:
            try:
                e = self.sup.evt_q.get_nowait()
            except queue.Empty:
                break
            t = e.get("type")
            if t == "TICK":
                ph = e.get("phase")
                if ph != self.phase:
                    self._log(f"phase {self.phase or '-'} → {ph}")
                self.phase = ph
                self.status = e.get("status") or {}
            elif t == "STATE_CHANGE":
                self._log(f"{e.get('old')} → {e.get('state')} ({e.get('reason')})")
            elif t in ("CRASH", "WARN", "REJECT", "ESTOP"):
                detail = e.get("error") or e.get("msg") or e.get("reason") or ""
                self._log(f"{t} {detail}")
        self.state = self.sup.state
        self.no_escape = bool(getattr(self.sup.mode, "in_no_escape", False))

    def view(self) -> dict[str, Any]:
        s = self.state
        if self.error:
            banner = self.error
        elif self.no_escape:
            banner = "TRONG ABYSS — timer 20' vẫn chạy, không có lối thoát"
        elif self.status.get("blocked"):
            banner = "MÙ: " + str(self.status["blocked"])
        else:
            banner = ""
        elapsed = int(time.time() - self.started) if self.started and s != "IDLE" else 0
        st = self.status
        return {
            "state": s,
            "phase": self.phase or "-",
            "banner": banner,
            "danger": bool(self.error) or self.no_escape,
            "runs": st.get("runs", 0),
            "room": st.get("room", 0),
            "hp": st.get("hp"),
            "filaments": st.get("filaments"),
            "elapsed": f"{elapsed // 3600}:{elapsed // 60 % 60:02d}:{elapsed % 60:02d}",
            "can_start": s in ("IDLE", "PAUSED"),
            "can_pause": s in ("RUNNING", "PAUSED"),
            "can_stop": s in ("RUNNING", "PAUSED"),
            "can_estop": s != "IDLE",
            "pause_label": "RESUME" if s == "PAUSED" else "PAUSE",
            "log": list(self.log),
        }
