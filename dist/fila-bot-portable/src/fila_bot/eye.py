"""Eye v2 — đọc UI tree EVE client từ memory qua eve-memory-reader.dll (master's node).

Nguồn vendor: D:/fila-bot/vendor/eve-memory-reader (fork của jamesalbert/eve-memory-reader,
inspired by Sanderling/Arcitectus). DLL đã build: vendor/eve-memory-reader/x64/Release/.

Quy tắc ground (không bịa): những gì cần attrs cụ thể của EVE client (HP, overview,
module button) phải verify với client thật mới trả giá trị — hiện đặt NotImplemented
với message rõ. Phần chắc chắn (load/refresh/find theo attrs) implement đầy đủ.
"""
from __future__ import annotations

import ctypes
import json
import os
from typing import Any

DLL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "vendor", "eve-memory-reader", "x64", "Release",
    "eve-memory-reader.dll")


class Eye:
    """Mắt của bot: UI tree JSON từ memory EVE client. Read-only, không write/inject."""

    def __init__(self, dll_path: str | None = None) -> None:
        path = os.path.abspath(dll_path or DLL_PATH)
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"eve-memory-reader.dll chưa build — xem vendor/eve-memory-reader/README.md ({path})")
        self.dll = ctypes.WinDLL(path)
        self.dll.initialize.argtypes = []
        self.dll.initialize.restype = ctypes.c_int
        self.dll.read_ui_trees.argtypes = []
        self.dll.read_ui_trees.restype = None
        self.dll.get_ui_json.argtypes = []
        self.dll.get_ui_json.restype = ctypes.c_char_p
        self.dll.free_ui_json.argtypes = []
        self.dll.free_ui_json.restype = None
        ret = self.dll.initialize()
        if ret != 0:
            raise RuntimeError(f"DLL initialize fail: {ret} (EVE client chưa chạy?)")
        self.root: dict[str, Any] | None = None

    def refresh(self) -> dict[str, Any] | None:
        """Đọc UI tree mới nhất. Trả root dict hoặc None khi không đọc được."""
        self.dll.read_ui_trees()
        raw = self.dll.get_ui_json()
        self.dll.free_ui_json()
        if not raw:
            self.root = None
            return None
        self.root = json.loads(raw.decode("utf-8", errors="ignore"))
        return self.root

    # ------------- traversal helpers -------------
    @staticmethod
    def walk(node: dict[str, Any]):
        yield node
        for child in node.get("children", []) or []:
            yield from Eye.walk(child)

    def find(self, type: str | None = None, contains: bool = False,
             select_many: bool = False, root: dict[str, Any] | None = None,
             **attrs: Any) -> list[dict[str, Any]]:
        """Tìm node theo type + attrs (_setText, _name...). contains = substring match.
        root=None → tìm cả cây; root=node → chỉ tìm trong subtree của node."""
        start = root if root is not None else self.root
        if start is None:
            return []
        out = []
        for node in self.walk(start):
            if type and node.get("type") != type:
                continue
            na = node.get("attrs", {})
            if all(
                (str(v) in str(na.get(k, ""))) if contains else (na.get(k) == v)
                for k, v in attrs.items()
            ):
                out.append(node)
                if not select_many:
                    break
        return out

    @staticmethod
    def center_xy(node: dict[str, Any], parent_x: float = 0.0, parent_y: float = 0.0) -> tuple[int, int]:
        """Tọa độ điểm giữa node theo _displayX/Y (lũy kế từ cha)."""
        x = parent_x + (node.get("attrs", {}).get("_displayX", 0) or 0)
        y = parent_y + (node.get("attrs", {}).get("_displayY", 0) or 0)
        w = (node.get("attrs", {}).get("_displayWidth", 0) or 0)
        h = (node.get("attrs", {}).get("_displayHeight", 0) or 0)
        return int(x + w // 2), int(y + h // 2)

    # ------------- game data (schema ground từ Sanderling ParseUserInterface.elm,
    # xem docs/EVE_UI_TREE_ATTRS.md; verify lần đầu trên Singularity client thật) -------------

    def _find_by_name(self, name: str, root: dict[str, Any] | None = None,
                      select_many: bool = False) -> list[dict[str, Any]]:
        """Node theo attrs _name (name= trong UI tree là dictEntriesOfInterest['_name'])."""
        return self.find(_name=name, select_many=select_many, root=root)

    def _find_by_type(self, type_name: str, root: dict[str, Any] | None = None,
                      select_many: bool = True) -> list[dict[str, Any]]:
        return self.find(type=type_name, select_many=select_many, root=root)

    def ship_ui(self) -> dict[str, Any] | None:
        ships = self._find_by_type("ShipUI", select_many=False)
        return ships[0] if ships else None

    def ship_health(self) -> dict[str, float] | None:
        """% shield/armor/structure từ 3 gauge (name=structureGauge/armorGauge/shieldGauge,
        giá trị ở attrs _lastValue float 0..1). Trả None nếu không thấy ShipUI/gauges."""
        ship = self.ship_ui()
        if ship is None:
            return None
        out: dict[str, float] = {}
        for gauge, key in (("shieldGauge", "shield"), ("armorGauge", "armor"),
                           ("structureGauge", "structure")):
            nodes = self._find_by_name(gauge, root=ship)
            val = nodes[0].get("attrs", {}).get("_lastValue") if nodes else None
            if isinstance(val, (int, float)):
                out[key] = round(float(val), 3)
        return out or None

    def capacitor_percent(self) -> float | None:
        """Cap % từ pmarks của CapacitorContainer: pmark có alpha < 20 = segment còn đầy
        (Sanderling: colorPercent.a < 20 → filled). Trả None nếu không đọc được."""
        ship = self.ship_ui()
        if ship is None:
            return None
        caps = self._find_by_type("CapacitorContainer", root=ship, select_many=False)
        if not caps:
            return None
        pmarks = self._find_by_name("pmark", root=caps[0], select_many=True)
        if not pmarks:
            return None
        fills = 0
        for p in pmarks:
            color = p.get("attrs", {}).get("_color") or p.get("attrs", {}).get("color")
            alpha = self._alpha_from_color(color)
            if alpha is not None and alpha < 20:
                fills += 1
        return round(fills * 100.0 / len(pmarks), 1)

    @staticmethod
    def _alpha_from_color(color: Any) -> float | None:
        """color có thể là dict {r,g,b,a} hoặc list [r,g,b,a] hoặc hex."""
        if isinstance(color, dict):
            a = color.get("a")
            return float(a) if isinstance(a, (int, float)) else None
        if isinstance(color, (list, tuple)) and len(color) == 4:
            return float(color[3])
        if isinstance(color, str) and color.startswith("#") and len(color) == 9:
            return int(color[7:9], 16) / 255.0 * 100
        return None

    def overview_entries(self) -> list[dict[str, Any]]:
        """Danh sách overview entries — XEM docs/EVE_UI_TREE_ATTRS.md (đã ground).
        OverView → headers (text cột) + OverviewScrollEntry (texts trái→phải)."""
        ovs = self._find_by_type("OverView", select_many=False)
        if not ovs:
            return []
        headers = self._parse_overview_headers(ovs[0])
        out = []
        for entry in self._find_by_type("OverviewScrollEntry", root=ovs[0]):
            texts = self._texts_of_node(entry)
            rec: dict[str, Any] = {"texts_left_to_right": texts}
            if headers:
                for i, t in enumerate(texts):
                    if i < len(headers):
                        rec[headers[i]] = t
            out.append(rec)
        return out

    def _parse_overview_headers(self, overview_root: dict[str, Any]) -> list[str]:
        heads = [n for n in self.walk(overview_root)
                 if "headers" in str(n.get("type", "")).lower()]
        if not heads:
            return []
        return [t for t in self._texts_of_node(heads[0]) if t]

    @staticmethod
    def _texts_of_node(node: dict[str, Any]) -> list[str]:
        out = []
        for n in Eye.walk(node):
            txt = n.get("attrs", {}).get("_setText")
            if isinstance(txt, str) and txt.strip():
                out.append(txt.strip())
        return out

    def maneuver(self) -> str | None:
        """Maneuver hiện tại: warp/jump/orbit/approach/None (node name chứa
        'indicationcontainer', attrs maneuverType). Ground: Sanderling ShipUIIndication."""
        ship = self.ship_ui()
        if ship is None:
            return None
        for n in self.walk(ship):
            if "indicationcontainer" in str(n.get("attrs", {}).get("_name", "")).lower():
                mt = n.get("attrs", {}).get("maneuverType")
                if isinstance(mt, str):
                    return mt.lower()
        return None

    def module_buttons(self) -> list[dict[str, Any]]:
        """Tất cả module buttons: [{center, is_active, hilite}] theo ShipSlot→ModuleButton."""
        ship = self.ship_ui()
        if ship is None:
            return []
        out = []
        for slot in self._find_by_type("ShipSlot", root=ship):
            for btn in self._find_by_type("ModuleButton", root=slot, select_many=False):
                attrs = btn.get("attrs", {})
                x, y = self.center_xy(btn)
                out.append({
                    "center": (x, y),
                    "is_active": attrs.get("isActive"),
                    "hilite": bool(attrs.get("_name") == "hilite"),
                })
                break
        return out

    def confirm_dialog(self) -> dict[str, Any] | None:
        """Popup cần confirm (filament spool-up): KeyActivationWindow hoặc MessageBox
        có text. Trả {type, texts, center} hoặc None."""
        for type_name in ("KeyActivationWindow", "MessageBox"):
            wins = self._find_by_type(type_name, select_many=True)
            for w in wins:
                texts = self._texts_of_node(w)
                if texts:
                    x, y = self.center_xy(w)
                    return {"type": type_name, "texts": texts[:10], "center": (x, y)}
        return None
