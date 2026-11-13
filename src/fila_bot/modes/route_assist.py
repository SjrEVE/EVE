"""RouteAssistRunner — autopilot HỖ TRỢ chạy trên client thật.

Người set destination trong game, bật bot lên; bot thay tay jump:
    route còn marker → tìm gate đúng tên hệ kế tiếp → warp-to-0 + jump (D+click)
    → chờ session change → chờ route panel CẬP NHẬT → lặp → (tuỳ chọn dock đích).

Fail-closed: mất client (watch _run_with_client_lock), mất quyền nhập (owner
đang dùng máy) → KHÔNG bấm, chờ/blocked. Không set route, không dock trạm khác.
"""
from __future__ import annotations

import time
from typing import Any

from ..autopilot import RouteAssist
from .. import control as ctl


class RouteAssistRunner:
    """Perception (Eye) + delivery (control) cho RouteAssist logic thuần."""

    def __init__(self, eye: Any, dry: bool = True, clock: Any = time.monotonic,
                 max_jumps: int | None = None, dock_at_end: bool = False) -> None:
        self.eye = eye
        self.dry = dry
        self.win: dict[str, Any] | None = None
        self.assist = RouteAssist(clock=clock, max_jumps=max_jumps,
                                  dock_at_end=dock_at_end)

    # ---------------- perception ----------------
    def read_world(self) -> dict[str, Any]:
        if hasattr(self.eye, "dll") and self.eye.dll is not None:
            self.eye.refresh()
        from ..world_snapshot import parse_world
        from ..mission import MissionEye
        snap = parse_world(self.eye)
        me = MissionEye(self.eye)
        gates = me.gate_entries() if not snap.docked else []
        # station entries cho dock_at_end — overview entries type Station
        stations = [e for e in (self.eye.overview_entries() or [])
                    if "station" in str(e.get("Type") or "").lower()] if not snap.docked else []
        return {
            "docked": snap.docked if snap.location_known else None,
            "location_known": snap.location_known,
            "system": snap.system,
            "connection_lost": snap.connection_lost,
            "undock_xy": (self.eye.station_window() or {}).get("undock", {}).get("center")
                         if snap.docked else None,
            "route": {"destination": snap.route.destination,
                      "next_system": snap.route.next_system,
                      "jumps": snap.route.jumps,
                      "markers": snap.route.markers},
            "gates": gates,
            "stations": stations,
        }

    # ---------------- delivery ----------------
    def apply(self, acts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not acts:
            return []
        if not self.dry:
            if self.win is None:
                from ..win import find_client_window
                self.win = find_client_window()
                if self.win:
                    from ..win import focus
                    focus(self.win)
            if self.win is not None:
                from ..win import is_foreground
                if not is_foreground(self.win):
                    return [{"act": a.get("do"), "ok": False, "status": "INPUT_NOT_OWNED",
                             "note": "EVE không foreground (owner đang dùng máy) — không bấm"}
                            for a in acts]
        out = []
        for a in acts:
            kind = a.get("do")
            r: dict[str, Any] = {"act": kind, "ok": False, "status": "NOT_SENT"}
            if kind == "jump":
                xy = a.get("at")
                if xy:
                    # Warp-to-0 + jump trong 1 hit: giữ D + click gate (đã ground)
                    res = ctl.execute(ctl.act_hotkey_dock_jump(xy), eye=self.eye,
                                      dry=self.dry, win=self.win)
                    r.update(res)
                    r["gate"] = a.get("name")
                else:
                    r["note"] = "jump không có toạ độ gate — không bấm mù"
            elif kind == "dock":
                xy = a.get("at")
                if xy:
                    res = ctl.execute(ctl.act_hotkey_dock_jump(xy), eye=self.eye,
                                      dry=self.dry, win=self.win)
                    r.update(res)
                    r["station"] = a.get("name")
                else:
                    r["note"] = "dock không có toạ độ — không bấm mù"
            elif kind == "undock":
                xy = a.get("at")
                if xy:
                    res = ctl.execute(ctl.act_undock_at(xy), eye=self.eye,
                                      dry=self.dry, win=self.win)
                    r.update(res)
                else:
                    r["note"] = "undock không có nút Undock — không bấm mù"
            elif kind in ("wait", "done", "blocked", "estop"):
                r["ok"] = kind not in ("blocked", "estop")
            out.append(r)
        return out
