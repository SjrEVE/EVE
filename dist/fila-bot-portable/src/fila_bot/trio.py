"""TRIO ROLES — FSM bổ sung cho multibox 2DPS+1Logi (nguồn: Gustav trio video + Minmatar wiki).

Mỗi acc = 1 Bot instance có role; room checklist chung ở docs/TRIO_PLAYBOOK.md.
Đây là phần "chiều tay" của endgame multibox — FSM khác nhau theo ROLE.
"""
from __future__ import annotations

from typing import Any

ROLES = ("tank", "dps", "logi")

# Ngưỡng kích hoạt hành vi theo role (nguồn: TRIO_PLAYBOOK checklist)
LOGI_REPS_ALL_AT_HP = 0.60      # tank hp <60% → logi mở hết reps
KIKI_SWARM_THRESHOLD = 6        # >6 kikimora → all reps lên tank (Gustav ngưỡng)


class TrioRole:
    """Gói hành vi role — Bot giữ 1 instance; tick() trả extra actions."""

    def __init__(self, role: str) -> None:
        if role not in ROLES:
            raise ValueError(f"role phải thuộc {ROLES}, nhận '{role}'")
        self.role = role
        self.reps_open = False

    # ---------------- TANK (Nergal) ----------------
    def tank_tick(self, st: dict[str, Any]) -> list[dict[str, Any]]:
        acts = []
        # entry: tank là aggro magnet — approach cache trước (no-switch enemies khóa nó)
        if st.get("room_entry") and not st.get("moved_this_room"):
            acts.append({"do": "approach_cache", "why": "tank = aggro magnet (no-switch rats)"})
        # hp rơi → emit cho logi (logi đọc bus riêng)
        if st.get("hp", 1.0) < LOGI_REPS_ALL_AT_HP and not self.reps_open:
            acts.append({"do": "signal_logi_all_reps", "why": f"tank hp <{LOGI_REPS_ALL_AT_HP:.0%}"})
        return acts

    # ---------------- DPS (Retribution) ----------------
    def dps_tick(self, st: dict[str, Any]) -> list[dict[str, Any]]:
        acts = []
        # DPS giữ orbit tank — không tự tank aggro
        if st.get("dist_to_tank_km", 0) > 5.0:
            acts.append({"do": "orbit_tank", "km": 2.5, "why": "giữ sát tank — logi chỉ rep 1 điểm"})
        # bắn theo lock_order (rats.py) — DPS không tự chọn mục tiêu khác
        target = st.get("current_target")
        want = st.get("want_target")
        if want and target != want:
            acts.append({"do": "switch_target", "to": want, "why": "focus fire đồng bộ trio"})
        return acts

    # ---------------- LOGI (Deacon) ----------------
    def logi_tick(self, st: dict[str, Any]) -> list[dict[str, Any]]:
        acts = []
        n_kiki = st.get("kikimora_count", 0)
        tank_hp = st.get("tank_hp", 1.0)
        # >6 kikimora room → mở CẢ 3 reps ngay từ đầu (Gustav ngưỡng)
        if n_kiki > KIKI_SWARM_THRESHOLD and not self.reps_open:
            acts.append({"do": "all_reps_on_tank", "why": f"{n_kiki} kikimora > {KIKI_SWARM_THRESHOLD} — all reps"})
            self.reps_open = True
        elif tank_hp < LOGI_REPS_ALL_AT_HP and not self.reps_open:
            acts.append({"do": "all_reps_on_tank", "why": f"tank hp {tank_hp:.0%} < 60%"})
            self.reps_open = True
        elif tank_hp > 0.85 and self.reps_open:
            acts.append({"do": "close_extra_reps", "why": "tank ổn — tiết kiệm cap"})
            self.reps_open = False
        # cap thấp = MAYDAY (cap brick vẫn có hạn)
        if st.get("cap", 1.0) < 0.2:
            acts.append({"do": "mayday", "why": "logi cap <20% — hết reps = fleet chết"})
        return acts

    def tick(self, st: dict[str, Any]) -> list[dict[str, Any]]:
        if self.role == "tank":
            return self.tank_tick(st)
        if self.role == "dps":
            return self.dps_tick(st)
        return self.logi_tick(st)

    def new_room(self) -> None:
        """Reset per-room state — reactive hardener + reps đóng (reset quên = dead slot)."""
        self.reps_open = False
