"""Upgraded Win32 Window Geometry, DPI-Awareness, Occlusion & Multibox Manager (fila_bot/win.py).

Solves the real-world EVE Online client window control issues:
  1. Per-Monitor DPI Awareness V2 (`enable_dpi_awareness`) so 125%/150% Windows scaling
     never shifts click coordinates.
  2. Exact Client-to-Screen translation (`client_to_screen`) eliminating the ~31px
     Title-Bar + Window-Border offset between EVE UI Tree `_displayX/Y` and `SetCursorPos`.
  3. Occlusion & Reachability Guard (`point_owner`, `is_reachable`) using `WindowFromPoint`
     and `GetAncestor(GA_ROOT)` to ensure clicks never hit an overlapping window.
  4. Foreground Focus Bypass (`focus`) using `AttachThreadInput` + `ShowWindow(SW_RESTORE)`
     + `BringWindowToTop` + `SetForegroundWindow`.
  5. Multibox Client Pool (`find_all_client_windows`) for switching between multiple
     `exefile.exe` instances by PID or character title.
"""

from __future__ import annotations
import ctypes
from ctypes import wintypes
from typing import Any

PROCESS_NAME: str = "exefile.exe"

GA_ROOT: int = 2
SW_RESTORE: int = 9
PROCESS_QUERY_LIMITED_INFORMATION: int = 0x1000


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def enable_dpi_awareness() -> bool:
    """Enable Per-Monitor DPI Awareness V2 on Windows so client coordinates are 1:1 physical pixels."""
    if not hasattr(ctypes, "windll"):
        return False
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
        res = ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        if res:
            return True
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return True
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
        return True
    except Exception:
        return False


# Activate DPI awareness immediately on module load
enable_dpi_awareness()


def _get_window_pid(hwnd: int) -> int:
    if not hasattr(ctypes, "windll"):
        return 0
    pid = wintypes.DWORD(0)
    ctypes.windll.user32.GetWindowThreadProcessId(wintypes.HWND(hwnd), ctypes.byref(pid))
    return int(pid.value)


def _get_process_basename(pid: int) -> str:
    if not hasattr(ctypes, "windll") or pid <= 0:
        return ""
    kernel32 = ctypes.windll.kernel32
    h_proc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h_proc:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(512)
        size = wintypes.DWORD(512)
        if kernel32.QueryFullProcessImageNameW(h_proc, 0, buf, ctypes.byref(size)):
            full_path = buf.value
            return full_path.replace("/", "\\").split("\\")[-1]
        return ""
    finally:
        kernel32.CloseHandle(h_proc)


def _get_window_title(hwnd: int) -> str:
    if not hasattr(ctypes, "windll"):
        return ""
    user32 = ctypes.windll.user32
    length = user32.GetWindowTextLengthW(wintypes.HWND(hwnd))
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(wintypes.HWND(hwnd), buf, length + 1)
    return buf.value


def _read_window_geometry(hwnd: int, pid: int, title: str) -> dict[str, Any] | None:
    if not hasattr(ctypes, "windll"):
        return None
    user32 = ctypes.windll.user32
    rect = _RECT()
    if not user32.GetClientRect(wintypes.HWND(hwnd), ctypes.byref(rect)):
        return None
    pt = _POINT(0, 0)
    if not user32.ClientToScreen(wintypes.HWND(hwnd), ctypes.byref(pt)):
        return None

    width = int(rect.right - rect.left)
    height = int(rect.bottom - rect.top)
    if width <= 0 or height <= 0:
        return None

    dpi = 96
    if hasattr(user32, "GetDpiForWindow"):
        try:
            d = int(user32.GetDpiForWindow(wintypes.HWND(hwnd)))
            if d > 0:
                dpi = d
        except Exception:
            pass

    return {
        "hwnd": int(hwnd),
        "pid": int(pid),
        "title": title,
        "origin": (int(pt.x), int(pt.y)),
        "size": (width, height),
        "dpi": dpi,
        "scale": round(dpi / 96.0, 3),
    }


