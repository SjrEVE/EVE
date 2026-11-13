"""UiModel — logic cửa sổ điều khiển, tách khỏi tkinter để test không cần màn hình.

UI chỉ gọi start/pause/stop/estop + poll()/view(). Bot chạy trong Supervisor thread.
"""
from __future__ import annotations

import queue
import time
from collections import deque
from pathlib import Path
from typing import Any, Callable

from .runlog import read_stats

MODES = ("abyss", "distribution", "security")
MODE_LABELS = {"abyss": "Abyss", "distribution": "Distribution (courier)",
               "security": "Security mission"}


class ModeUnavailable(Exception):
    """Mode chưa làm xong — báo thẳng, không chạy giả."""


def build_supervisor(mode: str, sim: bool = True, dry: bool = True, dll: str | None = None,
                     max_hours: float | None = 4.0, bus_dir: str | Path | None = None,
                     runs_dir: str | Path | None = None, *,
                     filament: str | None = None, max_runs: int | None = None,
                     max_missions: int | None = None, engine: str = "fsm",
                     allow_unknown_sec: bool = False, profile: Any = None,
                     fit_type: str = "default", resist_hole: str | None = None) -> Any:
    """Tao Supervisor cho 1 mode. Tham so duoc truyen xuong mode (khong hard-code).

    filament/max_runs  -> AbyssMode (truoc day CLI in ra filament nhung mode dung default)
    max_missions       -> DistributionMode
    allow_unknown_sec  -> chap nhan route chua ro sec (mac dinh False = fail-closed)
    engine             -> "fsm" (mac dinh) hoac "bt" (Behavior Tree)
    """
    from . import input as inp
    from .bus import FileBus
    from .config import Config
    from .modes.abyss import AbyssMode, DemoSim
    from .reflex import Bot
    from .runlog import RunLog
    from .runner import Supervisor

    if mode not in MODES:
        raise ModeUnavailable(f"mode lạ: {mode}")
    if mode == "security" and profile is not None:
        from .mission_profile import load_profile, profile_errors
        try:
            profile = load_profile(profile)
        except (ValueError, OSError) as exc:
            raise ModeUnavailable(f"Mission profile: {exc}") from exc
        if not sim and not dry:
            errors = profile_errors(profile)
            if errors:
                raise ModeUnavailable("Mission profile: " + "; ".join(errors))
    if mode == "security" and not sim and not dry and profile is None:
        raise ModeUnavailable("Security LIVE requires a configured mission profile before input")
    mission_session = None
    if mode == "security" and profile is not None:
        from .mission_session import MissionSession
        try:
            if all(profile.get(k) for k in ("character", "agent_id", "home_station")):
                mission_session = MissionSession(profile["character"],
                                                 profile["agent_id"],
                                                 profile["home_station"],
                                                 path=profile.get("session_file"))
        except (ValueError, TypeError) as exc:
            if profile.get("session_file"):
                raise ModeUnavailable(f"Mission session: {exc}") from exc
            mission_session = None
    rel = lambda: inp.release_all(dry_run=sim or dry)  # noqa: E731
    max_s = max_hours * 3600 if max_hours else None
    runlog = RunLog(runs_dir or Path(__file__).resolve().parents[2] / "runs")
    if mode != "abyss":
        if mode == "distribution":
            from .modes.distribution import DistributionMode
            if sim:
                from .sim_worlds import DistSim
                w = DistSim()
                refresh = w.world
                execute_fn = w.apply
            else:
                from .eye import Eye
                from .modes.live_distribution import LiveDistributionRunner
                runner = LiveDistributionRunner(Eye(dll_path=dll), dry=dry,
                                                allow_unknown_sec=allow_unknown_sec)
                refresh = runner.refresh
                execute_fn = runner.apply
            mode_obj: Any = DistributionMode(max_missions=max_missions)
            return Supervisor(mode_obj, execute=execute_fn, refresh=refresh, release_all=rel,
                              kill_switch=inp.kill_switch_pressed, max_session_s=max_s,
                              runlog=runlog)
        else:
            from .modes.security import SecurityMode
            if sim:
                # E2E sim: cung hop dong refresh -> tick -> apply nhu live,
                # di toi terminal state that (IDLE_DONE) de soi deadlock/stall.
                from .sim_worlds import SecurityE2ESim
                w = SecurityE2ESim()
                refresh = w.world
                execute_fn = w.apply
                runner_obj = w
            else:
                from .eye import Eye
                from .modes.live_security import LiveSecurityRunner
                runner_obj = LiveSecurityRunner(Eye(dll_path=dll), dry=dry, profile=profile)
                # Courier mission delegate qua Distribution (đã ground load/giao/trả).
                # DÙNG CHUNG EYE — DLL reader là singleton state, 2 instance riêng
                # sẽ initialize lẫn nhau (probe 11-11: process thứ 2 crash).
                from .modes.live_distribution import LiveDistributionRunner
                runner_obj.dist_runner = LiveDistributionRunner(runner_obj.eye, dry=dry)
                refresh = runner_obj.refresh
                execute_fn = runner_obj.apply
            mode_obj = SecurityMode(runner=runner_obj, max_missions=max_missions, is_sim=sim,
                                    clock=w.clock if sim else time.monotonic,
                                    session=mission_session)
            return Supervisor(mode_obj, execute=execute_fn, refresh=refresh, release_all=rel,
                              kill_switch=inp.kill_switch_pressed, max_session_s=max_s,
                              runlog=runlog)
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
    mode_obj = AbyssMode(Bot(bus, Config(), ex, fit_type=fit_type,
                             resist_hole=resist_hole),
                         filament=filament or "Tranquil Exotic Filament",
                         max_runs=max_runs, engine=engine)
    return Supervisor(mode_obj, execute=execute, refresh=refresh,
                      release_all=lambda: inp.release_all(dry_run=sim or dry),
                      kill_switch=inp.kill_switch_pressed,
                      max_session_s=max_hours * 3600 if max_hours else None,
                      runlog=runlog)


