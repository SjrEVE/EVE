"""SECURITY BRAIN — não thuần Python cho Security mission runner (không LLM).

Boss 13-11: "chân tay mũi miệng có rồi, lắp não cho nó". Các primitive đã PROVEN
live 13-11: approach (243 m/s thật), drone launch/recall, speed/cap/HP eyes,
overview distance (AU parse đúng), SelectedItemWnd fixed widgets.

Não này nhận WORLD (đã có tất cả mắt trên) và trả ACTIONS + tên action khớp
executor thật của mission.py (`do` keys đã ground). KHÔNG bấm mù: mỗi quyết định
kèm `why` + evidence name, mọi thiếu dữ liệu → WAIT/BLOCKED có lý do.

Chiến thuật nguồn: EVE-Survival mission reports (trigger/avoid), UniWiki
(orbit meta), rats.py (faction/priority), live evidence 12-13/11.
"""
from __future__ import annotations

import time  # noqa: F401  (dùng trong _clock default)
from typing import Any

from .mission_target import _distance_m  # noqa: F401  (AU-aware parse)
from .rats import classify, lock_order  # noqa: E402

# --- EVE-Survival ground: trigger/avoid per mission (12-13/11 reports) ---
MISSION_TACTICS: dict[tuple[str, int], dict[str, Any]] = {
    ("gone berserk", 1): {
        "faction": "EoM", "trigger_names": ("Fiend",), "kill_first": ("Imp",),
        "orbit_km": 20, "source": "eve-survival GoneBerserk1 (2017)",
    },
    ("gone berserk", 2): {
        "faction": "EoM", "trigger_names": ("Demon",), "kill_first": ("Succubus",),
        "orbit_km": 20, "source": "eve-survival GoneBerserk2 (2015; verify live)",
    },
    ("pirate intrusion", 2): {
        "faction": "Guristas", "trigger_names": (),
        "kill_first": ("Saboteur", "Killer", "Annihilator"), "orbit_km": 25,
        "source": "unverified level/pocket mapping; do not automate trigger without live report",
    },
    ("the blockade", 2): {
        "faction": "Guristas", "trigger_names": ("Plunderer", "Wrecker", "Infiltrator"),
        "kill_first": ("Stasis Tower",), "orbit_km": 20,
        "source": "unverified level/pocket mapping; verify before live",
    },
}

JAMMING_TOKENS = ("Killer", "Annihilator", "Saboteur", "Nullifier", "Dampener")
WEB_TOKENS = ("Webifier", "Stasis", "Web")
TRIGGER_HINTS = ("Trigger", "Fiend", "Plunderer", "Wrecker", "Infiltrator")

SURVIVAL_HP = 0.30
SURVIVAL_CAP = 25.0
# A tactical default only. Never substitute for fitted weapon/drone/lock ranges.
ENGAGE_RANGE_M = 25_000.0
DRONE_LEASH_M = 25_000.0


def _entry_distance_m(entry: dict[str, Any]) -> float | None:
    return _distance_m(entry.get("Distance"))


def _pick_name(entry: dict[str, Any]) -> str:
    return str(entry.get("Name") or "").strip()


def _has_token(name: str, tokens: tuple[str, ...]) -> bool:
    low = name.lower()
    return any(t.lower() in low for t in tokens)


