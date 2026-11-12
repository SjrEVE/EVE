"""Mode interface — mỗi chế độ (abyss / distribution / security) cắm vào Supervisor.

Hợp đồng:
- tick(world) -> list[action]   : quyết định 1 bước, KHÔNG tự bấm (executor bấm).
- request_safe_stop()           : người dùng bấm STOP an toàn → mode đi tới safe point.
- at_safe_point: bool           : đang ở điểm dừng an toàn (dock / ngoài site / đã ra abyss).
- in_no_escape: bool            : đang ở nơi không thoát được (trong abyss) → UI cảnh báo.
- phase: str                    : phase hiện tại để UI hiển thị.
- status() -> dict              : số liệu cho UI (tuỳ chọn).
"""
from __future__ import annotations

from typing import Any


class Mode:
    name = "base"

    def __init__(self) -> None:
        self.phase = "IDLE"
        self.stop_requested = False

    def tick(self, world: Any) -> list[Any]:  # pragma: no cover - interface
        raise NotImplementedError

    def on_action_results(self, results: list[Any]) -> None:
        """Optional read-back hook: executor delivery/verification results."""
        return None

    def request_safe_stop(self) -> None:
        self.stop_requested = True

    @property
    def at_safe_point(self) -> bool:
        return False

    @property
    def in_no_escape(self) -> bool:
        return False

    def status(self) -> dict[str, Any]:
        return {"mode": self.name, "phase": self.phase}
