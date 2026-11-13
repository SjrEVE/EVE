"""RouteAssist — autopilot HỖ TRỢ: bot thay tay jump theo route đã set.

Phân định ranh giới (Boss 14-11):
  - NGƯỜI tự set destination trong game. Bot KHÔNG set route, KHÔNG tự chọn hệ.
  - Bot làm đúng một việc: thấy route còn marker → tìm gate đúng tên hệ kế tiếp
    → D+click (warp-to-0 + jump, 1 hit đã ground) → chờ session change → lặp
    cho tới khi route rỗng (đã tới đích).
  - Fail-closed: route panel không đọc được, gate không khớp tên hệ kế tiếp,
    khong còn marker, mất client, mất quyền nhập → DỪNG với lý do, không bấm mù.

Nguy hiểm đã thiết kế chống:
  - Jump xong route panel CŨ còn treo (next_system = hệ vừa rời) → quay lại
    gate cũ nhảy ngược. Luật: sau mỗi jump phải chờ route panel CẬP NHẬT
    (next_system đổi hoặc số jump giảm) rồi mới tìm gate kế tiếp.
  - Spam D+click mỗi tick → re-click giữa warp. Một lệnh / pending, resend có
    bounded attempts.
"""
from __future__ import annotations

import time
from typing import Any, Callable

# warp tới gate ở xa (~100 AU) có thể vài phút; jump + render thêm ~15-30s
JUMP_TIMEOUT_S = 300.0
JUMP_RESEND_S = 120.0          # không thấy gì mới sau 2' → gửi lại 1 lần
JUMP_MAX_ATTEMPTS = 3
ROUTE_UPDATE_TIMEOUT_S = 60.0  # sau jump, chờ route panel cập nhật
UNKNOWN_GRACE_S = 45.0         # UI tree gãy lúc chuyển cảnh → chờ, quá mới block
BLOCKED_AFTER_NO_GATE_S = 60.0 # route nói next=X mà overview không có gate X


def _now() -> float:
    return time.monotonic()


