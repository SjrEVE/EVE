"""MISSION RUNNER — chạy mission security (PvE) bằng eye + keybind, fail-closed.

Khác abyss: mission KHÔNG có timer 20 phút, được warp out, có station để dock/turn-in.
Vòng đời 1 mission:

    DOCKED -> (agent) REQUEST/ACCEPT -> UNDOCK -> WARP_SITE -> POCKET (clear + gate)
           -> WARP_HOME -> DOCK -> TURN_IN

Nguyên tắc (giống phần còn lại của repo):
- KHÔNG bấm mù: mọi click phải đi qua tên entry/node đã verify (P0-5).
- Node chưa ground được → FAIL-CLOSED, trả lý do, không đoán.
- Đọc gì ghi nấy: `MissionEye.state()` chỉ trả dữ liệu thật từ UI tree.

Ground 2026-11-09 (TQ, Photon UI) — xem docs/EVE_UI_TREE_ATTRS.md:
- Station/system: InfoPanelLocationInfo → EveLabelMedium._setText có `alt= Current Station >`
- Security status: EveCaptionSmall._name=headerLabelSecStatus, text `<hint= Security status >...`
- Route: InfoPanelRoute → EveLabelMedium._name=noDestinationLabel = "No Destination",
  hoặc các node `AutopilotDestinationIcon` khi có route
- Agent dialogue (khi nói chuyện với agent): `AgentDialogueWindow`
- Mission đang nhận: InfoPanelJobBoard → `AgentMissionInfoPanelEntry` (layout cũ: InfoPanelAgentMissions → `MissionEntry`)
- Agent list trong station: `AgentsPanel` (container rỗng khi chưa load)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Tên entry overview dùng để nhận diện site/gate (EVE đặt tên beacon theo mission)
_GATE_NAME = "acceleration gate"
_MISSION_HINTS = ("mission", "deadspace", "beacon")

# Phase của mission runner
PHASES = (
    "UNKNOWN",       # chưa đọc được trạng thái
    "DOCKED",        # trong station
    "IN_SPACE",      # ngoài space, chưa rõ ở đâu
    "AT_SITE",       # đang ở pocket có quái
    "POCKET_CLEAR",  # pocket sạch, có gate để đi tiếp
    "DONE",          # objective xong, cần về trả
)


def _strip_tags(text: str) -> str:
    """Bỏ markup EVE (<url=..>x</url>, <color=..>, <hint=..>) → text thuần."""
    text = re.sub(r"<[^>]*>", "", str(text))
    return text.strip()


def _after_alt(text: str, marker: str) -> str | None:
    """Lấy phần sau `alt= <marker> >` trong _setText của EVE label."""
    m = re.search(rf"alt=\s*{re.escape(marker)}\s*>(.*)", str(text))
    if not m:
        return None
    val = _strip_tags(m.group(1))
    return val or None


@dataclass
class MissionState:
    phase: str = "UNKNOWN"
    in_station: bool = False
    station: str | None = None
    system: str | None = None
    security: float | None = None
    route_destination: str | None = None
    route_markers: int = 0
    agent_dialogue: list[str] = field(default_factory=list)
    mission_entries: list[str] = field(default_factory=list)
    gates: list[dict[str, Any]] = field(default_factory=list)
    mission_beacons: list[dict[str, Any]] = field(default_factory=list)
    hp: dict[str, float] | None = None
    cap: float | None = None
    speed: float | None = None
    targets: int = 0
    overview_count: int = 0
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase, "in_station": self.in_station, "station": self.station,
            "system": self.system, "security": self.security,
            "route_destination": self.route_destination, "route_markers": self.route_markers,
            "agent_dialogue": self.agent_dialogue, "mission_entries": self.mission_entries,
            "gates": self.gates, "mission_beacons": self.mission_beacons,
            "hp": self.hp, "cap": self.cap, "speed": self.speed,
            "targets": self.targets, "overview_count": self.overview_count,
            "notes": self.notes,
        }


class MissionEye:
    """Đọc trạng thái mission từ UI tree thật. Không ghi, không bấm."""

    def __init__(self, eye: Any) -> None:
        self.eye = eye

    # ---------------- helpers ----------------
    def _find_type(self, type_name: str) -> list[dict[str, Any]]:
        return self.eye._find_by_type(type_name, select_many=True)

    def _labels(self, root: dict[str, Any]) -> list[tuple[str | None, str]]:
        """[(tên node, text)] cho mọi label trong subtree."""
        out = []
        for n in self.eye.walk(root):
            a = n.get("attrs", {}) or {}
            txt = a.get("_setText") or a.get("_text")
            if isinstance(txt, str) and txt.strip():
                out.append((a.get("_name"), txt))
        return out

    # ---------------- dữ liệu vị trí ----------------
    def location(self) -> dict[str, Any]:
        """Station hiện tại + system + security status (ground 2026-11-09)."""
        out: dict[str, Any] = {"station": None, "system": None, "security": None}
        panel = self._find_type("InfoPanelLocationInfo")
        if panel:
            for name, txt in self._labels(panel[0]):
                if name == "nearestLocationInfo":
                    out["station"] = out["station"] or _after_alt(txt, "Current Station")
                    out["system"] = out["system"] or _after_alt(txt, "Current Solar System")
                elif name == "headerLabelSecStatus":
                    m = re.search(r">\s*([0-9]+(?:\.[0-9]+)?)\s*<", txt)
                    if m:
                        try:
                            out["security"] = float(m.group(1))
                        except ValueError:
                            pass
        return out

    def route(self) -> dict[str, Any]:
        """Route đang set: destination text (nếu có) + số marker autopilot."""
        # Ground 2026-11-09 (tests/fixtures/ui_tree_route_set.json):
        #   EveCaptionSmall 'Route <fontsize=12>1 Jump'  -> jumps
        #   EveLabelMedium  '<a href=showinfo:5//<id> alt= Next System in Route >Nourvukaiken</a>...'
        #   -> next_system (= dich khi con 1 jump). Caption KHONG phai ten dich.
        out: dict[str, Any] = {"destination": None, "next_system": None, "jumps": None,
                               "markers": 0}
        panels = self._find_type("InfoPanelRoute")
        if not panels:
            return out
        for n in self.eye.walk(panels[0]):
            a = n.get("attrs", {}) or {}
            if a.get("_name") == "noDestinationLabel":
                if _strip_tags(a.get("_setText", "")).lower() == "no destination":
                    return out
            if n.get("type") == "AutopilotDestinationIcon":
                out["markers"] += 1
        for _name, txt in self._labels(panels[0]):
            s = str(txt)
            if _strip_tags(s).strip().lower() == "no destination":
                return {**out, "markers": 0}
            mj = re.search(r"^\s*Route\b.*?(\d+)\s+Jumps?", _strip_tags(s), re.I)
            if mj and out["jumps"] is None:
                out["jumps"] = int(mj.group(1))
            mn = re.search(r"alt=\s*Next System in Route\s*>([^<]+)<", s)
            if mn and out["next_system"] is None:
                out["next_system"] = mn.group(1).strip()
        if out["jumps"] == 1 and out["next_system"]:
            out["destination"] = out["next_system"]
        return out

    # ---------------- agent / mission ----------------
    def agent_dialogue(self) -> list[str]:
        """Text của AgentDialogueWindow (đang nói chuyện với agent)."""
        wins = self._find_type("AgentDialogueWindow")
        if not wins:
            return []
        texts: list[str] = []
        for w in wins:
            for _, txt in self._labels(w):
                clean = _strip_tags(txt)
                if clean and clean not in texts:
                    texts.append(clean)
        return texts

    # Ground client TQ 2026-11-09 (dumps/g3_accepted_170325.json): sau Accept, mission
    # nằm ở InfoPanelJobBoard → AgentMissionInfoPanelEntry (_name='agent_missions:<agentID>'),
    # tiêu đề ở EveLabelLarge._setText. InfoPanelAgentMissions/MissionEntry là layout cũ (fallback).
    MISSION_PANEL_TYPES = ("InfoPanelJobBoard", "InfoPanelAgentMissions")
    MISSION_ENTRY_TYPES = ("AgentMissionInfoPanelEntry", "MissionEntry")

    def mission_entries(self) -> list[str]:
        """Tiêu đề các mission đang active trong info panel (rỗng nếu không thấy)."""
        out: list[str] = []
        for ptype in self.MISSION_PANEL_TYPES:
            for panel in self._find_type(ptype):
                for n in self.eye.walk(panel):
                    if n.get("type") not in self.MISSION_ENTRY_TYPES:
                        continue
                    texts = [_strip_tags(t) for _, t in self._labels(n)]
                    texts = [t for t in texts if t]
                    if texts and texts[0] not in out:
                        out.append(texts[0])
        return out

    # ---------------- overview: gate / beacon ----------------
    def _overview(self) -> list[dict[str, Any]]:
        return self.eye.overview_entries()

    def hostiles(self) -> list[dict[str, Any]]:
        """Entry overview là QUÁI thật (classify từ rats.py), không phải station/gate.

        Đây là khác biệt sống-còn: 'có selected item' ≠ 'đang trong combat'
        (ở Jita chọn stargate cũng có SelectedItemWnd).
        """
        from .rats import classify
        out = []
        for e in self._overview():
            name = e.get("Name") or ""
            if not name:
                continue
            c = classify(name)
            is_npc = c.get("faction") is not None or c.get("hull") is not None
            if is_npc:
                out.append({"name": name, "faction": c.get("faction"),
                            "hull": c.get("hull"), "priority": c.get("priority"),
                            "skip": c.get("skip"), "center": e.get("center"),
                            "distance": e.get("Distance")})
        return out

    def gate_entries(self) -> list[dict[str, Any]]:
        """Entry overview là acceleration gate (site có nhiều pocket)."""
        out = []
        for e in self._overview():
            name = (e.get("Name") or "").lower()
            if _GATE_NAME in name:
                out.append({"name": e.get("Name"), "center": e.get("center"),
                            "distance": e.get("Distance")})
        return out

    def mission_beacons(self) -> list[dict[str, Any]]:
        """Entry overview trông giống beacon mission/deadspace."""
        out = []
        for e in self._overview():
            name = (e.get("Name") or "").lower()
            typ = (e.get("Type") or "").lower()
            if any(h in name for h in _MISSION_HINTS) or "beacon" in typ:
                out.append({"name": e.get("Name"), "type": e.get("Type"),
                            "center": e.get("center"), "distance": e.get("Distance")})
        return out

    # ---------------- tổng hợp ----------------
    def state(self) -> MissionState:
        st = MissionState()
        st.hp = self.eye.ship_health()
        st.cap = self.eye.capacitor_percent()
        st.speed = self.eye.speed_mps()
        if st.hp is None:
            # không có ShipUI = đang ở trong station (hoặc màn hình chưa vào game)
            if self.eye.ship_ui() is None:
                st.in_station = True
        loc = self.location()
        st.station, st.system, st.security = loc["station"], loc["system"], loc["security"]
        if st.station:
            st.in_station = True
        rt = self.route()
        st.route_destination, st.route_markers = rt["destination"], rt["markers"]
        st.agent_dialogue = self.agent_dialogue()
        st.mission_entries = self.mission_entries()
        st.gates = self.gate_entries()
        st.mission_beacons = self.mission_beacons()
        ov = self._overview()
        st.overview_count = len(ov)
        st.targets = 1 if self.eye.selected_item() else 0

        # phase suy ra từ dữ liệu thật
        hostiles = self.hostiles()
        if st.in_station:
            st.phase = "DOCKED"
        elif hostiles:
            st.phase = "AT_SITE"          # có quái thật trong overview
        elif st.gates:
            # có gate mà không còn quái → pocket đã clear
            st.phase = "POCKET_CLEAR"
        elif st.mission_beacons:
            st.phase = "IN_SPACE"         # đang bay tới beacon
        else:
            st.phase = "IN_SPACE"

        # ghi chú những gì chưa ground được (không đoán)
        if st.in_station and not st.agent_dialogue:
            st.notes.append("chưa ground AgentsPanel entry + AgentDialogueWindow button "
                            "(cần mở agent trong station để dump)")
        if st.phase == "AT_SITE":
            st.notes.append(f"{len(hostiles)} quái trong overview — combat brain xử")
        if st.phase != "DOCKED" and not st.mission_beacons and not st.gates:
            st.notes.append("không thấy beacon mission/gate trong overview — có thể chưa "
                            "accept mission hoặc overview filter khác")
        return st

    # ---------------- verify (dùng cho control.ActionSpec) ----------------
    def verify_warp(self) -> bool:
        """Đang warp/align: speed > 0 hoặc maneuver warp."""
        man = self.eye.maneuver()
        if isinstance(man, str) and man in ("warp", "alignto"):
            return True
        sp = self.eye.speed_mps()
        return bool(sp and sp > 0)

    def verify_docked(self) -> bool:
        return self.eye.ship_ui() is None


# ---------------------------------------------------------------- FSM
class MissionRunner:
    """FSM mission — trả list action (chưa bấm). Bot/CLI gọi next_actions() rồi execute.

    Mỗi action: {"do": <tên action control.py>, ...} — KHÔNG tự bấm ở đây để test được.
    """

    def __init__(self, me: MissionEye, orbit_km: float = 2500) -> None:
        self.me = me
        self.orbit_km = orbit_km
        self.stage = "IDLE"
        self.menu_plan: list[tuple[str, str | None]] = []   # [(entry, submenu_entry)]

    def plan_warp_to(self, entry_name: str) -> None:
        """Lên kế hoạch warp qua context menu: Warp to Within → 0 m (ground menu thật).

        Menu EVE thật (2026-11-09): 'Warp to Within' có submenu khoảng cách; dùng
        cấp 1 = 'Warp to Within', cấp 2 = 'Within 0 m'. Nếu client hiện 'Warp To'
        trực tiếp thì đặt submenu=None.
        """
        self.menu_plan = [("Warp to Within", "Within 0 m")]

    def next_actions(self) -> list[dict[str, Any]]:
        st = self.me.state()
        acts: list[dict[str, Any]] = []
        eye = self.me.eye

        # Menu đang mở → ưu tiên xử menu (nếu không sẽ bấm loạn lên UI khác).
        # Ground 2026-11-09: menu hiện sau 1-2 s, nên phải POLL chứ không sleep cứng.
        menus = eye.context_menus()
        if menus:
            # menu mở mà không có kế hoạch → đóng cho sạch (Esc), tránh bấm nhầm
            if not self.menu_plan:
                # KHÔNG dùng ESC (mở Settings). Click vùng trống để đóng.
                return [{"do": "dismiss_menu", "at": eye.empty_point(),
                         "why": "menu mở ngoài kế hoạch — click vùng trống để đóng"}]
            name, sub = self.menu_plan[0]
            if sub:
                xy = eye.menu_entry_xy(sub, exact=False)
                if xy is None:
                    # cần hover cấp 1 để submenu bung ra
                    parent = eye.menu_entry_xy(name, exact=False)
                    if parent is None:
                        self.menu_plan.clear()
                        return [{"do": "blocked",
                                 "why": f"menu mở nhưng không có '{name}'",
                                 "needs": "kiểm tra lại entry menu"}]
                    return [{"do": "hover_menu", "text": name, "at": parent,
                             "why": f"hover '{name}' để submenu '{sub}' bung ra"}]
                self.menu_plan.pop(0)
                return [{"do": "menu_entry", "text": sub, "at": xy,
                         "why": "submenu entry đọc từ ContextMenu"}]
            xy = eye.menu_entry_xy(name, exact=False)
            if xy is None:
                self.menu_plan.clear()
                return [{"do": "blocked",
                         "why": f"menu đang mở nhưng không có entry '{name}'",
                         "needs": "kiểm tra lại tên entry trong menu"}]
            self.menu_plan.pop(0)
            return [{"do": "menu_entry", "text": name, "at": xy,
                     "why": "entry đọc từ ContextMenu (ground 2026-11-09)"}]

        if st.phase == "DOCKED":
            if not st.agent_dialogue and not st.mission_entries:
                self.stage = "NEED_AGENT"
                acts.append({"do": "blocked",
                             "why": "trong station nhưng chưa mở agent — AgentsPanel/"
                                    "AgentDialogueWindow chưa ground, không bấm mù",
                             "needs": "dump UI khi mở agent conversation"})
            elif st.mission_entries and st.agent_dialogue:
                self.stage = "AT_AGENT"
                acts.append({"do": "blocked",
                             "why": "có mission entry + dialog agent — nút Accept/Request "
                                    "chưa ground (chưa dump)",
                             "needs": "dump UI của AgentDialogueWindow có nút"})
            else:
                self.stage = "READY_UNDOCK"
                sw = self.me.eye.station_window()
                if sw and sw.get("undock"):
                    acts.append({"do": "undock", "at": sw["undock"]["center"],
                                 "why": "UndockButton đọc từ LobbyWnd (ground 2026-11-09)"})
                else:
                    acts.append({"do": "blocked",
                                 "why": "không thấy LobbyWnd/UndockButton trong UI tree",
                                 "needs": "mở station window (LobbyWnd)"})
            return acts

        if st.phase == "IN_SPACE":
            if st.mission_beacons:
                self.stage = "WARP_SITE"
                b = st.mission_beacons[0]
                self.plan_warp_to(b["name"])
                acts.append({"do": "open_menu", "at": b["center"], "label": b["name"],
                             "why": "mở context menu trên beacon → Warp to Within"})
            elif st.route_destination:
                self.stage = "WARP_ROUTE"
                acts.append({"do": "warp_route", "why": f"route → {st.route_destination}"})
            else:
                self.stage = "NO_TARGET"
                acts.append({"do": "blocked",
                             "why": "ngoài space nhưng không có beacon mission hay route",
                             "needs": "accept mission trước, hoặc set destination"})
            return acts

        if st.phase == "AT_SITE":
            self.stage = "FIGHT"
            acts.append({"do": "fight", "why": "có target/pocket — combat brain xử"})
            if st.gates:
                acts.append({"do": "gate", "label": st.gates[0]["name"],
                             "why": "pocket sạch → đi gate"})
            return acts

        if st.phase == "POCKET_CLEAR":
            self.stage = "GATE"
            acts.append({"do": "gate", "label": st.gates[0]["name"],
                         "why": "còn gate, không còn target"})
            return acts

        self.stage = "UNKNOWN"
        acts.append({"do": "blocked", "why": f"phase {st.phase} không xử lý"})
        return acts
