"""LiveSecurityRunner — kết nối SecurityMode với EVE client thật qua Eye + Control.

Đọc dữ liệu qua WorldSnapshot + MissionEye + AgentEye (read-only).
Thực thi bằng control (keybinds / scan-codes / click đã ground).
Tuân thủ nghiêm ngặt Fail-Closed: thiếu dữ liệu hoặc bị che -> dừng an toàn, không bấm mù.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any

from .. import control as ctl
from ..agent import AgentEye, agents_panel
from ..eye import Eye
from ..mission import MissionEye
from ..win import find_client_window, focus, is_foreground
from ..world_snapshot import parse_world

logger = logging.getLogger("fila_bot.live_security")


def mission_system_from_text(text: str | None) -> str | None:
    """The system the game's objective tells us to travel to.

    Ground LIVE 2026-11-12 18:27: the tracker said "You need to travel to
    <a href=showinfo:5//30001399 >Elonaya</a> 0.7". The label is the SYSTEM name.
    Only the showinfo:5 form is accepted (system icon class) — never free text,
    because a wrong guess would warp to a planet or moon.
    """
    if not text:
        return None
    raw = str(text)
    if not re.search(r"showinfo:5//\d+", raw):
        return None
    label = re.search(r">([^<>]+)</a>", raw)
    name = label.group(1).strip() if label else None
    return name or None


def resolve_home_travel(entries: list[dict[str, Any]], docked: bool,
                        home_station: str | None,
                        home_system: str | None) -> tuple[bool | None, Any]:
    """Locate the way back to the profile's home system, or say UNKNOWN.

    Ground LIVE 2026-11-12 16:05 (Elonaya): the overview listed
    "Piak | Stargate (Caldari System)" at 12 km while the home station is in Piak.
    The only acceptable target is a stargate whose name is EXACTLY the home
    system — a neighbouring gate (Litiura, Nonni) is a different system and must
    never be used to "make progress".
    """
    if not home_system:
        return None, None
    if docked:
        return True, None        # đang ở trạm home: không cần đi đâu
    gates = [e for e in (entries or [])
             if "stargate" in str(e.get("Type") or "").lower()
             and str(e.get("Name") or "").strip().casefold()
             == str(home_system).strip().casefold()]
    stations = [e for e in (entries or [])
                if "station" in str(e.get("Type") or "").lower()
                and home_station
                and str(e.get("Name") or "").strip().casefold()
                == str(home_station).strip().casefold()]
    gate_xy = gates[0].get("center") if len(gates) == 1 else None
    return bool(stations), gate_xy


class LiveSecurityRunner:
    """World provider + Action executor cho SecurityMode trên EVE client thật."""

    def __init__(self, eye: Eye, dry: bool = True, default_agent: str | None = None,
                 profile: dict[str, Any] | None = None) -> None:
        self.eye = eye
        self.dry = dry
        self.profile = profile or None
        self.default_agent = (self.profile or {}).get("agent_name") or default_agent
        self.win = None
        self._cached_home_station: str | None = (self.profile or {}).get("home_station")
        self._cached_agent_chat_xy: tuple[int, int] | None = None
        self._drones_out: bool = False
        self._locked_target_xy: tuple[int, int] | None = None
        self._weapons_firing: bool = False
        self._afterburner_on: bool = False
        self.weapon_slots: tuple[int, ...] = tuple(
            (self.profile or {}).get("weapon_slots") or (1, 2, 3, 4))
        self.propulsion_slot: int | None = (
            (self.profile or {}).get("afterburner_slot")
            if isinstance((self.profile or {}).get("afterburner_slot"), int) else None)
        self._inv_eye: Any = None                # InventoryEye lazy
        self._courier_delivered: bool = False    # courier đã giao (đóng lại khi nhận mới)
        # Courier delegate: runner con dùng chung eye (Distribution đã ground load/giao)
        self.dist_runner: Any = None
        # Bang chung travel da doc duoc trong phien (offer co objective/link toa do).
        self._grounded_travel_titles: set[str] = set()

    def refresh(self) -> dict[str, Any]:
        """Đọc toàn bộ thế giới game thật -> world dict cho SecurityMode.tick()."""
        if hasattr(self.eye, "dll") and self.eye.dll is not None:
            self.eye.refresh()
        snap = parse_world(self.eye)

        # 1. E-STOP khi mất mạng
        if snap.connection_lost:
            return {
                "docked": snap.docked,
                "station": snap.station,
                "connection_lost": True,
                "popup": "Connection to server was lost",
            }

        # 2. Lưu trạm xuất phát (home station) để về trả mission
        if snap.docked and snap.station:
            if not self._cached_home_station:
                self._cached_home_station = snap.station

        # 3. Agent & Dialogue
        offer = None
        agents = []
        if snap.docked:
            agents = agents_panel(self.eye) or []
            if snap.agent_dialog.open:
                ae = AgentEye(self.eye)
                offer = ae.read_offer()

        # 4. Mission status & Overview (beacons, hostiles, gates)
        me = MissionEye(self.eye)
        mission_panel_observed, mission_titles = me.mission_entries_observation()
        missions = mission_titles or []
        hostiles = me.hostiles() if not snap.docked else []
        gates = me.gate_entries() if not snap.docked else []
        # Ground 11-11: KHONG warp vao "Celestial Beacon" bat ky (Derelict Ruins).
        # Chi nhan entry neu ten khop site da doc tu objective/SelectedItemWnd.
        site_hint = (offer or {}).get("site_hint")
        beacons = me.mission_beacons(site_hint) if not snap.docked else []

        # 4b. Phan loai EXECUTION support — KHONG suy courier tu cargo_m3/dropoff
        # hay keyword trong title (P0 11-11). Bang chung:
        #  - AgentEye.read_offer(): "Transport Objective" / "Bring Item Objective"
        #    doc tu chinh briefing TQ that.
        #  - CCP SDE build 3682781: "Cargo Delivery" la killMission co item
        #    objective (dumps/g10_turnin_dialog.json = agent SECURITY L1, co nut
        #    Complete). Truoc day no bi gan courier -> block TRUOC nut Accept.
        from ..agent import mission_location_link
        from ..missions_db import (classify_security_mission, grounded_combat_objective,
                                  normalize_title, template_kind)
        from ..travel import read_world as travel_world
        active_title = ((offer or {}).get("title")
                        or (missions[0] if missions else None))
        mission_is_courier = bool(
            (offer or {}).get("type") == "courier"
            or template_kind(active_title) == "courier")
        mission_support = classify_security_mission(active_title)
        # Bang chung combat objective tu CHINH briefing live ("Engage any hostiles")
        # cho phep bot undock/di chuyen, nhung KHONG cap quyen ban. Quyen ban van
        # nam o authorize_security_targets (can title trong catalog + faction ID).
        # Giay phep di chuyen ton tai ca khi hoi thoai da dong (cold start):
        # bang chung objective da duoc dump tu client that, luu trong catalog co source.
        # Boss 11-11: "cu nhan mission, undock warp den noi lam mission" -> co link
        # toa do trong briefing la bang chung duong tinh co noi can den.
        mission_link_xy = mission_location_link(self.eye) if snap.docked else None
        if offer and ((offer.get("objective_kind") == "combat") or mission_link_xy):
            title_key = normalize_title(offer.get("title"))
            if title_key:
                self._grounded_travel_titles.add(title_key)
        # BANG CHUNG CUA GAME (ground 11-11, scratch/live_current_tree.json):
        # panel Opportunities / AgentMissionInfoPanelEntry hien
        # "Encounter (Deadspace)" + "You need to travel to Josameto 0.6" +
        # nut "Set Destination". Day la loai mission do chinh client bao, khong
        # can title co trong whitelist. No chi cap quyen DI CHUYEN (undock/warp),
        # KHONG cap quyen ban — authorize_security_targets() van giu nguyen.
        mp = self.eye.mission_panel_observation()
        from ..mission_target import resolve_objective_target
        overview_now = self.eye.overview_entries() if not snap.docked else []
        mission_target = resolve_objective_target(
            (mp or {}).get("objective_text"), overview_now)
        mission_type_label = (mp or {}).get("type_label")
        mission_location_text = (mp or {}).get("location_text")
        mission_location_button = (mp or {}).get("location_button")
        panel_evidence_travel = bool(
            mission_type_label
            and ("encounter" in mission_type_label.lower()
                 or "deadspace" in mission_type_label.lower()))
        mission_travel_support = bool(
            (offer or {}).get("objective_kind") == "combat"
            or grounded_combat_objective(active_title) is not None
            or mission_link_xy is not None
            or normalize_title(active_title) in self._grounded_travel_titles
            or panel_evidence_travel)
        travel = travel_world(self.eye)
        cargo_loaded = None
        cargo_empty_now = None
        if snap.docked and mission_is_courier:
            ie = getattr(self, "_inv_eye", None)
            if ie is None:
                from ..inventory import InventoryEye
                ie = InventoryEye(self.eye)
                self._inv_eye = ie
            if ie.window() is not None:
                cap = ie.capacity() or {}
                used = cap.get("used")
                free = cap.get("free")
                if isinstance(used, (int, float)) and used > 0.01:
                    cargo_loaded = True     # đang có hàng trong kho
                elif isinstance(free, (int, float)):
                    cargo_loaded = False
            # Đã giao: mission courier vẫn pending nhưng offer có Complete mà
            # hàng ĐÃ rời kho (đã load rồi lại rỗng sau undock vòng trước)
            if self._courier_delivered and ie.window() is not None:
                cargo_empty_now = True

        # 5. Station window (để undock)
        sw = self.eye.station_window() if snap.docked else None
        undock_xy = sw.get("undock", {}).get("center") if sw else None

        # Counts observed in the real DronesWindow; missing remains UNKNOWN.
        drones_in_space = snap.drones_in_space
        mods = self.eye.module_buttons() if not snap.docked else []
        # Ground LIVE 2026-11-12 (Gila, Piak): the real HUD exposes each slot's
        # state. High 2-5 = RLML II read `false`; Med 1 = 10MN Afterburner II and
        # the hardeners read `null` — a null is UNKNOWN and must never be toggled
        # blind (pressing Alt-F1 on an already-running AB turns it OFF).
        module_state: dict[str, dict[int, bool | None]] = {"high": {}, "med": {}, "low": {}}
        for m in mods:
            rack, idx = m.get("rack"), m.get("index")
            if rack in module_state and isinstance(idx, int):
                module_state[rack][idx] = m.get("is_active")
        high4 = [m for m in mods if m.get("rack") == "high"
                 and m.get("index") in self.weapon_slots]
        hstates = [m.get("is_active") for m in high4]
        weapons_active = (True if hstates and all(s is True for s in hstates)
                          else False if any(s is False for s in hstates) else None)
        prop_slot = (self.profile or {}).get("afterburner_slot")
        prop_observed = (module_state["med"].get(prop_slot)
                         if isinstance(prop_slot, int) else None)
        defense_slots = [s for s in ((self.profile or {}).get("defense_slots") or [])
                         if isinstance(s, int)]
        defense = [{"slot": s, "observed": module_state["med"].get(s)}
                   for s in defense_slots]
        afterburner_on = (prop_observed if prop_observed is not None
                          else self._afterburner_on)

        # Ground LIVE 2026-11-12 16:05 (Elonaya): after the mission the ship sat
        # in another system whose overview lists "Piak | Stargate (Caldari
        # System)" at 12 km. ESI route 30001399 -> 30001403 is a single hop, so
        # going home means jumping THAT gate. Resolve it from the game's own
        # overview by exact system name; never pick a random stargate.
        home_system = (self.profile or {}).get("home_system")
        try:
            _entries = self.eye.overview_entries() or []
        except Exception:  # noqa: BLE001 — sim eye
            _entries = []
        home_in_system, home_gate_xy = resolve_home_travel(
            _entries, snap.docked, self._cached_home_station, home_system)

        # Ground LIVE 2026-11-12 18:27 (Piak): mission 'Eliminate the Pirate
        # Campers' is in Elonaya 0.7 and the tracker says "You need to travel to
        # Elonaya" with a 'Warp to Location' button — but that button only warps
        # inside the CURRENT system, so the ship never left Piak. The way out is
        # the stargate the overview names after the mission's system.
        mission_system = mission_system_from_text(
            (mp or {}).get("objective_text") or (mp or {}).get("location_text"))
        mission_gate_xy = None
        if mission_system and not snap.docked:
            gates = [e for e in _entries
                     if "stargate" in str(e.get("Type") or "").lower()
                     and str(e.get("Name") or "").strip().casefold()
                     == str(mission_system).strip().casefold()]
            if len(gates) == 1:
                mission_gate_xy = gates[0].get("center")

        return {
            "docked": snap.docked if snap.location_known else None,
            "location_state": snap.location_state,
            "location_known": snap.location_known,
            "snapshot_valid": isinstance(self.eye.root, dict) and bool(self.eye.root),
            "station": snap.station,
            "home_station": self._cached_home_station,
            "agent_name": self.default_agent,
            "profile_agent_id": (self.profile or {}).get("agent_id"),
            "system": snap.system,
            "security": snap.security,
            "connection_lost": False,
            "agents": agents,
            "agent_dialog_open": snap.agent_dialog.open,
            "offer": offer,
            "missions": missions if mission_panel_observed else None,
            "has_active_mission": bool(missions) if mission_panel_observed else None,
            "hostiles": hostiles,
            "protected_contacts": (me.protected_contacts() if not snap.docked else []),
            "gates": gates,
            "beacons": beacons,
            "ship_health": snap.ship_health,
            "capacitor_percent": snap.capacitor_percent,
            "speed_mps": snap.speed_mps,
            "maneuver": snap.maneuver,
            "undock_xy": undock_xy,
            "drones_in_space": drones_in_space,
            "drones_in_bay": snap.drones_in_bay,
            "drone_panel_observed": snap.drone_panel_observed,
            "drones_out": (drones_in_space > 0) if drones_in_space is not None else None,
            "weapons_firing": self._weapons_firing,
            "weapons_active": weapons_active,
            "locked_target": (None if snap.docked else self._locked_observation()),
            "target_bar_supported": self._target_bar_supported(),
            "modules_observed": bool(mods),
            "module_state": module_state,
            "propulsion_slot": prop_slot,
            "propulsion_observed": prop_observed,
            "defense_modules": defense,
            "home_system": home_system,
            "home_in_system": home_in_system,
            "home_gate_xy": home_gate_xy,
            "mission_system": mission_system,
            "mission_gate_xy": mission_gate_xy,
            "afterburner_on": afterburner_on,
            "_agent_eye": AgentEye(self.eye) if snap.docked else None,
            "mission_is_courier": mission_is_courier,
            "mission_support": mission_support,
            "mission_travel_support": mission_travel_support,
            "mission_link_xy": mission_link_xy,
            "mission_site_hint": site_hint,
            "mission_type_label": mission_type_label,
            "mission_location_text": mission_location_text,
            "mission_objective_text": (mp or {}).get("objective_text"),
            "mission_target": mission_target,
            "objective_complete": (mp or {}).get("objective_complete"),
            "mission_agent_id": (mp or {}).get("agent_id"),
            "mission_location_button": mission_location_button,
            "mission_panel_title": (mp or {}).get("title"),
            "space_menu": (self.eye.context_menus() or []) if not snap.docked else [],
            "empty_xy": (self.eye.empty_point() if not snap.docked else None),
            "travel": travel,
            "active_mission_title": active_title,
            "mission_panel_observed": mission_panel_observed,
            "cargo_loaded": cargo_loaded,
            "cargo_empty_now": cargo_empty_now,
            "modal": snap.modal,
        }

    def _locked_observation(self) -> dict[str, Any] | None:
        """The client's active target, or None when it cannot be told.

        Ground 2026-11-12: `TargetInBar` / `ActiveTargetOnBracket` do not exist in
        this reader build, and the target bar is only rendered while something is
        locked — so "no node" cannot be read as "no lock". The FSM treats None as
        UNKNOWN and falls back to its bounded one-shot behaviour instead of
        blocking a mission it is executing correctly.
        """
        try:
            if not self.eye.targets_observable():
                return None
            return self.eye.locked_target()
        except Exception:  # noqa: BLE001 — sim eye
            return None

    def _target_bar_supported(self) -> bool:
        """True only when this eye can actually read the target bar.

        A sim/legacy eye has no `targets_in_bar`, so "no lock" there means
        "cannot tell" — the FSM must keep its old behaviour instead of blocking.
        """
        return callable(getattr(self.eye, "targets_in_bar", None))

    def _resolve_lock_target(self, target_id: Any, target_name: Any) -> tuple[int, int] | None:
        """Refresh the live overview and resolve one row by exact client object ID."""
        if (not isinstance(target_id, int) or isinstance(target_id, bool)
                or target_id <= 0):
            return None
        refresh = getattr(self.eye, "refresh", None)
        entries = getattr(self.eye, "overview_entries", None)
        if not callable(refresh) or not callable(entries):
            return None
        try:
            if refresh() is None:
                return None
            rows = entries()
            if not isinstance(rows, list):
                return None
            matches = [e for e in rows
                       if isinstance(e, dict) and e.get("object_id") == target_id]
            if len(matches) != 1:
                return None
            row = matches[0]
            if target_name and str(row.get("Name") or "").strip().casefold() != \
                    str(target_name).strip().casefold():
                return None
            xy = row.get("center")
            if (not isinstance(xy, (tuple, list)) or len(xy) != 2
                    or any(not isinstance(v, int) or isinstance(v, bool) for v in xy)):
                return None
            return int(xy[0]), int(xy[1])
        except Exception:  # noqa: BLE001 — stale/partial client tree fails closed
            return None

    def apply(self, acts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Thực thi danh sách action do SecurityMode phát ra trên game client."""
        if not acts:
            return []

        if not self.dry and self.win is None:
            self.win = find_client_window()
            if self.win:
                focus(self.win)
                # Read-back is performed by the next supervisor snapshot.

        if not self.dry and self.win is not None and not is_foreground(self.win):
            note = ("EVE client is not foreground — refusing to send input "
                    "(owner may be using another window)")
            return [{"act": a.get("do"), "ok": False, "verified": False,
                     "status": "INPUT_NOT_OWNED", "note": note} for a in acts]

        res = []

        def _execute(spec, **kwargs):
            # Delivery result is propagated. Do not self-confirm game state.
            if r.get("status") in ("FAILED", "CANCELLED"):
                return r
            result = ctl.execute(spec, **kwargs)
            r.update(result)
            return result

        for a in acts:
            kind = a.get("do")
            r: dict[str, Any] = {"act": kind, "ok": False, "verified": False, "status": "NOT_SENT"}

            if kind == "open_agent_chat":
                xy = a.get("at")
                if xy:
                    spec = ctl.ActionSpec("open_agent_chat", [{"do": "click", "at": xy}])
                    _execute(spec, eye=self.eye, dry=self.dry, win=self.win)
                    # Read-back is performed by the next supervisor snapshot.

            elif kind == "accept_mission":
                xy = a.get("at")
                if xy:
                    spec = ctl.ActionSpec("accept_mission", [{"do": "click", "at": xy}])
                    _execute(spec, eye=self.eye, dry=self.dry, win=self.win)
                    # Read-back is performed by the next supervisor snapshot.

            elif kind == "request_mission":
                # Hội thoại lần đầu: tìm nút theo TÊN thật (catalog TQ: có Request
                # Mission_Button ở một số dialog) rồi fallback text 'request mission'.
                xy = None
                try:
                    ae = AgentEye(self.eye)
                    xy = ae.button_xy("request")
                except Exception:  # noqa: BLE001 — thiếu eye (sim) -> bỏ qua
                    xy = None
                if xy:
                    spec = ctl.ActionSpec("request_mission", [{"do": "click", "at": xy}])
                    _execute(spec, eye=self.eye, dry=self.dry, win=self.win)
                    # Read-back is performed by the next supervisor snapshot.

            elif kind == "quit_mission":
                xy = a.get("at")
                if xy:
                    spec = ctl.ActionSpec("quit_mission", [{"do": "click", "at": xy}])
                    _execute(spec, eye=self.eye, dry=self.dry, win=self.win)
                    # Read-back is performed by the next supervisor snapshot.

            elif kind == "decline_mission":
                xy = a.get("at")
                if xy:
                    spec = ctl.ActionSpec("decline_mission", [{"do": "click", "at": xy}])
                    _execute(spec, eye=self.eye, dry=self.dry, win=self.win)
                    # Read-back is performed by the next supervisor snapshot.

            elif kind == "load_cargo":
                # Courier: mở Inventory (nếu chưa) rồi kéo item mission vào ShipHangar.
                # Tái dùng logic của LiveDistributionRunner (pick_item_xy).
                from .live_distribution import pick_item_xy
                from ..inventory import InventoryEye
                spec = None
                ie = self._inv_eye or InventoryEye(self.eye)
                self._inv_eye = ie
                offer0 = AgentEye(self.eye).read_offer() or {} if self.eye.root else {}
                item_name = offer0.get("cargo_item")
                if ie.window() is None:
                    btn = self.eye._find_by_type("ButtonInventory", select_many=True)
                    if btn:
                        spec = ctl.act_menu_entry(self.eye.abs_center(btn[0]))
                        _execute(spec, eye=self.eye, dry=self.dry, win=self.win)
                        # Read-back is performed by the next supervisor snapshot.
                    # Wait for an observed open inventory on the next snapshot.
                else:
                    hangars = {e2["name"]: e2["center"] for e2 in (ie.tree_entries() or [])}
                    ship_hangar_xy = hangars.get("ShipHangar")
                    items = ie.items() or []
                    item_xy = pick_item_xy(items, item_name or "")
                    if item_xy is None:
                        r["ok"] = False
                        r["note"] = (f"khong thay item mission {item_name!r} trong "
                                     f"ItemHangar ({len(items)} items) — fail-closed, không kéo bua")
                        logger.warning("load_cargo: %s", r["note"])
                    elif ship_hangar_xy:
                        spec = ctl.act_drag_item(item_xy, ship_hangar_xy)
                    else:
                        r["ok"] = False
                        r["note"] = "khong thay ShipHangar trong Inventory tree"
                if spec is not None:
                    _execute(spec, eye=self.eye, dry=self.dry, win=self.win)
                    # Read-back is performed by the next supervisor snapshot.

            elif kind == "close_dialog":
                # Đóng AgentDialog (nút CloseAgentConversation_Button) — nó đè nút Undock
                xy = a.get("at")
                if xy:
                    spec = ctl.act_menu_entry(xy)
                    _execute(spec, eye=self.eye, dry=self.dry, win=self.win)
                    # Read-back is performed by the next supervisor snapshot.

            elif kind == "dismiss_modal":
                # Modal chặn (Cannot Complete Mission...): bấm OK để đóng
                xy = a.get("at")
                if xy:
                    spec = ctl.act_menu_entry(xy)
                    _execute(spec, eye=self.eye, dry=self.dry, win=self.win)
                    # Read-back is performed by the next supervisor snapshot.

            elif kind == "complete_mission":
                xy = a.get("at")
                if xy:
                    spec = ctl.ActionSpec("complete_mission", [{"do": "click", "at": xy}])
                    _execute(spec, eye=self.eye, dry=self.dry, win=self.win)
                    # Read-back is performed by the next supervisor snapshot.

            elif kind == "undock":
                xy = a.get("at")
                spec = ctl.act_undock_at(xy) if xy else ctl.act_undock()
                res_u = _execute(spec, eye=self.eye, dry=self.dry, win=self.win)
                logger.info("undock: xy=%s ok=%s log=%s", xy, res_u.get("ok"),
                            res_u.get("input_log"))
                if not res_u.get("ok"):
                    logger.warning("undock KHÔNG hiệu lực: %s", res_u.get("fail"))
                # Courier đã load hàng -> sau khi undock bay giao, hàng rời kho
                # Read-back is performed by the next supervisor snapshot.

            elif kind == "warp_beacon":
                xy = a.get("at")
                # Overview entry mission: warp = giữ S + click? Không — S là hotkey
                # "Warp to" khi entry ĐÃ chọn. act_warp_to đã click + S đúng chuẩn.
                spec = ctl.act_warp_to(xy)
                _execute(spec, eye=self.eye, dry=self.dry, win=self.win)
                # Read-back is performed by the next supervisor snapshot.

            elif kind == "orbit_site":
                xy = a.get("at")
                spec = ctl.act_orbit(xy, distance_km=30)
                _execute(spec, eye=self.eye, dry=self.dry, win=self.win)

            elif kind == "toggle_ab":
                # Slot lấy từ profile (afterburner_slot), không hard-code Mid 1:
                # live 11-12 profile ghi AB ở Med 1 nhưng fit khác có thể khác.
                slot = a.get("slot") or self.propulsion_slot or 1
                spec = ctl.act_module(int(slot), rack="mid")
                _execute(spec, eye=self.eye, dry=self.dry, win=self.win)

            elif kind == "toggle_defense":
                slot = a.get("slot")
                if isinstance(slot, int):
                    spec = ctl.act_module(slot, rack="mid")
                    _execute(spec, eye=self.eye, dry=self.dry, win=self.win)
                else:
                    r["status"] = "NOT_SENT"
                    r["note"] = "toggle_defense thiếu slot — không bấm mù"

            elif kind == "lock_target":
                target_id = a.get("target_id")
                target_name = a.get("target_name")
                xy = self._resolve_lock_target(target_id, target_name)
                if xy is None:
                    r["status"] = "IDENTITY_UNRESOLVED"
                    r["note"] = ("lock không gửi: overview không có đúng một row "
                                 "fresh khớp client object ID/name")
                else:
                    spec = ctl.act_lock(xy, target_id=target_id)
                    _execute(spec, eye=self.eye, dry=self.dry, win=self.win)
                    r["target_id"] = target_id
                    r["resolved_at"] = xy
                    # This action is verified by the post-input target-bar readback.

            elif kind == "fire_weapons":
                # Press only slots OBSERVED inactive. Pressing an already-active
                # launcher toggles it OFF, and an unknown flag is not an excuse
                # to toggle. Legacy/sim eyes without module data keep F1-F4.
                mods = []
                try:
                    mods = self.eye.module_buttons() or []
                except Exception:  # noqa: BLE001 — sim eye
                    mods = []
                high = {m.get("index"): m.get("is_active") for m in mods
                        if m.get("rack") == "high"}
                observed = any(isinstance(v, bool) for v in high.values())
                targets = [s for s in self.weapon_slots if s in high]
                if observed:
                    for slot in targets:
                        state = high.get(slot)
                        if state is False:
                            _execute(ctl.act_module(slot, rack="high"),
                                     eye=self.eye, dry=self.dry, win=self.win)
                    r["note"] = (f"fire_weapons: slots {self.weapon_slots} "
                                 f"observed {high}")
                elif high:
                    # Module buttons exist but no ramp/isActive flag: pressing
                    # could toggle an already-active launcher OFF. Refuse.
                    r["status"] = "UNKNOWN_STATE"
                    r["note"] = "module state unavailable — không bấm F1-F4 mù"
                else:
                    for s in self.weapon_slots:
                        _execute(ctl.act_module(s, rack="high"),
                                 eye=self.eye, dry=self.dry, win=self.win)

            elif kind == "launch_drones":
                spec = ctl.act_launch_drones()
                _execute(spec, eye=self.eye, dry=self.dry, win=self.win)
                # Read-back is performed by the next supervisor snapshot.

            elif kind == "engage_drones":
                spec = ctl.act_drones_engage()
                _execute(spec, eye=self.eye, dry=self.dry, win=self.win)

            elif kind == "recall_drones":
                spec = ctl.act_drones_return()
                _execute(spec, eye=self.eye, dry=self.dry, win=self.win)
                # Read-back is performed by the next supervisor snapshot.

            elif kind == "approach_target":
                xy = a.get("at")
                if xy:
                    spec = ctl.act_approach(xy)
                    _execute(spec, eye=self.eye, dry=self.dry, win=self.win)
                    # Read-back: the next snapshot re-reads the objective/panel.
                    r["note"] = f"approach_target ({xy})"

            elif kind == "close_distance":
                # Combat approach must use a fresh row resolved by exact client ID;
                # the planner's previous screen coordinates may now identify another object.
                target_id = a.get("target_id")
                target_name = a.get("target_name")
                xy = self._resolve_lock_target(target_id, target_name)
                if xy is None:
                    r["ok"] = False
                    r["status"] = "IDENTITY_UNRESOLVED"
                    r["note"] = ("approach không gửi: overview không có đúng một row "
                                 "fresh khớp client object ID/name")
                else:
                    spec = ctl.act_approach(xy)
                    _execute(spec, eye=self.eye, dry=self.dry, win=self.win)
                    r["target_id"] = target_id
                    r["resolved_at"] = xy
                    r["note"] = f"close_distance → approach ({xy})"

            elif kind == "activate_gate":
                xy = a.get("at")
                if xy:
                    spec = ctl.act_gate_jump(xy)
                    _execute(spec, eye=self.eye, dry=self.dry, win=self.win)
                    # Read-back is performed by the next supervisor snapshot.

            elif kind == "jump_to_system":
                # Nhảy cổng tới hệ home: click cổng trong overview rồi bấm D
                # (Dock/Jump/Activate) — cùng cơ chế đã ground cho gate.
                xy = a.get("at")
                if xy:
                    spec = ctl.act_gate_jump(xy)
                    _execute(spec, eye=self.eye, dry=self.dry, win=self.win)
                    r["note"] = f"jump_to_system → cổng ({xy})"

            elif kind == "warp_home":
                # Về trạm home: nếu profile đã chốt tên trạm, CHỈ dock đúng trạm
                # đó. Không có profile (SIM/legacy) mới dùng entry station đầu.
                station_xy = None
                home = self._cached_home_station
                try:
                    stations = [e for e in self.eye.overview_entries()
                                if "station" in (e.get("Type") or "").lower()
                                or "station" in (e.get("Name") or "").lower()]
                    if home:
                        exact = [e for e in stations
                                 if str(e.get("Name") or "").strip().casefold()
                                 == str(home).strip().casefold()]
                        if len(exact) == 1:
                            station_xy = exact[0].get("center")
                        else:
                            # Ground LIVE 2026-11-12 16:01 (run16): after a
                            # mission in another system the home station is not
                            # in the current overview at all, so this branch
                            # repeated the same warning every tick for minutes.
                            # That is a NAVIGATION gap (need a route to the home
                            # system), not a docking decision — say so once and
                            # let the FSM stop instead of looping.
                            r["status"] = "HOME_NOT_IN_SYSTEM"
                            r["note"] = (f"home station {home!r} không có trong "
                                         f"overview hệ hiện tại ({len(exact)} entry) — "
                                         "cần route về hệ của trạm, không dock trạm khác")
                            logger.warning("warp_home: %s", r["note"])
                    elif stations:
                        station_xy = stations[0].get("center")
                except Exception as exc:  # noqa: BLE001 — missing eye in sim
                    r["note"] = f"warp_home: không đọc được overview ({exc})"
                if station_xy:
                    spec = ctl.act_hotkey_dock_jump(station_xy)
                    _execute(spec, eye=self.eye, dry=self.dry, win=self.win)
                    r["note"] = f"warp_home → {home or 'first observed station'}"
                elif not r.get("note"):
                    r["note"] = "warp_home: không thấy station trong overview — không click mù"
                    logger.warning("warp_home: %s", r["note"])

            elif kind == "warp_out":
                # Thoát hiểm khẩn cấp
                spec = ctl.ActionSpec("emergency_warp_out", [
                    {"do": "combo", "mods": ["ctrl"], "key": "SPACE"},
                    {"do": "wait", "s": 0.5},
                    {"do": "combo", "mods": [], "key": "S"},
                ])
                _execute(spec, eye=self.eye, dry=self.dry, win=self.win)

            elif kind == "set_destination":
                # Right-click link "Location <sec> <system>" trong briefing ->
                # cho menu hien -> click "Set Destination". Ground G5 / live 11-11.
                xy = a.get("at")
                if xy:
                    _execute(ctl.act_open_context_menu(xy), eye=self.eye,
                                dry=self.dry, win=self.win)
                    # Ground LIVE 11-11: menu cua link "Location <sec> <system>"
                    # co "Add Waypoint" (KHONG co "Set Destination"). Dung ca 2 ten,
                    # uu tien cai doc duoc. Khong de menu mo roi bo -> no an click Undock.
                    xy_set = None
                    if hasattr(self.eye, "dll") and self.eye.dll is not None:
                        for entry_name in ("Add Waypoint", "Set Destination"):
                            xy_set = self.eye.wait_entry(entry_name, timeout_s=3.0)
                            if xy_set:
                                break
                    if xy_set:
                        _execute(ctl.act_menu_entry(xy_set), eye=self.eye,
                                    dry=self.dry, win=self.win)
                        # Read-back is performed by the next supervisor snapshot.
                    else:
                        empty = self.eye.empty_point()
                        if empty:
                            _execute(ctl.act_click_empty(empty), eye=self.eye,
                                        dry=self.dry, win=self.win)
                        if hasattr(self.eye, "dll") and self.eye.dll is not None:
                            r["note"] = "menu link Location khong co Add Waypoint/Set Destination — da dong menu"
                            logger.warning("set_destination: %s", r["note"])
                        else:
                            r["note"] = "offline replay: bo qua doc lai menu (khong co DLL)"

            elif kind == "open_menu":
                xy = a.get("at")
                if xy:
                    _execute(ctl.act_open_context_menu(xy), eye=self.eye,
                                dry=self.dry, win=self.win)

            elif kind == "menu_entry":
                xy = a.get("at")
                if xy:
                    _execute(ctl.act_menu_entry(xy), eye=self.eye,
                                dry=self.dry, win=self.win)
                    # Read-back is performed by the next supervisor snapshot.

            elif kind == "dismiss_menu":
                empty = self.eye.empty_point()
                if empty:
                    _execute(ctl.act_click_empty(empty), eye=self.eye,
                                dry=self.dry, win=self.win)

            elif kind == "warp_to_mission":
                # Ground TQ (docs/MISSION_TRAVEL_RESEARCH_2026-11-11.md §6):
                # StatefulButton _name='missionObjective_button_location_<id>' trong
                # mission tracker; label 'Set Destination' (chua o dung he) ->
                # 'Warp to Location' (da o dung he). Doc NHAN truoc khi bam.
                # Fallback right-click empty space -> Agent Missions -> Encounter
                # (Deadspace) -> Warp to Location chi dung khi khong thay nut; text
                # menu chua ground tren TQ -> fail-closed, KHONG warp beacon.
                btn = self.eye.mission_location_button()
                blabel = (btn.get("label") or "").lower() if btn else ""
                if btn and "warp to" in blabel:
                    _execute(ctl.ActionSpec("warp_to_mission_button", [
                        {"do": "click", "at": btn["center"]}]),
                        eye=self.eye, dry=self.dry, win=self.win)
                    # Read-back is performed by the next supervisor snapshot.
                    r["note"] = (f"warp_to_mission: click tracker "
                                 f"'{btn['label']}' ({btn['name']})")
                elif btn and "set destination" in blabel:
                    # Chua o dung he: chi dat route toi HE, KHONG warp vao pocket.
                    # FSM se di theo route markers o nhung tick sau.
                    _execute(ctl.ActionSpec("set_destination_button", [
                        {"do": "click", "at": btn["center"]}]),
                        eye=self.eye, dry=self.dry, win=self.win)
                    # Read-back is performed by the next supervisor snapshot.
                    r["note"] = (f"chua o dung he — nut '{btn['label']}' da dat "
                                 f"route, KHONG warp pocket")
                elif btn and "undock" in blabel:
                    # Ground dumps/g10_turnin_dialog.json + fixture 05/06: label
                    # 'Undock' = tau con o tram. KHONG warp, khong click o day —
                    # undock thuoc action rieng cua FSM.
                    r["ok"] = True
                    r["status"] = "GUARDED"
                    r["note"] = (f"nut Location dang la '{btn['label']}' "
                                 f"(docked) — KHONG warp, cho lenh undock")
                else:
                    empty = self.eye.empty_point()
                    if not empty:
                        r["ok"] = False
                        r["note"] = "khong co nut Location va khong co vung trong de mo menu"
                    else:
                        _execute(ctl.act_open_context_menu(empty), eye=self.eye,
                                    dry=self.dry, win=self.win)
                        leaf = None
                        parent = None
                        if hasattr(self.eye, "dll") and self.eye.dll is not None:
                            self.eye.wait_menu(timeout_s=6.0)
                        for menu in self.eye.context_menus() or []:
                            for ent in menu.get("entries") or []:
                                txt = str(ent.get("text") or "")
                                low = txt.lower()
                                if "warp to location" in low or "warp to destination" in low:
                                    leaf = ent
                                elif ("agent missions" in low or "encounter" in low
                                      or "deadspace" in low):
                                    parent = ent
                        if leaf is None and parent is not None:
                            # Hover cha de mo submenu (click cha = menu sap), doc lai.
                            pxy = parent.get("center")
                            if pxy:
                                hover = ctl.ActionSpec("open_submenu", [
                                    {"do": "hover", "at": pxy, "dwell_s": 0.35}])
                                _execute(hover, eye=self.eye, dry=self.dry, win=self.win)
                                if hasattr(self.eye, "dll") and self.eye.dll is not None:
                                    self.eye.wait_menu(timeout_s=3.0)
                                for menu in self.eye.context_menus() or []:
                                    for ent in menu.get("entries") or []:
                                        if "warp to location" in str(ent.get("text") or "").lower():
                                            leaf = ent
                        if leaf and leaf.get("center"):
                            _execute(ctl.act_menu_entry(leaf["center"]), eye=self.eye,
                                        dry=self.dry, win=self.win)
                            # Read-back is performed by the next supervisor snapshot.
                            r["note"] = f"warp_to_mission (menu): {leaf.get('text')}"
                        else:
                            empty2 = self.eye.empty_point()
                            if empty2:
                                _execute(ctl.act_click_empty(empty2), eye=self.eye,
                                            dry=self.dry, win=self.win)
                            r["ok"] = False
                            r["note"] = ("khong co nut Location / menu 'Warp to "
                                         "Location' — da dong menu, KHONG warp beacon")

            elif kind in ("arrived", "need_undock", "wait", "estop", "blocked"):
                # TravelTo / FSM chi bao trang thai; executor khong bam gi them.
                r["ok"] = kind not in ("blocked", "estop")

            res.append(r)
        return res
