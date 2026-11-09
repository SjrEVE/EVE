"""Nhật ký chạy (M6) — mỗi phiên START→IDLE ghi 1 cặp dòng JSONL vào runs/<YYYY-MM-DD>.jsonl.

Định dạng dòng (mỗi dòng 1 JSON object):
    {"type": "session_start", "t": <wall epoch>, "mode": "abyss"}
    {"type": "crash",         "t": ..., "mode": ..., "error": "RuntimeError('boom')"}
    {"type": "session_end",   "t": ..., "mode": ..., "reason": "đã tới safe point",
     "dur_s": 42.0, "ticks": 7, "status": {...}}   # status = mode.status() cuối cùng

Fail-safe: ghi lỗi file không được giết bot — RunLog nuốt exception I/O (log phụ,
không phải safety floor). Thống kê đọc bằng read_stats(): UI hiện "Đã xong N run".
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable


class RunLog:
    def __init__(self, runs_dir: str | Path, clock: Callable[[], float] = time.monotonic) -> None:
        self.dir = Path(runs_dir)
        self.clock = clock
        self._start_t: float | None = None
        self._mode: str | None = None

    def _write(self, rec: dict[str, Any]) -> None:
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            day = time.strftime("%Y-%m-%d", time.localtime(rec["t"]))
            with (self.dir / (day + ".jsonl")).open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except OSError:
            pass  # log phụ — không giết bot vì ổ đĩa đầy/quyền

    def session_start(self, mode: str) -> None:
        self._start_t = self.clock()
        self._mode = mode
        self._write({"type": "session_start", "t": time.time(), "mode": mode})

    def session_end(self, reason: str, *, ticks: int = 0,
                    status: dict[str, Any] | None = None) -> None:
        if self._start_t is None:
            return
        dur = self.clock() - self._start_t
        self._start_t = None
        self._write({"type": "session_end", "t": time.time(), "mode": self._mode,
                     "reason": reason, "dur_s": round(dur, 3), "ticks": ticks,
                     "status": status or {}})

    def crash(self, error: str) -> None:
        if self._start_t is None:
            return
        self._write({"type": "crash", "t": time.time(), "mode": self._mode, "error": error})


def read_stats(runs_dir: str | Path) -> dict[str, Any]:
    """Tổng hợp toàn bộ runs/*.jsonl — UI đọc để hiện thống kê. Line hỏng bị bỏ qua."""
    stats: dict[str, Any] = {"sessions": 0, "completed": 0, "crashes": 0,
                             "last_reason": None, "last_t": None, "modes": {}}
    d = Path(runs_dir)
    if not d.is_dir():
        return stats
    for p in sorted(d.glob("*.jsonl")):
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            t = rec.get("type")
            if t == "session_start":
                stats["sessions"] += 1
                mode = rec.get("mode") or "?"
                stats["modes"][mode] = stats["modes"].get(mode, 0) + 1
            elif t == "session_end":
                stats["completed"] += int((rec.get("status") or {}).get("runs") or 0)
                stats["last_reason"] = rec.get("reason")
                stats["last_t"] = rec.get("t")
            elif t == "crash":
                stats["crashes"] += 1
    return stats
