"""DRONE MODULE — quản lý drone theo cơ chế aggro thật (UniWiki Tips/Drone mechanics).

DEATH-by-drone facts (nguồn): rats đổi aggro sang drone DỄ; launch khi chưa redbox =
drone bị nuke off-field; drone ngoài leash 20-25km trả về chậm; gila bonus 250% HP.

Merge 2026-11-10 — 3 tín hiệu recall CHỦ ĐỘNG (trước khi máy đếm hp kịp tụt):
  1. room_cleared     — room sạch thì recall trước khi kích gate (DEATH #3: quên = mất)
  2. suppressor ≤15km — tháp Short-Range Deviant Automata Suppressor nổ AOE chết drone
  3. yellowbox        — Grip Tessera/Elite Lucifer đổi aggro sang drone (red→yellow box)
                        là dấu hiệu mất drone trong 1-2 loạt, không đợi hp_avg tụt 40%

Contract (test_drone/test_endgame): attrs max/leash_km/hp_floor/gila/state/hp_avg/
in_space/aggroed_by; can_launch(redboxed) chặn khi chưa redbox; on_launch đặt
in_space=max; update() trả {"action": ...} hoặc None; leash → return_orbit (không
recall); hết drone ngoài → HIDDEN; gate_ready() == (in_space == 0).
"""
from __future__ import annotations
from typing import Any


class DroneManager:
    """FSM drone: HIDDEN → LAUNCHING → ENGAGED → (damaged→RECALLING) → HIDDEN.
    Bot không bấm mù: mọi transition đều verify qua eye (DroneView)."""

    def __init__(self, max_drones: int = 5, leash_km: float = 25.0,
                 hp_floor: float = 0.4, gila_bonus: bool = False) -> None:
        self.max = max_drones
        self.leash_km = leash_km
        self.hp_floor = hp_floor
        self.gila = gila_bonus
        self.state = "HIDDEN"
        self.hp_avg: float = 1.0
        self.in_space: int = 0
        self.aggroed_by: str | None = None   # con đang bắn drone

    def can_launch(self, redboxed: bool, suppressor_close: bool = False) -> tuple[bool, str]:
        """DEATH RULE: chỉ launch khi mình ĐANG bị bắn (redbox) — launch sớm = drone chết.
        suppressor_close=True (tháp Suppressor ≤15km) → cấm launch (AOE ăn drone)."""
        if suppressor_close:
            return False, "tháp Suppressor ≤15km — AOE chết drone, không launch"
        if self.state != "HIDDEN":
            return False, f"state={self.state}, không phải HIDDEN"
        if not redboxed:
            return False, "chưa redbox — launch sớm = rats nuke drone (UniWiki Tips)"
        return True, ""

    def on_launch(self) -> None:
        self.state = "ENGAGED"
        self.in_space = self.max
        self.hp_avg = 1.0

    def update(self, st: dict[str, Any]) -> dict[str, Any] | None:
        """Mỗi tick: đọc trạng thái drone từ eye snapshot → quyết định recall gì.
        Trả action dict hoặc None."""
        self.in_space = int(st.get("drones_in_space", self.in_space))
        self.hp_avg = float(st.get("drones_hp_avg", self.hp_avg))
        # tín hiệu mới (không có trong snapshot cũ → mặc định tắt, hành vi giữ nguyên)
        room_cleared = bool(st.get("room_cleared", False))
        yellowboxed = bool(st.get("yellowboxed_anti_drone", False))
        suppressor_km = float(st.get("suppressor_dist_km", 999.0))

        out = None
        # 0a) room sạch → recall hết TRƯỚC khi kích gate
        if self.state in ("ENGAGED", "RECALLING") and room_cleared and self.in_space > 0:
            self.state = "RECALLING"
            return {"action": "recall", "reason": "room cleared — recall drone trước gate "
                    "(DEATH #3: jump còn drone ngoài = mất)"}
        # 0b) tháp Suppressor ngắn ≤15km — AOE chết drone
        if self.state == "ENGAGED" and self.in_space > 0 and suppressor_km <= 15.0:
            self.state = "RECALLING"
            return {"action": "recall", "reason": "Deviant Automata Suppressor ≤15km — "
                    "AOE nổ drone, rút ngay"}
        # 0c) anti-drone rats yellow-box (đổi aggro sang drone) — recall TRƯỚC khi mất
        if (self.state == "ENGAGED" and self.in_space > 0 and yellowboxed
                and (not self.gila or self.hp_avg < 0.85)):
            self.state = "RECALLING"
            self.aggroed_by = "yellowbox_switch"
            return {"action": "recall", "reason": "anti-drone rats yellow-box — đổi aggro "
                    "sang drone (1-2 loạt là mất, không đợi hp tụt)"}
        # 1) drone bị đánh → recall ngay (rats đổi aggro = drone chết vài giây)
        if self.state == "ENGAGED" and self.hp_avg < self.hp_floor:
            out = {"action": "recall", "reason": f"drone hp {self.hp_avg:.0%} < {self.hp_floor:.0%} — "
                   "rats aggro drone = chết nhanh"}
            self.state = "RECALLING"
        # 2) leash: target/drone quá xa → return&orbit (MWD) không để idle trôi
        elif self.state == "ENGAGED" and st.get("dist_to_drone_target_km", 0) > self.leash_km:
            out = {"action": "return_orbit", "reason": f"target ngoài leash {self.leash_km}km — "
                   "idle trôi về sublight = chậm chết"}
        # 3) room chuyển → recall hết trước gate (guard DroneOut đã chặn GATE)
        elif self.state in ("ENGAGED", "RECALLING") and self.in_space == 0:
            self.state = "HIDDEN"
        return out

    def gate_ready(self) -> bool:
        return self.in_space == 0
