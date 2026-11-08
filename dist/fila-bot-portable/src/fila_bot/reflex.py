"""Reflex loop v1 — "thuyền trưởng": FSM phase theo world model abyss thật.

Key changes v1 (so v0):
- FSM phase: DOCKED → TRAVEL_ENTRY → FILA_SPOOL → ROOM{n}_FIGHT → ROOM{n}_CLEARED
  → GATE_TRANSIT → ... → EXIT → LOOT → WARP_HOME → DOCKED
- Trong abyss: hp thấp → SURVIVAL MODE (không WARP_OUT — warp out là tự sát trong abyss)
- Ngoài abyss: hp thấp/ABORT → warp_home
- Timer 20 phút: warn FC khi còn warn_timer_left giây
- Lệnh mới: KEEP_RANGE, STOP, GATE, CONFIRM, LOOT
"""
from __future__ import annotations

import time
from typing import Any

from .bus import FileBus
from .commands import NO_ARG_CMDS, CommandError, validate
from .config import Config

IN_ABYSS = frozenset({
    "FILA_SPOOL", "ROOM1_FIGHT", "ROOM1_CLEARED", "GATE_TRANSIT",
    "ROOM2_FIGHT", "ROOM2_CLEARED", "ROOM3_FIGHT", "ROOM3_CLEARED",
    "EXIT", "LOOT", "SURVIVAL",
})


class SimExecutor:
    """Game-adapter giả: trạng thái giả + ghi hành động đã "làm" (test không cần EVE)."""

    def __init__(self) -> None:
        self.phase = "DOCKED"
        self.room = 0
        self.hp = 1.0
        self.cap = 0.9
        self.shield = 1.0
        self.armor = 1.0
        self.hull = 1.0
        self.dist_gate = 0
        self.targets = 0
        self.ammo = 1.0
        self.weather: str | None = None
        self.filaments = 2          # kho filament giả
        self.actions: list[tuple] = []

    def snapshot(self) -> dict[str, Any]:
        return {
            "phase": self.phase, "room": self.room,
            "hp": round(self.hp, 3), "cap": round(self.cap, 3),
            "shield": round(self.shield, 3), "armor": round(self.armor, 3),
            "hull": round(self.hull, 3), "dist_gate": self.dist_gate,
            "targets": self.targets, "ammo": round(self.ammo, 3),
            "weather": self.weather,
        }


