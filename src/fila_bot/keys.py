"""VK codes + Hardware Scan-Code mapper — chuẩn Windows (dùng chung cho input).

Nguồn: Win32 API chuẩn; merge 2026-11-10: thêm MapVirtualKeyW scan-code (DirectX/
Carbon UI hay nuốt phím giữ Q/W/E/D/S/Ctrl khi bScan=0) + bảng scan-code dự phòng
cho môi trường không phải Windows + alias D0..D9 cho type_text.
"""
from __future__ import annotations
import ctypes

VK_SHIFT: int = 0x10
VK_CONTROL: int = 0x11
VK_MENU: int = 0x12          # Alt

KEY: dict[str, int] = {
    "SHIFT": VK_SHIFT,
    "CTRL": VK_CONTROL,
    "CONTROL": VK_CONTROL,
    "ALT": VK_MENU,
    "MENU": VK_MENU,
    "BACKSPACE": 0x08,
    "TAB": 0x09,
    "ENTER": 0x0D,
    "RETURN": 0x0D,
    "ESC": 0x1B,
    "ESCAPE": 0x1B,
    "SPACE": 0x20,
    "LEFT": 0x25,
    "UP": 0x26,
    "RIGHT": 0x27,
    "DOWN": 0x28,
}

# Function keys F1..F12 (0x70..0x7B)
for _i in range(1, 13):
    KEY[f"F{_i}"] = 0x70 + (_i - 1)

# Digits 0..9 + alias D0..D9 (type_text gõ số qua "D5"...)
for _d in range(10):
    KEY[str(_d)] = 0x30 + _d
    KEY[f"D{_d}"] = 0x30 + _d

# Chữ A..Z (0x41..0x5A)
for _c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    KEY[_c] = ord(_c)

# Bảng scan-code US QWERTY dự phòng khi chạy ngoài Windows (test)
_FALLBACK_SCANCODES: dict[int, int] = {
    VK_SHIFT: 0x2A,
    VK_CONTROL: 0x1D,
    VK_MENU: 0x38,
    0x0D: 0x1C,  # ENTER
    0x1B: 0x01,  # ESC
    0x20: 0x39,  # SPACE
    0x70: 0x3B,  # F1
    0x71: 0x3C,  # F2
    0x72: 0x3D,  # F3
    0x73: 0x3E,  # F4
    0x74: 0x3F,  # F5
    0x75: 0x40,  # F6
    0x76: 0x41,  # F7
    0x77: 0x42,  # F8
    ord("Q"): 0x10,
    ord("W"): 0x11,
    ord("E"): 0x12,
    ord("R"): 0x13,
    ord("A"): 0x1E,
    ord("S"): 0x1F,
    ord("D"): 0x20,
    ord("F"): 0x21,
}


def resolve_vk(key_name: str) -> int:
    """Tên phím/ký tự → Windows Virtual-Key code."""
    k = str(key_name).strip().upper()
    if k in KEY:
        return KEY[k]
    if len(k) == 1:
        return ord(k)
    raise ValueError(f"Unknown key name: {key_name!r}")


def vk_to_scancode(vk: int) -> int:
    """VK → hardware scan code qua MapVirtualKeyW (DirectX nhận trạng thái giữ phím)."""
    if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "user32"):
        try:
            sc = int(ctypes.windll.user32.MapVirtualKeyW(int(vk), 0))
            if sc > 0:
                return sc
        except Exception:      # noqa: BLE001 — Windows cũ/fake rơi về bảng dự phòng
            pass
    return _FALLBACK_SCANCODES.get(int(vk), 0)
