"""DEATH GUARDS — mỗi guard = 1 cái chết thật của người khác (học từ xác tàu).

Nguồn xác tàu (dump 2026-11-07):
- AbyssBot changelog v1.019/v1.05x (bug chính thức của bot thương mại)
- Forum AbyssBot t.728 (5 Gila T3 chết đứng vì overview empty)
- Reddit r/Eve: Tachyon cloud văng ra biên, disconnect khi manual pilot,
  Skybreaker T0, cap cạn 10s trước Scylla Tyrannos, drone bỏ lại phòng cũ

Guards tích hợp vào Bot.tick() — chạy mỗi tick, fail → event + hành động an toàn.
"""
from __future__ import annotations

import time
from typing import Any, Callable


class Guard:
    """Base: check(state) → None (OK) hoặc dict(action)."""
    name = "base"

    def check(self, st: dict[str, Any]) -> dict[str, Any] | None:
        raise NotImplementedError


# ----------------------------------------------------------------
# DEATH #1 — "5 Gila T3 chết đứng 20 phút" (forum t.728)
# Nguyên nhân: overview empty / bot đứng im không nhận ra → timer nổ
# Guard: nếu đang FIGHT mà overview trống > N giây → MAYDAY + SURVIVAL
# ----------------------------------------------------------------
class OverviewEmptyGuard(Guard):
    name = "overview_empty"

    def __init__(self, timeout_s: float = 10.0) -> None:
        self.timeout_s = timeout_s
        self.empty_since: float | None = None

    def check(self, st: dict[str, Any]) -> dict[str, Any] | None:
        fighting = str(st.get("phase", "")).endswith("_FIGHT")
        entries = st.get("overview_count", 0)
        now = time.time()
        if fighting and entries == 0:
            if self.empty_since is None:
                self.empty_since = now
            if now - self.empty_since >= self.timeout_s:
                return {"action": "survival", "reason": f"overview empty {self.timeout_s:.0f}s — "
                        "đứng im = chết timer (5 Gila t.728)"}
        else:
            self.empty_since = None
        return None


# ----------------------------------------------------------------
# DEATH #2 — spam loop "Cruiser Abyss Confirmed" x15 (t.728)
# Nguyên nhân: bấm lặp không thấy state đổi → treo mãi
# Guard: watchdog — cùng 1 action lặp N lần mà state không đổi → bail
# ----------------------------------------------------------------
class LoopWatchdog(Guard):
    name = "loop_watchdog"

    # Chỉ soi trong abyss: docked/idle thì phase đứng yên là bình thường (spam MAYDAY vô nghĩa)
    ABYSS_PHASES = frozenset({
        "FILA_SPOOL", "ROOM1_FIGHT", "ROOM1_CLEARED", "GATE_TRANSIT",
        "ROOM2_FIGHT", "ROOM2_CLEARED", "ROOM3_FIGHT", "ROOM3_CLEARED",
        "EXIT", "LOOT", "SURVIVAL",
    })

    def __init__(self, max_same: int = 5) -> None:
        self.max_same = max_same
        self.last_action: str | None = None
        self.count = 0

    def check(self, st: dict[str, Any]) -> dict[str, Any] | None:
        if st.get("phase") not in self.ABYSS_PHASES:
            self.last_action = None
            self.count = 0
            return None
        act = f"{st.get('phase')}|{st.get('last_action', '')}"
        if act == self.last_action:
            self.count += 1
        else:
            self.last_action = act
            self.count = 1
        if self.count > self.max_same:
            self.count = 0   # reset sau khi báo — FC quyết path khác
            return {"action": "mayday", "reason": f"action '{act}' lặp {self.max_same}+ lần "
                    "không đổi state — loop vô hạn (Vila spam t.728)"}
        return None


# ----------------------------------------------------------------
# DEATH #3 — drone bỏ lại phòng cũ (AbyssBot v1.019 changelog)
# Nguyên nhân: gate jump khi drone còn ngoài
# Guard: cấm GATE khi drone_in_space > 0 → recall trước, verify rồi mới gate
# ----------------------------------------------------------------
class DroneOutGuard(Guard):
    name = "drone_out"

    def check(self, st: dict[str, Any]) -> dict[str, Any] | None:
        # chỉ chặn khi FSM MUỐN gate (lệnh GATE đang chờ) — được gọi từ _do_gate
        return None   # check này nằm trong Bot._do_gate, không phải tick

    @staticmethod
    def allow_gate(st: dict[str, Any]) -> tuple[bool, str]:
        drones_out = st.get("drones_in_space", 0)
        if drones_out > 0:
            return False, f"còn {drones_out} drone ngoài — jump = mất drone (v1.019 bug). Shift+R trước."
        return True, ""