class RouteAssist:
    """Logic thuần — world dict vào, action list ra. Test không cần EVE."""

    def __init__(self, clock: Callable[[], float] = _now,
                 max_jumps: int | None = None, dock_at_end: bool = False) -> None:
        self.clock = clock
        self.max_jumps = max_jumps
        self.dock_at_end = dock_at_end
        self.jumps_done = 0
        self.state = "IDLE"
        self.blocked: str | None = None
        # pending jump
        self._jump_sent_at: float | None = None
        self._jump_attempts = 0
        self._jump_gate: str | None = None
        # sau khi system đổi
        self._await_route_update = False
        self._route_update_since: float | None = None
        self._prev_next_system: str | None = None
        self._jumps_seen: int | None = None
        self._jumps_before: int | None = None
        self._last_system: str | None = None
        self._unknown_since: float | None = None
        self._no_gate_since: float | None = None
        self._done_reason: str | None = None

    # ---------------- helpers ----------------
    def _reset_jump(self) -> None:
        self._jump_sent_at = None
        self._jump_attempts = 0
        self._jump_gate = None

    def _resolve_gate(self, world: dict[str, Any]) -> dict[str, Any] | None:
        """Gate dẫn ĐÚNG tới next_system trong route. None = không xác định được."""
        nxt = str((world.get("route") or {}).get("next_system") or "").strip()
        if not nxt:
            return None
        want = nxt.casefold()
        matches = [g for g in (world.get("gates") or [])
                   if "stargate" in str(g.get("type") or "").lower()
                   and str(g.get("name") or "").strip().casefold() == want]
        return matches[0] if len(matches) == 1 else None

    def _resolve_station(self, world: dict[str, Any]) -> dict[str, Any] | None:
        """Station để dock cuối hành trình. Chỉ dock khi KHỚP destination —
        destination của route là đích người chơi chọn; station không khớp =
        chưa tới đúng nơi (hoặc tên trạm render khác destination), dock mù trạm
        khác là sai mục tiêu. Không khớp → None (caller chờ, không dock)."""
        dest = str((world.get("route") or {}).get("destination") or "").strip()
        if not dest:
            return None
        stations = [e for e in (world.get("stations") or [])
                    if "station" in str(e.get("type") or "").lower()]
        exact = [e for e in stations
                 if str(e.get("name") or "").strip().casefold() == dest.casefold()]
        return exact[0] if len(exact) == 1 else None

    # ---------------- main ----------------
    def tick(self, world: dict[str, Any]) -> list[dict[str, Any]]:
        now = self.clock()
        system = world.get("system")
        route = world.get("route") or {}
        markers = route.get("markers") or 0

        # 0) mất client/server
        if world.get("connection_lost"):
            self.state = "BLOCKED"
            self.blocked = "Connection Lost — E-STOP, không bấm gì"
            return [{"do": "estop", "why": self.blocked}]

        # 1) đang docked: có route → undock; không route → đã ở nơi cần đến
        if world.get("docked"):
            if markers > 0:
                self.state = "UNDOCK"
                xy = world.get("undock_xy")
                if not xy:
                    self.state = "BLOCKED"
                    self.blocked = "Đang docked nhưng không đọc được nút Undock — không bấm mù"
                    return [{"do": "blocked", "why": self.blocked}]
                return [{"do": "undock", "at": xy,
                         "why": "Route còn marker — undock bắt đầu hành trình"}]
            self.state = "DONE"
            self._done_reason = "Đang docked và route rỗng — đã ở đích"
            return [{"do": "done", "why": self._done_reason}]

        # 2) đang trong transition (UI chưa parse lại sau warp/jump): chờ, KHÔNG bấm
        if world.get("location_known") is False or not system:
            if self._unknown_since is None:
                self._unknown_since = now
            waited = now - self._unknown_since
            if waited > UNKNOWN_GRACE_S:
                self.state = "BLOCKED"
                self.blocked = (f"Không đọc được vị trí sau {int(waited)}s "
                                "(system/location UNKNOWN) — dừng để operator xem client")
                return [{"do": "blocked", "why": self.blocked}]
            self.state = "TRANSITION"
            return [{"do": "wait", "why": f"Đang chuyển cảnh — chưa đọc lại được vị trí "
                                          f"({int(waited)}/{int(UNKNOWN_GRACE_S)}s), không bấm"}]
        self._unknown_since = None

        # 3) jump vừa hoàn tất (system đổi so với lúc gửi lệnh) → chờ route panel cập nhật
        if self._jump_sent_at is not None and system != self._last_system:
            self.jumps_done += 1
            self._await_route_update = True
            self._route_update_since = now
            self._prev_next_system = self._jump_gate   # next_system cũ trỏ hệ vừa rời
            self._reset_jump()
        self._last_system = system
        # snapshot jumps mỗi tick qua lại — jumps giảm sau jump = panel đã cập nhật
        self._jumps_seen = route.get("jumps") if isinstance(route.get("jumps"), int) else None

        if self._await_route_update:
            jumps_now = self._jumps_seen
            updated = (str(route.get("next_system") or "").strip()
                       != str(self._prev_next_system or "").strip()
                       or (jumps_now is not None and self._jumps_before is not None
                           and jumps_now < self._jumps_before))
            if updated:
                self._await_route_update = False
            elif now - (self._route_update_since or now) > ROUTE_UPDATE_TIMEOUT_S:
                self.state = "BLOCKED"
                self.blocked = ("Route panel chưa cập nhật sau jump — có thể next_system "
                                "cũ còn treo; nhảy tiếp theo panel cũ là quay ngược. Dừng.")
                return [{"do": "blocked", "why": self.blocked}]
            else:
                self.state = "TRANSITION"
                return [{"do": "wait", "why": "Jump xong — chờ route panel cập nhật hệ kế tiếp "
                                              "(chống nhảy ngược theo panel cũ)"}]
        self._jumps_before = self._jumps_seen

        # 4) route rỗng → tới đích (tuỳ chọn dock)
        if markers <= 0:
            if self.dock_at_end and not world.get("docked"):
                st = self._resolve_station(world)
                if st and st.get("center"):
                    self.state = "DOCK_END"
                    return [{"do": "dock", "at": st["center"],
                             "name": st.get("name"),
                             "why": f"Đã tới hệ đích — dock {st.get('name')}"}]
                self.state = "WAIT_END"
                return [{"do": "wait", "why": "Đã tới hệ đích — chưa thấy đúng một station "
                                              "khớp destination, không dock mù"}]
            self.state = "DONE"
            self._done_reason = f"Route rỗng — đã tới đích sau {self.jumps_done} jump"
            return [{"do": "done", "why": self._done_reason}]

        # 5) guard số jump tối đa
        if self.max_jumps is not None and self.jumps_done >= self.max_jumps:
            self.state = "DONE"
            self._done_reason = f"Đã jump {self.jumps_done}/{self.max_jumps} — dừng theo --max-jumps"
            return [{"do": "done", "why": self._done_reason}]

        # 6) tìm gate kế tiếp
        gate = self._resolve_gate(world)
        if gate is None:
            if self._no_gate_since is None:
                self._no_gate_since = now
            waited = now - self._no_gate_since
            if waited > BLOCKED_AFTER_NO_GATE_S:
                self.state = "BLOCKED"
                nxt = route.get("next_system")
                self.blocked = (f"Route panel nói hệ kế tiếp là {nxt!r} nhưng overview không có "
                                f"đúng một gate tên đó sau {int(waited)}s — không bấm mù")
                return [{"do": "blocked", "why": self.blocked}]
            self.state = "WAIT_GATE"
            return [{"do": "wait", "why": f"Chưa thấy gate tới {route.get('next_system')} "
                                          f"({int(waited)}/{int(BLOCKED_AFTER_NO_GATE_S)}s)"}]
        self._no_gate_since = None

        # 7) pending jump: chờ hoặc resend có giới hạn
        if self._jump_sent_at is not None:
            elapsed = now - self._jump_sent_at
            if elapsed < JUMP_RESEND_S:
                self.state = "JUMPING"
                return [{"do": "wait", "why": f"Đã gửi jump {self._jump_gate} — đang warp/jump "
                                              f"({int(elapsed)}s, không gửi lại)"}]
            if elapsed >= JUMP_TIMEOUT_S or self._jump_attempts >= JUMP_MAX_ATTEMPTS:
                self.state = "BLOCKED"
                self.blocked = (f"Jump tới {self._jump_gate} không hoàn tất sau "
                                f"{int(elapsed)}s ({self._jump_attempts} lệnh) — dừng")
                return [{"do": "blocked", "why": self.blocked}]
            self._jump_attempts += 1
            self._jump_sent_at = now
            self.state = "JUMPING"
            return [{"do": "jump", "at": gate.get("center"), "name": gate.get("name"),
                     "attempt": self._jump_attempts,
                     "why": f"Gửi lại jump {gate.get('name')} "
                            f"(lần {self._jump_attempts}/{JUMP_MAX_ATTEMPTS})"}]

        # 8) gửi jump mới
        self._jump_sent_at = now
        self._jump_attempts = 1
        self._jump_gate = str(route.get("next_system") or gate.get("name"))
        self.state = "JUMPING"
        return [{"do": "jump", "at": gate.get("center"), "name": gate.get("name"),
                 "attempt": 1,
                 "why": f"Warp-to-0 + jump gate {gate.get('name')} "
                        f"(còn {markers} jump) — thay tay người"}]
