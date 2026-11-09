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

print("ALL OK test_agent")
