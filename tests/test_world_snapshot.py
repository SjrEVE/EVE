"""Test WorldSnapshot — parse 1 lan tren cac fixture dump that.
PYTHONPATH=src python tests/test_world_snapshot.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.eye import Eye  # noqa: E402
from fila_bot.world_snapshot import parse_world  # noqa: E402

FX = ROOT / "tests" / "fixtures"


def ok(n):
    print(f"[PASS] {n}")


def make_eye(fixture_name: str) -> Eye:
    e = Eye.__new__(Eye)
    for k in ("root", "_pos", "_pos_root"):
        setattr(e, k, None)
    e.root = json.load(open(FX / fixture_name, encoding="utf-8"))
    return e


# 1. Connection Lost
w = parse_world(make_eye("ui_tree_connection_lost.json"))
assert w.connection_lost is True
assert len(w.message_boxes) == 1
ok("snapshot connection_lost = True khi co modal Connection Lost")

# 2. Agent Offer
w = parse_world(make_eye("ui_tree_agent_offer.json"))
assert w.connection_lost is False
assert w.agent_dialog.open is True
assert w.agent_dialog.title == "Rancorous Researcher (1 of 5)"
assert "accept" in w.agent_dialog.buttons
assert "decline" in w.agent_dialog.buttons
assert w.agent_dialog.pickup_link_xy == (939, 317)
assert w.agent_dialog.dropoff_link_xy == (935, 371)
ok("snapshot agent_dialog: title, buttons (accept/decline), pickup/dropoff links dung")

# 3. Agent Completed dialog
w = parse_world(make_eye("ui_tree_agent_complete.json"))
assert w.agent_dialog.open is True
assert "complete" in w.agent_dialog.buttons
assert "accept" not in w.agent_dialog.buttons
ok("snapshot agent_dialog complete: nut complete (424,808) co san")

# 4. Inventory Window
w = parse_world(make_eye("ui_tree_inventory_cargo.json"))
assert w.inventory.open is True
assert "ItemHangar" in w.inventory.hangars
assert "ShipHangar" in w.inventory.hangars
assert w.inventory.capacity == {"used": 0.0, "max": 932.7, "selected": None}
ok("snapshot inventory: open, hangars (ItemHangar/ShipHangar), capacity dung")

# 5. Space & Selected Item Buttons (Dock / Jump)
w = parse_world(make_eye("ui_tree_selected_dock.json"))
assert w.docked is False
assert "dock" in w.selected_buttons
assert "jump" not in w.selected_buttons
ok("snapshot space: docked=False, selected_buttons has 'dock'")

w = parse_world(make_eye("ui_tree_selected_jump.json"))
assert w.docked is False
assert "jump" in w.selected_buttons
assert "warpto" in w.selected_buttons
ok("snapshot space: selected_buttons has 'jump' and 'warpto'")

print("\nALL OK test_world_snapshot")
