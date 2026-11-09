"""TRIO ROLES — FSM bổ sung cho multibox 2DPS+1Logi (nguồn: Gustav trio video +
Minmatar wiki; merge 2026-11-10 thêm tactic T5/T6: kite Tessera 22km, Vedmak
transversal control, đổi đạn theo cự ly, logi counter-orbit khi bị primary).

Mỗi acc = 1 Bot instance có role; room checklist chung ở docs/TRIO_PLAYBOOK.md.
Đây là phần "chiều tay" của endgame multibox — FSM khác nhau theo ROLE.

Contract (test_trio + test_endgame): acts dùng key "do", TrioRole có reps_open +
new_room(); reflex build st với keys hp/cap/room_entry/moved_this_room/
kikimora_count/tank_hp/dist_to_tank_km/current_target/want_target. Tactic mới
chỉ kích hoạt khi st có "overview" (danh sách tên quái) — SIM/test không có
nên giữ nguyên hành vi cũ.
"""
from __future__ import annotations
from typing import Any

try:
    from . import rats
    from . import rooms as rooms_mod
except ImportError:  # pragma: no cover — chạy standalone
    import rats  # type: ignore
    import rooms as rooms_mod  # type: ignore

ROLES = ("tank", "dps", "logi")

# Ngưỡng kích hoạt hành vi theo role (nguồn: TRIO_PLAYBOOK checklist)
LOGI_REPS_ALL_AT_HP = 0.60      # tank hp <60% → logi mở hết reps
KIKI_SWARM_THRESHOLD = 6        # >6 kikimora → all reps lên tank (Gustav ngưỡng)


def _select_ammo(dist_km: float, weapon_system: str = "rocket") -> str:
    """Đổi đạn theo cự ly: tầm xa giữ DPS tốt vs tầm gần dùng đạn damage cao nhất."""
    w = weapon_system.lower()
    if w == "rocket":
        return "javelin" if dist_km > 18.0 else "rage"
    if w == "laser":
        return "scorch" if dist_km > 15.0 else "conflagration"
    if w == "disintegrator":
        return "mystic" if dist_km > 13.0 else "occult"
    return "standard"