# ----------------------------------------------------------------
# DEATH #4 — Tachyon cloud văng ra biên (reddit 150-run player)
# Nguyên nhân: MWD vào cloud ×8 accel → slingshot qua vùng đỏ
# Guard: weather Dark (cloud trắng phổ biến) → cấm MWD override; velocity spike bất thường → stop ngay
# ----------------------------------------------------------------
class CloudSlingGuard(Guard):
    name = "cloud_sling"

    def __init__(self, max_speed_mps: float = 2500.0) -> None:
        self.max_speed = max_speed_mps   # Gila AB ~1.2k, MWD ~3-4k; 2500 = ngưỡng bất thường cho AB fit

    def check(self, st: dict[str, Any]) -> dict[str, Any] | None:
        speed = st.get("speed_mps", 0) or 0
        weather = str(st.get("weather", "")).lower()
        if speed > self.max_speed:
            return {"action": "stop", "reason": f"speed {speed} m/s bất thường "
                    "(Tachyon ×8 accel?) — Ctrl+Space NGAY để không slingshot ra biên"}
        if "dark" in weather and st.get("mwd_on"):
            return {"action": "disable_mwd", "reason": "Dark + MWD = mồi Tachyon sling; AB-only"}
        return None


# ----------------------------------------------------------------
# DEATH #5 — cap cạn 10s trước Scylla Tyrannos (reddit 2.5B loss)
# Nguyên nhân: neut dồn → cap 0 → active tank tắt → chết
# Guard: cap dưới ngưỡng → tắt module phụ (prop/web) giữ rep; báo FC
# ----------------------------------------------------------------
class CapStarveGuard(Guard):
    name = "cap_starve"

    def __init__(self, cap_floor: float = 0.25) -> None:
        self.cap_floor = cap_floor
        self._warned_at = 0.0

    def check(self, st: dict[str, Any]) -> dict[str, Any] | None:
        cap = st.get("cap")
        tank_on = st.get("tank_on", True)
        if cap is None:
            # PyColor chưa decode → cap MÙ. Không đoán; cảnh báo 60s/lần để không spam.
            import time as _t
            if _t.time() - self._warned_at > 60.0:
                self._warned_at = _t.time()
                return {"action": "cap_unknown",
                        "reason": "cap chưa đọc được (pmark._color = PyColor chưa decode) — "
                                  "guard cap đang MÙ, không tự power_save"}
            return None
        if cap < self.cap_floor and tank_on:
            return {"action": "power_save",
                    "reason": f"cap {cap:.0%} < {self.cap_floor:.0%} — neut-heavy room "
                    "(Scylla Tyrannos 2.5B loss): tắt prop/web giữ rep",
                    "disable": ["prop", "web"]}
        return None


# ----------------------------------------------------------------
# DEATH #6 — damping: mất priority target T4+ (AbyssBot known issue)
# Nguyên nhân: bị damp không lock được con nguy hiểm → đứng bắn sai
# Guard: lock fail N lần liên tiếp → đổi target kế trong order; hết order → survival
# ----------------------------------------------------------------
class DampingGuard(Guard):
    name = "damping"

    def __init__(self, max_lock_fail: int = 3) -> None:
        self.max_lock_fail = max_lock_fail
        self.lock_fails = 0

    def check(self, st: dict[str, Any]) -> dict[str, Any] | None:
        if st.get("last_lock_failed"):
            self.lock_fails += 1
        else:
            self.lock_fails = 0
        if self.lock_fails >= self.max_lock_fail:
            self.lock_fails = 0
            return {"action": "next_target",
                    "reason": "lock fail 3 lần — đang bị damp (T4+ known issue): "
                    "bỏ target này, chọn con kế trong lock_order"}
        return None


