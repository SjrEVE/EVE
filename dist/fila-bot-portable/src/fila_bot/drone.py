"""DRONE MODULE — quản lý drone theo cơ chế aggro thật (UniWiki Tips/Drone mechanics).

DEATH-by-drone facts (nguồn): rats đổi aggro sang drone DỄ; launch khi chưa redbox =
drone bị nuke off-field; drone ngoài leash 20-25km trả về chậm; gila bonus 250% HP.
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

    def can_launch(self, redboxed: bool) -> tuple[bool, str]:
        """DEATH RULE: chỉ launch khi mình ĐANG bị bắn (redbox) — launch sớm = drone chết."""
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
        self.in_space = st.get("drones_in_space", self.in_space)
        self.hp_avg = st.get("drones_hp_avg", self.hp_avg)
        out = None
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
