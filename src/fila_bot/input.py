"""Input shim — chuột/phím với humanize + dry-run cho test.

FC (LLM) KHÔNG bao giờ gọi trực tiếp module này — chỉ reflex/control của bot dùng
(đúng kiến trúc Boss chốt: LLM ra lệnh chữ, không click).

Merge 2026-11-10 (Auto-Control Layer):
  - keybd_event gửi HARDWARE SCAN-CODE (MapVirtualKeyW) — DirectX/Carbon UI hay nuốt
    phím giữ Q/W/E/D/S/Ctrl khi bScan=0 (P0-3 lock Ctrl+click từng hụt vì lỗi này)
  - move_cursor_smooth: quỹ đạo chuột Cubic-Bezier + minimum-jerk, không teleport 0ms
    (Carbon UI cần OnMouseEnter trước khi click, nhất là submenu)
  - hover-settle trước khi hạ click; drag có mồi ngưỡng >10px rồi mới lướt
  - INPUT_LOCK (multibox: chuỗi ctrl_down→click→ctrl_up không bị thread khác chen)
  - _ACTIVE_HOLDS: theo dõi phím đang giữ — release_all nhả sạch, không kẹt phím
  - humanized_delay = lognormal (không phải uniform) + jitter_xy Gaussian 2 chiều

GIỮ NGUYÊN API cũ (contract test + control.py): send_click/send_right_click/send_key/
hover/type_text/send_key_click/send_drag/send_combo/release_all/kill_switch_pressed.
LƯU Ý an toàn: humanized_delay thuần tính toán, KHÔNG raise — kill-switch do
Supervisor poll mỗi tick; raise giữa click-down→click-up sẽ kẹt chuột giữ.
"""
from __future__ import annotations

import ctypes
import math
import random
import threading
import time
from typing import Any, Iterable

from .keys import KEY, VK_CONTROL, VK_MENU, VK_SHIFT
from . import keys as keys_mod

_DELAY_BASE = 0.08  # giây giữa các bước input khi humanize

KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP = 0x0002, 0x0004
MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP = 0x0008, 0x0010

INPUT_LOCK = threading.RLock()
_ACTIVE_HOLDS: set[int] = set()

# P2-4: kill-switch — Ctrl+Shift+Space, poll bằng GetAsyncKeyState (không cài hook
# toàn cục, không cần quyền admin). Test truyền get_async giả.
VK_CONTROL_L, VK_SHIFT_L, VK_SPACE_ = 0x11, 0x10, 0x20


def kill_switch_pressed(get_async: Any = None) -> bool:
    """True khi Ctrl+Shift+Space đang được giữ (poll mỗi tick)."""
    if get_async is None:
        import ctypes
        get_async = ctypes.windll.user32.GetAsyncKeyState

    def down(vk: int) -> bool:
        return bool(get_async(vk) & 0x8000)

    return down(VK_CONTROL_L) and down(VK_SHIFT_L) and down(VK_SPACE_)


def humanized_delay(base: float = _DELAY_BASE) -> float:
    """Trễ kiểu sinh học: lognormal (median 1.0, sigma 0.14) kẹp [0.75, 1.45]×base.

    Thay phân phối đều cũ (dễ bị nhận diện bằng chuỗi thời gian uniform). Thuần
    tính toán — KHÔNG đụng kill-switch ở đây (xem docstring module).
    """
    factor = random.lognormvariate(0.0, 0.14)
    return base * max(0.75, min(1.45, factor))


def jitter_xy(x: int, y: int, sigma_px: float = 2.2, max_offset_px: int = 5) -> tuple[int, int]:
    """Lệch tọa độ click theo Gaussian 2 chiều quanh tâm nút — chống click trùng
    khít tọa độ tuyệt đối. Chỉ áp cho click THẬT; dry-run giữ tọa độ chính xác."""
    dx = int(round(max(-max_offset_px, min(max_offset_px, random.gauss(0.0, sigma_px)))))
    dy = int(round(max(-max_offset_px, min(max_offset_px, random.gauss(0.0, sigma_px)))))
    return (int(x) + dx, int(y) + dy)


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def _get_cursor_pos() -> tuple[int, int]:
    if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "user32"):
        pt = _POINT(0, 0)
        if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
            return (int(pt.x), int(pt.y))
    return (0, 0)


