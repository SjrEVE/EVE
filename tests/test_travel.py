"""Test travel.py (M2) — PYTHONPATH=src python tests/test_travel.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fila_bot.travel import NO_ROUTE_DEBOUNCE, TravelTo, pick_menu_entry  # noqa: E402


def ok(n):
    print(f"[PASS] {n}")


def w(system="A", markers=((10, 10),), menu=(), warping=False, docked=False, panel=True):
    return {"system": system, "station": None, "docked": docked, "markers": list(markers),
            "warping": warping, "menu": list(menu), "route_panel": panel}


# 1. ưu tiên dock trước jump
assert pick_menu_entry([("Jump", 1), ("Dock", 2)]) == ("Dock", 2)
assert pick_menu_entry([("Warp to Within", 1), ("Jump", 3)]) == ("Jump", 3)
assert pick_menu_entry([("Warp to Within", 1)]) is None
ok("menu: dock > jump, không có thì None")

# 2. không menu → mở menu trên marker đầu; menu hiện → bấm jump
t = TravelTo()
a = t.tick(w(markers=[(5, 6), (9, 9)]), 0)
assert a[0]["do"] == "open_menu" and a[0]["at"] == (5, 6)
a = t.tick(w(), 0.5)
assert a[0]["do"] == "wait"
a = t.tick(w(menu=[("Jump", (50, 60))]), 1.5)
assert a[0] == {"do": "menu_entry", "text": "Jump", "at": (50, 60)}
ok("marker đầu → open_menu → chọn Jump")

# 3. đang warp → chờ, không bấm
assert t.tick(w(warping=True), 3)[0]["do"] == "wait"
ok("warping → wait")

# 4. system đổi → jumps += 1
t.tick(w(system="B", warping=True), 10)
assert t.jumps == 1
ok("jump đếm khi tên system đổi")

# 5. marker mất lẻ tẻ không kết luận hết route
t = TravelTo()
t.tick(w(), 0)
for i in range(NO_ROUTE_DEBOUNCE):
    a = t.tick(w(markers=()), 1 + i)
    assert a[0]["do"] == "wait" and t.state != "ARRIVED"
a = t.tick(w(markers=()), 10)
assert a[0]["do"] == "arrived" and t.state == "ARRIVED"
ok("debounce >3 lần không marker mới ARRIVED")

# 6. dock xong (ShipUI mất, route hết) → ARRIVED
t = TravelTo()
t.tick(w(), 0)
a = t.tick(w(markers=(), docked=True), 5)
assert a[0]["do"] == "arrived"
ok("docked + hết route → ARRIVED")

# 7. đang dock không có route → BLOCKED
t = TravelTo()
assert t.tick(w(markers=(), docked=True), 0)[0]["do"] == "blocked"
ok("dock không route → BLOCKED")

# 8. menu không có dock/jump → BLOCKED
t = TravelTo()
t.tick(w(), 0)
from fila_bot.travel import AFTER_CLICK_S, MENU_RETRY  # noqa: E402
for _i in range(MENU_RETRY):
    _a = t.tick(w(menu=[("Look At", (1, 1))]), 1 + _i)
    assert _a[0]["do"] == "dismiss_menu", _a
assert t.tick(w(menu=[("Look At", (1, 1))]), 10)[0]["do"] == "blocked"
ok("menu sai → đóng + thử lại MENU_RETRY lần rồi BLOCKED, không bấm mù")

# 8b. G6 regression: menu cũ còn sau khi bấm Dock → KHÔNG bấm lại (log thật spam 17 lần)
t = TravelTo()
t.tick(w(), 0)
assert t.tick(w(menu=[("Dock", (222, 301))]), 1)[0]["do"] == "menu_entry"
assert t.tick(w(menu=[("Dock", (222, 301))]), 2)[0]["do"] == "dismiss_menu"
for _s in (3, 4, 5):
    assert t.tick(w(menu=[("Dock", (222, 301))]), _s)[0]["do"] == "wait"
assert t.tick(w(), 1 + AFTER_CLICK_S + 0.1)[0]["do"] == "open_menu"
ok("sau click Dock: đóng menu cũ 1 lần, chờ, không spam")

# 9. không tiến triển quá lâu → BLOCKED
t = TravelTo()
t.tick(w(), 0)
t.tick(w(), 7)
assert t.tick(w(), 200)[0]["do"] == "blocked"
ok("90s không tiến triển → BLOCKED")

# 10. không có panel Route → BLOCKED
t = TravelTo()
assert t.tick(w(markers=(), panel=False), 0)[0]["do"] == "blocked"
ok("không InfoPanelRoute → BLOCKED")

print("ALL OK test_travel")
