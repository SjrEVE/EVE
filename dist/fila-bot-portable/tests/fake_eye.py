"""fake_eye.py — FakeEye dùng chung cho tests (kế thừa Eye thật, chỉ thay fake root)."""


class FakeEye:
    def __init__(self) -> None:
        from fila_bot.eye import Eye
        e = Eye.__new__(Eye)   # bỏ __init__ (không load DLL)
        e.root = {
            "address": 1, "type": "Root", "attrs": {}, "children": [
                {"address": 10, "type": "ShipUI", "attrs": {}, "children": [
                    {"address": 11, "type": "G", "attrs": {"_name": "shieldGauge", "_lastValue": 0.9}, "children": []},
                    {"address": 12, "type": "G", "attrs": {"_name": "armorGauge", "_lastValue": 0.55}, "children": []},
                    {"address": 13, "type": "G", "attrs": {"_name": "structureGauge", "_lastValue": 1.0}, "children": []},
                    {"address": 14, "type": "CapacitorContainer", "attrs": {}, "children": [
                        {"address": 15, "type": "S", "attrs": {"_name": "pmark", "color": {"a": 10}}, "children": []},
                        {"address": 16, "type": "S", "attrs": {"_name": "pmark", "color": {"a": 10}}, "children": []},
                    ]},
                    {"address": 17, "type": "X", "attrs": {"_name": "indicationcontainer", "maneuverType": "Orbit"}, "children": []},
                ]},
                {"address": 20, "type": "OverView", "attrs": {}, "children": [
                    {"address": 21, "type": "OverviewScrollEntry", "attrs": {
                        "_displayX": 100, "_displayY": 200, "_displayWidth": 50, "_displayHeight": 20},
                        "children": [
                            {"address": 22, "type": "Label", "attrs": {"_setText": "Kikimora"}, "children": []}]},
                ]},
                {"address": 30, "type": "DroneView", "attrs": {}, "children": [
                    {"address": 31, "type": "DroneEntry", "attrs": {}, "children": []},
                    {"address": 32, "type": "DroneEntry", "attrs": {}, "children": []},
                ]},
            ],
        }
        self.__class__ = Eye
        self.__dict__ = e.__dict__