class UiModel:
    def __init__(self, factory: Callable = build_supervisor, threaded: bool = True,
                 tick: float = 0.3, log_max: int = 200,
                 runs_dir: str | Path | None = None) -> None:
        self.factory = factory
        self.threaded = threaded
        self.tick = tick
        self.runs_dir = runs_dir or Path(__file__).resolve().parents[2] / "runs"
        self.mode = "abyss"
        self.sim = True
        self.dry = True
        self.max_hours: float | None = 4.0
        self.filament = "Tranquil Exotic Filament"
        self.max_missions: int | None = None
        self.max_runs: int | None = None
        self.engine = "fsm"
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
        if not self.sim:
            self.error = ("GUI live reader/input is disabled until this path uses the per-client "
                          "ownership gate. Use the fila_bot.cli entrypoint for live access.")
            self.state = "IDLE"
            self._log("FATAL: " + self.error)
            return
        try:
            self.sup = self.factory(self.mode, sim=self.sim, dry=self.dry,
                                    max_hours=self.max_hours, filament=self.filament,
                                    max_missions=self.max_missions, max_runs=self.max_runs,
                                    engine=self.engine)
        except TypeError as e:
            if "unexpected keyword" not in str(e):
                self.sup = None
                self.state = "IDLE"
                self.error = f"FATAL: {e}"
                self._log(self.error)
                return
            # factory cu / test double chi nhan tham so co ban
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
        self._last_act: tuple[str, float] | None = None
        self._log(f"START {self.mode} | SIM={self.sim} | DRY={self.dry}")
        if self.sim:
            self._log("[CHẾ ĐỘ] GIẢ LẬP (SIM): Bot chạy mô phỏng, KHÔNG kết nối EVE client.")
        elif self.dry:
            self._log("[CHẾ ĐỘ] AN TOÀN (DRY-RUN): Bot đọc game thật nhưng KHÔNG bấm chuột. Bỏ tích 'DRY' để bot tự bấm.")
        else:
            self._log("[CHẾ ĐỘ] LIVE THỰC THI: Bot sẽ tự động bấm chuột & phím thật vào EVE client!")

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
                    self._log(f"Phase: {self.phase or '-'} → {ph}")
                self.phase = ph
                self.status = e.get("status") or {}
                acts = e.get("acts") or []
                prefix = "[DRY]" if self.dry else "[LIVE]"
                for a in acts:
                    if isinstance(a, dict):
                        why = a.get("why") or a.get("do")
                        xy = a.get("at")
                        xy_str = f" tại {xy}" if xy else ""
                        msg = f"{prefix} {why}{xy_str}"
                    elif isinstance(a, tuple):
                        msg = f"{prefix} {a[0]} {' '.join(str(x) for x in a[1:])}".strip()
                    else:
                        msg = f"{prefix} {a}"
                    last_msg, last_t = getattr(self, "_last_act", ("", 0.0)) or ("", 0.0)
                    if msg != last_msg or time.time() - last_t > 4.0:
                        self._log(msg)
                        self._last_act = (msg, time.time())
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
            "detail": st.get("detail", ""),
            "banner": banner,
            "danger": bool(self.error) or self.no_escape,
            "stats": read_stats(self.runs_dir),
            "runs": st.get("runs", 0),
            "declined": st.get("declined", 0),
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
