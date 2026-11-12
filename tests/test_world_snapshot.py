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

# 6. Live mission knowledge is three-valued: detected list, confirmed empty, or unknown.
w = parse_world(make_eye("ui_tree_mission_accepted.json"))
assert w.active_missions == ["Rancorous Researcher (1 of 5)"]
assert w.mission_panel_observed is True
ok("snapshot exposes active mission titles from the live Job Board")

w = parse_world(make_eye("ui_tree_mission_docked.json"))
assert w.active_missions is None
assert w.mission_panel_observed is False
assert w.location_state == "DOCKED"
ok("missing Job Board is UNKNOWN, not falsely reported as no mission")

# 7. Agent list and the station's explicitly Active ship card are surfaced.
w = parse_world(make_eye("ui_tree_agents_panel.json"))
assert w.agents_known is True
assert w.agents[0]["name"] == "Iji Kiyura"
assert w.agents[0]["level"] == 1 and w.agents[0]["division"] == "Distribution"
ok("snapshot exposes live agent name, level, division, and availability")

w = parse_world(make_eye("ui_tree_station_menu.json"))
assert w.active_ship == {"name": "Amarr Shuttle - Oksora Aivo", "hull": "Amarr Shuttle"}
ok("snapshot reads the Active ship card, not the Board-my button")

print("\nALL OK test_world_snapshot")