# ----------------------------------------------------------------
# DEATH #7 — nhặt can cách gate 25km rồi không về kịp (reddit Gila #1)
# Nguyên nhân: đầu tư time vào loot xa → boundary + timer
# Guard: loot decision — chỉ cho loot can khi dist_gate còn < budget
# ----------------------------------------------------------------
class LootGreedGuard(Guard):
    name = "loot_greed"

    def __init__(self, max_dist_for_loot_m: int = 15000) -> None:
        self.max_dist = max_dist_for_loot_m

    def check(self, st: dict[str, Any]) -> dict[str, Any] | None:
        if st.get("want_loot"):
            d = st.get("dist_gate", 0) or 0
            if d > self.max_dist:
                return {"action": "skip_loot",
                        "reason": f"can cách gate {d}m > {self.max_dist}m — nhặt can xa "
                        "= đổi mạng lấy loot (reddit Gila 25km từ gate)"}
        return None


# ----------------------------------------------------------------
# DEATH #8 — quên nạp đạn / filament sai (reddit: took wrong filament)
# Guard precheck: trước FILA verify ammo + đúng tier/weather theo plan
# ----------------------------------------------------------------
class PreflightGuard(Guard):
    name = "preflight"

    @staticmethod
    def allow_fila(st: dict[str, Any]) -> tuple[bool, str]:
        if not st.get("ammo_loaded", True):
            return False, "ammo chưa nạp — Ctrl+R trước (AbyssBot: check reload sau undock)"
        plan = st.get("plan_fila", {})
        actual = st.get("fila_name", "")
        want_tier = plan.get("tier")
        want_weather = plan.get("weather")
        if want_tier is not None and want_tier not in actual:
            return False, f"filament '{actual}' không đúng tier plan {want_tier} — sai filament = tự sát"
        if want_weather and want_weather.lower() not in actual.lower():
            return False, f"filament '{actual}' không đúng weather plan {want_weather}"
        return True, ""


# ----------------------------------------------------------------
# DEATH #9 — disconnect khi manual pilot sát biên (reddit: orbit là sống)
# Guard: hành vi mặc định luôn có orbit đang active (orbit cache/gate) —
# disconnect khi orbit = tàu tự giữ vị trí an toàn. Check: đang FIGHT mà
# maneuver=None (đứng trơ) → bay vào orbit ngay.
# ----------------------------------------------------------------
class PassiveSafetyGuard(Guard):
    name = "passive_safety"

    def __init__(self, timeout_s: float = 6.0) -> None:
        self.timeout_s = timeout_s
        self.drift_since: float | None = None

    def check(self, st: dict[str, Any]) -> dict[str, Any] | None:
        fighting = str(st.get("phase", "")).endswith("_FIGHT")
        maneuver = st.get("maneuver")   # None = không orbit/approach gì cả
        now = time.time()
        if fighting and maneuver in (None, ""):
            if self.drift_since is None:
                self.drift_since = now
            if now - self.drift_since >= self.timeout_s:
                self.drift_since = None
                return {"action": "orbit_cache",
                        "reason": f"đang FIGHT mà không maneuver {self.timeout_s:.0f}s — "
                        "disconnect lúc drift sát biên = chết; orbit cache là passive safety"}
        else:
            self.drift_since = None
        return None


# ----------------------------------------------------------------
# Bộ quản lý — Bot.tick gọi check_all
# ----------------------------------------------------------------
DEFAULT_GUARDS: list[Guard] = [
    OverviewEmptyGuard(),
    LoopWatchdog(),
    CloudSlingGuard(),
    CapStarveGuard(),
    DampingGuard(),
    LootGreedGuard(),
    PassiveSafetyGuard(),
]


class GuardManager:
    def __init__(self, guards: list[Guard] | None = None) -> None:
        self.guards = guards if guards is not None else list(DEFAULT_GUARDS)

    def check_all(self, st: dict[str, Any]) -> list[dict[str, Any]]:
        """Chạy tất cả guards, trả list actions (guard nào nêu action thì thực hiện)."""
        out = []
        for g in self.guards:
            try:
                r = g.check(st)
            except Exception as e:   # noqa: BLE001 — guard lỗi không được kill bot
                r = {"action": "guard_error", "reason": f"{g.name}: {e}"}
            if r:
                r["guard"] = g.name
                out.append(r)
        return out