def find_all_client_windows(process_name: str = PROCESS_NAME) -> list[dict[str, Any]]:
    """Enumerate all visible EVE Online (`exefile.exe`) client windows with live geometry."""
    if not hasattr(ctypes, "windll"):
        return []

    user32 = ctypes.windll.user32
    found: list[dict[str, Any]] = []
    target_proc = process_name.lower()

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _enum_cb(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(wintypes.HWND(hwnd)):
            return True
        pid = _get_window_pid(hwnd)
        proc_name = _get_process_basename(pid).lower()
        title = _get_window_title(hwnd)
        if proc_name == target_proc or (not proc_name and title.startswith("EVE - ")):
            geom = _read_window_geometry(hwnd, pid, title)
            if geom is not None:
                found.append(geom)
        return True

    cb = WNDENUMPROC(_enum_cb)
    user32.EnumWindows(cb, 0)
    return found


def find_client_window(pid: int | None = None, title_contains: str | None = None) -> dict[str, Any] | None:
    """Locate the target EVE Online client window by optional PID or character name substring."""
    windows = find_all_client_windows()
    for w in windows:
        if pid is not None and w["pid"] != int(pid):
            continue
        if title_contains is not None and title_contains.lower() not in w["title"].lower():
            continue
        return w
    return None


def client_to_screen(
    win: dict[str, Any] | None,
    xy: tuple[int, int],
    clamp_margin: int = 2,
) -> tuple[int, int]:
    """Translate EVE UI client-relative coordinates `(x, y)` to physical screen coordinates.

    Eliminates the Title-Bar (~31px) and window border offset, and clamps `(x, y)` safely
    within the client viewport so clicks never land on window borders or the taskbar.
    """
    cx, cy = int(xy[0]), int(xy[1])
    if not win:
        return (cx, cy)

    size = win.get("size")
    if size and len(size) == 2:
        w, h = int(size[0]), int(size[1])
        if w > clamp_margin * 2 and h > clamp_margin * 2:
            cx = max(clamp_margin, min(w - clamp_margin, cx))
            cy = max(clamp_margin, min(h - clamp_margin, cy))

    # Query live ClientToScreen if hwnd is valid on Windows (handles moved windows dynamically)
    hwnd = win.get("hwnd")
    if hwnd and hasattr(ctypes, "windll"):
        try:
            pt = _POINT(cx, cy)
            if ctypes.windll.user32.ClientToScreen(wintypes.HWND(int(hwnd)), ctypes.byref(pt)):
                return (int(pt.x), int(pt.y))
        except Exception:
            pass

    origin = win.get("origin", (0, 0))
    return (int(origin[0]) + cx, int(origin[1]) + cy)


def point_owner(x: int, y: int) -> tuple[int, int]:
    """Return `(root_hwnd, pid)` of the top-level window owning screen point `(x, y)`."""
    if not hasattr(ctypes, "windll"):
        return (0, 0)
    user32 = ctypes.windll.user32
    pt = _POINT(int(x), int(y))
    child_hwnd = user32.WindowFromPoint(pt)
    if not child_hwnd:
        return (0, 0)
    root_hwnd = user32.GetAncestor(wintypes.HWND(child_hwnd), GA_ROOT) or child_hwnd
    pid = _get_window_pid(int(root_hwnd))
    return (int(root_hwnd), int(pid))


def is_reachable(win: dict[str, Any] | None, screen_xy: tuple[int, int]) -> bool:
    """Verify that screen coordinates `screen_xy` belong directly to the EVE client window
    and are not occluded by another application or OS overlay.
    """
    if not win:
        return True
    if not hasattr(ctypes, "windll"):
        return True

    sx, sy = int(screen_xy[0]), int(screen_xy[1])
    origin = win.get("origin", (0, 0))
    size = win.get("size", (0, 0))
    if size[0] > 0 and size[1] > 0:
        if not (origin[0] <= sx <= origin[0] + size[0] and origin[1] <= sy <= origin[1] + size[1]):
            return False

    owner_hwnd, owner_pid = point_owner(sx, sy)
    target_hwnd = int(win.get("hwnd", 0))
    target_pid = int(win.get("pid", 0))
    if owner_hwnd == 0:
        return False
    if target_hwnd and owner_hwnd == target_hwnd:
        return True
    if target_pid and owner_pid == target_pid:
        return True
    return False


def focus(win: dict[str, Any] | None) -> bool:
    """Force the EVE Online client window to the foreground using `AttachThreadInput`."""
    if not win or not hasattr(ctypes, "windll"):
        return True

    hwnd = int(win.get("hwnd", 0))
    if hwnd <= 0:
        return False

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    try:
        fg_hwnd = user32.GetForegroundWindow()
        if fg_hwnd == hwnd:
            return True

        if user32.IsIconic(wintypes.HWND(hwnd)):
            user32.ShowWindow(wintypes.HWND(hwnd), SW_RESTORE)

        cur_tid = kernel32.GetCurrentThreadId()
        target_tid = user32.GetWindowThreadProcessId(wintypes.HWND(hwnd), None)
        fg_tid = user32.GetWindowThreadProcessId(wintypes.HWND(fg_hwnd), None) if fg_hwnd else 0

        attached_fg = False
        attached_target = False
        try:
            if fg_tid and fg_tid != cur_tid:
                attached_fg = bool(user32.AttachThreadInput(cur_tid, fg_tid, True))
            if target_tid and target_tid != cur_tid:
                attached_target = bool(user32.AttachThreadInput(cur_tid, target_tid, True))

            user32.BringWindowToTop(wintypes.HWND(hwnd))
            user32.SetForegroundWindow(wintypes.HWND(hwnd))
            user32.SetActiveWindow(wintypes.HWND(hwnd))
        finally:
            if attached_target:
                user32.AttachThreadInput(cur_tid, target_tid, False)
            if attached_fg:
                user32.AttachThreadInput(cur_tid, fg_tid, False)

        return bool(user32.GetForegroundWindow() == hwnd)
    except Exception:
        return False