def move_cursor_smooth(target_x: int, target_y: int, dry_run: bool = False,
                       humanize: bool = True) -> tuple[int, int]:
    """Di chuột theo cung Cubic-Bezier + minimum-jerk (10t³-15t⁴+6t⁵) — không teleport.

    Số micro-step scale theo khoảng cách (Fitts). dry_run hoặc không humanize → đặt
    thẳng đích (test deterministic). Trả toạ độ đích."""
    if dry_run or not (hasattr(ctypes, "windll") and hasattr(ctypes.windll, "user32")):
        return (int(target_x), int(target_y))
    user32 = ctypes.windll.user32
    if not humanize:
        user32.SetCursorPos(int(target_x), int(target_y))
        return (int(target_x), int(target_y))
    start_x, start_y = _get_cursor_pos()
    dist = math.hypot(target_x - start_x, target_y - start_y)
    if dist < 6.0:
        user32.SetCursorPos(int(target_x), int(target_y))
        return (int(target_x), int(target_y))
    n_steps = max(5, min(14, int(dist / 90.0) + 5))
    arc = min(35.0, dist * 0.12)
    c1x = start_x + (target_x - start_x) * 0.33 + random.uniform(-arc, arc)
    c1y = start_y + (target_y - start_y) * 0.33 + random.uniform(-arc, arc)
    c2x = start_x + (target_x - start_x) * 0.66 + random.uniform(-arc / 2, arc / 2)
    c2y = start_y + (target_y - start_y) * 0.66 + random.uniform(-arc / 2, arc / 2)
    for i in range(1, n_steps + 1):
        t = i / n_steps
        u = t * t * t * (10.0 + t * (-15.0 + 6.0 * t))
        inv = 1.0 - u
        bx = (inv ** 3) * start_x + 3 * (inv ** 2) * u * c1x + 3 * inv * (u ** 2) * c2x + (u ** 3) * target_x
        by = (inv ** 3) * start_y + 3 * (inv ** 2) * u * c1y + 3 * inv * (u ** 2) * c2y + (u ** 3) * target_y
        user32.SetCursorPos(int(round(bx)), int(round(by)))
        time.sleep(0.004)
    user32.SetCursorPos(int(target_x), int(target_y))
    return (int(target_x), int(target_y))


def _hw_key_event(vk: int, is_up: bool = False, user32: Any = None) -> None:
    """keybd_event với hardware scan-code (DirectX nhận trạng thái giữ phím)."""
    api = user32
    if api is None and hasattr(ctypes, "windll") and hasattr(ctypes.windll, "user32"):
        api = ctypes.windll.user32
    if api is None:
        return
    sc = keys_mod.vk_to_scancode(vk)
    flags = KEYEVENTF_KEYUP if is_up else 0
    api.keybd_event(int(vk), int(sc), int(flags), 0)
    if is_up:
        _ACTIVE_HOLDS.discard(int(vk))
    else:
        _ACTIVE_HOLDS.add(int(vk))


# M0: E-STOP / PAUSE / crash phải NHẢ mọi phím đang giữ (lock = giữ Ctrl → kẹt Ctrl nếu dừng giữa chừng).
_RELEASE_KEYS = (("ctrl", 0x11), ("shift", 0x10), ("alt", 0x12))
_RELEASE_MOUSE = (("lmb", 0x01, 0x0004), ("rmb", 0x02, 0x0010))  # (tên, VK, MOUSEEVENTF_*UP)


def release_all(dry_run: bool = False, user32: Any = None) -> dict[str, Any]:
    """Nhả Ctrl/Shift/Alt + chuột trái/phải NẾU đang bị giữ (GetAsyncKeyState +
    sổ _ACTIVE_HOLDS). Chỉ gửi key-up cho phím đang down — không bắn sự kiện thừa
    vào game. `user32` inject được để test không cần Windows."""
    if dry_run:
        _ACTIVE_HOLDS.clear()
        return {"ok": True, "released": [], "dry": True}
    if user32 is None:
        user32 = ctypes.windll.user32
    released: list[str] = []
    held_vks = set(_ACTIVE_HOLDS)
    for name, vk in _RELEASE_KEYS:
        if vk in held_vks or user32.GetAsyncKeyState(vk) & 0x8000:
            _hw_key_event(vk, is_up=True, user32=user32)
            released.append(name)
    for name, vk, up in _RELEASE_MOUSE:
        if user32.GetAsyncKeyState(vk) & 0x8000:
            user32.mouse_event(up, 0, 0, 0, 0)
            released.append(name)
    _ACTIVE_HOLDS.clear()
    return {"ok": True, "released": released, "dry": False}


