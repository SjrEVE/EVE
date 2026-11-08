"""COMBAT BRAIN (P1-1 issue #1) — vòng tự quyết combat mỗi tick.

Trước: rats/rooms nằm chết (không ai gọi). Giờ: Bot.tick gọi combat_brain.tick()
→ detect room → lock_order → issue lock/orbit/activate actions vào ex.actions.

Hoạt động qua executor interface (sim hay RealExecutor đều chạy được).
Executor cần expose: overview_texts() → list tên quái; có actions list.
"""
from __future__ import annotations

from typing import Any

from . import rats
from . import rooms as rooms_mod


class CombatBrain:
    def __init__(self) -> None:
        self.current_target: str | None = None
        self.locked: set[str] = set()
        self.last_action: str | None = None

    def reset_room(self) -> None:
        self.current_target = None
        self.locked.clear()
        self.last_action = None

    def tick(self, ex: Any, phase: str) -> list[tuple]:
        """Trả list actions cần append vào ex.actions. Chỉ chạy khi *_FIGHT."""
        if not str(phase).endswith("_FIGHT"):
            return []
        names = ex.overview_texts() if hasattr(ex, "overview_texts") else []
        if not names:
            return []
        room_kind = rooms_mod.detect_room(names)
        order = rats.lock_order(names)
        acts: list[tuple] = []
        # 1) chọn target đầu tiên chưa lock (skip Swarmer)
        want = None
        for c in order:
            if c["skip"]:
                continue
            raw = c["raw"]
            if raw not in self.locked:
                want = raw
                break
        if want and want != self.current_target:
            acts.append(("lock", want))
            self.locked.add(want)
            self.current_target = want
        # 2) orbit target đang khóa ở khoảng cách theo room playbook (mặc định 10km)
        if self.current_target:
            acts.append(("orbit", 10, self.current_target))
        # 3) bắn slot 1-2 (high) — module management chi tiết theo fit ở adapter
        if self.current_target:
            acts.append(("activate", 1, "high"))
        self.last_action = f"{room_kind}|{self.current_target}"
        return acts
