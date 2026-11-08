"""Input shim — chuột/phím với humanize (jitter) + dry-run cho test.

FC (LLM) KHÔNG bao giờ gọi trực tiếp module này — chỉ reflex/control của bot dùng
(đúng kiến trúc Boss chốt: LLM ra lệnh chữ, không click).
"""
from __future__ import annotations

import random
import time
from typing import Any, Iterable

from .keys import KEY, VK_CONTROL, VK_MENU, VK_SHIFT

_DELAY_BASE = 0.08  # giây giữa các bước input khi humanize


def humanized_delay(base: float = _DELAY_BASE) -> float:
    """±50% jitter quanh base — tránh nhịp máy móc đều."""
    return base * (0.5 + random.random())


def send_click(x: int, y: int, dry_run: bool = False, humanize: bool = True) -> dict[str, Any]:
    if dry_run:
        return {"ok": True, "x": x, "y": y, "dry": True}
    import ctypes

    user32 = ctypes.windll.user32
    user32.SetCursorPos(int(x), int(y))
    if humanize:
        time.sleep(humanized_delay())
    MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP = 0x0002, 0x0004
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(humanized_delay(0.02))
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    return {"ok": True, "x": x, "y": y, "dry": False}


def send_combo(mods: Iterable[str], key: str, dry_run: bool = False,
               humanize: bool = True) -> dict[str, Any]:
    """Bấm tổ hợp: giữ mods → nhấn key → nhả theo thứ tự ngược.
    mods: tập con của {'ctrl','alt','shift'}. key: 'F1'..'F8', 'Q'..'Z', 'SPACE'..."""
    mod_vk = {"ctrl": VK_CONTROL, "alt": VK_MENU, "shift": VK_SHIFT}
    kv = KEY[key]
    if dry_run:
        return {"ok": True, "combo": "+".join(list(mods) + [key]), "dry": True}
    import ctypes

    user32 = ctypes.windll.user32
    down = [mod_vk[m] for m in mods]
    for vk in down:
        user32.keybd_event(vk, 0, 0, 0)
    if humanize:
        time.sleep(humanized_delay(0.03))
    user32.keybd_event(kv, 0, 0, 0)
    time.sleep(humanized_delay(0.02))
    user32.keybd_event(kv, 0, 2, 0)  # KEYEVENTF_KEYUP
    for vk in reversed(down):
        user32.keybd_event(vk, 0, 2, 0)
    return {"ok": True, "combo": "+".join(list(mods) + [key]), "dry": False}


def send_key(code: int, dry_run: bool = False, humanize: bool = True) -> dict[str, Any]:
    """1 phím đơn không modifier (giữ cho tương thích)."""
    if dry_run:
        return {"ok": True, "code": code, "dry": True}
    import ctypes

    user32 = ctypes.windll.user32
    user32.keybd_event(code, 0, 0, 0)
    time.sleep(humanized_delay(0.02))
    user32.keybd_event(code, 0, 2, 0)  # KEYEVENTF_KEYUP
    return {"ok": True, "code": code, "dry": False}


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
