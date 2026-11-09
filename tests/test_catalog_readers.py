"""Test reader sinh tu UI_CATALOG (42 dump that) — PYTHONPATH=src python tests/test_catalog_readers.py

Moi test dung fixture la dump THAT, khong bam client.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.eye import Eye  # noqa: E402
from fila_bot.agent import AgentEye  # noqa: E402
from fila_bot.inventory import InventoryEye  # noqa: E402

FX = ROOT / "tests" / "fixtures"


def ok(n):
    print(f"[PASS] {n}")


def E(name):
    e = Eye.__new__(Eye)
    for k in ("root", "_pos", "_pos_root"):
        setattr(e, k, None)
    e.root = json.load(open(FX / name, encoding="utf-8"))
    return e


# 1. MessageBox 'Connection Lost' (g7_after_manual_180231) -> E-STOP
e = E("ui_tree_connection_lost.json")
assert e.connection_lost() is True
mb = e.message_boxes()
assert len(mb) == 1 and "Connection Lost" in mb[0]["texts"], mb
assert any(b["name"] == "ok_dialog_button" and b["text"] == "Quit" for b in mb[0]["buttons"])
ok("connection_lost: MessageBox modal 'Connection Lost' -> True, nut Quit nhan dien")

e = E("ui_tree_mission_accepted.json")
assert e.connection_lost() is False and e.message_boxes() == []
ok("connection_lost: khong co MessageBox -> False")

# 2. SelectedItemButton theo _name selectedItem<Action>
sel = E("ui_tree_selected_dock.json").selected_item_buttons()
assert sel.get("dock") == (914, 148) and "jump" not in sel, sel
ok("selected_item_buttons: tram -> dock (914,148), khong co jump")
sel = E("ui_tree_selected_jump.json").selected_item_buttons()
assert sel.get("jump") == (914, 148) and "dock" not in sel, sel
assert sel.get("warpto") == (878, 148)
ok("selected_item_buttons: stargate -> jump (914,148), warpto (878,148)")
assert E("ui_tree_route_set.json").selected_item_buttons() == {}
ok("selected_item_buttons: khong co SelectedItemWnd -> {}")

# 3. Nut agent theo Button._name (Complete/Quit/Close)
o = AgentEye(E("ui_tree_agent_complete.json")).read_offer()
assert o["title"] == "Rancorous Researcher (1 of 5)"
b = o["buttons"]
assert b["complete"] == (424, 808) and b["quit"] == (568, 808) and b["close"] == (712, 808), b
assert b["accept"] is None and b["decline"] is None
ok("agent da accept: CompleteMission/QuitMission/CloseAgentConversation theo _name")
b = AgentEye(E("ui_tree_agent_offer.json")).read_offer()["buttons"]
assert b["accept"] == (503, 808) and b["complete"] is None and b["quit"] is None, b
ok("agent offer: chi Accept/Decline/Defer, khong co Complete")

# 4. Cay hangar inventory
ie = InventoryEye(E("ui_tree_inventory_cargo.json"))
names = [x["name"] for x in ie.tree_entries()]
assert names == ["ShipHangar", "ShipDroneBay", "StationShips", "ItemHangar",
                 "StationCorpDeliveries", "CorporationItemDeliveries"], names
assert ie.tree_entry_xy("ItemHangar") == (162, 472)
assert ie.tree_entry_xy("ShipHangar") == (162, 392)
assert ie.tree_entry_xy("Nope") is None
ok("tree_entries: 6 hangar, ItemHangar (162,472), ShipHangar (162,392)")
assert InventoryEye(E("ui_tree_mission_accepted.json")).tree_entries() is None
ok("tree_entries: khong co inventory window -> None")
