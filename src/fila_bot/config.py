"""Config runtime của bot — FC SET qua DSL (commands.SET_PARAMS)."""
from __future__ import annotations

import threading


class Config:
    def __init__(self, **overrides) -> None:
        self._lock = threading.Lock()
        self.escape_hp: float = 0.25
        self.unknown_timeout: float = 45.0
        self.orbit_default: int = 2500
        self.humanize: bool = True
        self.tick_interval: float = 0.3
        self.warn_timer_left: int = 300
        self.sim_mode: bool = True
        for k, v in overrides.items():
            if not hasattr(self, k):
                raise AttributeError(f"unknown config key '{k}'")
            setattr(self, k, v)

    def as_dict(self) -> dict:
        with self._lock:
            return {
                "escape_hp": self.escape_hp,
                "unknown_timeout": self.unknown_timeout,
                "orbit_default": self.orbit_default,
                "humanize": self.humanize,
                "tick_interval": self.tick_interval,
                "warn_timer_left": self.warn_timer_left,
                "sim_mode": self.sim_mode,
            }

    def set_param(self, param: str, value: float | bool) -> None:
        with self._lock:
            if param == "humanize":
                self.humanize = bool(value)
                return
            cur = getattr(self, param)
            setattr(self, param, type(cur)(value))
