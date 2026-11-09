"""Test agent.py — PYTHONPATH=src python tests/test_agent.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fila_bot.agent import AgentEye, accept_rule  # noqa: E402


def ok(n):
    print(f"[PASS] {n}")


def node(t, text=None, children=(), xy=(0, 0)):
    return {"type": t, "attrs": {"_setText": text} if text else {}, "children": list(children), "xy": xy}


class FakeEye:
    def __init__(self, root):
        self.root = root

    def walk(self, n):
        yield n
        for c in n.get("children", []):
            yield from self.walk(c)

    def _find_by_type(self, t, select_many=True):
        return [n for n in self.walk(self.root) if n["type"] == t]

    def abs_center(self, n):
        return n.get("xy")


# 1. khong co cua so -> None / blocked
a = AgentEye(FakeEye(node("UIRoot")))
assert a.window() is None and a.texts() is None and a.read_offer() is None
assert a.button_xy("accept") is None
assert accept_rule(None, 400, True)[0] == "blocked"
ok("khong co AgentDialogueWindow -> None + blocked")

# 2. nut khop DUNG text; 'Accepted' khong phai 'Accept'; nut ngoai cua so bi bo qua
tree = node("UIRoot", children=[
    node("Button", "Accept", xy=(999, 999)),                       # ngoai cua so agent
    node("AgentDialogueWindow", children=[
        node("Label", "Courier mission: deliver 2.0 m3 of cargo"),
        node("Label", "Accepted missions: 0", xy=(5, 5)),
        node("Button", "<b>Accept</b>", xy=(100, 200)),
        node("Button", "Decline", xy=(150, 200)),
    ])])
a = AgentEye(FakeEye(tree))
assert a.button_xy("accept") == (100, 200), a.button_xy("accept")
assert a.button_xy("decline") == (150, 200)
assert a.button_xy("complete") is None and a.button_xy("bogus") is None
ok("nut khop dung text trong cua so agent, khong substring, khong ngoai cua so")

# 3. read_offer: loai + m3
o = a.read_offer()
assert o["type"] == "courier" and o["cargo_m3"] == 2.0, o
assert o["buttons"]["accept"] == (100, 200)
ok("read_offer: courier 2.0 m3")

# 4. encounter + khong doc duoc m3
t2 = node("UIRoot", children=[node("AgentDialogueWindow", children=[
    node("Label", "Encounter: The Blockade")])])
o2 = AgentEye(FakeEye(t2)).read_offer()
assert o2["type"] == "encounter" and o2["cargo_m3"] is None
ok("read_offer: encounter, cargo None")

# 5. accept_rule
assert accept_rule(o, 400, True)[0] == "accept"
assert accept_rule(o, 1.0, True)[0] == "decline"
assert accept_rule(o, 400, False)[0] == "decline"
assert accept_rule(o, 400, None)[0] == "blocked"
assert accept_rule(o, None, True)[0] == "blocked"
assert accept_rule(o2, 400, True)[0] == "decline"
assert accept_rule({"type": None}, 400, True)[0] == "blocked"
ok("accept_rule: accept / decline (cargo, lowsec, encounter) / blocked khi thieu du kien")

# 6. G1 GROUND: AgentsPanel tren dump client that (TQ 2026-11-09, Tunttaras)
import json  # noqa: E402
from fila_bot.agent import agents_panel, pick_agent  # noqa: E402
from fila_bot.eye import Eye  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures" / "ui_tree_agents_panel.json"
real = Eye.__new__(Eye)
real.root = json.loads(FIX.read_text(encoding="utf-8"))
ags = agents_panel(real)
assert ags is not None and len(ags) == 3, ags
by = {x["name"]: x for x in ags}
assert by["Iji Kiyura"]["level"] == 1 and by["Iji Kiyura"]["division"] == "Distribution"
assert by["Iji Kiyura"]["available"] is True and by["Iji Kiyura"]["chat_xy"] == (1258, 477)
assert by["Ashataalen Kaitsiras"]["level"] == 2 and by["Ashataalen Kaitsiras"]["available"] is False
assert by["Vaalemainen Suenen"]["level"] == 4 and by["Vaalemainen Suenen"]["available"] is False
ok("G1 ground: AgentsPanel 3 agent, level/division/available/chat_xy dung dump that")

assert pick_agent(ags, "Distribution")["name"] == "Iji Kiyura"
assert pick_agent(ags, "Security") is None
assert pick_agent(None, "Distribution") is None
assert agents_panel(FakeEye(node("UIRoot"))) is None
ok("pick_agent: chi agent kha dung + dung division; khong co panel -> None")

# 7. G2 GROUND: AgentDialogueWindow offer that (DLL 2c19958: Bunch htmlstr + PyChildrenList)
FIX2 = Path(__file__).resolve().parent / "fixtures" / "ui_tree_agent_offer.json"
real2 = Eye.__new__(Eye)
real2.root = json.loads(FIX2.read_text(encoding="utf-8"))
off = AgentEye(real2).read_offer()
assert off is not None and off["type"] == "courier", off and off["type"]
assert off["title"] == "Rancorous Researcher (1 of 5)" and off["chain"] == (1, 5), off["title"]
assert off["cargo_m3"] == 0.1 and off["cargo_qty"] == 1 and off["cargo_item"] == "Encoded Data Chip", off
assert off["pickup"] == {"sec": 0.8, "name": "Nourvukaiken VI - Moon 2 - State and Region Bank Depository"}, off["pickup"]
assert off["dropoff"] == {"sec": 0.9, "name": "Tunttaras IX - Moon 11 - Ytiri Storage"}, off["dropoff"]
assert 21000 in off["isk"], off["isk"]
ok("G2 ground: offer that -> courier, chain 1/5, 0.1 m3, pickup/dropoff + sec, 21k ISK")

b = off["buttons"]
assert b["accept"] == (503, 808) and b["decline"] == (594, 808) and b["delay"] == (685, 808), b
assert b["complete"] is None and b["request"] is None, b
assert accept_rule(off, 400, True)[0] == "accept"
ok("G2 ground: nut Accept/Decline/Delay theo Button._name; Complete chua co -> None")

# 8. G5 GROUND: link Pickup/Drop-off trong objective_browser (dump that g5_pickup_menu2_173144)
from fila_bot.agent import location_links  # noqa: E402

FIX3 = Path(__file__).resolve().parent / "fixtures" / "ui_tree_pickup_menu.json"
real3 = Eye.__new__(Eye)
for _k in ("root", "_pos", "_pos_root"):
    setattr(real3, _k, None)
real3.root = json.loads(FIX3.read_text(encoding="utf-8"))
ll = location_links(real3)
assert ll == {"pickup": (939, 317), "dropoff": (935, 371)}, ll
ok("G5 ground: location_links -> pickup (939,317) / dropoff (935,371) theo Cell row 0/1")

menu = [x for m in real3.context_menus() for x in m["entries"]]
sd = [x["center"] for x in menu if x["text"] == "Set Destination"]
assert sd == [(1029, 371)], menu
ok("G5 ground: menu link location co 'Set Destination' (1029,371)")

assert location_links(FakeEye(node("UIRoot"))) is None
assert location_links(real2) is None or isinstance(location_links(real2), dict)
ok("location_links: khong co dialog -> None (fail-closed)")

FIX4 = Path(__file__).resolve().parent / "fixtures" / "ui_tree_route_set.json"
real4 = Eye.__new__(Eye)
for _k in ("root", "_pos", "_pos_root"):
    setattr(real4, _k, None)
real4.root = json.loads(FIX4.read_text(encoding="utf-8"))
rp = real4._find_by_type("InfoPanelRoute", select_many=True)
rtxt = " ".join(str((n.get("attrs") or {}).get("_setText") or "") for n in Eye.walk(rp[0]))
mk = [n for n in Eye.walk(real4.root) if n.get("type") == "AutopilotDestinationIcon"]
assert "Nourvukaiken" in rtxt and "1 Jump" in rtxt and len(mk) == 1, (rtxt[:200], len(mk))
ok("G5 ground: sau Set Destination -> Route '1 Jump' Nourvukaiken + 1 marker")

print("ALL OK test_agent")
