"""LiveDistributionRunner — ket noi DistributionMode voi EVE client that qua Eye + Control.
Doc qua WorldSnapshot (single-pass perception) + thuc thi bang control (keybinds / hotkeys / click).

Tuan thu fail-closed: bat ky buoc nao thieu du kien -> bao loi, khong bam mu.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from .. import control as ctl
from ..agent import AgentEye, agents_panel
from ..eye import Eye
from ..inventory import InventoryEye
from ..mission import MissionEye
from ..win import find_client_window, focus
from ..world_snapshot import parse_world

logger = logging.getLogger("fila_bot.live_distribution")


def pick_item_xy(items: list[Any], wanted: str) -> tuple[int, int] | None:
    """Toa do item co ten khop `wanted` (khong phan biet hoa thuong).

    Tra None khi khong biet ten item hoac khong tim thay -> caller KHONG duoc keo bua.
    """
    w = (wanted or "").strip().lower()
    if not w:
        return None
    for it in items or []:
        if isinstance(it, dict):
            name, center = str(it.get("name", "")), it.get("center")
        else:
            name, center = str(it[0]), it[1]
        if w in name.lower():
            return center
    return None


def route_hisec_value(allow_unknown: bool, sec: Any, markers: int) -> bool | None:
    """True = chac chan hisec, False = chac chan khong, None = khong biet (fail-closed)."""
    if allow_unknown:
        return True
    if isinstance(sec, (int, float)) and sec >= 0.5 and markers == 0:
        return True
    return None


class LiveDistributionRunner:
    """World provider + Action executor cho DistributionMode tren client EVE that."""

    def __init__(self, eye: Eye, dry: bool = True, default_agent: str | None = None,
                 allow_unknown_sec: bool = False) -> None:
        self.eye = eye
        self.dry = dry
        self.default_agent = default_agent
        self.allow_unknown_sec = allow_unknown_sec
        self.win = None
        self._cached_agent_station: str | None = None
        self._cached_pickup: str | None = None
        self._cached_dropoff: str | None = None
        self._mission_item_name: str | None = None

    def refresh(self) -> dict[str, Any]:
        """Doc the gioi game that -> world dict hop le cho DistributionMode.tick()."""
        if hasattr(self.eye, "dll") and self.eye.dll is not None:
            self.eye.refresh()
        snap = parse_world(self.eye)

        # 1. E-STOP khi mat mang
        if snap.connection_lost:
            return {
                "docked": snap.docked,
                "station": snap.station,
                "popup": "Connection to server was lost (Connection Lost modal)",
            }

        # 2. Xac dinh thong tin station / agent
        if snap.docked and snap.station:
            if not self._cached_agent_station:
                self._cached_agent_station = snap.station

        # 3. Mission status tu JobBoard / InfoPanel
        me = MissionEye(self.eye)
        missions = me.mission_entries()
        has_mission = len(missions) > 0

        # 4. Agent offer / dialog
        offer = None
        if snap.agent_dialog.open:
            ae = AgentEye(self.eye)
            offer = ae.read_offer()
            if offer:
                if offer.get("cargo_item"):
                    self._mission_item_name = offer["cargo_item"]
                pk = offer.get("pickup", {}) or {}
                dp = offer.get("dropoff", {}) or {}
                if pk.get("name"):
                    self._cached_pickup = pk["name"]
                if dp.get("name"):
                    self._cached_dropoff = dp["name"]

        # 5. Inventory & Cargo — KHONG bia so lieu: dong Inventory = unknown (None)
        cargo_free: float | None = None
        cargo_loaded: bool | None = None
        ie = InventoryEye(self.eye)
        if snap.inventory.open:
            cap = snap.inventory.capacity or {}
            max_v = cap.get("max")
            if max_v is not None:
                cargo_free = float(max_v) - float(cap.get("used") or 0.0)
            if self._mission_item_name:
                cargo_loaded = bool(ie.has_item(self._mission_item_name))
            elif max_v is not None:
                # Chua biet ten item mission: chi coi la da load khi cargo co gi do
                cargo_loaded = (cap.get("used") or 0.0) > 0.05

        # 6. Travel snapshot
        from ..travel import read_world as read_travel_world
        travel_dict = read_travel_world(self.eye)

        # 7. Route hisec: chi ket luan khi CHAC CHAN (cung he, sec >= 0.5, khong jump)
        #    Ngoai ra None -> accept_rule se block (fail-closed), tru khi user bat
        #    --allow-unknown-sec.
        sec = snap.security
        markers = len(travel_dict.get("markers") or [])
        route_hisec = route_hisec_value(self.allow_unknown_sec, sec, markers)

        return {
            "docked": snap.docked,
            "station": snap.station,
            "agent_station": self._cached_agent_station,
            "pickup": self._cached_pickup,
            "dropoff": self._cached_dropoff,
            "offer": offer,
            "mission_active": has_mission,
            "cargo_loaded": cargo_loaded,
            "cargo_free": cargo_free,
            "route_hisec": route_hisec,
            "popup": None,
            "travel": travel_dict,
        }

    def apply(self, acts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Thuc thi danh sach actions do DistributionMode phat ra tren game client."""
        if not acts:
            return []

        if not self.dry and self.win is None:
            self.win = find_client_window()
            if self.win:
                focus(self.win)
                time.sleep(0.3)

        out = []
        for a in acts:
            d = a.get("do")
            spec = None

            if d == "open_agent":
                # Uu tien AgentsPanel nut chat
                ag_list = agents_panel(self.eye) or []
                ag = None
                if self.default_agent:
                    ag = next((x for x in ag_list if x["name"] == self.default_agent and x.get("chat_xy")), None)
                if ag is None and ag_list:
                    ag = next((x for x in ag_list if x.get("available") and x.get("chat_xy")), ag_list[0])

                if ag and ag.get("chat_xy"):
                    spec = ctl.act_menu_entry(ag["chat_xy"])
                else:
                    # Fallback qua Mission Entry tren JobBoard
                    ents = self.eye._find_by_type("AgentMissionInfoPanelEntry", select_many=True) or []
                    lbl = [n for n in Eye.walk(ents[0]) if n.get("type") == "EveLabelLarge"] if ents else []
                    if lbl:
                        spec = ctl.act_open_context_menu(self.eye.abs_center(lbl[0]))

            elif d == "click":
                xy = a.get("at")
                if xy:
                    spec = ctl.act_menu_entry(xy)

            elif d == "open_inventory":
                btn = self.eye._find_by_type("ButtonInventory", select_many=True) or []
                if btn:
                    spec = ctl.act_menu_entry(self.eye.abs_center(btn[0]))

            elif d == "load_cargo":
                # Keo DUNG item mission tu ItemHangar sang ShipHangar (kho tau).
                # Buoc 0: chon ItemHangar trong tree truoc (items() doc container
                # DANG chon — neu dang la ShipCargo thi doc sai noi dung).
                ie = InventoryEye(self.eye)
                if ie.window() is None:
                    btn = self.eye._find_by_type("ButtonInventory", select_many=True)
                    if btn:
                        spec = ctl.act_menu_entry(self.eye.abs_center(btn[0]))
                    out.append({"action": d, "ok": True, "dry": self.dry,
                                "note": "mo Inventory truoc — keo o tick sau"})
                    continue
                if ie.selected_container() != "ItemHangar":
                    item_hangar_xy = ie.tree_entry_xy("ItemHangar")
                    if item_hangar_xy:
                        spec = ctl.act_menu_entry(item_hangar_xy)   # click chon hangar
                    else:
                        out.append({"action": d, "ok": False, "dry": self.dry,
                                    "note": "khong thay entry ItemHangar trong tree"})
                        continue
                else:
                    hangars = {e["name"]: e["center"] for e in (ie.tree_entries() or [])}
                    ship_hangar_xy = hangars.get("ShipHangar")
                    item_xy = pick_item_xy(ie.items() or [], self._mission_item_name or "")
                    if item_xy is None:
                        # Khong biet ten item mission / khong co hang -> KHONG keo bua
                        out.append({"action": d, "ok": False, "dry": self.dry,
                                    "note": f"khong thay item mission {self._mission_item_name!r} "
                                            "trong ItemHangar"})
                        continue
                    if ship_hangar_xy:
                        spec = ctl.act_drag_item(item_xy, ship_hangar_xy)

            elif d == "set_destination":
                # Lay link pickup hoac dropoff tu agent dialog. Dialog dong -> mo
                # chat agent truoc (11-11: khong co dialog thi khong co link,
                # TravelTo se block "khong co route" mai mai).
                ae = AgentEye(self.eye)
                from ..agent import location_links, agents_panel
                links = location_links(self.eye) or {}
                target_xy = links.get("dropoff") if a.get("to") == self._cached_dropoff else links.get("pickup")
                if target_xy:
                    # Right click link -> CHO menu "Set Destination" hien -> click.
                    # (11-11: chi mo menu roi bo / khong ai click -> route khong bao
                    #  gio duoc set, TravelTo block vinh vien.)
                    open_spec = ctl.act_open_context_menu(target_xy)
                    ctl.execute(open_spec, eye=self.eye, dry=self.dry, win=self.win)
                    xy_set = self.eye.wait_entry("Set Destination", timeout_s=6.0)
                    if xy_set:
                        spec = ctl.act_menu_entry(xy_set)
                    else:
                        out.append({"action": d, "ok": False, "dry": self.dry,
                                    "note": "menu khong co 'Set Destination' sau 6s"})
                        continue
                else:
                    ags = agents_panel(self.eye) or []
                    ag = next((x for x in ags if x.get("available") and x.get("chat_xy")), None)
                    if ag:
                        spec = ctl.act_menu_entry(ag["chat_xy"])
                        self._need_destination_retry = True
                    out.append({"action": d, "ok": False, "dry": self.dry,
                                "note": "dialog dong — mo chat agent de lay link, set_destination o tick sau"})
                    continue

            elif d == "open_menu":
                # Mo menu marker hoac selected item
                xy = a.get("at")
                if xy:
                    spec = ctl.act_open_context_menu(xy)

            elif d == "menu_entry":
                xy = a.get("at")
                if xy:
                    spec = ctl.act_menu_entry(xy)

            elif d == "dismiss_menu":
                empty = self.eye.empty_point()
                spec = ctl.act_click_empty(empty)

            elif d == "hotkey_dock_jump":
                xy = a.get("at")
                if xy:
                    spec = ctl.act_hotkey_dock_jump(xy)

            if spec is not None:
                res = ctl.execute(spec, dry=self.dry, win=self.win)
                out.append({"action": d, "ok": res.get("ok", False), "dry": self.dry, "fail": res.get("fail")})
            else:
                out.append({"action": d, "ok": False, "dry": self.dry, "note": "spec is None (khong the chuyen hanh dong)"})

        return out
