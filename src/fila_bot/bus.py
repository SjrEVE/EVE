"""FileBus — file-based command/event bridge giữ FC (LLM) <-> bot.

Inbox  : DLG ghi lệnh, mỗi dòng 1 JSON {"id", "cmd", "arg"=optional}
Outbox : bot ghi events, mỗi dòng 1 JSON {"t", "seq", "type", ...}
Cả 2 file được "trim tail" khi quá keep dòng để không phình vô hạn.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any


class FileBus:
    def __init__(self, dirpath: str | Path, inbox: str = "fc_to_bot.jsonl",
                 outbox: str = "bot_to_fc.jsonl", keep: int = 500) -> None:
        self.dirpath = Path(dirpath)
        self.inbox_path = self.dirpath / inbox
        self.outbox_path = self.dirpath / outbox
        self.keep = keep
        self._in_offset = 0
        self._out_seq = 0
        self.dirpath.mkdir(parents=True, exist_ok=True)
        self.inbox_path.touch(exist_ok=True)
        self.outbox_path.touch(exist_ok=True)

    # ---------------- inbox (lệnh từ FC) ----------------
    def poll(self) -> list[dict[str, Any]]:
        """Đọc TẤT CẢ lệnh mới kể từ lần poll trước. Trả list dict."""
        try:
            size = self.inbox_path.stat().st_size
        except OSError:
            return []
        if size < self._in_offset:          # file bị xoá/trim → đọc lại từ đầu
            self._in_offset = 0
        if size == self._in_offset:
            return []
        out: list[dict[str, Any]] = []
        with self.inbox_path.open("r", encoding="utf-8") as fh:
            fh.seek(self._in_offset)
            raw = fh.read()
            self._in_offset = fh.tell()
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                out.append({"corrupt": line})
                self.emit("REJECT", cmd=None, reason="corrupt inbox line")
        self._trim(self.inbox_path)
        return out

    # ---------------- outbox (event về FC) ----------------
    def emit(self, etype: str, note: str | None = None, **fields: Any) -> dict[str, Any]:
        self._out_seq += 1
        ev: dict[str, Any] = {
            "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "seq": self._out_seq,
            "type": etype,
        }
        if note:
            ev["note"] = note
        ev.update(fields)
        with self.outbox_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
        self._trim(self.outbox_path)
        return ev

    def read_outbox(self, tail: int = 100) -> list[dict[str, Any]]:
        lines = self.outbox_path.read_text(encoding="utf-8").splitlines()
        out = []
        for line in lines[-tail:]:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return out

    # ---------------- internal ----------------
    def _trim(self, path: Path) -> None:
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) <= self.keep:
            return
        tail = "\n".join(lines[-self.keep:]) + "\n"
        path.write_text(tail, encoding="utf-8")
        if path == self.inbox_path:
            self._in_offset = 0   # sau trim, đọc lại mọi thứ để không mất lệnh mới
