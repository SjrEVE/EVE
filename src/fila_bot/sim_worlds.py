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
