"""Single-instance lock cho bot runtime — cấm 2 bot cùng bấm game.

Ground 2026-11-13 01:5x: 4 bot ngầm cùng bấm (mỗi lần `timeout` tool cắt nhưng
python con vẫn sống) → game nhận input hỗn loạn. Quy tắc Boss: "Bot active trùng
nhau là không được, phải biết lúc nào kết thúc phiên".

Cơ chế: PID file `logs/bot.pid`. Khi start:
  - Không có file → ghi PID mình, chạy.
  - File có PID còn sống → TỰ ĐỘNG KILL bot cũ (SIGKILL an toàn vì bot chỉ bấm
    vào game client, không ghi file gì quan trọng giữa chừng), ghi PID mới, chạy.
  - File có PID đã chết → ghi đè, chạy.
Khi thoát (kể cả Ctrl+C) → xoá file.

Windows: dùng OpenProcess+TerminateProcess qua ctypes (không cần psutil).
"""
from __future__ import annotations

import atexit
import ctypes
import os
import signal
import sys
from pathlib import Path

_PID_FILE = Path("logs/bot.pid")


def _pid_alive(pid: int) -> bool:
    """True nếu process pid còn sống (Windows)."""
    if pid <= 0:
        return False
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    k32 = ctypes.windll.kernel32
    handle = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False
    try:
        code = ctypes.c_ulong()
        k32.GetExitCodeProcess(handle, ctypes.byref(code))
        return code.value == STILL_ACTIVE
    finally:
        k32.CloseHandle(handle)


def _kill_pid(pid: int) -> bool:
    """TerminateProcess — bot cũ chỉ bấm game, không có dữ liệu cần flush."""
    PROCESS_TERMINATE = 0x0001
    k32 = ctypes.windll.kernel32
    handle = k32.OpenProcess(PROCESS_TERMINATE, False, pid)
    if not handle:
        return False
    try:
        return bool(k32.TerminateProcess(handle, 1))
    finally:
        k32.CloseHandle(handle)


def acquire(reason: str = "") -> None:
    """Đảm bảo chỉ 1 bot đang chạy. Kill bot cũ nếu còn sống."""
    _PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _PID_FILE.is_file():
        try:
            old = int(_PID_FILE.read_text(encoding="utf-8").strip() or 0)
        except (ValueError, OSError):
            old = 0
        if old and old != os.getpid() and _pid_alive(old):
            if _kill_pid(old):
                print(f"[LOCK] Đã dừng bot cũ (pid {old}) — {reason or 'chạy phiên mới'}")
            else:
                raise SystemExit(
                    f"[KHONG CHAY] Bot cũ (pid {old}) vẫn sống và không kill được — "
                    "dừng để không có 2 bot cùng bấm game.")
            # chờ bot cũ nhả phím
            import time
            time.sleep(2.0)
    _PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    atexit.register(release)


def release() -> None:
    """Xoá PID file nếu vẫn là PID của mình (không xoá của bot kế nhiệm)."""
    try:
        if _PID_FILE.is_file() and _PID_FILE.read_text(
                encoding="utf-8").strip() == str(os.getpid()):
            _PID_FILE.unlink()
    except OSError:
        pass


if __name__ == "__main__":
    print(_PID_FILE.resolve())
