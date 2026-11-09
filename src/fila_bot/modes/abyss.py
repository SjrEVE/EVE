"""Abyss mode — bọc reflex.Bot (KHÔNG viết lại logic) + driver phase cho Supervisor.

reflex.Bot chỉ đổi phase khi nhận lệnh (UNDOCK/FILA/GATE/DOCK). Driver ở đây phát
đúng các lệnh đó theo phase hiện tại:

    DOCKED -> UNDOCK -> TRAVEL_ENTRY -> FILA -> FILA_SPOOL (confirm bằng eye/sim)
    -> ROOMn_FIGHT -(sạch quái)-> ROOMn_CLEARED -> GATE ... ROOM3_CLEARED
    -> (Origin Conduit) WARP_HOME -> DOCK -> DOCKED  (run += 1)

LIVE: undock/filament/gate/dock CHƯA ground (G6/G10) → driver BLOCKED, không phát
lệnh tiến phase (nếu không, executor sẽ "tưởng" đã vào abyss trong khi client
không đổi gì). Guards + SURVIVAL vẫn chạy mỗi tick qua bot.tick().
"""
from __future__ import annotations

from typing import Any, Callable

from . import Mode
from ..commands import CommandError
from ..reflex import IN_ABYSS, SimExecutor


def _no_hostiles(ex: Any) -> bool:
    """Room sạch = overview không còn entry classify được là NPC."""
    from ..rats import classify
    texts = ex.overview_texts() if hasattr(ex, "overview_texts") else None
    if texts is None:
        return False                      # không đọc được → KHÔNG coi là sạch
    for t in texts:
        c = classify(t)
        if c.get("faction") is not None or c.get("hull") is not None:
            return False
    return True


class AbyssMode(Mode):
    name = "abyss"

    def __init__(self, bot: Any, filament: str = "Tranquil Exotic Filament",
                 max_runs: int | None = None,
                 clear_check: Callable[[Any], bool] | None = None,
                 live_grounded: bool = False) -> None:
        super().__init__()
        self.bot = bot
        self.ex = bot.ex
        self.filament = filament
        self.max_runs = max_runs
        self.clear_check = clear_check or _no_hostiles
        self.live_grounded = live_grounded
        self.runs = 0
        self.blocked: str | None = None
        self._seen = 0

    # phase lấy thẳng từ executor (Mode.__init__ gán self.phase → setter bỏ qua)
    @property
    def phase(self) -> str:
        return getattr(getattr(self, "ex", None), "phase", "IDLE")

    @phase.setter
    def phase(self, _v: str) -> None:
        pass

    @property
    def is_sim(self) -> bool:
        return isinstance(self.ex, SimExecutor)

    @property
    def at_safe_point(self) -> bool:
        return self.phase == "DOCKED"

    @property
    def in_no_escape(self) -> bool:
        # FILA_SPOOL: tàu vẫn ở ngoài (chưa vào abyss) — không báo 'không lối thoát' sớm
        return self.phase in IN_ABYSS and self.phase != "FILA_SPOOL"

    def status(self) -> dict[str, Any]:
        return {"mode": self.name, "phase": self.phase, "runs": self.runs,
                "room": getattr(self.ex, "room", 0), "hp": getattr(self.ex, "hp", None),
                "filaments": getattr(self.ex, "filaments", None), "blocked": self.blocked}

    # ---------------- driver ----------------
    def _cmd(self, cmd: str, arg: Any = None) -> bool:
        handler = getattr(self.bot, f"_do_{cmd.lower()}")
        try:
            handler(arg)
            return True
        except CommandError as e:
            self.bot.bus.emit("REJECT", cmd=cmd, reason=str(e))
            return False

    def _drive(self) -> None:
        if not self.is_sim and not self.live_grounded:
            self.blocked = ("abyss live: undock/filament/gate/dock chưa ground (G6/G10) — "
                            "không tiến phase, chỉ chạy guards")
            return
        self.blocked = None
        p = self.phase
        ex = self.ex
        if p == "DOCKED":
            done = self.max_runs is not None and self.runs >= self.max_runs
            if self.stop_requested or done or getattr(ex, "filaments", 0) <= 0:
                return
            self._cmd("UNDOCK")
        elif p == "TRAVEL_ENTRY":
            if self.stop_requested:
                self._cmd("DOCK")
            else:
                self._cmd("FILA", self.filament)
        elif p.endswith("_FIGHT") and p.startswith("ROOM"):
            if self.clear_check(ex):
                ex.phase = f"ROOM{ex.room}_CLEARED"
                self.bot.bus.emit("ROOM_CLEARED", room=ex.room, gate_open=True)
        elif p in ("ROOM1_CLEARED", "ROOM2_CLEARED"):
            self._cmd("GATE")
        elif p == "ROOM3_CLEARED":
            ex.phase = "WARP_HOME"          # Origin Conduit → về điểm bật filament
            self.runs += 1
            self.bot.abby_started = None
            self.bot.bus.emit("RUN_DONE", runs=self.runs)
        elif p == "WARP_HOME":
            self._cmd("DOCK")

    def tick(self, world: Any) -> list[Any]:
        self._drive()
        self.bot.tick()
        new = self.ex.actions[self._seen:]
        self._seen = len(self.ex.actions)
        return list(new)


class DemoSim(SimExecutor):
    """Sim cho UI demo: mỗi room có quái `fight_ticks` tick đầu rồi sạch.

    SimExecutor gốc luôn trả quái → room không bao giờ clear. DemoSim CHỈ để xem
    luồng trên UI, không phải bằng chứng chạy được trên client.
    """

    def __init__(self, fight_ticks: int = 5) -> None:
        super().__init__()
        self.sim_confirm = True
        self.fight_ticks = fight_ticks
        self._n = 0
        self._key: Any = None

    def overview_texts(self) -> list[str]:
        key = (self.phase, self.room)
        if key != self._key:
            self._key, self._n = key, 0
        self._n += 1
        return super().overview_texts() if self._n <= self.fight_ticks else []
