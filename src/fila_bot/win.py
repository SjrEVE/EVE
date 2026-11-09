"""win.py — cửa sổ EVE client: tìm HWND + đổi toạ độ client ↔ màn hình.

VÌ SAO CẦN: UI tree của EVE trả `_displayX/Y` trong hệ toạ độ CLIENT (gốc 0,0 = góc
trong của cửa sổ game). `SetCursorPos`/`mouse_event` lại dùng toạ độ MÀN HÌNH.
Thiếu bước cộng offset → click lệch đúng bằng viền + title bar (ground 2026-11-09:
undock thật ở màn hình y=313, client y=282 → lệch 31px = title bar).

Không dùng toạ độ đoán: mọi offset đọc từ Win32 (GetClientRect + ClientToScreen).
"""
from __future__ import annotations

import ctypes
import time
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


def focus(win: dict[str, Any]) -> bool:
    """Đưa cửa sổ game lên trước — SetForegroundWindow TRẦN KHÔNG ĐỦ.

    Windows chặn SetForegroundWindow từ process không phải foreground (ground
    2026-11-09: cửa sổ Hermes che EVE, foreground vẫn là Hermes → click rơi vào Hermes).
    Cách đúng: AttachThreadInput vào thread đang giữ foreground rồi mới SetForegroundWindow.
    Trả True nếu EVE thực sự thành foreground.
    """
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    hwnd = win["hwnd"]

    user32.ShowWindow(hwnd, 9)                       # SW_RESTORE
    fg = user32.GetForegroundWindow()
    if fg == hwnd:
        return True

    fg_thread = user32.GetWindowThreadProcessId(fg, None)
    my_thread = kernel32.GetCurrentThreadId()
    attached = False
    if fg_thread and fg_thread != my_thread:
        attached = bool(user32.AttachThreadInput(my_thread, fg_thread, True))
    try:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SetActiveWindow(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(my_thread, fg_thread, False)

    time.sleep(0.25)
    return user32.GetForegroundWindow() == hwnd


def point_owner(x: int, y: int) -> tuple[int, int]:
    """(hwnd, pid) của cửa sổ THỰC SỰ nằm dưới điểm (x,y) trên màn hình.

    Dùng để phát hiện bị che: WindowFromPoint trả cửa sổ trên cùng tại điểm đó,
    sau đó leo lên root owner (cửa sổ con vẫn thuộc pid game).
    """
    user32 = ctypes.windll.user32
    pt = wt.POINT(int(x), int(y))
    hwnd = user32.WindowFromPoint(pt)
    if not hwnd:
        return 0, 0
    # leo lên root owner
    root = hwnd
    while True:
        parent = user32.GetAncestor(root, 2)   # GA_ROOT
        if not parent or parent == root:
            break
        root = parent
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(root, ctypes.byref(pid))
    return root, pid.value


def is_reachable(win: dict[str, Any], screen_xy: tuple[int, int]) -> bool:
    """Điểm (toạ độ màn hình) có thực sự thuộc cửa sổ game và không bị che?"""
    _, pid = point_owner(*screen_xy)
    return pid == win["pid"]
