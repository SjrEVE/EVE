"""VK codes — chuẩn Windows (dùng chung cho input). Nguồn: Win32 API chuẩn."""
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12          # Alt

KEY = {
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
    "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
    "SPACE": 0x20, "ENTER": 0x0D, "ESC": 0x1B, "R": 0x52,
    "D1": 0x31, "D2": 0x32, "D3": 0x33, "D4": 0x34,
    "D5": 0x35, "D6": 0x36, "D7": 0x37, "D8": 0x38, "D9": 0x39, "D0": 0x30,
}
for _c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    KEY[_c] = ord(_c)
