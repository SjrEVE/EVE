"""win.py — cửa sổ EVE client: tìm HWND + đổi toạ độ client ↔ màn hình.

VÌ SAO CẦN: UI tree của EVE trả `_displayX/Y` trong hệ toạ độ CLIENT (gốc 0,0 = góc
trong của cửa sổ game). `SetCursorPos`/`mouse_event` lại dùng toạ độ MÀN HÌNH.
Thiếu bước cộng offset → click lệch đúng bằng viền + title bar (ground 2026-11-09:
undock thật ở màn hình y=313, client y=282 → lệch 31px = title bar).

Không dùng toạ độ đoán: mọi offset đọc từ Win32 (GetClientRect + ClientToScreen).
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes as wt
from typing import Any

PROCESS_NAME = "exefile.exe"


def find_client_window(pid: int | None = None) -> dict[str, Any] | None:
    """Tìm cửa sổ EVE. pid=None → tự tìm exefile.exe.

    Trả {hwnd, pid, title, origin:(x,y), size:(w,h), dpi} hoặc None.
    """
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    if pid is None:
        pid = _find_pid(PROCESS_NAME)
        if pid is None:
            return None

    found: list[tuple[int, str]] = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def _cb(hwnd, _lparam):
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value != pid or not user32.IsWindowVisible(hwnd):
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        if not n:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        found.append((hwnd, buf.value))
        return True

    user32.EnumWindows(_cb, 0)
    if not found:
        return None
    hwnd, title = found[0]

    rect = wt.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    origin = wt.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(origin))
    try:
        dpi = user32.GetDpiForWindow(hwnd)
    except Exception:      # noqa: BLE001 — Windows cũ không có API
        dpi = 96
    return {"hwnd": hwnd, "pid": pid, "title": title,
            "origin": (origin.x, origin.y),
            "size": (rect.right - rect.left, rect.bottom - rect.top),
            "dpi": dpi}


def _find_pid(name: str) -> int | None:
    """PID của process theo tên (dùng tasklist — không cần psutil)."""
    import subprocess
    try:
        out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {name}", "/FO", "CSV", "/NH"],
                             capture_output=True, text=True, timeout=15).stdout
    except Exception:      # noqa: BLE001
        return None
    for line in out.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) >= 2 and parts[0].lower() == name.lower():
            try:
                return int(parts[1])
            except ValueError:
                continue
    return None


def client_to_screen(win: dict[str, Any], xy: tuple[int, int]) -> tuple[int, int]:
    """Toạ độ client (từ UI tree) → toạ độ màn hình (để click)."""
    ox, oy = win["origin"]
    return int(xy[0] + ox), int(xy[1] + oy)


def focus(win: dict[str, Any]) -> None:
    """Đưa cửa sổ game lên trước (click chỉ ăn khi cửa sổ active)."""
    user32 = ctypes.windll.user32
    hwnd = win["hwnd"]
    user32.ShowWindow(hwnd, 9)            # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
