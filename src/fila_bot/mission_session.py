"""Mission identity and verified turn-in ledger.

The UI exposes a tracker title and an agent panel name, never a stable mission
ID. The session therefore keys on (character, agent, exact title) and refuses a
second exact title while the first is still active unless a verified turn-in
cleared it. A completion is counted only once, and only with objective +
response + panel-absent evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def _mission_key(character: str, agent_id: str, title: str) -> str:
    raw = f"{character}\x00{agent_id}\x00{title}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


class MissionSession:
    def __init__(self, character: str, agent_id: str, home_station: str,
                 path: str | Path | None = None) -> None:
        if not str(character).strip() or not str(agent_id).strip() or not str(home_station).strip():
            raise ValueError("character, agent_id and home_station are required")
        self.character = str(character).strip()
        self.agent_id = str(agent_id).strip()
        self.home_station = str(home_station).strip()
        self.active_key: str | None = None
        self.title: str | None = None
        self.completed = 0
        self._completed_keys: set[str] = set()
        self.path = Path(path) if path else None
        if self.path is not None and self.path.exists():
            self._load()

    def _load(self) -> None:
        if self.path is None:
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError(f"cannot read mission session {self.path}: {exc}") from exc
        for key in ("character", "agent_id", "home_station"):
            if str(data.get(key) or "").strip() != getattr(self, key):
                raise ValueError(
                    f"mission session identity mismatch on {key}: "
                    f"{data.get(key)!r} != {getattr(self, key)!r}")
        completed = data.get("completed")
        if type(completed) is not int or completed < 0:
            raise ValueError("mission session completed count is invalid")
        self.completed = completed
        self.active_key = data.get("active_key") or None
        self.title = data.get("title") or None
        keys = data.get("completed_keys") or []
        if not isinstance(keys, list) or any(not isinstance(k, str) for k in keys):
            raise ValueError("mission session completed_keys is invalid")
        self._completed_keys = set(keys)

    def _save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "character": self.character, "agent_id": self.agent_id,
            "home_station": self.home_station, "active_key": self.active_key,
            "title": self.title, "completed": self.completed,
            "completed_keys": sorted(self._completed_keys),
        }
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def reconcile_absent(self, *, panel_observed: bool, mission_absent: bool) -> bool:
        """Clear a stale active key when the GAME shows no mission at all.

        Ground LIVE 2026-11-12 17:27 (Piak): the previous run really clicked
        Complete on 'The Guristas Spies', but the completion could not be counted
        (the tracker vanished before the panel read-back), so the ledger kept it
        as active. The next run then ACCEPTED 'The Roving Rogue Drones' and only
        afterwards hit MISSION_IDENTITY_CONFLICT — a mission accepted and then
        abandoned, which is worse than either being honest about.

        A mission the game no longer lists is not active. Drop the key WITHOUT
        counting a completion (completed stays untouched: no fabricated success).
        """
        if not self.active_key:
            return False
        if not (panel_observed and mission_absent):
            return False
        self.active_key = None
        self.title = None
        self._save()
        return True

    def bind(self, title: str, agent_id: str | None = None) -> str:
        clean = str(title or "").strip()
        if not clean:
            raise ValueError("mission title is required")
        key = _mission_key(self.character, str(agent_id or self.agent_id), clean)
        if self.active_key and key != self.active_key:
            raise ValueError(
                "a different mission is still active: "
                f"{self.title!r}; refusing to replace it without a verified turn-in"
            )
        if not self.active_key and key in self._completed_keys:
            # Re-observing a completed title is a new offer/cycle, not a
            # duplicate completion. It becomes active again only after binding.
            self.active_key = key
            self.title = clean
            self._save()
            return key
        self.active_key = key
        self.title = clean
        self._save()
        return key

    def confirm_turnin(
        self,
        key: str,
        *,
        objective_complete: bool,
        response_confirmed: bool,
        panel_observed: bool,
        mission_absent: bool,
        dialog_evidence: bool = False,
    ) -> bool:
        """Count a completion only with all independent evidence signals.

        `panel_observed` may be replaced by `dialog_evidence`: ground LIVE
        2026-11-12 15:02 showed EVE removing the tracker entirely after a
        successful Complete, while the agent dialog itself read "… Objectives
        Complete …" and offered a fresh Request Mission with no Complete button.
        Requiring the panel there made a real turn-in uncountable — and the stale
        active key then blocked the next mission.
        """
        if key != self.active_key or key in self._completed_keys:
            return False
        if not (objective_complete and response_confirmed
                and (panel_observed or dialog_evidence) and mission_absent):
            return False
        self._completed_keys.add(key)
        self.completed += 1
        self.active_key = None
        self.title = None
        self._save()
        return True