def send_click(x: int, y: int, dry_run: bool = False, humanize: bool = True,
               button: str = "left") -> dict[str, Any]:
    """Chuột trái/phải tại (x,y): bezier move → hover-settle → click.
    Dry-run giữ tọa độ chính xác, không bấm."""
    if dry_run:
        base = {"ok": True, "x": int(x), "y": int(y), "dry": True}
        if str(button).lower() == "right":
            base["button"] = "right"
        return base
    if humanize:
        x, y = jitter_xy(int(x), int(y))
    with INPUT_LOCK:
        move_cursor_smooth(int(x), int(y), humanize=humanize)
        if humanize:
            time.sleep(humanized_delay(0.04))   # hover-settle: Carbon UI cần OnMouseEnter
        btn = str(button).lower()
        down = MOUSEEVENTF_RIGHTDOWN if btn == "right" else MOUSEEVENTF_LEFTDOWN
        up = MOUSEEVENTF_RIGHTUP if btn == "right" else MOUSEEVENTF_LEFTUP
        ctypes.windll.user32.mouse_event(down, 0, 0, 0, 0)
        time.sleep(humanized_delay(0.02))
        ctypes.windll.user32.mouse_event(up, 0, 0, 0, 0)
    out = {"ok": True, "x": int(x), "y": int(y), "dry": False}
    if btn == "right":
        out["button"] = "right"
    return out


def send_right_click(x: int, y: int, dry_run: bool = False, humanize: bool = True) -> dict[str, Any]:
    """Chuột phải tại (x,y) — mở context menu. Ground 2026-11-09: dùng cho warp/dock/menu."""
    return send_click(x, y, dry_run=dry_run, humanize=humanize, button="right")


def send_key(code: int, dry_run: bool = False, humanize: bool = True) -> dict[str, Any]:
    """1 phím đơn không modifier (giữ cho tương thích)."""
    if dry_run:
        return {"ok": True, "code": code, "dry": True}
    with INPUT_LOCK:
        _hw_key_event(int(code), is_up=False, user32=ctypes.windll.user32)
        time.sleep(humanized_delay(0.02))
        _hw_key_event(int(code), is_up=True, user32=ctypes.windll.user32)
    return {"ok": True, "code": code, "dry": False}


def hover(x: int, y: int, dry_run: bool = False) -> dict[str, Any]:
    """Đưa chuột tới (x,y) KHÔNG click — dùng để mở submenu (ground 2026-11-09:
    context menu nhiều cấp chỉ bung khi hover, click sẽ chọn luôn entry cấp 1)."""
    if dry_run:
        return {"ok": True, "x": int(x), "y": int(y), "hover": True, "dry": True}
    ctypes.windll.user32.SetCursorPos(int(x), int(y))
    return {"ok": True, "x": int(x), "y": int(y), "hover": True, "dry": False}


def send_hover(x: int, y: int, dwell_s: float = 0.28, dry_run: bool = False,
               humanize: bool = True) -> dict[str, Any]:
    """Hover mượt (bezier) + đứng yên dwell_s để submenu bung ra — dùng cho
    act_submenu_select; giống hover() nhưng có dwell đo được."""
    if dry_run:
        return {"ok": True, "x": int(x), "y": int(y), "hover": True, "dwell_s": dwell_s,
                "dry": True}
    move_cursor_smooth(int(x), int(y), humanize=humanize)
    time.sleep(max(0.05, float(dwell_s)))
    return {"ok": True, "x": int(x), "y": int(y), "hover": True, "dwell_s": dwell_s,
            "dry": False}


def type_text(text: str, dry_run: bool = False, humanize: bool = True) -> dict[str, Any]:
    """Gõ chuỗi số/chữ (dialog orbit/keep distance). Chỉ digit + chữ không dấu."""
    if dry_run:
        return {"ok": True, "typed": text, "dry": True}
    for ch in text:
        if ch.isdigit():
            send_combo((), f"D{ch}", dry_run=False, humanize=humanize)
        elif ch.upper() in KEY:
            mods = ("shift",) if ch.isupper() else ()
            send_combo(mods, ch.upper(), dry_run=False, humanize=humanize)
        if humanize:
            time.sleep(humanized_delay(0.05))
    return {"ok": True, "typed": text, "dry": False}


def send_type(text: str, dry_run: bool = False, humanize: bool = True) -> dict[str, Any]:
    """Alias của type_text — tên gọi thống nhất với control layer mới."""
    return type_text(text, dry_run=dry_run, humanize=humanize)