class SecurityBrain:
    """Não quyết định 1 tick: world snapshot → danh sách hành động đúng executor."""

    def __init__(self, mission_title: str | None = None,
                 fit: dict[str, Any] | None = None,
                 clock: Any = None, mission_level: int | None = None) -> None:
        self.mission_title = mission_title or ""
        key = self.mission_title.strip().lower()
        self.tactics = MISSION_TACTICS.get((key, mission_level), {}) if mission_level else {}
        self.fit = fit or {}
        self.locked_names: set[str] = set()
        self.drones_out: bool = False
        self.modules_on: bool = False
        self._clock = clock or time.time
        self.last_why: str = ""

    # ------------------------------------------------------------------ senses
    def rank_targets(self, hostiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Pure ranking of authorized production contacts; no assumed locks."""
        triggers = self.tactics.get("trigger_names") or ()
        first = self.tactics.get("kill_first") or ()
        def key(row):
            name = str(row.get("name") or "")
            tier = (2 if _has_token(name, triggers) else
                    0 if _has_token(name, first) else 1)
            distance = _distance_m(row.get("distance"))
            return (tier, row.get("priority", 6),
                    distance if distance is not None else float("inf"), name)
        return sorted(hostiles, key=key)

    @staticmethod
    def _hostiles(overview: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Quái thật: classify được, faction combat, KHÔNG station/gate/wreck."""
        out = []
        for e in overview or []:
            name = _pick_name(e)
            if not name:
                continue
            cls = classify(name)
            if cls.get("skip"):
                continue
            faction = cls.get("faction")
            if faction in (None, "MissionNPC", "CONCORD") or "Navy" in str(faction):
                continue
            if any(t in name.lower() for t in ("gate", "station", "wreck", "container",
                                               "acceleration", "beacon")):
                continue
            out.append({**e, "_cls": cls,
                        "distance_m": _distance_m(e.get("Distance"))})
        return out

    @staticmethod
    def _gate(overview: list[dict[str, Any]]) -> dict[str, Any] | None:
        for e in overview or []:
            if "acceleration gate" in _pick_name(e).lower():
                return e
        return None

    # ------------------------------------------------------------------ decide
    def decide(self, world: dict[str, Any]) -> list[dict[str, Any]]:
        """1 tick não. Trả list action khớp executor: lock/orbit/approach/
        activate_module/launch_drones/recall_drones/wait/warp_to/undock/dock."""
        hp = world.get("ship_health") or {}
        cap = world.get("capacitor_percent")
        low_hp = min((hp.get("shield", 1.0), hp.get("armor", 1.0),
                      hp.get("structure", 1.0)))
        docked = bool(world.get("docked"))
        overview = world.get("overview") or []
        drones = world.get("drones") or {}
        drones_in_space = drones.get("in_space") or 0
        drones_in_bay = drones.get("in_bay") or 0

        # ---- 1. SURVIVAL trước mọi thứ (ưu tiên cao nhất, đứng trước FSM) ----
        if not docked and low_hp is not None and low_hp < SURVIVAL_HP:
            self.last_why = f"hp {low_hp:.2f} < {SURVIVAL_HP} → survival: recall drone + orbit out"
            acts = []
            if drones_in_space:
                acts.append({"do": "recall_drones", "why": self.last_why})
            acts.append({"do": "orbit_out", "why": self.last_why})
            return acts
        if cap is not None and cap < SURVIVAL_CAP and not docked:
            self.last_why = f"cap {cap:.0f}% < {SURVIVAL_CAP*100:.0f}% → tắt hardener, cap recharge"
            acts = [{"do": "cap_save", "why": self.last_why}]
            if drones_in_space:
                acts.append({"do": "recall_drones", "why": self.last_why})
            return acts

        if docked:
            self.locked_names.clear()
            self.drones_out = False
            self.modules_on = False
            return []

        # ---- 2. pocket logic: gate + không quái → kích gate (pocket kế) ----
        hostiles = self._hostiles(overview)
        gate = self._gate(overview)
        gate_dist = _entry_distance_m(gate) if gate else None
        if gate is not None and not hostiles:
            if gate_dist is None or gate_dist > 2600.0:
                self.last_why = (f"pocket sạch, gate {gate_dist/1000 if gate_dist else '?':.0f} km"
                                 " → approach gate vào tầm kích")
                return [{"do": "approach", "at": gate.get("center"),
                         "target": _pick_name(gate), "why": self.last_why}]
            self.last_why = "pocket sạch + gate trong tầm → kích gate vào pocket kế"
            return [{"do": "activate_gate", "at": gate.get("center"),
                     "why": self.last_why}]

        # ---- 3. KHÔNG quái, KHÔNG gate → mission objective đã xong ở pocket này
        if not hostiles and gate is None:
            self.last_why = "không quái không gate → chờ objective update (không đoán)"
            return [{"do": "wait", "s": 3.0, "why": self.last_why}]

        # ---- 4. COMBAT: quái có trong tầm → lock theo thứ tự + orbit + drone ----
        in_range = [h for h in hostiles
                    if h.get("distance_m") is not None
                    and h["distance_m"] <= 60_000.0]
        too_far = [h for h in hostiles
                   if h.get("distance_m") is not None
                   and h["distance_m"] > 60_000.0]

        acts: list[dict[str, Any]] = []

        # 4a. Đang có quái xa hơn 60km và không có gì trong range → approach
        #     con GẦN NHẤT (evidence: distance_m từ AU/km parse đúng đơn vị).
        if not in_range and too_far:
            nearest = min(too_far, key=lambda h: h["distance_m"])
            self.last_why = (f"quái gần nhất {_pick_name(nearest)} "
                             f"{nearest['distance_m']/1e9:.1f} AU → approach tới")
            return [{"do": "approach", "at": nearest.get("center"),
                     "target": _pick_name(nearest), "why": self.last_why}]

        # 4b. Trigger discipline: kill_first (EWAR/web) trước, trigger LAST.
        names = [_pick_name(h) for h in in_range]
        ordered = lock_order(names) if names else []
        trigger_names = self.tactics.get("trigger_names") or ()
        kill_first = self.tactics.get("kill_first") or ()
        jamming = self.tactics.get("jamming_names") or JAMMING_TOKENS[:4]

        def _is_trigger(name: str) -> bool:
            return bool(trigger_names) and _has_token(name, trigger_names)

        def _prio(name: str) -> int:
            if _is_trigger(name):
                return 3            # trigger cuối cùng
            if _has_token(name, kill_first) or _has_token(name, jamming) or _has_token(name, WEB_TOKENS):
                return 0            # EWAR/web/kill-first trước
            return 1

        ordered.sort(key=lambda c: (_prio(c.get("raw", "")),
                                    -float(c.get("priority", 0))))

        # 4c. Drone: có drone trong bay + có target + chưa out → launch (P1 proven)
        if drones_in_bay and drones_in_space == 0 and in_range:
            acts.append({"do": "launch_drones",
                         "why": f"{drones_in_bay} drone trong bay, có target trong range"})
            self.drones_out = True
        # leash: drone out + target xa hơn leash → recall (drone chết oan)
        if drones_in_space and in_range:
            farthest = max((h.get("distance_m") or 0) for h in in_range)
            if farthest > DRONE_LEASH_M:
                acts.append({"do": "recall_drones",
                             "why": f"target {farthest/1000:.0f} km > leash {DRONE_LEASH_M/1000:.0f} km"})

        # 4d. Lock 1 target MỚI (không lock lại đã lock — tránh spam)
        target_entry = None
        for cand in ordered:
            nm = cand.get("raw") or ""
            real = next((h for h in in_range if _pick_name(h) == nm), None)
            if real and nm not in self.locked_names:
                target_entry = real
                self.locked_names.add(nm)
                break

        if target_entry is not None:
            acts.append({"do": "lock", "at": target_entry.get("center"),
                         "target": _pick_name(target_entry),
                         "why": f"lock theo kill-order: {_pick_name(target_entry)} "
                                f"({_prio(_pick_name(target_entry))})"})

        # 4e. Orbit target gần nhất (trong range, proven approach primitive)
        if in_range:
            near = min(in_range, key=lambda h: h["distance_m"])
            orbit_km = self.tactics.get("orbit_km", 20)
            acts.append({"do": "orbit", "at": near.get("center"),
                         "target": _pick_name(near), "km": orbit_km,
                         "why": f"orbit {orbit_km}km quanh {_pick_name(near)} (kite frigates)"})

        # 4f. Module: bật 1 lần khi vào combat (state UNKNOWN — không toggle mù)
        if not self.modules_on and in_range:
            acts.append({"do": "activate_module", "slots": self.fit.get("weapon_slots", [1, 2]),
                         "why": "vào combat — bật vũ khí (1 lần, không toggle mù)"})
            self.modules_on = True

        if not acts:
            self.last_why = "có quái trong range nhưng mọi target đã lock — chờ bắn hạ"
            return [{"do": "wait", "s": 2.0, "why": self.last_why}]
        return acts
