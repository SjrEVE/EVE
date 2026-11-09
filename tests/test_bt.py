"""Test Behavior Tree — cay uu tien sinh ton > hanh dong cho Abyss.
PYTHONPATH=src python tests/test_bt.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.bt import Node, Status, act, cond, par, sel, seq  # noqa: E402
from fila_bot.bt_abyss import build_abyss_tree, tick_tree  # noqa: E402


def ok(n):
    print(f"[PASS] {n}")


# 1. Selector ưu tiên: node SUCCESS đầu tiên thắng
hits = []
tree = sel("root", [
    cond("a_false", lambda c: (hits.append("a") or Status.FAILURE)),
    cond("b_true", lambda c: (hits.append("b") or Status.SUCCESS)),
    cond("c_true", lambda c: (hits.append("c") or Status.SUCCESS)),
])
assert tree.tick({}) == Status.SUCCESS and hits == ["a", "b"]
ok("Selector: node SUCCESS dau tien thang, khong tick node sau")

# 2. Sequence: 1 node FAILURE -> cả sequence FAILURE
hits.clear()
tree = seq("root", [
    cond("a_true", lambda c: Status.SUCCESS),
    cond("b_false", lambda c: Status.FAILURE),
    act("c_never", lambda c: (hits.append("c") or Status.SUCCESS)),
])
assert tree.tick({}) == Status.FAILURE and hits == []
ok("Sequence: 1 dieu kien FAIL -> ca nhanh FAIL, action khong chay")

# 3. Parallel: chay ca 2 nhanh
hits.clear()
tree = par("root", [
    act("x", lambda c: (hits.append("x") or Status.SUCCESS)),
    act("y", lambda c: (hits.append("y") or Status.SUCCESS)),
])
assert tree.tick({}) == Status.SUCCESS and set(hits) == {"x", "y"}
ok("Parallel: chay TAT CA nhanh con (safety song song mission)")

# 4. ABYSS TREE: binh thuong docked co filament -> undock
tree = build_abyss_tree()
acts = tick_tree(tree, {"docked": True, "filaments": 2, "phase": "DOCKED"})
assert acts == [{"do": "undock"}], acts
ok("Abyss BT: docked + co filament -> undock (khong co action safety nao)")

# 5. SAFETY uu tien: hp thấp + docked -> SURVIVAL chay truoc, mission van tiep sau
# (thiet ke Parallel: safety KHONG chan mission, chi uu tien thu tu trong list actions)
acts = tick_tree(tree, {"docked": True, "filaments": 2, "phase": "DOCKED", "hp": 0.2})
assert acts[0] == {"do": "survival"} and acts[1] == {"do": "undock"}, acts
ok("Abyss BT: hp<30% SURVIVAL duoc flag TRUOC undock trong cung 1 tick (uu tien thu tu)")

# 6. Connection lost -> ESTOP duoc flag dau tien (uu tien cao nhat trong list actions)
acts = tick_tree(tree, {"docked": False, "filaments": 2, "phase": "ROOM1_FIGHT",
                        "hp": 0.1, "connection_lost": True})
assert acts[0] == {"do": "estop"}, acts
ok("Abyss BT: connection_lost -> E-STOP flag dau tien (executor uu tien xu ly E-STOP)")

# 7. Cap thấp -> power_save (flag dau, mission tiep theo)
acts = tick_tree(tree, {"docked": False, "filaments": 1, "phase": "ROOM2_FIGHT", "cap": 0.1})
assert acts[0] == {"do": "power_save"}, acts
ok("Abyss BT: cap<15% -> power_save flag dau tien")

# 8. Drone con ngoai + đang warp -> recall (flag dau)
acts = tick_tree(tree, {"docked": False, "filaments": 1, "phase": "ROOM1_FIGHT",
                        "drones_in_space": 2, "maneuver": "warp"})
assert acts[0] == {"do": "drones_return"}, acts
ok("Abyss BT: drone ngoai + warp -> recall flag dau tien (DEATH #3 guard)")

# 9. Mission flow: TRAVEL_ENTRY -> fila; FILA_SPOOL -> confirm; ROOM1_CLEARED -> gate
for phase, want in (("TRAVEL_ENTRY", "fila"), ("FILA_SPOOL", "confirm"),
                    ("ROOM1_CLEARED", "gate"), ("ROOM2_CLEARED", "gate")):
    acts = tick_tree(tree, {"docked": False, "filaments": 1, "phase": phase})
    assert acts == [{"do": want}], (phase, acts)
ok("Abyss BT: mission flow TRAVEL_ENTRY->fila, SPOOL->confirm, CLEARED->gate")

# 10. ROOM3_CLEARED -> warp_home, sau do WARP_HOME -> dock
acts = tick_tree(tree, {"docked": False, "filaments": 1, "phase": "ROOM3_CLEARED"})
assert acts == [{"do": "warp_home"}], acts
acts = tick_tree(tree, {"docked": False, "filaments": 1, "phase": "WARP_HOME"})
assert acts == [{"do": "dock"}], acts
ok("Abyss BT: ROOM3_CLEARED -> warp_home -> dock (hoan thanh run)")

# 11. Het filament -> khong undock (dung yen)
acts = tick_tree(tree, {"docked": True, "filaments": 0, "phase": "DOCKED"})
assert acts == [], acts
ok("Abyss BT: het filament -> khong undock, dung yen cho nguoi can thiep")

print("\nALL OK test_bt")
