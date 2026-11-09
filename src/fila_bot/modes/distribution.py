"""Distribution (courier) mode — M3 task 3.3. FSM tren world snapshot, KHONG tu bam.

world (dict, reader that hoac sim cung cap; None = khong doc duoc):
  docked, station, agent_station, pickup, dropoff,
  offer (AgentEye.read_offer), mission_active, cargo_loaded, cargo_free,
  route_hisec, popup (text MessageBox), travel (travel.read_world dict)

Luong: AGENT -> OFFER -> (accept|decline) -> LOAD -> TO_DROPOFF -> COMPLETE -> TO_AGENT -> AGENT
Buoc chua ground (open_agent, load_cargo keo tha, set_destination) -> action do + dict
de executor that FAIL-CLOSED; sim thi thuc hien duoc.
"""
from __future__ import annotations

import time
from typing import Any

from . import Mode
from ..agent import accept_rule
from ..travel import TravelTo


class DistributionMode(Mode):
    name = "distribution"

    def __init__(self, max_missions: int | None = None, clock=time.monotonic) -> None:
        super().__init__()
        self.phase = "AGENT"
        self.max_missions = max_missions
        self.clock = clock
        self.done = 0
        self.declined = 0
        self.travel: TravelTo | None = None
        self.blocked: str | None = None
        self._docked = True

    @property
    def at_safe_point(self) -> bool:
        return self._docked and self.phase in ("AGENT", "IDLE_DONE", "BLOCKED")

    def status(self) -> dict[str, Any]:
        return {"mode": self.name, "phase": self.phase, "runs": self.done,
                "declined": self.declined, "blocked": self.blocked}

    def _block(self, why: str) -> list[dict[str, Any]]:
        self.phase, self.blocked = "BLOCKED", why
        return [{"do": "blocked", "why": why}]

    def _go(self, dest: Any, w: dict[str, Any], nxt: str) -> list[dict[str, Any]]:
        if self.travel is None:
            self.travel = TravelTo()
            return [{"do": "set_destination", "to": dest}]
        acts = self.travel.tick(w.get("travel") or {}, self.clock())
        if self.travel.state == "BLOCKED":
            return self._block(f"travel: {self.travel.reason}")
        if self.travel.state == "ARRIVED":
            self.travel = None
            self.phase = nxt
        return acts

    def tick(self, w: Any) -> list[dict[str, Any]]:
        if not isinstance(w, dict):
            return self._block("khong co world snapshot (eye loi)")
        self._docked = bool(w.get("docked"))
        if self.phase == "BLOCKED":
            return []
        if w.get("popup"):
            return self._block(f"popup khong nhan ra: {w['popup']!r} — dung, khong bam qua")
        p = self.phase

        if p == "AGENT":
            if self.stop_requested or (self.max_missions is not None and self.done >= self.max_missions):
                self.phase = "IDLE_DONE"
                return []
            if w.get("mission_active"):
                self.phase = "LOAD"
                return []
            if w.get("offer") is None:
                return [{"do": "open_agent", "station": w.get("agent_station")}]
            self.phase = "OFFER"
            p = "OFFER"

        if p == "OFFER":
            offer = w.get("offer")
            verdict, why = accept_rule(offer, w.get("cargo_free"), w.get("route_hisec"))
            if verdict == "blocked":
                return self._block(why)
            xy = (offer.get("buttons") or {}).get(verdict)
            if xy is None:
                return self._block(f"khong thay nut '{verdict}' trong AgentDialogueWindow (G2)")
            if verdict == "decline":
                self.declined += 1
                self.phase = "AGENT"
            else:
                self.phase = "LOAD"
            return [{"do": "click", "at": xy, "why": f"{verdict}: {why}"}]

        if p == "LOAD":
            if w.get("cargo_loaded"):
                self.phase = "TO_DROPOFF"
                return []
            if w.get("cargo_loaded") is None:
                return self._block("khong doc duoc cargo hold (G4 chua ground)")
            if w.get("station") != w.get("pickup"):
                return self._go(w.get("pickup"), w, "LOAD")
            return [{"do": "load_cargo", "why": "keo cargo mission tu item hangar vao cargo hold"}]

        if p == "TO_DROPOFF":
            if self._docked and w.get("station") == w.get("dropoff"):
                self.travel = None
                self.phase = "COMPLETE"
                return []
            return self._go(w.get("dropoff"), w, "TO_DROPOFF")

        if p == "COMPLETE":
            if not w.get("mission_active"):
                self.done += 1
                self.phase = "TO_AGENT"
                return []
            offer = w.get("offer") or {}
            xy = (offer.get("buttons") or {}).get("complete")
            if xy is None:
                return [{"do": "open_agent", "station": w.get("agent_station"),
                         "why": "complete tu xa"}]
            return [{"do": "click", "at": xy, "why": "complete mission"}]

        if p == "TO_AGENT":
            if self._docked and w.get("station") == w.get("agent_station"):
                self.travel = None
                self.phase = "AGENT"
                return []
            if self.stop_requested and self._docked:
                self.phase = "IDLE_DONE"
                return []
            return self._go(w.get("agent_station"), w, "TO_AGENT")

        return []
