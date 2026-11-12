"""Supervisor — chạy vòng tick của 1 Mode trong thread riêng, điều khiển bằng queue.

UI (tkinter) chỉ nói chuyện qua `send(cmd)` và đọc `evt_q` → UI treo không kéo bot
treo và ngược lại.

Trạng thái:
    IDLE --START--> RUNNING --PAUSE--> PAUSED --RESUME/START--> RUNNING
    RUNNING/PAUSED --STOP--> STOPPING --(mode.at_safe_point)--> IDLE
    bất kỳ --ESTOP / kill-switch--> IDLE (nhả phím ngay, không tick thêm)
    exception trong tick --> PAUSED + CRASH (nhả phím, không bấm tiếp)

Thứ tự mỗi step (glue contract): lệnh UI → kill-switch → refresh(eye) → mode.tick
→ execute(actions). Safety floor nằm trong mode/guards, UI không tắt được.
"""
from __future__ import annotations

import queue
import threading
import time
import traceback
from typing import Any, Callable

STATES = ("IDLE", "RUNNING", "PAUSED", "STOPPING")
COMMANDS = ("START", "PAUSE", "RESUME", "STOP", "ESTOP")


class Supervisor:
    def __init__(self, mode: Any, *,
                 execute: Callable[[list[Any]], Any] | None = None,
                 refresh: Callable[[], Any] | None = None,
                 release_all: Callable[[], Any] | None = None,
                 kill_switch: Callable[[], bool] | None = None,
                 max_session_s: float | None = None,
                 runlog: Any | None = None,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.mode = mode
        self.execute = execute or (lambda acts: [])
        self.refresh = refresh
        self.release_all = release_all or (lambda: None)
        self.kill_switch = kill_switch or (lambda: False)
        self.max_session_s = max_session_s
        self.runlog = runlog
        self.clock = clock
        self.cmd_q: queue.Queue = queue.Queue()
        self.evt_q: queue.Queue = queue.Queue()
        self.state = "IDLE"
        self.started_at: float | None = None
        self.ticks = 0
        self.last_error: str | None = None
        self.last_status: dict[str, Any] = {}
        self._thread: threading.Thread | None = None
        self._quit = threading.Event()
        self._cancelled = threading.Event()
        self._epoch = 0
        self._command_lock = threading.RLock()
        self._watcher: threading.Thread | None = None

    # ---------------- events ----------------
    def _emit(self, etype: str, **fields: Any) -> None:
        self.evt_q.put({"type": etype, "state": self.state, "t": time.time(), **fields})

    def _set(self, new: str, reason: str = "") -> None:
        if new != self.state:
            old = self.state
            self.state = new
            if self.runlog is not None:
                if new == "RUNNING" and old == "IDLE":
                    name = getattr(self.mode, "name", None) or type(self.mode).__name__
                    self.runlog.session_start(name)
                elif new == "IDLE":
                    self.runlog.session_end(reason or new, ticks=self.ticks,
                                            status=self.last_status)
            self._emit("STATE_CHANGE", old=old, reason=reason)

    # ---------------- commands ----------------
    def send(self, cmd: str) -> None:
        with self._command_lock:
            if str(cmd).upper() in ("ESTOP", "PAUSE"):
                # These commands must not wait behind a native reader call.
                while not self.cmd_q.empty():
                    try:
                        self.cmd_q.get_nowait()
                    except queue.Empty:
                        break
                self._handle(cmd)
            else:
                self.cmd_q.put(cmd)

    def _handle(self, cmd: str) -> None:
        c = str(cmd).upper()
        if c == "START":
            self._cancelled.clear()
            self._epoch += 1
            if self.state == "IDLE":
                self.started_at = self.clock()
                self.ticks = 0
                if hasattr(self.mode, "stop_requested"):
                    self.mode.stop_requested = False
                self._set("RUNNING", "START")
            elif self.state == "PAUSED":
                self._set("RUNNING", "RESUME")
        elif c == "RESUME":
            if self.state == "PAUSED":
                self._cancelled.clear()
                self._epoch += 1
                self._set("RUNNING", "RESUME")
        elif c == "PAUSE":
            if self.state == "RUNNING":
                self._cancelled.set()
                self._epoch += 1
                self.release_all()
                self._set("PAUSED", "PAUSE")
                if getattr(self.mode, "in_no_escape", False):
                    self._emit("WARN", msg="đang trong abyss — timer 20 phút VẪN chạy khi PAUSE")
        elif c == "STOP":
            if self.state in ("RUNNING", "PAUSED"):
                self.mode.request_safe_stop()
                self._set("STOPPING", "STOP an toàn")
                if getattr(self.mode, "in_no_escape", False):
                    self._emit("WARN", msg="trong abyss không thoát được — chạy nốt run rồi dừng")
        elif c == "ESTOP":
            self._estop("E-STOP")
        else:
            self._emit("REJECT", cmd=cmd, reason="lệnh không hợp lệ")

    def _estop(self, reason: str) -> None:
        self._cancelled.set()
        self._epoch += 1
        self.release_all()
        self._set("IDLE", reason)
        self._emit("ESTOP", reason=reason)

    # ---------------- one step ----------------
    def step(self) -> None:
        with self._command_lock:
            while True:
                try:
                    cmd = self.cmd_q.get_nowait()
                except queue.Empty:
                    break
                self._handle(cmd)

        if self.state != "IDLE":
            try:
                ks = bool(self.kill_switch())
            except Exception:  # noqa: BLE001 — đọc phím lỗi không được giết bot
                ks = False
            if ks:
                self._estop("kill-switch Ctrl+Shift+Space")
                return

        if self.state not in ("RUNNING", "STOPPING"):
            return

        if (self.state == "RUNNING" and self.max_session_s is not None
                and self.started_at is not None
                and self.clock() - self.started_at >= self.max_session_s):
            self.mode.request_safe_stop()
            self._set("STOPPING", "hết max_session")

        if self.state == "STOPPING" and getattr(self.mode, "at_safe_point", False):
            self._set("IDLE", "đã tới safe point")
            return

        try:
            epoch = self._epoch
            world = self.refresh() if self.refresh else None
            if self._cancelled.is_set() or self._quit.is_set() or epoch != self._epoch:
                return
            acts = self.mode.tick(world) or []
            if self._cancelled.is_set() or self._quit.is_set() or epoch != self._epoch:
                return
            results = self.execute(acts) if acts else []
            if results:
                hook = getattr(self.mode, "on_action_results", None)
                if callable(hook):
                    hook(results)
            self.ticks += 1
            status = self.mode.status() if hasattr(self.mode, "status") else {}
            self.last_status = status
            self._emit("TICK", ticks=self.ticks, phase=getattr(self.mode, "phase", None),
                       actions=len(acts), acts=acts, results=results, status=status)
        except Exception as e:  # noqa: BLE001
            self.release_all()
            self.last_error = repr(e)
            if self.runlog is not None:
                self.runlog.crash(repr(e))
            self._emit("CRASH", error=repr(e), trace=traceback.format_exc(limit=5))
            self._set("PAUSED", "crash")
            return

        if self.state == "STOPPING" and getattr(self.mode, "at_safe_point", False):
            self._set("IDLE", "đã tới safe point")

    # ---------------- thread ----------------
    def run(self, tick_interval: float = 0.3) -> None:
        while not self._quit.is_set():
            self.step()
            self._quit.wait(tick_interval)

    def _watch_safety(self) -> None:
        while not self._quit.wait(0.025):
            if self.state != "IDLE":
                try:
                    pressed = bool(self.kill_switch())
                except Exception:
                    pressed = False
                if pressed:
                    self.send("ESTOP")

    def start_thread(self, tick_interval: float = 0.3) -> threading.Thread:
        if self._thread and self._thread.is_alive():
            return self._thread
        self._quit.clear()
        self._watcher = threading.Thread(target=self._watch_safety, name="fila-safety", daemon=True)
        self._watcher.start()
        self._thread = threading.Thread(target=self.run, args=(tick_interval,),
                                        name="fila-supervisor", daemon=True)
        self._thread.start()
        return self._thread

    def shutdown(self, timeout: float = 2.0) -> None:
        """Đóng app: E-STOP rồi dừng thread."""
        self._estop("shutdown")
        self._quit.set()
        if self._thread:
            self._thread.join(timeout)
        if self._watcher and self._watcher is not threading.current_thread():
            self._watcher.join(min(timeout, 0.5))
