"""FLEET STATE — HP/role của đồng đội cho multibox, không bịa từ HP của mình.

Bug đã bắt (test_fit_punisher #4): reflex.py set `tank_hp = self.ex.hp` — HP của
CHÍNH con bot. Logi chạy với role='logi' sẽ đọc HP của mình làm "tank_hp" → mở
all_reps khi chính nó giảm hp, rep sai người. Luật:
  - Không có báo cáo từ tank → tank_hp là UNKNOWN (None) → logi KHÔNG mở reps
    theo HP (chỉ ngưỡng kikimora vẫn dùng được vì đó là data của room mình).
  - Có báo cáo (file bus giữa các instance) → dùng số thật.
Bộ file bus: mỗi instance ghi `fleet/<role>.json` (pid, hp, updated); read-of-other
chỉ nhận khi file còn tươi (< freshness_s) — file cũ = UNKNOWN, không phải số cũ.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


class FleetState:
    """Chia sẻ HP giữa các bot instance bằng file JSON trong bus_dir/fleet/."""

    def __init__(self, bus_dir: str | Path | None = None,
                 freshness_s: float = 10.0, role: str = "solo") -> None:
        self.role = role
        self.freshness_s = freshness_s
        self._dir = (Path(bus_dir) / "fleet") if bus_dir else None
        # báo cáo đã nhận trong-process (test không cần file)
        self._inproc: dict[str, dict[str, Any]] = {}

    # ---------------- report (tự ghi) ----------------
    def publish(self, hp: float, cap: float | None = None,
                room: Any = None, phase: str | None = None) -> None:
        """Ghi trạng thái của CHÍNH MÌNH cho đồng đội đọc."""
        record = {"role": self.role, "hp": hp, "cap": cap, "room": room,
                  "phase": phase, "t": time.time()}
        self._inproc[self.role] = record
        if self._dir is not None:
            try:
                self._dir.mkdir(parents=True, exist_ok=True)
                tmp = self._dir / f".{self.role}.tmp"
                tmp.write_text(json.dumps(record), encoding="utf-8")
                os.replace(tmp, self._dir / f"{self.role}.json")
            except OSError:
                pass   # fleet sharing là best-effort, không được giết bot

    # ---------------- read (đồng đội) ----------------
    def tank_hp(self) -> float | None:
        rec = self._report_of("tank")
        hp = rec.get("hp") if rec else None
        return hp if isinstance(hp, (int, float)) else None

    def _report_of(self, role: str) -> dict[str, Any] | None:
        rec = self._inproc.get(role)
        if rec is None and self._dir is not None:
            f = self._dir / f"{role}.json"
            try:
                rec = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None
        if not isinstance(rec, dict):
            return None
        if time.time() - rec.get("t", 0) > self.freshness_s:
            return None   # file cũ = UNKNOWN, không dùng số cũ làm quyết định
        return rec
