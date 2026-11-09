"""fake_eye.py — FakeEye dùng chung cho tests (kế thừa Eye thật, chỉ thay fake root).

Schema ở đây theo ĐÚNG client thật (ground 2026-11-09):
OverviewWindow + OverviewLabel(_text), SelectedItemWnd, ShipHudSpriteGauge (_lastValue float),
SpeedGauge label. Fixture đầy đủ hơn: tests/fixtures/ui_tree_ground_tq.json.
"""


class FakeEye:
    def __init__(self, with_active_item: bool = True) -> None:
        from fila_bot.eye import Eye
        e = Eye.__new__(Eye)   # bỏ __init__ (không load DLL)
        e.root = {
            "address": 1, "type": "Root", "attrs": {}, "children": [
                {"address": 10, "type": "ShipUI", "attrs": {}, "children": [
                    {"address": 11, "type": "ShipHudSpriteGauge", "attrs": {"_name": "shieldGauge", "_lastValue": 0.9}, "children": []},
                    {"address": 12, "type": "ShipHudSpriteGauge", "attrs": {"_name": "armorGauge", "_lastValue": 0.55}, "children": []},
                    {"address": 13, "type": "ShipHudSpriteGauge", "attrs": {"_name": "structureGauge", "_lastValue": 1.0}, "children": []},
                    {"address": 14, "type": "CapacitorContainer", "attrs": {}, "children": [
                        {"address": 15, "type": "Sprite", "attrs": {"_name": "pmark", "color": {"a": 10}}, "children": []},
                        {"address": 16, "type": "Sprite", "attrs": {"_name": "pmark", "color": {"a": 10}}, "children": []},
                    ]},
                    {"address": 17, "type": "X", "attrs": {"_name": "indicationcontainer", "maneuverType": "Orbit"}, "children": []},
                ]},
                {"address": 20, "type": "OverviewWindow", "attrs": {"_name": "overview", "_display": True}, "children": [
                    {"address": 21, "type": "OverviewScrollEntry", "attrs": {
                        "_displayX": 100, "_displayY": 200, "_displayWidth": 50, "_displayHeight": 20},
                        "children": [
                            {"address": 22, "type": "OverviewLabel", "attrs": {"_text": "Kikimora"}, "children": []}]},
                ]},
                {"address": 50, "type": "SelectedItemWnd", "attrs": {}, "children": [
                    {"address": 51, "type": "Label", "attrs": {"_setText": "Selected Item"}, "children": []},
                    {"address": 52, "type": "Label", "attrs": {"_setText": "Kikimora"}, "children": []}]} if with_active_item
                else {"address": 50, "type": "Noop", "attrs": {}, "children": []},
                {"address": 30, "type": "DroneView", "attrs": {}, "children": [
                    {"address": 31, "type": "DroneEntry", "attrs": {}, "children": []},
                    {"address": 32, "type": "DroneEntry", "attrs": {}, "children": []},
                ]},
            ],
        }
        self.__class__ = Eye
        self.__dict__ = e.__dict__
