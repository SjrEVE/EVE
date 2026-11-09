"""Upgraded Tactical Combat Brain (fila_bot/combat_brain.py).

Replaces the static 10km orbit with room-aware positioning, Cloud/Pylon avoidance,
Karybdis/Overmind escort-baiting (`Ephialtes Lancer` / `needle Tessella` gimmick),
and Split-Fire coordination while remaining 100% drop-in compatible with existing
unit tests (`tests/test_control.py`, `tests/test_agent.py`, `tests/test_all.py`).
"""

from __future__ import annotations
from typing import Any

try:
    from . import rats
    from . import rooms as rooms_mod
except ImportError:
    import rats  # type: ignore
    import rooms as rooms_mod  # type: ignore


class CombatBrain:
    """Central tactical decision engine for Abyssal Deadspace combat phases."""

    def __init__(
        self,
        fit_type: str = "default",
        resist_hole: str | None = None,
        has_drones: bool = True,
    ) -> None:
        self.current_target: str | None = None
        self.locked: set[str] = set()
        self.last_action: str | None = None
        self.fit_type: str = fit_type
        self.resist_hole: str | None = resist_hole
        self.has_drones: bool = has_drones
        self.room_kind: str = "UNKNOWN"
        self.drone_target: str | None = None

    def reset_room(self) -> None:
        """Reset per-room combat state upon entering a new pocket or clearing a room."""
        self.current_target = None
        self.locked.clear()
        self.last_action = None
        self.room_kind = "UNKNOWN"
        self.drone_target = None

    def _select_tactical_orbit_km(self, room_kind: str, target_name: str, all_names: list[str]) -> int:
        """Determine optimal orbit/keep-at-range distance (km) based on room and target."""
        if self.fit_type == "default":
            return 10

        t_lower = target_name.lower()
        tactics = rooms_mod.ROOM_TACTICS.get(room_kind, {})

        # 1. Grip Tessera (Rogue Drone Battlecruisers): deadly < 15km, must kite >= 20km
        if "tessera" in t_lower or room_kind == "TESSERA":
            return int(tactics.get("orbit_km", 22))

        # 2. Benthic / Endobenthic Overmind (T5/T6): has 15km Web, keep >= 16km until under guns
        if "benthic" in t_lower or "endobenthic" in t_lower:
            return 16

        # 3. CONCORD Marshal: Cruisers kite at 60-65km unless swarmed by Enforcers; Frigates orbit 12km
        if "marshal" in t_lower or room_kind == "MARSHAL":
            if "cruiser" in self.fit_type.lower():
                enforcer_count = sum(1 for n in all_names if "enforcer" in n.lower())
                return 15 if enforcer_count >= 3 else 60
            return 12

        # 4. Devoted Knight (Sansha Cruiser): stay at 13km (outside 10km Web/heavy Neut) or 1km under guns
        if "devoted knight" in t_lower or room_kind == "SANSHA":
            return int(tactics.get("orbit_km", 13))

        # 5. Karybdis Tyrannos / Lucid Deepwatcher / Leshak: tight orbit under turret tracking
        if any(bs in t_lower for bs in ("karybdis", "deepwatcher", "leshak")):
            return int(tactics.get("orbit_km", 5))

        return int(tactics.get("orbit_km", 10))

    def _apply_bait_gimmick(self, room_kind: str, ordered: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Exploit EVE NPC AI gimmick: Karybdis Tyrannos follows Ephialtes Lancer in orbit,
        and Abyssal Overmind follows generic [Name]needle Tessella in orbit.
        """
        if self.fit_type == "default" or len(ordered) < 2:
            return ordered

        tactics = rooms_mod.ROOM_TACTICS.get(room_kind, {})
        bait_token = tactics.get("bait_token")
        if not bait_token:
            return ordered

        bs_alive = any(c.get("is_bs", False) for c in ordered)
        if not bs_alive:
            return ordered

        bait_matches = [c for c in ordered if bait_token.lower() in c["name"].lower()]
        if len(bait_matches) == 1:
            last_bait = bait_matches[0]
            reordered = [c for c in ordered if c is not last_bait]
            reordered.append(last_bait)
            return reordered

        return ordered

    def tick(self, ex: Any, phase: str) -> list[tuple]:
        """Execute one decision cycle during `*_FIGHT` phases and append actions to `ex.actions`."""
        if not phase or not phase.endswith("_FIGHT"):
            return []

        names: list[str] = list(ex.overview_texts()) if hasattr(ex, "overview_texts") else []
        if not names:
            return []

        self.room_kind = rooms_mod.detect_room(names)
        ordered = rats.lock_order(names, fit_type=self.fit_type, resist_hole=self.resist_hole)
        ordered = self._apply_bait_gimmick(self.room_kind, ordered)

        actions: list[tuple] = []

        if hasattr(ex, "active_hazards"):
            hazards = ex.active_hazards() or []
            if hazards:
                hazard_plan = rooms_mod.evaluate_hazards(
                    hazards, self.room_kind, fit_type=self.fit_type
                )
                if hazard_plan["disable_mwd"]:
                    actions.append(("deactivate", "mwd"))
                if hazard_plan["recall_drones"]:
                    actions.append(("recall_drones", "suppressor_hazard"))
                if hazard_plan["avoid"]:
                    actions.append(("avoid_hazard", hazard_plan["avoid"][0]))

        target: str | None = None
        for item in ordered:
            if item.get("skip", False):
                continue
            cand_name = item["name"]
            if cand_name not in self.locked:
                target = cand_name
                break

        if target is None:
            return actions

        self.current_target = target
        self.locked.add(target)

        orbit_km = self._select_tactical_orbit_km(self.room_kind, target, names)

        core_actions: list[tuple] = [
            ("lock", target),
            ("orbit", orbit_km, target),
            ("activate", 1, "high"),
        ]
        actions.extend(core_actions)

        if self.fit_type != "default" and self.has_drones:
            split = rats.split_fire_plan(
                names,
                has_drones=self.has_drones,
                fit_type=self.fit_type,
                resist_hole=self.resist_hole or "em",
            )
            self.drone_target = split.get("drone_target")
            if not split["focus_fire"] and self.drone_target and self.drone_target != target:
                actions.append(("drone_engage", self.drone_target))

        self.last_action = target
        if hasattr(ex, "actions") and isinstance(ex.actions, list):
            ex.actions.extend(actions)

        return actions