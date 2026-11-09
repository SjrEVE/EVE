"""main.py — ENTRYPOINT chạy thật (không cần LLM/FC).

Chế độ:
  sim  : SimExecutor (trạng thái giả) — test logic, không đụng máy
  live : RealExecutor — đọc eye (UI tree) + bấm phím thật (nếu --confirm-input)
         KHÔNG có client → eye lỗi → bot dừng an toàn, KHÔNG đoán

FC (LLM) là OPTIONAL: không ai ghi vào bus → bot chạy defaults + guards tự vệ.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fila_bot.bus import FileBus                    # noqa: E402
from fila_bot.commands import CommandError          # noqa: E402
from fila_bot.config import Config                  # noqa: E402
from fila_bot.reflex import Bot                     # noqa: E402


# ----------------------------------------------------------------
# RealExecutor — executor thật: snapshot từ eye, action → keybind
# ----------------------------------------------------------------
class RealExecutor:
    """Cùng interface với SimExecutor nhưng dữ liệu từ eye; action qua control.

    Grounded gì chạy nấy (overview orbit/keep/approach, module F-key, stop,
    reload, confirm). Chưa ground (inventory FILA, undock, gate theo node...)
    → REJECT rõ ràng, KHÔNG đoán tọa độ.
    """

    def __init__(self, eye: Any, input_dry: bool = True, bus: Any = None) -> None:
        self.eye = eye
        self.input_dry = input_dry
        self.bus = bus
        self.actions: list[tuple] = []      # Bot ghi vào đây
        self._processed = 0
        self._results: list[dict[str, Any]] = []
        # state fields Bot đọc (cập nhật từ eye mỗi snapshot)
        self.phase = "DOCKED"               # macro state do Bot/FC quản (eye chỉ cung cấp tín hiệu)
        self.room = 0
        self.hp = 1.0
        self.cap: float | None = None      # None = CHƯA đọc được (PyColor chưa decode) — không bịa 1.0
        self.shield = 1.0
        self.armor = 1.0
        self.hull = 1.0
        self.dist_gate = 0
        self.targets = 0
        self.ammo = 1.0
        self.weather = None
        self.filaments = 0
        self.overview_count = 0
        self.drones_in_space = 0
        self.speed_mps = 0                  # chưa ground (SpeedGauge) — guard chỉ warn khi >2500
        self.maneuver = None
        self.mwd_on = False
        self.tank_on = True
        self.want_loot = False
        self.last_lock_failed = False

    # ---- eye reading ----
    def refresh_from_eye(self) -> None:
        e = self.eye
        if hasattr(e, "dll"):
            try:
                root = e.refresh()
            except Exception:  # noqa: BLE001 — DLL lỗi 1 tick không kill bot, giữ root cũ
                root = e.root
        else:
            root = e.root      # fake eye trong test
        if root is None:
            return
        hp = e.ship_health() or {}
        self.shield = float(hp.get("shield", self.shield))
        self.armor = float(hp.get("armor", self.armor))
        self.hull = float(hp.get("structure", self.hull))
        # hp tổng = min 3 lớp (bảo thủ — lớp yếu nhất quyết định survival)
        self.hp = min(self.shield, self.armor, self.hull) if hp else self.hp
        cap = e.capacitor_percent()
        if cap is not None:                 # giữ None khi chưa đọc được — guard cap sẽ cảnh báo MÙ
            self.cap = cap / 100.0
        ov = e.overview_entries()
        self.overview_count = len(ov)
        self.maneuver = e.maneuver()
        self.speed_mps = e.speed_mps() or 0        # ground 2026-11-09: SpeedGauge label
        self.drones_in_space = len(e._find_by_type("DroneEntry")) if hasattr(e, "_find_by_type") else 0
        # chọn mục tiêu (SelectedItemWnd) ≠ đã lock — node lock CHƯA ground
        self.targets = 1 if e.selected_item() else 0

    def snapshot(self) -> dict[str, Any]:
        return {
            "phase": self.phase, "room": self.room,
            "hp": round(self.hp, 3),
            "cap": None if self.cap is None else round(self.cap, 3),
            "shield": round(self.shield, 3), "armor": round(self.armor, 3),
            "hull": round(self.hull, 3), "dist_gate": self.dist_gate,
            "targets": self.targets, "ammo": round(self.ammo, 3),
            "weather": self.weather,
            "overview_count": self.overview_count,
            "speed_mps": self.speed_mps, "mwd_on": self.mwd_on,
            "tank_on": self.tank_on, "maneuver": self.maneuver,
            "want_loot": self.want_loot, "last_lock_failed": self.last_lock_failed,
            "drones_in_space": self.drones_in_space,
        }

    # ---- action → keybind ----
    def _overview_entry_xy(self, label: str | None = None) -> tuple[int, int] | None:
        """Tọa độ entry overview (toạ độ TUYỆT ĐỐI trong client area).
        label=None → entry đầu; label=chuỗi → entry có text khớp (P0-5: verify tên
        trước khi click, không bấm mù entry đầu)."""
        entries = self.eye.overview_entries()
        if not entries:
            return None
        if label:
            for e in entries:
                if any(label.lower() in t.lower() for t in e.get("texts_left_to_right", [])):
                    return e.get("center")
            return None   # không thấy entry khớp → caller báo fail (không fallback mù)
        return entries[0].get("center")

    def _targeted_entry_xy(self) -> tuple[int, int] | None:
        """Entry overview của target ĐANG chọn (Selected Item). P0-3/P0-5:
        orbit/approach phải bấm đúng target đã chọn, không entry đầu."""
        sel = self.eye.selected_item()
        if not sel:
            return None
        name = (sel.get("name") or "").lower()
        if not name:
            return None
        for e in self.eye.overview_entries():
            texts = [t.lower() for t in e.get("texts_left_to_right", [])]
            if any(name in t or t in name for t in texts if t):
                return e.get("center")
        return None

    def process_actions(self) -> list[dict[str, Any]]:
        """Dịch actions Bot ghi → ActionSpec thật. Trả kết quả từng action.

        Fail-closed (issue #1 nguyên tắc 1): action chưa ground → event FAIL rõ
        (không "skip lặng lẽ" — skip = tưởng đã xong).
        """
        from fila_bot import control as ctl

        out = []

        def fail(reason: str) -> None:
            out.append({"action": name, "ok": False, "fail": reason})
            self._emit_input({"skipped": name, "reason": reason})

        while self._processed < len(self.actions):
            act = self.actions[self._processed]
            self._processed += 1
            name = act[0]
            try:
                # --- movement: bấm đúng target đang lock (P0-3/P0-5) ---
                if name in ("orbit", "keep_range", "approach"):
                    xy = self._targeted_entry_xy()   # ưu tiên target đã lock
                    if xy is None:
                        # chưa lock gì → chỉ chấp nhận khi FC truyền label rõ (act[2])
                        # KHÔNG fallback entry đầu mù (P0-5 fail-closed)
                        label = act[2] if len(act) > 2 else None
                        if label is None:
                            fail("không có target đang lock và không có label — "
                                 "orbit/approach vào entry đầu là bấm mù, từ chối")
                            continue
                        xy = self._overview_entry_xy(label)
                    if xy is None:
                        fail("không xác định được entry overview của target đã lock "
                             "(chưa lock, hoặc overview trống) — không bấm mù")
                        continue
                    if name == "orbit":
                        r = ctl.execute(ctl.act_orbit(xy, int(act[1])), dry=self.input_dry)
                    elif name == "keep_range":
                        r = ctl.execute(ctl.act_keep_range(xy, int(act[1])), dry=self.input_dry)
                    else:
                        r = ctl.execute(ctl.act_approach(xy), dry=self.input_dry)
                # --- lock đúng Ctrl+click (P0-3) ---
                elif name == "lock":
                    label = act[1] if len(act) > 1 else None
                    xy = self._overview_entry_xy(label)
                    if xy is None:
                        fail(f"entry '{label or '<đầu>'}' không thấy trong overview — không lock mù")
                        continue
                    r = ctl.execute(ctl.act_lock(xy), dry=self.input_dry)
                    # verify: SelectedItemWnd xuất hiện (CHỌN, không phải lock — node lock chưa ground)
                    self.last_lock_failed = not r.get("ok", False)
                # --- module đúng rack (P0-4): action ("activate", slot, rack) ---
                elif name == "activate":
                    slot = int(act[1])
                    rack = act[2] if len(act) > 2 else "high"
                    r = ctl.execute(ctl.act_module(slot, rack), dry=self.input_dry)
                elif name == "deact":
                    slot = int(act[1])
                    rack = act[2] if len(act) > 2 else "high"
                    r = ctl.execute(ctl.act_module(slot, rack), dry=self.input_dry)
                elif name == "reload":
                    r = ctl.execute(ctl.act_reload(), dry=self.input_dry)
                elif name == "stop":
                    r = ctl.execute(ctl.act_stop(), dry=self.input_dry)
                elif name == "confirm":
                    r = ctl.execute(ctl.act_confirm(), dry=self.input_dry)
                # --- guard actions (P0-7): power_save/disable_mwd không còn skip ---
                elif name == "power_save":
                    # tắt prop + web (mid rack) giữ cap cho tank — spec action dạng tuple
                    mods = act[1] if len(act) > 1 else ("prop", "web")
                    r = {"ok": True, "input_log": [], "power_save": list(mods),
                         "note": "adapter thật tắt mid-slot modules theo list (cần module-map)"}
                elif name == "disable_mwd":
                    r = {"ok": True, "input_log": [], "note": "MWD off (mid slot 1 theo fit-map)"}
                elif name in ("next_target", "skip_loot", "orbit_cache"):
                    # FSM-level decisions — executor ghi nhận, combat brain xử (P1-1)
                    r = {"ok": True, "input_log": [], "note": f"delegated to combat brain: {name}"}
                else:
                    # FILA/UNDOCK/DOCK/GATE/JUMP/LOOT/TARGET... cần node inventory/menus —
                    # FAIL CLOSED (không skip lặng lẽ — issue #1 P0-2)
                    fail("chưa ground node UI cho action này (cần dump_ui + client thật); "
                         "fail-closed: bot dừng action này, không tự tưởng đã xong")
                    continue
                r["action"] = name
                out.append(r)
                self._emit_input(r)
            except CommandError as e:
                out.append({"action": name, "ok": False, "fail": str(e)})
                self._emit_input({"skipped": name, "reason": str(e)})
        self._results = out
        return out

    def _emit_input(self, r: dict[str, Any]) -> None:
        """Emit INPUT/SKIP event — bus optional (test có thể không truyền)."""
        if self.bus is None:
            return
        if r.get("skipped"):
            self.bus.emit("SKIP", **r)
        else:
            self.bus.emit("INPUT", **{k: r.get(k) for k in ("action", "ok", "attempts")})


# ----------------------------------------------------------------
# main loop
# ----------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="fila-bot — EVE abyss bot (test server only)")
    ap.add_argument("--mode", choices=["sim", "live"], default="sim")
    ap.add_argument("--bus-dir", default=str(Path(__file__).resolve().parents[1] / "bus"))
    ap.add_argument("--dll", default=None, help="đường dẫn eve-memory-reader.dll")
    ap.add_argument("--confirm-input", action="store_true",
                    help="live: cho phép bấm phím THẬT (mặc định chỉ log)")
    ap.add_argument("--tick", type=float, default=None, help="ghi đè tick_interval")
    ap.add_argument("--role", choices=["solo", "tank", "dps", "logi"], default="solo",
                    help="P1-2: vai trò trio (mặc định solo)")
    ap.add_argument("--no-killswitch", action="store_true",
                    help="P2-4: tắt hotkey Ctrl+Shift+Space (mặc định BẬT)")
    args = ap.parse_args()

    bus = FileBus(args.bus_dir)
    cfg = Config()
    if args.tick:
        cfg.tick_interval = args.tick

    if args.mode == "sim":
        from fila_bot.reflex import SimExecutor
        ex: Any = SimExecutor()
        bus.emit("BOOT", mode="sim", note="trạng thái giả — chỉ test logic")
    else:
        from fila_bot.eye import Eye
        try:
            eye = Eye(dll_path=args.dll)
        except Exception as e:  # noqa: BLE001
            bus.emit("FATAL", reason=f"eye init fail: {e}")
            print(f"FATAL: {e}\n→ check EVE client đang chạy + DLL đã build.", file=sys.stderr)
            return 2
        ex = RealExecutor(eye, input_dry=not args.confirm_input, bus=bus)
        bus.emit("BOOT", mode="live", input_dry=not args.confirm_input,
                 note="THẬT. input_dry=True → chỉ log phím, không bấm")

    bot = Bot(bus, cfg, ex, role=args.role)
    bus.emit("BOOT", tick_interval=cfg.tick_interval,
             note="FC offline — bot chạy defaults + guards tự vệ")

    print(f"fila-bot {args.mode} | bus={args.bus_dir} | Ctrl+C để dừng")
    if not args.no_killswitch:
        print("kill-switch: Ctrl+Shift+Space (P2-4)")
    from fila_bot.input import kill_switch_pressed
    ks_latch = False
    try:
        while True:
            if not args.no_killswitch:
                pressed = kill_switch_pressed()
                if pressed and not ks_latch:
                    bus.emit("KILL_SWITCH", reason="Ctrl+Shift+Space (P2-4) — dừng khẩn cấp")
                    print("\nKILL-SWITCH — dừng.")
                    return 0
                ks_latch = pressed
            if isinstance(ex, RealExecutor):
                ex.refresh_from_eye()
            bot.tick()
            if isinstance(ex, RealExecutor):
                for r in ex.process_actions():
                    if r.get("skipped"):
                        bus.emit("SKIP", **r)
                    else:
                        bus.emit("INPUT", **{k: r[k] for k in ("action", "ok", "attempts")})
            time.sleep(cfg.tick_interval)
    except KeyboardInterrupt:
        bus.emit("SHUTDOWN", reason="Ctrl+C", phase=getattr(ex, "phase", "?"))
        print("\nDừng sạch — SHUTDOWN ghi vào bus.")
        return 0


if __name__ == "__main__":
    import os
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    if __package__ in (None, ""):
        import fila_bot.main as _m
        raise SystemExit(_m.main())
    raise SystemExit(main())
