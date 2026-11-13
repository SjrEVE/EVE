"""FIT MAP — khai báo fit tàu thật (slot/rack) cho brain, không hard-code.

Mỗi fit mô tả:
  weapon_slots/weapon_rack   — giàn chủ lực (fire_weapons)
  propulsion_slot/rack       — Afterburner/MWD (toggle_ab)
  repair_slots/repair_rack   — local tank ACTIVE (Small Armor Repairer / Shield Booster)
  hardener_slots/rack        — hardener tự chạy (bật một lần, không toggle lại)
  tank                       — "armor" | "shield" (để logi/brain biết lớp nào đang rep)
  rep_always_on              — True = local tank bật một lần rồi GIỮ (fit cap-stable,
                               đúng doctrine Punisher T1 Electrical); False = hysteresis
                               theo rep_open_hp/rep_close_hp (fit hụt cap)
  has_drones                 — fit không drone phải TẮT nhánh drone của brain

Rack → keybind (ground control.py act_module): high=F{slot}, mid=Alt+F, low=Ctrl+F.

NGUY HIỂM ĐÃ GHI (test_tank_modules, live 11-12): HUD không xuất trạng thái module
trong space → bấm đúp là TẮT module đang chạy. FitController chỉ bấm khi:
  - observed False → bấm (cần bật)
  - observed True → KHÔNG BẤM (đang chạy)
  - observed None/unknown → bấm MỘT LẦN mỗi engagement (never re-press)
Active reps (SAR/booster) là ngoại lệ có chính sách riêng: mở khi hp < rep_open_hp,
đóng khi hp > rep_close_hp — đọc được True/False thì theo quan sát, unknown thì
một lần cho mỗi chuyển trạng thái.
"""
from __future__ import annotations

from typing import Any

# ---------------- fit registry ----------------
# Nguồn fit Punisher: Aceface "EASY 10 mil Punisher for SOLO T1 Abyss"
# (youtube.com/watch?v=sr-fklVYGSU) — cap-stable trong Electrical, max difficulty
# Electrical T1 (Abyss Tracker bc999d8b, 369 run ghi nhận).
FITS: dict[str, dict[str, Any]] = {
    "ab_punisher": {
        "ship": "Punisher",
        "weapon_slots": (1, 2, 3, 4), "weapon_rack": "high",
        "propulsion_slot": 1, "propulsion_rack": "mid",
        "repair_slots": (1, 2), "repair_rack": "low",
        "hardener_slots": (3,), "hardener_rack": "low",
        "tank": "armor",
        "rep_always_on": True,   # cap-stable trong Electrical T1 — tank chạy liên tục
        "rep_open_hp": 0.60, "rep_close_hp": 0.85,   # chỉ dùng khi rep_always_on=False
        "has_drones": False,
    },
}


def module_rack_key(rack: str) -> tuple[str, ...]:
    """Rack → modifier của keybind F (ground act_module trong control.py)."""
    return {"high": (), "mid": ("alt",), "low": ("ctrl",)}.get(rack, ())


def _toggle(acts: list[dict[str, Any]], do: str, fit: dict[str, Any],
            rack: str, slot: int, why: str) -> None:
    acts.append({"do": do, "rack": rack, "slot": slot,
                 "mods": list(module_rack_key(rack)), "why": why})


