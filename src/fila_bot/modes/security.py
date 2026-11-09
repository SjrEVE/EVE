"""Security mission mode (M4) — boc MissionRunner (khong viet lai), them an toan.

Them so voi MissionRunner:
- hp < escape_hp khi o site -> warp_out (mission DUOC warp, khac abyss).
- wave_wait: pocket sach -> cho WAVE_WAIT_S roi moi di gate (bat wave den muon).
- STOP an toan: khong vao site moi; ngoai station -> warp_home; safe point = DOCKED.
Action chua ground (gate/fight/warp_out) do executor that FAIL-CLOSED.
"""
from __future__ import annotations

import time
from typing import Any

from . import Mode

WAVE_WAIT_S = 18.0


class SecurityMode(Mode):
    name = "security"

    def __init__(self, runner: Any, escape_hp: float = 0.25, clock=time.monotonic) -> None:
        super().__init__()
        self.runner = runner
        self.escape_hp = escape_hp
        self.clock = clock
        self.clear_since: float | None = None
        self.blocked: str | None = None
        self._phase = "UNKNOWN"

    @property
    def phase(self) -> str:
        return getattr(self, "_phase", "UNKNOWN")

    @phase.setter
    def phase(self, v: str) -> None:
        self._phase = v

    @property
    def at_safe_point(self) -> bool:
        return self._phase == "DOCKED"

    def status(self) -> dict[str, Any]:
        return {"mode": self.name, "phase": self._phase, "blocked": self.blocked}

    def tick(self, world: Any) -> list[dict[str, Any]]:
        st = self.runner.me.state()
        self._phase = st.phase
        hp = st.hp or {}
        low = min(hp.values()) if hp else None

        if st.phase in ("AT_SITE", "POCKET_CLEAR") and low is not None and low < self.escape_hp:
            return [{"do": "warp_out", "why": f"hp {low:.2f} < {self.escape_hp} — mission warp ra duoc"}]

        if self.stop_requested:
            if st.phase == "DOCKED":
                return []
            if st.phase != "AT_SITE":
                return [{"do": "warp_home", "why": "STOP an toan — ve station"}]

        if st.phase == "POCKET_CLEAR":
            now = self.clock()
            if self.clear_since is None:
                self.clear_since = now
            if now - self.clear_since < WAVE_WAIT_S:
                return [{"do": "wait", "why": f"wave_wait {int(now - self.clear_since)}/{int(WAVE_WAIT_S)}s"}]
        else:
            self.clear_since = None

        acts = self.runner.next_actions() or []
        b = [a for a in acts if a.get("do") == "blocked"]
        self.blocked = b[0].get("why") if b else None
        return acts
