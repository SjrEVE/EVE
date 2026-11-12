"""Sim world cho UI demo Distribution / Security (KHONG phai bang chung chay tren client).

Supervisor goi: world = sim.world() -> mode.tick(world) -> sim.apply(actions).
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

BTN = {"accept": (10, 10), "decline": (20, 10), "complete": (30, 10)}
COURIER = {"type": "courier", "cargo_m3": 2.0, "buttons": BTN}
HOPS = 2


class DistSim:
    """Courier L1: agent o AGT, giao toi DST cach HOPS jump."""

    def __init__(self) -> None:
        self.station: str | None = "AGT"
        self.docked = True
        self.system = "S0"
        self.offer: dict[str, Any] | None = None
        self.mission_active = False
        self.cargo_loaded = False
        self.dest: str | None = None
        self.jumps = 0
        self.menu: list = []
        self.markers: list = []

    def world(self) -> dict[str, Any]:
        return {
            "docked": self.docked, "station": self.station, "agent_station": "AGT",
            "pickup": "AGT", "dropoff": "DST", "offer": self.offer,
            "mission_active": self.mission_active, "cargo_loaded": self.cargo_loaded,
            "cargo_free": 400.0, "route_hisec": True, "popup": None,
            "travel": {"system": self.system, "station": self.station, "docked": self.docked,
                       "markers": list(self.markers), "warping": False,
                       "menu": list(self.menu), "route_panel": True},
        }

    def apply(self, acts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for a in acts:
            d = a.get("do")
            if d == "open_agent":
                self.offer = dict(COURIER)
            elif d == "click":
                xy = a.get("at")
                if xy == BTN["accept"]:
                    self.mission_active, self.offer = True, None
                elif xy == BTN["decline"]:
                    self.offer = None
                elif xy == BTN["complete"]:
                    self.mission_active, self.cargo_loaded, self.offer = False, False, None
            elif d == "load_cargo":
                self.cargo_loaded = True
            elif d == "set_destination":
                self.dest, self.jumps = a.get("to"), 0
                self.docked, self.station, self.markers = False, None, [(5, 5)]
            elif d == "open_menu":
                self.menu = [("Dock" if self.jumps >= HOPS else "Jump", (50, 60))]
            elif d == "menu_entry":
                self.menu = []
                if str(a.get("text")).lower() == "dock":
                    self.docked, self.station, self.markers = True, self.dest, []
                else:
                    self.jumps += 1
                    self.system = f"S{self.jumps}" if self.dest == "DST" else f"R{self.jumps}"
            out.append({"action": d, "ok": True, "sim": True})
        return out


class SecSim:
    """Runner gia cho SecurityMode: 1 mission = 2 pocket, moi pocket co quai FIGHT_TICKS tick."""

    FIGHT_TICKS = 4
    POCKETS = 2

    def __init__(self) -> None:
        self.me = self
        self.phase = "DOCKED"
        self.pocket = 0
        self.fight = 0
        self.missions = 0

    def state(self) -> Any:
        return SimpleNamespace(phase=self.phase, hp={"shield": 1.0, "armor": 1.0, "structure": 1.0})

    def next_actions(self) -> list[dict[str, Any]]:
        p = self.phase
        if p == "DOCKED":
            return [{"do": "undock"}]
        if p == "IN_SPACE":
            return [{"do": "warp_site"}]
        if p == "AT_SITE":
            return [{"do": "fight"}]
        if p == "POCKET_CLEAR":
            if self.pocket + 1 < self.POCKETS:
                return [{"do": "gate", "label": "Acceleration Gate"}]
            return [{"do": "warp_home", "why": "mission xong"}]
        return []

    def apply(self, acts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for a in acts:
            d = a.get("do")
            if d == "undock":
                self.phase = "IN_SPACE"
            elif d == "warp_site":
                self.phase, self.pocket, self.fight = "AT_SITE", 0, 0
            elif d == "fight":
                self.fight += 1
                if self.fight >= self.FIGHT_TICKS:
                    self.phase = "POCKET_CLEAR"
            elif d == "gate":
                self.phase, self.pocket, self.fight = "AT_SITE", self.pocket + 1, 0
            elif d in ("warp_home", "warp_out"):
                if self.phase == "POCKET_CLEAR" and d == "warp_home":
                    self.missions += 1
                self.phase = "DOCKED"
            out.append({"action": d, "ok": True, "sim": True})
        return out


class SecurityE2ESim:
    """SIM end-to-end cho SecurityMode: nhan offer -> undock -> site -> combat
    -> ve tram -> Complete -> READ-BACK -> IDLE_DONE.

    Day la gia lap dieu khien, KHONG phai bang chung client that. No dung cung
    hop dong `refresh() -> tick() -> apply()` nhu LiveSecurityRunner de soi duoc
    deadlock/stall trong FSM ma unit test tung tick bo sot.
    """

    TITLE = "The Blockade"          # combat mission co trong catalog da ground
    AGENT = {"name": "Jukosoni Kauniki", "level": 1, "division": "Security",
             "available": True, "chat_xy": (640, 400)}
    HOSTILE = {"name": "Guristas Frigate", "faction": "Guristas", "priority": 5,
               "distance": 15000, "center": (500, 500), "skip": False}

    def __init__(self) -> None:
        self.stage = "NO_DIALOG"
        self._vt = 1000.0            # dong ho ao: moi tick +2s (wave-wait 18s = 9 tick)
        self.fight_ticks = 0
        self.pending_ticks = 0
        self.trace: list[str] = []

    def clock(self) -> float:
        return self._vt

    def world(self) -> dict[str, Any]:
        self._vt += 2.0
        # Combat ket thuc sau 3 tick o site (bot ban 1 lan roi giu modules).
        if self.stage == "SITE_FIGHT":
            self.fight_ticks += 1
            if self.fight_ticks >= 3:
                self.stage, self._drones_out = "SITE_CLEAR", True
        docked = self.stage not in ("SPACE_BEACON", "SITE_FIGHT", "SITE_CLEAR")
        base: dict[str, Any] = {
            "docked": docked,
            "station": "Sobaseki VII - Caldari Navy Logistic Support" if docked else None,
            "home_station": "Sobaseki VII - Caldari Navy Logistic Support",
            "system": "Sobaseki" if docked else None,
            "security": 0.8,
            "connection_lost": False,
            "agents": [dict(self.AGENT)] if docked else [],
            "agent_dialog_open": False,
            "offer": None,
            "missions": [],
            "has_active_mission": False,
            "mission_is_courier": False,
            "mission_support": None,
            "active_mission_title": None,
            "mission_panel_observed": True,
            "hostiles": [],
            "gates": [],
            "beacons": [],
            "ship_health": {"shield": 1.0, "armor": 1.0, "structure": 1.0},
            "speed_mps": 0 if docked else 120,
            "maneuver": None,
            "undock_xy": (999, 700) if docked else None,
            "drones_in_space": None,
            "drones_out": False,
            "weapons_firing": False,
            "afterburner_on": False,
            "modal": None,
        }
        active = [self.TITLE]
        offer_buttons = {"accept": (343, 808), "decline": (434, 808),
                         "delay": (525, 808), "request": None, "complete": None,
                         "quit": None, "close": None}
        complete_buttons = {k: None for k in offer_buttons}
        complete_buttons.update({"complete": (400, 808), "quit": (500, 808),
                                 "close": (600, 808)})
        if self.stage == "OFFER":
            base.update(agent_dialog_open=True,
                        offer={"type": "encounter", "objective_kind": "combat",
                               "template_kind": None, "title": self.TITLE,
                               "buttons": offer_buttons})
        elif self.stage in ("ACCEPTED", "DOCKED_TURNIN", "TURNIN_PENDING"):
            base.update(missions=active, has_active_mission=True,
                        active_mission_title=self.TITLE,
                        mission_support="combat")
        if self.stage == "DOCKED_TURNIN":
            base.update(agent_dialog_open=True,
                        offer={"type": "encounter", "title": self.TITLE,
                               "buttons": complete_buttons})
        elif self.stage == "TURNIN_PENDING":
            base.update(agent_dialog_open=True,
                        offer={"type": "encounter", "title": self.TITLE,
                               "buttons": complete_buttons})
        elif self.stage == "SPACE_BEACON":
            base.update(missions=active, has_active_mission=True,
                        active_mission_title=self.TITLE, mission_support="combat",
                        beacons=[{"name": "Mission Beacon", "center": (410, 300)}])
        elif self.stage == "SITE_FIGHT":
            base.update(missions=active, has_active_mission=True,
                        active_mission_title=self.TITLE, mission_support="combat",
                        hostiles=[dict(self.HOSTILE)], drones_out=True)
        elif self.stage == "SITE_CLEAR":
            base.update(missions=active, has_active_mission=True,
                        active_mission_title=self.TITLE, mission_support="combat",
                        drones_out=self._drones_out)
        elif self.stage == "DONE":
            base.update(missions=[], has_active_mission=False,
                        mission_panel_observed=True)
        return base

    def apply(self, acts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        self._drones_out = getattr(self, "_drones_out", True)
        for a in acts:
            d = a.get("do")
            self.trace.append(d or "?")
            if self.stage == "NO_DIALOG" and d == "open_agent_chat":
                self.stage = "OFFER"
            elif self.stage == "OFFER" and d == "accept_mission":
                self.stage = "ACCEPTED"
            elif self.stage == "ACCEPTED" and d == "undock":
                self.stage = "SPACE_BEACON"
            elif self.stage == "SPACE_BEACON" and d == "warp_beacon":
                self.stage, self.fight_ticks = "SITE_FIGHT", 0
            elif self.stage == "SITE_CLEAR" and d == "recall_drones":
                self._drones_out = False
            elif self.stage == "SITE_CLEAR" and d == "warp_home":
                self.stage = "DOCKED_TURNIN"
            elif self.stage == "DOCKED_TURNIN" and d == "complete_mission":
                self.stage, self.pending_ticks = "TURNIN_PENDING", 0
            out.append({"action": d, "ok": True, "sim": True})
        if self.stage == "TURNIN_PENDING":
            self.pending_ticks += 1
            if self.pending_ticks >= 2:      # client cap nhat panel sau 2 tick
                self.stage = "DONE"
        elif self.stage == "DONE":
            self.stage = "NO_DIALOG"         # san sang mission tiep theo
        return out