class FitController:
    """Bật/giữ module theo fit — quyết định từ TRẠNG THÁI ĐỌC ĐƯỢC, không bấm mù.

    Cách dùng: tick(world_module_state, hp=..., engagement=<run/room tag>) mỗi
    tick khi ở *_FIGHT. Trả list action (dict có do/rack/slot/mods/why) — executor
    bấm qua act_module(slot, rack).
    """

    def __init__(self, fit: dict[str, Any]) -> None:
        self.fit = fit
        self._pressed: set[tuple[str, int]] = set()   # (rack, slot) đã bấm khi unknown
        self._reps_open: bool | None = None           # None = chưa quyết định
        self._engagement: Any = None

    def _state(self, world: dict[str, Any], rack: str, slot: int) -> bool | None:
        st = (world.get("module_state") or {}).get(rack) or {}
        v = st.get(slot)
        return v if isinstance(v, bool) else None

    def tick(self, world: dict[str, Any], hp: float,
             engagement: Any) -> list[dict[str, Any]]:
        fit = self.fit
        if self._engagement != engagement:
            self._engagement = engagement
            self._pressed.clear()
            self._reps_open = None
        acts: list[dict[str, Any]] = []

        # 1) giàn chủ lực — observed False → bật; True → giữ; None → một lần
        for slot in fit["weapon_slots"]:
            rack = fit["weapon_rack"]
            st = self._state(world, rack, slot)
            if st is False:
                _toggle(acts, "fire_weapons", fit, rack, slot,
                        f"Weapon slot {slot} observed OFF — bật")
            elif st is None and (rack, slot) not in self._pressed:
                self._pressed.add((rack, slot))
                _toggle(acts, "fire_weapons", fit, rack, slot,
                        f"Weapon slot {slot} state unknown — bật một lần/engagement")

        # 2) propulsion — bật một lần (AB giữ nguyên cả room; không toggle lại)
        rack, slot = fit["propulsion_rack"], fit["propulsion_slot"]
        st = self._state(world, rack, slot)
        if st is False:
            _toggle(acts, "toggle_ab", fit, rack, slot, "Propulsion observed OFF — bật")
        elif st is None and (rack, slot) not in self._pressed:
            self._pressed.add((rack, slot))
            _toggle(acts, "toggle_ab", fit, rack, slot,
                    "Propulsion state unknown — bật một lần/engagement")

        # 3) hardener — bật một lần, KHÔNG BAO GIỜ toggle lại (RAH tự adapt)
        for slot in fit["hardener_slots"]:
            rack = fit["hardener_rack"]
            st = self._state(world, rack, slot)
            if st is False:
                _toggle(acts, "toggle_hardener", fit, rack, slot,
                        f"Hardener slot {slot} observed OFF — bật")
            elif st is None and (rack, slot) not in self._pressed:
                self._pressed.add((rack, slot))
                _toggle(acts, "toggle_hardener", fit, rack, slot,
                        f"Hardener slot {slot} unknown — bật một lần/engagement")

        # 4) active tank (SAR/booster) — hai chính sách:
        #    rep_always_on=True  → bật một lần rồi GIỮ (cap-stable fit);
        #    rep_always_on=False → hysteresis theo HP (open < rep_open_hp,
        #                          close > rep_close_hp).
        always_on = bool(fit.get("rep_always_on"))
        want_open: bool | None = None
        if always_on:
            want_open = True
        elif hp < fit["rep_open_hp"]:
            want_open = True
        elif hp > fit["rep_close_hp"]:
            want_open = False
        # hp trong khoảng hysteresis → giữ nguyên quyết định cũ
        if want_open is True and self._reps_open is not True:
            opened = False
            for slot in fit["repair_slots"]:
                rack = fit["repair_rack"]
                st = self._state(world, rack, slot)
                if st is False:
                    _toggle(acts, "toggle_rep", fit, rack, slot,
                            f"hp {hp:.0%} < {fit['rep_open_hp']:.0%} — SAR slot {slot} observed OFF")
                    opened = True
                elif st is None and (rack, slot) not in self._pressed:
                    self._pressed.add((rack, slot))
                    _toggle(acts, "toggle_rep", fit, rack, slot,
                            f"hp {hp:.0%} < {fit['rep_open_hp']:.0%} — SAR slot {slot} unknown, bật một lần")
                    opened = True
            if opened or all(self._state(world, fit["repair_rack"], s) is True
                             for s in fit["repair_slots"]):
                self._reps_open = True
        elif want_open is False and self._reps_open is not False:
            closed = False
            for slot in fit["repair_slots"]:
                rack = fit["repair_rack"]
                st = self._state(world, rack, slot)
                if st is True:
                    _toggle(acts, "close_rep", fit, rack, slot,
                            f"hp {hp:.0%} > {fit['rep_close_hp']:.0%} — đóng SAR slot {slot} tiết kiệm cap")
                    closed = True
            if closed or not any(self._state(world, fit["repair_rack"], s) is True
                                 for s in fit["repair_slots"]):
                self._reps_open = False
        return acts
