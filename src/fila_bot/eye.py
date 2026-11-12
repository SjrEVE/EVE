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

    # default để test dựng Eye.__new__ không cần __init__
    _pos: dict[int, tuple[int, int]] | None = None
    _pos_root: dict[str, Any] | None = None

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
        self._pos: dict[int, tuple[int, int]] | None = None
        self._pos_root: dict[str, Any] | None = None

    def refresh(self) -> dict[str, Any] | None:
        """Doc UI tree moi nhat. Tra root dict hoac None khi khong doc duoc.

        Trace rac khi client cap nhat dan node (< 2026-11-10 NULL khi xay ra):
        json.loads co the fail vi raw nat giua 2 lan scan (UI dang thay doi).
        Thuu lai toi da 3 lan (0.2s) truoc khi bao loi — khong bia du lieu.
        """
        import time as _t
        self.root = None
        last_err: Exception | None = None
        parsed = False
        for _ in range(3):
            # FREE TRUOC moi lan scan (fix 2026-11-10): neu scan that bai (UI dang
            # chuyen canh, number_of_children <= 5), DLL KHONG gan lai ui_json —
            # con tro cu dang free la DANS  → get_ui_json tra rac "char 0".
            # Free truoc dua ui_json ve NULL → raw None = fail-closed, doc lai.
            self.dll.free_ui_json()
            self.dll.read_ui_trees()
            raw = self.dll.get_ui_json()
            if not raw:
                return None
            try:
                text = raw.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                # byte UTF-8 dut = client ghi JSON giua chung; thay U+FFFD, khong bo mu (fix 2026-11-10)
                text = raw.decode("utf-8", errors="replace")
            try:
                self.root = json.loads(text)
                parsed = True
                break
            except json.JSONDecodeError as err:
                last_err = err
                self.dll.free_ui_json()
                _t.sleep(0.2)
        if parsed:
            self._pos = None
            self._pos_root = None
            return self.root
        self.dll.free_ui_json()
        raise RuntimeError(f"UI JSON hong sau 3 lan doc: {last_err}")

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
        """Tâm node theo _displayX/Y CỘNG THÊM parent_x/y (mặc định 0 = toạ độ cục bộ).

        ⚠️ Muốn toạ độ click thật: dùng abs_center(node) — tự cộng cả chuỗi cha
        (ground 2026-11-09: _displayX/Y là tương đối với cha).
        """
        x = parent_x + (node.get("attrs", {}).get("_displayX", 0) or 0)
        y = parent_y + (node.get("attrs", {}).get("_displayY", 0) or 0)
        w = (node.get("attrs", {}).get("_displayWidth", 0) or 0)
        h = (node.get("attrs", {}).get("_displayHeight", 0) or 0)
        return int(x + w // 2), int(y + h // 2)

    def _ensure_pos(self) -> None:
        """Index toạ độ tuyệt đối (cộng dồn _displayX/Y từ UIRoot) cho mọi node."""
        if self._pos is not None and self._pos_root is self.root:
            return
        pos: dict[int, tuple[int, int]] = {}

        def walk(node: dict[str, Any], x: int, y: int) -> None:
            a = node.get("attrs", {}) or {}
            nx = x + int(a.get("_displayX") or 0)
            ny = y + int(a.get("_displayY") or 0)
            pos[id(node)] = (nx, ny)
            for child in node.get("children") or []:
                walk(child, nx, ny)

        if self.root is not None:
            walk(self.root, 0, 0)
        self._pos = pos
        self._pos_root = self.root

    def abs_center(self, node: dict[str, Any]) -> tuple[int, int]:
        """Tâm node theo toạ độ TUYỆT ĐỐI trong client area (dùng để click)."""
        self._ensure_pos()
        x, y = (self._pos or {}).get(id(node), (0, 0))
        a = node.get("attrs", {}) or {}
        return int(x + int(a.get("_displayWidth") or 0) // 2), \
            int(y + int(a.get("_displayHeight") or 0) // 2)

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
        """Cap % từ pmarks của CapacitorContainer.

        Ground 2026-11-09 (TQ client): pmark._color là PyColor. DLL đã decode
        (ground từ Sanderling read-memory-64-bit/EveOnline64.cs): PyColor +0x10 trỏ
        tới dict {_a,_r,_g,_b} → emit JSON {"aPercent","rPercent","gPercent","bPercent"}.
        Sanderling đếm pmark có aPercent < 20 = đoạn cap CÒN, chia tổng pmark → %.
        Nếu không decode được màu nào → trả None (unknown), KHÔNG trả 0.0 giả.
        """
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
        colored = 0
        for p in pmarks:
            color = p.get("attrs", {}).get("_color") or p.get("attrs", {}).get("color")
            alpha = self._alpha_from_color(color)
            if alpha is None:
                continue
            colored += 1
            if alpha < 20:
                fills += 1
        if colored == 0:
            return None   # màu không decode được → unknown, không đoán
        return round(fills * 100.0 / colored, 1)

    @staticmethod
    def _alpha_from_color(color: Any) -> float | None:
        """Alpha 0..100. Ưu tiên 'aPercent' (PyColor đã decode bởi DLL).

        Các dạng cũ vẫn chấp nhận để test/legacy: dict {"a":..}, list [r,g,b,a], hex #rrggbbaa.
        """
        if isinstance(color, dict):
            if "aPercent" in color:
                v = color["aPercent"]
                return float(v) if isinstance(v, (int, float)) else None
            a = color.get("a")
            return float(a) if isinstance(a, (int, float)) else None
        if isinstance(color, (list, tuple)) and len(color) == 4:
            return float(color[3])
        if isinstance(color, str) and color.startswith("#") and len(color) == 9:
            return int(color[7:9], 16) / 255.0 * 100
        return None

    def overview_window(self) -> dict[str, Any] | None:
        """Cửa sổ overview đang hiển thị. Ground 2026-11-09 (TQ client): type thật
        là 'OverviewWindow' (name='overview') — KHÔNG phải 'OverView' (Sanderling cũ)."""
        for type_name in ("OverviewWindow", "OverView"):
            wins = [w for w in self._find_by_type(type_name, select_many=True)
                    if (w.get("attrs", {}) or {}).get("_display") is not False]
            if wins:
                return wins[0]
        return None

    def overview_entries(self) -> list[dict[str, Any]]:
        """Danh sách overview entries. Ground 2026-11-09 (TQ client):
        OverviewWindow → OverviewScrollEntry → OverviewLabel (text ở attrs['_text']).

        Trả mỗi entry dạng {"texts_left_to_right": [...], <TênCột>: giá trị, "center": (x,y)}
        — cột map theo thứ tự x của header (EveLabelSmall._setText) trong cùng cửa sổ.
        """
        win = self.overview_window()
        if win is None:
            return []
        entries = self._find_by_type("OverviewScrollEntry", root=win)
        if not entries:
            return []
        header_cols = self._overview_columns(win, entries[0])
        out = []
        for entry in entries:
            labels: list[tuple[int, str]] = []
            for n in self.walk(entry):
                if n.get("type") != "OverviewLabel":
                    continue
                txt = (n.get("attrs", {}) or {}).get("_text")
                if isinstance(txt, str) and txt.strip():
                    labels.append((self.abs_center(n)[0], txt.strip()))
            labels.sort(key=lambda t: t[0])
            rec: dict[str, Any] = {"texts_left_to_right": [t for _, t in labels]}
            for lx, txt in labels:
                name = self._nearest_column(lx, header_cols)
                if name:
                    rec[name] = txt
            # Guard "đọc toàn nhầm" (live 13-11): EVE overview luôn có Distance
            # ở CỘT ĐẦU. Nếu header map lệch (tab/filter đổi) làm mất key
            # Distance nhưng texts[0] rõ ràng là một khoảng cách — gán đúng chỗ.
            if "Distance" not in rec and rec["texts_left_to_right"]:
                first = rec["texts_left_to_right"][0].strip().lower()
                if first.endswith((" m", " km", " au")):
                    rec["Distance"] = rec["texts_left_to_right"][0].strip()
            rec["center"] = self.abs_center(entry)
            out.append(rec)
        return out

    def _overview_columns(self, win: dict[str, Any],
                          first_entry: dict[str, Any]) -> list[tuple[int, str]]:
        """Cột overview: [(tâm_x, tên_cột)] từ hàng header NGAY TRÊN entry đầu.

        Ground 2026-11-09: header là EveLabelSmall (_setText), luôn nằm TRÊN entry
        đầu tiên. Khoảng cách thay đổi theo scroll — KHÔNG hard-code 40px như bản
        cũ (header y=252, entry y=276 lúc đầu; sau khi scroll entry y=324 → trượt).
        Cách đúng: gom mọi label có y < y_entry, lấy nhóm có y lớn nhất (gần nhất).
        """
        _, y_entry = self.abs_center(first_entry)
        candidates: list[tuple[int, int, str]] = []
        for n in self.walk(win):
            if n.get("type") != "EveLabelSmall":
                continue
            txt = (n.get("attrs", {}) or {}).get("_setText")
            if not isinstance(txt, str) or not txt.strip():
                continue
            x, y = self.abs_center(n)
            if y < y_entry:
                candidates.append((y, x, txt.strip()))
        if not candidates:
            return []
        header_y = max(c[0] for c in candidates)
        cols = [(x, t) for y, x, t in candidates if y == header_y]
        cols.sort(key=lambda c: c[0])
        return cols

    @staticmethod
    def _nearest_column(x: int, cols: list[tuple[int, str]]) -> str | None:
        if not cols:
            return None
        return min(cols, key=lambda c: abs(c[0] - x))[1]

    def targets_in_bar(self) -> list[dict[str, Any]]:
        """Targets actually LOCKED by the client, read from what it really renders.

        Ground 2026-11-12 (client source + live TQ):
        - `targetInBar.py` defines `class TargetInBar(ContainerAutoSize)` and
          `class TargetHealthBars(Container)` with `default_name = 'targetHealthBars'`.
        - Sanderling selects locked targets by `pythonObjectTypeName == "TargetInBar"`
          and marks the active one with a descendant `ActiveTargetOnBracket`.
        BUT this reader build does not emit those Python type names: a full walk of
        the live tree in space found 172 distinct types and NO `TargetInBar` /
        `ActiveTargetOnBracket` at all. So the type-based rule returns nothing here.

        What the client DOES render for a locked target is the health-bar container
        named `targetHealthBars` (one per locked target) with `shieldBar`,
        `armorBar`, `hullBar` children. Those names come from the client's own
        source, so they are evidence, not a guess. This method therefore:
          1. uses `TargetInBar` / `ActiveTargetOnBracket` when the tree has them
             (other builds / future reader versions), and
          2. otherwise falls back to `targetHealthBars` containers.
        An empty list means "nothing locked" only when at least one of those
        structures exists somewhere in the tree; when none exist at all the caller
        gets [] and `targets_observable()` says False — never a silent lie.
        """
        out: list[dict[str, Any]] = []
        for node in self._find_by_type("TargetInBar", select_many=True) or []:
            texts = [t.strip() for t in self._texts_of_node(node) if t and t.strip()]
            active = bool(self._find_by_type("ActiveTargetOnBracket", root=node,
                                             select_many=True))
            out.append({"texts": texts[:6],
                        "name": texts[0] if texts else None,
                        "is_active": active,
                        "center": self.abs_center(node)})
        if out:
            return out
        for node in self._find_by_name("targetHealthBars", select_many=True) or []:
            texts = [t.strip() for t in self._texts_of_node(node) if t and t.strip()]
            out.append({"texts": texts[:6],
                        "name": texts[0] if texts else None,
                        # Without ActiveTargetOnBracket we cannot tell WHICH of
                        # several locked targets the drones would attack, so the
                        # active flag stays None (unknown) rather than a guess.
                        "is_active": None,
                        "center": self.abs_center(node)})
        return out

    def targets_observable(self) -> bool:
        """True when this tree contains any structure that can show a lock.

        Ground LIVE 2026-11-12: the live client renders the target bar only when a
        target is actually locked, so "no such node anywhere" cannot be told apart
        from "nothing locked" — and treating it as 'no lock' made the bot refuse to
        fire and then block. Say UNKNOWN instead.
        """
        if self._find_by_type("TargetInBar", select_many=True):
            return True
        return bool(self._find_by_name("targetHealthBars", select_many=True))

    def locked_target(self) -> dict[str, Any] | None:
        """The single ACTIVE target, or None when nothing is actively targeted."""
        active = [t for t in self.targets_in_bar() if t.get("is_active")]
        if len(active) == 1:
            return active[0]
        return None

    def selected_item(self) -> dict[str, Any] | None:
        """Selected Item window. Ground 2026-11-09: type 'SelectedItemWnd'
        (name='selecteditemview'), text ở _setText. Trả {name, texts, center} hoặc None."""
        for type_name in ("SelectedItemWnd", "ActiveItem"):
            for win in self._find_by_type(type_name, select_many=True):
                texts = self._texts_of_node(win)
                if texts:
                    return {"name": texts[1] if len(texts) > 1 else texts[0],
                            "texts": texts[:10], "center": self.abs_center(win)}
        return None

    def speed_mps(self) -> float | None:
        """Tốc độ hiện tại đọc từ SpeedGauge label ('600 m/s'). Ground 2026-11-09."""
        for n in self.walk(self.root or {}):
            a = n.get("attrs", {}) or {}
            if a.get("_name") == "speedLabel":
                txt = a.get("_setText") or ""
                num = "".join(ch for ch in str(txt) if ch.isdigit() or ch == ".")
                try:
                    return float(num)
                except ValueError:
                    return None
        return None

    @staticmethod
    def _texts_of_node(node: dict[str, Any]) -> list[str]:
        """Text của node + con: nhận cả _setText (label thường) và _text (OverviewLabel)."""
        out = []
        for n in Eye.walk(node):
            a = n.get("attrs", {}) or {}
            for key in ("_setText", "_text"):
                txt = a.get(key)
                if isinstance(txt, str) and txt.strip():
                    out.append(txt.strip())
                    break
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
        """Module buttons on the HUD, each tied to its OBSERVED ship slot.

        Ground 2026-11-12 (live runtime fixture): SlotsContainer → ShipSlot
        `_name=inFlightHighSlot1..` → ModuleButton `_name=ModuleButton_<typeID>`.
        `ramp_active` is present on active-rack buttons but missing on some
        launchers; a missing flag is UNKNOWN (None), never False.
        """
        ship = self.ship_ui()
        if ship is None:
            return []
        import re
        out: list[dict[str, Any]] = []

        def visit(node: dict[str, Any], slot: str | None) -> None:
            attrs = node.get("attrs", {}) or {}
            if node.get("type") == "ShipSlot":
                name = str(attrs.get("_name") or "")
                if name.startswith("inFlight"):
                    slot = name
            if node.get("type") == "ModuleButton":
                active = attrs.get("ramp_active")
                if not isinstance(active, bool):
                    active = attrs.get("isActive")
                if not isinstance(active, bool):
                    active = None
                name = str(attrs.get("_name") or "")
                m = re.match(r"^inFlight(High|Medium|Low)Slot([0-9]+)$", slot or "")
                out.append({
                    "center": self.abs_center(node),
                    "is_active": active,
                    "hilite": name == "hilite",
                    "slot": slot,
                    "rack": m.group(1).lower() if m else None,
                    "index": int(m.group(2)) if m else None,
                    "name": name or None,
                    "type_id": (int(name.rsplit("_", 1)[1])
                                if name.startswith("ModuleButton_") and name.rsplit("_", 1)[1].isdigit()
                                else None),
                })
            for child in node.get("children") or []:
                visit(child, slot)

        visit(ship, None)
        return out

    def drones_observation(self) -> dict[str, Any]:
        """Ground: DronesWindow labels in ui_tree_20261112_runtime.json.
        Missing or conflicting counts are unknown, never zero by default.
        """
        import re
        panels = self._find_by_type("DronesWindow", select_many=True)
        panels = [p for p in panels if (p.get("attrs") or {}).get("_display") is not False]
        out = {"observed": bool(panels), "in_space": None, "in_bay": None}
        if len(panels) != 1:
            return out
        texts = self._texts_of_node(panels[0])
        for key, pattern in (("in_space", r"^Drones in Space \(([0-9]+)(?:/[0-9]+)?\)$"),
                             ("in_bay", r"^Drones in Bay \(([0-9]+)\)$")):
            values = {int(m.group(1)) for t in texts if (m := re.fullmatch(pattern, t.strip()))}
            if len(values) == 1:
                out[key] = values.pop()
        return out

    def confirm_dialog(self) -> dict[str, Any] | None:
        """Popup cần confirm (filament spool-up): KeyActivationWindow hoặc MessageBox
        có text. Trả {type, texts, center} hoặc None."""
        for type_name in ("KeyActivationWindow", "MessageBox"):
            wins = self._find_by_type(type_name, select_many=True)
            for w in wins:
                texts = self._texts_of_node(w)
                if texts:
                    return {"type": type_name, "texts": texts[:10],
                            "center": self.abs_center(w)}
        return None

    # ---------------- popup modal (catalog: g7_after_manual_180231 'Connection Lost') ----------------
    def message_boxes(self) -> list[dict[str, Any]]:
        """MessageBox (_name='modal') + nut trong ButtonGroup. Port Viir parseMessageBox.
        Tra [{texts, buttons: [{text, name, center}], center}]."""
        out: list[dict[str, Any]] = []
        for w in self._find_by_type("MessageBox", select_many=True) or []:
            buttons = []
            for g in self.walk(w):
                if "ButtonGroup" not in str(g.get("type", "")):
                    continue
                for b in self.walk(g):
                    if b is g or "Button" not in str(b.get("type", "")) or "Group" in str(b.get("type")):
                        continue
                    tx = self._texts_of_node(b)
                    buttons.append({"text": tx[0] if tx else None,
                                    "name": (b.get("attrs") or {}).get("_name"),
                                    "center": self.abs_center(b)})
            out.append({"texts": self._texts_of_node(w)[:10], "buttons": buttons,
                        "center": self.abs_center(w)})
        return out

    def connection_lost(self) -> bool:
        """True = client mat ket noi -> E-STOP, KHONG bam gi (nut duy nhat la Quit)."""
        for m in self.message_boxes():
            blob = " ".join(m["texts"]).lower()
            if "connection lost" in blob or "connection to server was lost" in blob:
                return True
        return False

    # ---------------- SelectedItemWnd buttons (catalog g6_end_*) ----------------
    def selected_item_buttons(self) -> dict[str, tuple[int, int]]:
        """{'dock'|'jump'|'warpto'|'alignto'|'approach'|...: center} theo _name
        'selectedItem<Action>'. Thay context menu cho Dock/Jump/Warp (khong menu cu, khong spam)."""
        out: dict[str, tuple[int, int]] = {}
        for n in self._find_by_type("SelectedItemButton", select_many=True) or []:
            nm = (n.get("attrs") or {}).get("_name")
            if isinstance(nm, str) and nm.startswith("selectedItem"):
                out[nm[len("selectedItem"):].lower()] = self.abs_center(n)
        return out

    # ---------------- station window (ground 2026-11-09, TQ Photon UI) ----------------
    def station_window(self) -> dict[str, Any] | None:
        """Cửa sổ station (LobbyWnd). Ground: type 'LobbyWnd' (name='lobbyWnd'),
        nút undock = 'UndockButton' (name='undockButton') → EveLabelMedium 'label' = 'Undock'.

        Trả {center, undock: {center, text}, tabs: [{name, center}]} hoặc None.
        """
        wins = self._find_by_type("LobbyWnd", select_many=True)
        if not wins:
            return None
        win = wins[0]
        out: dict[str, Any] = {"center": self.abs_center(win), "undock": None, "tabs": []}
        for n in self.walk(win):
            if n.get("type") == "UndockButton":
                label = ""
                for d in self.walk(n):
                    txt = (d.get("attrs", {}) or {}).get("_setText")
                    if isinstance(txt, str) and txt.strip():
                        label = txt.strip()
                        break
                out["undock"] = {"center": self.abs_center(n), "text": label}
            elif n.get("type") == "Tab":
                a = n.get("attrs", {}) or {}
                out["tabs"].append({"name": a.get("_name"), "center": self.abs_center(n)})
        return out

    def active_ship_observation(self) -> tuple[bool, dict[str, str] | None]:
        """Read the active hull from an OBSERVED panel, never from a lobby button.

        The LobbyWnd ``Board my <ship>`` button is a candidate, not proof of the
        ship currently boarded, so it is never used as the active hull.

        Ground 11-11 (live client ``EVE - Kompi Yaken``): when docked, the hull is
        in the FittingWindow ``nameCaption`` ("Gila - Kompi Yaken"), while the
        lobby still showed a generic "Board my Corvette" button. Reading that
        button as the hull produced a wrong "corvette" claim. Prefer ShipsPanel,
        then FittingWindow; if neither is observed return (False, None).
        """
        lobbies = self._find_by_type("LobbyWnd", select_many=True)
        panels = ([n for n in self.walk(lobbies[0]) if n.get("type") == "ShipsPanel"]
                  if lobbies else [])
        if panels:
            active_ships: list[dict[str, str]] = []
            for panel in panels:
                for card in (n for n in self.walk(panel) if n.get("type") == "ShipItemCard"):
                    state_texts: list[str] = []
                    hull: str | None = None
                    ship_name: str | None = None
                    for node in self.walk(card):
                        attrs = node.get("attrs", {}) or {}
                        text = attrs.get("_setText") or attrs.get("_text")
                        if isinstance(text, str) and text.strip():
                            if node.get("type") == "TextDetail":
                                hull = text.strip()
                            elif node.get("type") == "TextBody" and " - " in text:
                                ship_name = text.strip()
                        if attrs.get("_name") == "activeState":
                            for child in self.walk(node):
                                child_text = (child.get("attrs", {}) or {}).get("_setText")
                                if isinstance(child_text, str) and child_text.strip():
                                    state_texts.append(child_text.strip())
                    if "Active" in state_texts and hull and ship_name:
                        active_ships.append({"name": ship_name, "hull": hull})
            return True, active_ships[0] if len(active_ships) == 1 else None

        # FittingWindow is opened in station and names the ship being fit.
        fits = self._find_by_type("FittingWindow", select_many=True)
        if fits:
            for n in self.walk(fits[0]):
                a = n.get("attrs") or {}
                if a.get("_name") != "nameCaption":
                    continue
                label = a.get("_setText") or a.get("_text")
                if isinstance(label, str) and label.strip():
                    label = label.strip()
                    hull = label.split(" - ")[0].strip() if " - " in label else label
                    if hull and "board my" not in hull.lower():
                        return True, {"name": label, "hull": hull}
            return True, None      # window observed but caption not rendered yet
        return False, None

    def is_docked(self) -> bool:
        """Đang docked: thấy station window (LobbyWnd) và KHÔNG có ShipUI."""
        return self.station_window() is not None and self.ship_ui() is None

    def space_brackets(self) -> list[dict[str, Any]]:
        """Identity-only projected brackets. Native renderObject coordinates are
        not exported by the current reader; layout coordinates are NOT projected
        click geometry. A matching item ID must still be resolved to a visible UI
        target. Missing geometry remains None (zero alone is not missing).
        """
        out: list[dict[str, Any]] = []
        for n in self.walk(self.root or {}):
            a = n.get("attrs", {}) or {}
            name = a.get("_name")
            if not isinstance(name, str) or not name.startswith("__inflightbracket_"):
                continue
            texts = self._texts_of_node(n)
            out.append({
                "name": name,
                "center": None,
                "geometry_observed": False,
                "label": (texts[0] if texts else None),
            })
        return out

    # ---------------- context menu (ground 2026-11-09) ----------------
    def context_menus(self) -> list[dict[str, Any]]:
        """Menu chuột phải đang mở: [{center, entries:[{text, center, name}]}].

        Ground: ContextMenu (name='menuview') → MenuEntryView (name='context_menu_Xxx')
        → TextBody text hiển thị. Menu nhiều cấp = nhiều ContextMenu trong cây
        (cấp con nằm trong layer l_menu, toạ độ tuyệt đối đọc qua abs_center).
        """
        # Ground G6 2026-11-09 (dumps/g6_sec_None_174059.json, menu stargate trong space):
        # DLL decode SAI type cua entry (PyColor/Sprite/PyChildrenList thay vi MenuEntryView)
        # va label con cung sai type. Nhan dien entry bang _name='context_menu_<Text>'
        # (on dinh), text = _setText dau tien trong subtree (khong loc theo type).
        out: list[dict[str, Any]] = []
        for menu in self._find_by_type("ContextMenu", select_many=True):
            entries = []
            for n in self.walk(menu):
                name = (n.get("attrs", {}) or {}).get("_name")
                is_entry = n.get("type") == "MenuEntryView" or (
                    isinstance(name, str) and name.startswith("context_menu_"))
                if not is_entry:
                    continue
                text = ""
                for d in self.walk(n):
                    if d is n:
                        continue
                    da = d.get("attrs", {}) or {}
                    txt = da.get("_setText") or da.get("_text")
                    if isinstance(txt, str) and txt.strip():
                        text = txt.strip()
                        break
                if not text and isinstance(name, str) and name.startswith("context_menu_"):
                    text = name[len("context_menu_"):]
                entries.append({"text": text, "name": name, "center": self.abs_center(n)})
            out.append({"center": self.abs_center(menu), "entries": entries})
        return out

    def menu_entry_xy(self, text: str, exact: bool = False) -> tuple[int, int] | None:
        """Toạ độ entry trong menu ĐANG MỞ theo text (verify trước khi bấm — P0-5)."""
        want = text.strip().lower()
        for menu in self.context_menus():
            for e in menu["entries"]:
                t = (e.get("text") or "").strip().lower()
                if (t == want) if exact else (want and want in t):
                    return e["center"]
        return None

    def mission_location_button(self) -> dict[str, Any] | None:
        """Nút Location trong mission tracker — ground trên client TQ thật.

        dumps/g11_docked_fresh.json: StatefulButton
        _name='missionObjective_button_location_3016839', con EveLabelMedium
        _name='label' _setText='Set Destination'. dumps/g8_opportunities_open.json
        có 'No Destination' + 'WarpTo' (selectedItemWarpTo). Theo CCP/community,
        nhãn nút này đổi 'Set Destination' -> 'Warp to Location' khi tàu ĐÃ ở đúng
        hệ (docs/MISSION_TRAVEL_RESEARCH_2026-11-11.md §2, §6).

        Trả {center, label, name} hoặc None. KHÔNG suy đích từ 'Celestial Beacon'
        bất kỳ trong overview và KHÔNG bịa text menu.
        """
        nodes = self.find(type="StatefulButton", contains=True,
                          _name="missionObjective_button_location_")
        if not nodes:
            return None
        n = nodes[0]
        label = ""
        for d in self.walk(n):
            if d is n:
                continue
            da = d.get("attrs") or {}
            if da.get("_name") == "label":
                t = da.get("_setText") or da.get("_text")
                if isinstance(t, str) and t.strip():
                    label = t.strip()
                    break
        return {"center": self.abs_center(n), "label": label,
                "name": (n.get("attrs") or {}).get("_name")}

    def mission_panel_observation(self) -> dict[str, Any] | None:
        """Doc panel Opportunities / AgentMissionInfoPanelEntry dang mo.

        Ground LIVE 11-11 20:3x (scratch/live_current_tree.json, client TQ
        'EVE - Kompi Yaken'):
          EveLabelLarge name=None  -> "What s in a Name  - Poke (3 of 5)"  (title)
          EveLabelLarge name=title -> "Encounter (Deadspace)"              (loai mission)
          EveLabelMedium           -> "You need to travel to Josameto 0.6" (he can toi)
          EveLabelMedium name=label (con cua StatefulButton
            missionObjective_button_location_3010986) -> "Set Destination"

        Day la BANG CHUNG CUA GAME, khong phai suy luan tu title/catalog. Tra None
        khi panel khong quan sat duoc — khong biet thi khong duoc doan.
        """
        panels = self._find_by_type("AgentMissionInfoPanelEntry", select_many=True)
        if not panels:
            return None
        panel_name = str((panels[0].get("attrs") or {}).get("_name") or "")
        agent_id = panel_name.partition(":")[2] if panel_name.startswith("agent_missions:") else None
        out: dict[str, Any] = {"observed": True, "title": None,
                               "agent_id": agent_id,
                               "objective_complete": None,
                               "type_label": None, "location_text": None,
                               "objective_text": None,
                               "location_button": None, "location_button_xy": None}
        for n in self.walk(panels[0]):
            if n is panels[0]:
                continue
            a = n.get("attrs") or {}
            t = a.get("_setText") or a.get("_text")
            if not isinstance(t, str) or not t.strip():
                continue
            s = t.strip()
            nm = a.get("_name")
            low = s.lower()
            if nm == "title" and low == "complete mission":
                # Grounded tracker header, NOT the AgentDialogue button.
                # missions/client/ui/missionObjectiveData.py:AllObjectivesComplete.
                out["objective_complete"] = True
            elif nm == "title" and ("encounter" in low or "deadspace" in low
                                  or "courier" in low or "mining" in low):
                out["type_label"] = s
            elif nm == "label" and ("destination" in low or "warp to" in low
                                    or "undock" in low):
                out["location_button"] = s
            elif "you need to" in low:
                out["objective_complete"] = False
                # Ground 11-11: "You need to activate the Acceleration Gate"
                # / "You need to travel to Josameto 0.6" — game tu bao buoc tiep.
                out["objective_text"] = s
                if "travel to" in low:
                    out["location_text"] = s
            elif "travel to" in low or "location" in low:
                out["location_text"] = s
            elif n.get("type") == "EveLabelLarge" and out["title"] is None:
                out["title"] = s
        btn = self.mission_location_button()
        if btn:
            out["location_button_xy"] = btn["center"]
            if not out["location_button"]:
                out["location_button"] = btn["label"] or None
        return out

    def empty_point(self) -> tuple[int, int]:
        """Toạ độ vùng trống an toàn trong client area (để click đóng menu).

        Ground 2026-11-09: KHÔNG dùng ESC (ESC mở Settings window trong EVE).
        Chọn điểm giữa-dưới màn hình nơi không có node UI nào phủ, kiểm bằng cách
        duyệt toàn bộ node có _display và loại vùng phủ của chúng.
        """
        win = self._find_by_type("ShipUI", select_many=False)
        w = (win[0].get("attrs", {}) or {}).get("_displayWidth", 1280) if win else 1280
        h = (win[0].get("attrs", {}) or {}).get("_displayHeight", 1018) if win else 1018

        # vùng bị phủ bởi window/container lớn (bỏ qua HUD nhỏ ở giữa)
        covered: list[tuple[int, int, int, int]] = []
        for n in self.walk(self.root or {}):
            a = n.get("attrs", {}) or {}
            if a.get("_display") is False:
                continue
            nw, nh = int(a.get("_displayWidth") or 0), int(a.get("_displayHeight") or 0)
            if nw * nh < 40000:            # bỏ node nhỏ (icon, label)
                continue
            x, y = self.abs_center_x_y(n)
            covered.append((x, y, nw, nh))

        # quét lưới: chọn điểm không nằm trong vùng phủ nào
        for gy in range(int(h * 0.85), int(h * 0.30), -40):
            for gx in range(int(w * 0.12), int(w * 0.55), 40):
                if not any(cx <= gx <= cx + cw and cy <= gy <= cy + ch
                           for cx, cy, cw, ch in covered):
                    return (gx, gy)
        return (int(w * 0.25), int(h * 0.75))

    def abs_center_x_y(self, node: dict[str, Any]) -> tuple[int, int]:
        """Góc trên-trái tuyệt đối của node (khác abs_center = tâm)."""
        self._ensure_pos()
        return (self._pos or {}).get(id(node), (0, 0))

    def wait_menu(self, timeout_s: float = 5.0, poll_s: float = 0.35) -> bool:
        """Chờ menu chuột phải hiện (ground: 1-2 s sau right-click, không tức thì).

        Đọc lại UI tree theo chu kỳ; trả True khi có ít nhất 1 ContextMenu.
        KHÔNG dùng sleep cố định — chậm/mất menu là nguyên nhân click mù.
        """
        import time as _t
        deadline = _t.time() + timeout_s
        while _t.time() < deadline:
            self.refresh()
            if self.context_menus():
                return True
            _t.sleep(poll_s)
        return False

    def wait_entry(self, text: str, timeout_s: float = 5.0,
                   poll_s: float = 0.35) -> tuple[int, int] | None:
        """Chờ entry có text xuất hiện trong menu đang mở → toạ độ (hoặc None)."""
        import time as _t
        want = text.strip().lower()
        deadline = _t.time() + timeout_s
        while _t.time() < deadline:
            self.refresh()
            for menu in self.context_menus():
                for e in menu["entries"]:
                    if want in (e.get("text") or "").strip().lower():
                        return e["center"]
            _t.sleep(poll_s)
        return None