def send_combo(mods: Iterable[str], key: str, dry_run: bool = False,
               humanize: bool = True) -> dict[str, Any]:
    """Bấm tổ hợp: giữ mods → nhấn key → nhả theo thứ tự ngược (scan-code + INPUT_LOCK;
    nhả mods trong finally — exception giữa chừng không kẹt Ctrl).
    mods: tập con của {'ctrl','alt','shift'}. key: 'F1'..'F8', 'Q'..'Z', 'SPACE'..."""
    mod_vk = {"ctrl": VK_CONTROL, "alt": VK_MENU, "shift": VK_SHIFT}
    kv = KEY[key]
    combo_label = "+".join(list(mods) + [key])
    if dry_run:
        return {"ok": True, "combo": combo_label, "dry": True}
    user32 = ctypes.windll.user32
    down = [mod_vk[m] for m in mods]
    with INPUT_LOCK:
        try:
            for vk in down:
                _hw_key_event(vk, is_up=False, user32=user32)
            if humanize:
                time.sleep(humanized_delay(0.03))
            _hw_key_event(kv, is_up=False, user32=user32)
            time.sleep(humanized_delay(0.02))
            _hw_key_event(kv, is_up=True, user32=user32)
        finally:
            for vk in reversed(down):
                _hw_key_event(vk, is_up=True, user32=user32)
    return {"ok": True, "combo": combo_label, "dry": False}


def send_hold(hold_token: str, dry_run: bool = False, humanize: bool = True) -> dict[str, Any]:
    """Giữ/nhả 1 phím ('ctrl_down'/'ctrl_up'/'shift_down'.../w/e/q/s/d) — dùng cho
    chuỗi Ctrl+click lock: modifier phải là hold steps, KHÔNG phải combo (skill)."""
    tok = str(hold_token).strip().lower()
    is_up = tok.endswith("_up")
    base_key = tok.replace("_down", "").replace("_up", "")
    vk = keys_mod.resolve_vk(base_key)
    if not dry_run:
        with INPUT_LOCK:
            _hw_key_event(vk, is_up=is_up, user32=ctypes.windll.user32)
            if humanize:
                time.sleep(humanized_delay(0.035))
    return {"ok": True, "hold": hold_token, "vk": vk, "dry_run": dry_run}


def send_key_click(key: str, x: int, y: int, dry_run: bool = False,
                   humanize: bool = True) -> dict[str, Any]:
    """Giữ phím (vd 'D' cho Dock/Jump, 'S' cho Warp) + click chuột trái tại (x,y) -> nhả phím.
    Thao tác native 1-hit của EVE, thay thế hoàn toàn context menu."""
    if dry_run:
        return {"ok": True, "key": key, "x": int(x), "y": int(y), "dry": True}
    if humanize:
        x, y = jitter_xy(int(x), int(y))
    user32 = ctypes.windll.user32
    kv = KEY[key]
    with INPUT_LOCK:
        move_cursor_smooth(int(x), int(y), humanize=humanize)
        if humanize:
            time.sleep(humanized_delay(0.04))
        _hw_key_event(kv, is_up=False, user32=user32)
        time.sleep(humanized_delay(0.03))
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(humanized_delay(0.03))
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(humanized_delay(0.03))
        _hw_key_event(kv, is_up=True, user32=user32)
    return {"ok": True, "key": key, "x": int(x), "y": int(y), "dry": False}


def send_drag(from_xy: tuple[int, int], to_xy: tuple[int, int], dry_run: bool = False,
              humanize: bool = True) -> dict[str, Any]:
    """Kéo thả chuột trái từ from_xy sang to_xy. Dùng cho chuyển hàng giữa các hangar.
    Merge 2026-11-10: nhích >10px đầu tay để Carbon UI kích drag proxy, lướt bezier,
    dừng 90ms cho ô đích sáng lên rồi mới nhả."""
    fx, fy = from_xy
    tx, ty = to_xy
    if dry_run:
        return {"ok": True, "from": (int(fx), int(fy)), "to": (int(tx), int(ty)), "dry": True}
    user32 = ctypes.windll.user32
    with INPUT_LOCK:
        move_cursor_smooth(int(fx), int(fy), humanize=humanize)
        if humanize:
            time.sleep(humanized_delay(0.05))
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(humanized_delay(0.08))
        # mồi ngưỡng kéo: nhích nhẹ >10px để game nhận drag gesture
        user32.SetCursorPos(int(fx) + 12, int(fy) + 6)
        time.sleep(0.05)
        move_cursor_smooth(int(tx), int(ty), humanize=humanize)
        time.sleep(0.09)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.05)
    return {"ok": True, "from": (int(fx), int(fy)), "to": (int(tx), int(ty)), "dry": False}