class TrioRole:
    """Gói hành vi role — Bot giữ 1 instance; tick() trả extra actions (advisory)."""

    def __init__(self, role: str) -> None:
        role_clean = str(role).strip().lower()
        if role_clean not in ROLES:
            raise ValueError(f"role phải thuộc {ROLES}, nhận '{role}'")
        self.role = role_clean
        self.reps_open = False
        self._vedmak_stopped = False

    # ---------------- helpers tactic mới ----------------
    def _room_of(self, st: dict[str, Any]) -> str:
        names = st.get("overview") or []
        if not names:
            return "UNKNOWN"
        return rooms_mod.detect_room(list(names))

    def _primary(self, st: dict[str, Any]) -> str | None:
        """Con cần bắn theo lock_order (fit ab_trio); fallback want_target."""
        names = st.get("overview") or []
        if names:
            ordered = rats.lock_order(list(names), fit_type="ab_trio",
                                      resist_hole=st.get("resist_hole"))
            if ordered:
                return ordered[0]["name"]
        return st.get("want_target") or st.get("current_target")

    # ---------------- TANK (Nergal) ----------------
    def tank_tick(self, st: dict[str, Any]) -> list[dict[str, Any]]:
        acts = []
        # entry: tank là aggro magnet — approach cache trước (no-switch enemies khóa nó)
        if st.get("room_entry") and not st.get("moved_this_room"):
            acts.append({"do": "approach_cache", "why": "tank = aggro magnet (no-switch rats)"})
        # hp rơi → emit cho logi (logi đọc bus riêng)
        if st.get("hp", 1.0) < LOGI_REPS_ALL_AT_HP and not self.reps_open:
            acts.append({"do": "signal_logi_all_reps", "why": f"tank hp <{LOGI_REPS_ALL_AT_HP:.0%}"})
        # tactic mới (chỉ khi thấy overview): Tessera kite 22km / Vedmak đứng im
        room = self._room_of(st)
        if room == "TESSERA":
            acts.append({"do": "keep_range", "target": "Triglavian Bioadaptive Cache",
                         "km": 22, "why": "Grip Tessera xé mọi thứ <15km — kite ngoài tầm"})
        elif room == "VEDMAK" and not any("starving" in n.lower() for n in (st.get("overview") or [])):
            if not self._vedmak_stopped:
                acts.append({"do": "stop_ship", "why": "vedmak_transversal_control — "
                             "hết neut thì đứng im cho Vedmak orbit hụt"})
                self._vedmak_stopped = True
        return acts

    # ---------------- DPS (Retribution) ----------------
    def dps_tick(self, st: dict[str, Any]) -> list[dict[str, Any]]:
        acts = []
        # DPS giữ orbit tank — không tự tank aggro
        if st.get("dist_to_tank_km", 0) > 5.0:
            acts.append({"do": "orbit_tank", "km": 2.5, "why": "giữ sát tank — logi chỉ rep 1 điểm"})
        # bắn theo lock_order (rats.py) — DPS không tự chọn mục tiêu khác
        target = st.get("current_target")
        want = st.get("want_target")
        if want and target != want:
            acts.append({"do": "switch_target", "to": want, "why": "focus fire đồng bộ trio"})
        # tactic mới: Tessera DPS orbit 10km xả đạn gần; Vedmak đứng im; đổi đạn theo cự ly
        room = self._room_of(st)
        primary = self._primary(st)
        if room == "TESSERA" and primary:
            acts.append({"do": "orbit_target", "target": primary, "km": 10.0,
                         "why": "tank kéo Tessera 22km — DPS áp sát 10km bắn đạn Rage/Conflag"})
        elif room == "VEDMAK" and not any("starving" in n.lower() for n in (st.get("overview") or [])):
            if not self._vedmak_stopped:
                acts.append({"do": "stop_ship", "why": "vedmak_transversal_control"})
                self._vedmak_stopped = True
        if primary and st.get("target_dist_km") is not None:
            acts.append({"do": "attack", "target": primary,
                         "ammo": _select_ammo(float(st["target_dist_km"]),
                                              str(st.get("weapon", "laser")))})
        return acts

    # ---------------- LOGI (Deacon) ----------------
    def logi_tick(self, st: dict[str, Any]) -> list[dict[str, Any]]:
        acts = []
        n_kiki = st.get("kikimora_count", 0)
        tank_hp = st.get("tank_hp", 1.0)
        # >6 kikimora room → mở CẢ 3 reps ngay từ đầu (Gustav ngưỡng)
        if n_kiki > KIKI_SWARM_THRESHOLD and not self.reps_open:
            acts.append({"do": "all_reps_on_tank", "why": f"{n_kiki} kikimora > {KIKI_SWARM_THRESHOLD} — all reps"})
            self.reps_open = True
        elif tank_hp < LOGI_REPS_ALL_AT_HP and not self.reps_open:
            acts.append({"do": "all_reps_on_tank", "why": f"tank hp {tank_hp:.0%} < 60%"})
            self.reps_open = True
        elif tank_hp > 0.85 and self.reps_open:
            acts.append({"do": "close_extra_reps", "why": "tank ổn — tiết kiệm cap"})
            self.reps_open = False
        # cap thấp = MAYDAY (cap brick vẫn có hạn)
        cap = st.get("cap")
        if cap is not None and cap < 0.2:
            acts.append({"do": "mayday", "why": "logi cap <20% — hết reps = fleet chết"})
        # tactic mới: logi bị primary → counter-orbit giữ transversal cho logi rep kịp
        if st.get("logi_primaried"):
            acts.append({"do": "counter_orbit_transversal", "km": 5.0,
                         "why": "logi đang bị bắn — bay vòng ngược hướng primary"})
        return acts

    def tick(self, st: dict[str, Any]) -> list[dict[str, Any]]:
        if self.role == "tank":
            return self.tank_tick(st)
        if self.role == "dps":
            return self.dps_tick(st)
        return self.logi_tick(st)

    def new_room(self) -> None:
        """Reset per-room state — reactive hardener + reps đóng (reset quên = dead slot)."""
        self.reps_open = False
        self._vedmak_stopped = False