class Bot:
    def __init__(self, bus: FileBus, config: Config, executor: SimExecutor | None = None) -> None:
        self.bus = bus
        self.cfg = config
        self.ex = executor or SimExecutor()
        self.unknown_since: float | None = None
        self.mayday_sent = False
        self.timer_warned = False
        self.fila_started: float | None = None   # t0 spool-up 15s
        self.abby_started: float | None = None   # t0 20-minute abyss timer
        self._ticks = 0
        self._last_emitted: str | None = None
        self._prev_phase: str | None = None   # phase trước khi rơi vào UNKNOWN (để biết trong/ngoài abyss)
        self._last_guard_action: str | None = None
        from .guards import GuardManager      # local import tránh vòng
        self.guards = GuardManager()

    def _apply_guard_action(self, act: dict) -> None:
        """Guard nêu action → thực hiện hành động an toàn tương ứng + emit event."""
        action = act.get("action")
        reason = act.get("reason", "")
        guard = act.get("guard", "?")
        if action == "survival":
            if self.ex.phase in IN_ABYSS and self.ex.phase != "SURVIVAL":
                self.ex.phase = "SURVIVAL"
            self.bus.emit("GUARD", guard=guard, action=action, reason=reason)
        elif action == "mayday":
            self.bus.emit("MAYDAY", reason=f"[{guard}] {reason}")
        elif action == "stop":
            self.ex.actions.append(("stop",))
            self.bus.emit("GUARD", guard=guard, action=action, reason=reason)
        elif action in ("disable_mwd", "power_save"):
            # sim: ghi hành động; adapter thật tắt module prop/web
            self.ex.actions.append((action, tuple(act.get("disable", ())))
                                   if action == "power_save" else (action,))
            self.bus.emit("GUARD", guard=guard, action=action, reason=reason)
        elif action in ("next_target", "skip_loot", "orbit_cache"):
            self.ex.actions.append((action,))
            self.bus.emit("GUARD", guard=guard, action=action, reason=reason)
        else:
            self.bus.emit("GUARD", guard=guard, action=str(action), reason=reason)

    # ------------- command handling -------------
    def handle_cmd(self, entry: dict[str, Any]) -> None:
        cid = entry.get("id")
        cmd = entry.get("cmd")
        arg = entry.get("arg")
        if "corrupt" in entry:
            return  # bus đã emit REJECT cho dòng hỏng
        try:
            norm = validate(cmd, arg) if (cmd not in NO_ARG_CMDS or arg not in (None, "", {})) else None
        except CommandError as e:
            self.bus.emit("REJECT", cmd=cmd, id=cid, reason=str(e))
            return
        handler = getattr(self, f"_do_{str(cmd).lower()}", None)
        if handler is None:
            self.bus.emit("REJECT", cmd=cmd, id=cid, reason=f"'{cmd}' chưa implement ở adapter")
            return
        try:
            detail = handler(norm)
        except Exception as e:  # noqa: BLE001 — adapter lỗi không được kill loop
            self.bus.emit("REJECT", cmd=cmd, id=cid, reason=f"adapter error: {e}")
            return
        self.bus.emit("OK", cmd=cmd, id=cid, detail=detail)

    # ------------- commands -------------
    def _do_set(self, norm: tuple[str, float]) -> dict:
        param, value = norm
        self.cfg.set_param(param, value)
        return {"param": param, "value": value}

    def _do_set_phase(self, norm: Any) -> dict:
        # FC thấy quái sạch (từ telemetry) → báo bot chuyển CLEARED để GATE mở
        old = self.ex.phase
        if old not in ("ROOM1_FIGHT", "ROOM2_FIGHT", "ROOM3_FIGHT"):
            raise CommandError(f"SET_PHASE chỉ hợp lệ từ *_FIGHT, đang là {old}")
        if norm not in ("ROOM1_CLEARED", "ROOM2_CLEARED", "ROOM3_CLEARED"):
            raise CommandError(f"SET_PHASE chỉ nhận *_CLEARED, nhận '{norm}'")
        self.ex.phase = norm
        self.bus.emit("ROOM_CLEARED", room=self.ex.room, gate_open=True)
        return {"phase": norm}

    def _do_target(self, norm: Any) -> dict:
        self.ex.actions.append(("target", norm))
        if norm == "nearest":
            self.ex.targets = max(1, self.ex.targets)
        return {"mode": norm}

    def _do_approach(self, norm: Any) -> dict:
        self.ex.actions.append(("approach", norm))
        return {"approach": norm}

    def _do_orbit(self, norm: Any) -> dict:
        self.ex.actions.append(("orbit", norm))
        return {"orbit": norm}

    def _do_keep_range(self, norm: Any) -> dict:
        self.ex.actions.append(("keep_range", norm))
        return {"range": norm}

    def _do_activate(self, norm: Any) -> dict:
        self.ex.actions.append(("activate", norm))
        return {"slot": norm}

    def _do_deactivate(self, norm: Any) -> dict:
        self.ex.actions.append(("deact", norm))
        return {"slot": norm}

    def _do_reload(self, _norm: Any) -> dict:
        self.ex.actions.append(("reload",))
        self.ex.ammo = 1.0
        return {"ammo": self.ex.ammo}

    def _do_stop(self, _norm: Any) -> dict:
        self.ex.actions.append(("stop",))
        return {"stopped": True}

    def _do_speed(self, norm: Any) -> dict:
        self.ex.actions.append(("speed", norm))
        return {"speed": norm}

    def _do_gate(self, _norm: Any) -> dict:
        if self.ex.phase not in ("ROOM1_CLEARED", "ROOM2_CLEARED"):
            raise CommandError("GATE chỉ hợp lệ khi room CLEARED (gate chưa mở)")
        # DEATH #3 guard: drone còn ngoài = jump là mất drone (AbyssBot v1.019 bug)
        drones_out = getattr(self.ex, "drones_in_space", 0)
        if drones_out > 0:
            raise CommandError(f"còn {drones_out} drone ngoài — GATE bị chặn, recall trước (Shift+R)")
        self.ex.actions.append(("gate",))
        nxt = min(self.ex.room + 1, 3)
        self.ex.room = nxt
        self.ex.phase = f"ROOM{nxt}_FIGHT"
        self.ex.targets = 3
        self.ex.dist_gate = 50000
        return {"room": nxt, "phase": self.ex.phase}

    def _do_dock(self, _norm: Any) -> dict:
        self.ex.actions.append(("dock",))
        self.ex.phase = "DOCKED"
        return {"phase": self.ex.phase}

    def _do_undock(self, _norm: Any) -> dict:
        self.ex.actions.append(("undock",))
        self.ex.phase = "TRAVEL_ENTRY"
        return {"phase": self.ex.phase}

    def _do_jump(self, norm: Any) -> dict:
        self.ex.actions.append(("jump", norm))
        return {"dest": norm}

    def _do_fila(self, norm: Any) -> dict:
        if self.ex.filaments <= 0:
            self.bus.emit("FILA_MISSING", reason="kho hết filament, không retry")
            raise CommandError("hết filament trong kho")
        if "FILA_SPOOL" in (self.ex.phase,) or self.ex.phase in IN_ABYSS:
            raise CommandError(f"đang trong abyss/spool — không kích hoạt thêm")
        self.ex.filaments -= 1
        self.ex.actions.append(("fila", norm))
        self.ex.phase = "FILA_SPOOL"
        self.fila_started = time.time()
        if isinstance(norm, str):
            for w in ("dark", "electrical", "exotic", "firestorm", "gamma"):
                if w in norm.lower():
                    self.ex.weather = w.capitalize()
                    break
        return {"filament": norm, "weather": self.ex.weather}

    def _do_confirm(self, _norm: Any) -> dict:
        # trong sim: confirm luôn chấp nhận; adapter thật check dialog tồn tại
        self.ex.actions.append(("confirm",))
        self.ex.phase = "ROOM1_FIGHT"
        self.ex.room = 1
        self.ex.targets = 3
        self.ex.dist_gate = 55000
        self.abby_started = time.time()
        self.timer_warned = False
        return {"phase": self.ex.phase}

    def _do_loot(self, _norm: Any) -> dict:
        self.ex.actions.append(("loot",))
        return {"looted": True}

    def _do_hold(self, _norm: Any) -> dict:
        self.ex.actions.append(("hold",))
        return {"held": True}

    def _do_abort(self, _norm: Any) -> dict:
        return self.safe_exit(reason="ABORT từ FC")

    def _do_status(self, _norm: Any) -> dict:
        self._emit_state(force=True)
        return {"sent": True}

    # ------------- safety core -------------
    def safe_exit(self, reason: str) -> dict:
        self.ex.actions.append(("safe_exit",))
        in_abyss = self.ex.phase in IN_ABYSS or (self.ex.phase == "UNKNOWN" and self._prev_phase in IN_ABYSS)
        if in_abyss:
            mode = "survival"
            self.ex.phase = "SURVIVAL"
        else:
            mode = "warp_home"
            self.ex.phase = "WARP_HOME"
        self.bus.emit("SAFE_EXIT", mode=mode, reason=reason, phase=self.ex.phase)
        return {"reason": reason, "mode": mode, "phase": self.ex.phase}

    # ------------- main loop -------------
    def tick(self) -> None:
        self._ticks += 1
        # ghi lại phase thật gần nhất (không tính UNKNOWN) để safe_exit biết trong/ngoài abyss
        if self.ex.phase != "UNKNOWN" and self.ex.phase != self._prev_phase:
            self._prev_phase = self.ex.phase
        for entry in self.bus.poll():
            self.handle_cmd(entry)

        # 0) DEATH GUARDS — học từ xác tàu người khác (guards.py); chạy TRƯỚC mọi quyết định
        guard_state = self.ex.snapshot()
        guard_state["last_action"] = self._last_guard_action
        guard_state["overview_count"] = getattr(self.ex, "overview_count", 0)
        guard_state["speed_mps"] = getattr(self.ex, "speed_mps", 0)
        guard_state["mwd_on"] = getattr(self.ex, "mwd_on", False)
        guard_state["tank_on"] = getattr(self.ex, "tank_on", True)
        guard_state["maneuver"] = getattr(self.ex, "maneuver", None)
        guard_state["want_loot"] = getattr(self.ex, "want_loot", False)
        guard_state["last_lock_failed"] = getattr(self.ex, "last_lock_failed", False)
        for act in self.guards.check_all(guard_state):
            self._apply_guard_action(act)
        self._last_guard_action = self.ex.phase

        # 1) hp thấp → trong abyss = SURVIVAL; ngoài = warp_home
        if self.ex.hp < self.cfg.escape_hp and self.ex.phase not in ("DOCKED", "WARP_HOME", "SURVIVAL"):
            mode = "survival" if self.ex.phase in IN_ABYSS else "warp_home"
            if mode == "survival":
                self.ex.phase = "SURVIVAL"
                self.bus.emit("SAFE_EXIT", mode="survival",
                              reason=f"hp {self.ex.hp:.2f} < {self.cfg.escape_hp:.2f} → SURVIVAL (abyss không warp được)")
            else:
                self.safe_exit(reason=f"hp {self.ex.hp:.2f} < escape_hp")

        # 2) FILA_SPOOL → tự chuyển ROOM1_FIGHT sau 15s (sim: rút ngắn bằng tick)
        if self.ex.phase == "FILA_SPOOL" and self.fila_started is not None:
            elapsed = time.time() - self.fila_started
            if elapsed >= 15.0:
                self._do_confirm(None)   # tự confirm khi dialog xuất hiện
                self.bus.emit("OK", cmd="AUTO_CONFIRM", detail={"after_s": round(elapsed, 1)})

        # 3) 20-minute timer: warn 1 lần
        if self.abby_started is not None and not self.timer_warned:
            left = 1200 - (time.time() - self.abby_started)
            if left <= self.cfg.warn_timer_left:
                self.bus.emit("TIMER_WARN", timer_left_s=int(max(left, 0)),
                              phase=self.ex.phase)
                self.timer_warned = True

        # 4) UNKNOWN quá lâu → MAYDAY + safe_exit
        if self.ex.phase == "UNKNOWN":
            if self.unknown_since is None:
                self.unknown_since = time.time()
            elapsed = time.time() - self.unknown_since
            if elapsed >= self.cfg.unknown_timeout and not self.mayday_sent:
                self.bus.emit("MAYDAY", reason=f"UNKNOWN {elapsed:.0f}s >= {self.cfg.unknown_timeout:.0f}s")
                self.mayday_sent = True
            if elapsed >= self.cfg.unknown_timeout:
                self.safe_exit(reason="unknown_timeout")
        else:
            if self._prev_phase != self.ex.phase:
                self._prev_phase = self.ex.phase
            self.unknown_since = None
            self.mayday_sent = False

        # 5) STATE định kỳ / khi đổi phase
        self._emit_state(force=False)

    def run(self, max_ticks: int = 1000, stop_fn=None, tick_sleep: float | None = None) -> int:
        """tick_sleep=None → dùng cfg.tick_interval (test truyền nhỏ cho nhanh)."""
        for _ in range(max_ticks):
            self.tick()
            if stop_fn and stop_fn():
                break
            time.sleep(tick_sleep if tick_sleep is not None else self.cfg.tick_interval)
        return self._ticks

    def _emit_state(self, force: bool) -> None:
        p = self.ex.phase
        periodic = self._ticks % 60 == 0
        if p != self._last_emitted or periodic or force:
            self.bus.emit("STATE", **self.ex.snapshot())
            self._last_emitted = p
