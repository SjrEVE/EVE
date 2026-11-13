"""Punisher T1 Electrical fit — fit-map + module read-back control (RED first).

Fit của Aceface (https://youtu.be/sr-fklVYGSU):
  High 1-4: Small Focused Beam Laser II (multifrequency, không đổi đạn giữa room)
  Mid 1:    1MN Monopropellant Enduring Afterburner
  Mid 2:    Small Compact Pb-Acid Cap Battery
  Low 1-2:  Small Armor Repairer II  (ACTIVE ARMOR TANK — rack LOW, không phải mid)
  Low 3:    Reactive Armor Hardener (adaptive, không cần bấm gì sau khi bật)
  Rig:      Small Auxiliary Nano Pump

Ba contract:
1. fit_map: declarative slot map cho fit thật (không hard-code trong brain).
2. FitController: bật module theo TRẠNG THÁI ĐỌC ĐƯỢC — False mới bấm, True
   KHÔNG BẦM (toggle = tắt module đang chạy = chết), None = một lần/engagement.
3. Trio state không được bịa tank_hp từ HP của chính mình (logi không phải tank).
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.bus import FileBus            # noqa: E402
from fila_bot.config import Config         # noqa: E402
from fila_bot.reflex import Bot, SimExecutor  # noqa: E402

PASS = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} — {msg}")
        sys.exit(1)


def events(d: Path) -> list[dict]:
    p = d / "bot_to_fc.jsonl"
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


# ---------------- 1. fit map ----------------
from fila_bot.fit_map import FITS, module_rack_key  # noqa: E402

fit = FITS["ab_punisher"]
ok("punisher_fit_registered", fit is not None, "fit 'ab_punisher' chưa có trong FITS")
ok("punisher_weapons_four_beams",
   fit["weapon_slots"] == (1, 2, 3, 4) and fit["weapon_rack"] == "high",
   f"{fit.get('weapon_slots')}/{fit.get('weapon_rack')}")
ok("punisher_afterburner_mid1",
   fit["propulsion_slot"] == 1 and fit["propulsion_rack"] == "mid",
   f"{fit.get('propulsion_slot')}/{fit.get('propulsion_rack')}")
ok("punisher_armor_reps_low_rack",
   fit["repair_slots"] == (1, 2) and fit["repair_rack"] == "low",
   f"SAR là low-slot module — rack phải là 'low', không phải 'mid': {fit}")
ok("punisher_rah_low3",
   fit["hardener_slots"] == (3,) and fit["hardener_rack"] == "low",
   f"RAH ở low 3: {fit}")
ok("punisher_no_drones", fit["has_drones"] is False,
   "Punisher không có drone bay — brain phải tắt nhánh drone")
ok("punisher_armor_tank_policy",
   fit["tank"] == "armor" and fit["rep_open_hp"] == 0.60 and fit["rep_close_hp"] == 0.85,
   f"ngưỡng reps theo logi_tick cũ (60/85): {fit}")
ok("fit_rack_key_high", module_rack_key("high") == (), "high = F không modifier")
ok("fit_rack_key_mid", module_rack_key("mid") == ("alt",), "mid = Alt+F")
ok("fit_rack_key_low", module_rack_key("low") == ("ctrl",), "low = Ctrl+F")

# ---------------- 2. module control với read-back ----------------
from fila_bot.fit_map import FitController  # noqa: E402


def hud(states: dict[str, dict[int, bool | None]]) -> dict:
    """world['module_state'] shape giống live_security.refresh()."""
    return {"module_state": states, "modules_observed": bool(states)}


FULL_OFF = {"high": {1: False, 2: False, 3: False, 4: False},
            "mid": {1: False, 2: None}, "low": {1: False, 2: False, 3: False}}

fc = FitController(fit)
acts = fc.tick(hud(FULL_OFF), hp=1.0, engagement="run1-room1")
kinds = {(a["do"], a.get("rack"), a.get("slot")) for a in acts}
ok("cold_start_activates_weapons",
   ("fire_weapons", "high", 1) in kinds and ("fire_weapons", "high", 4) in kinds,
   str(acts))
ok("cold_start_activates_ab",
   ("toggle_ab", "mid", 1) in kinds, str(acts))
ok("cold_start_activates_armor_reps_low",
   ("toggle_rep", "low", 1) in kinds and ("toggle_rep", "low", 2) in kinds,
   f"SAR bật bằng Ctrl+F (low rack): {acts}")
ok("cold_start_activates_rah",
   ("toggle_hardener", "low", 3) in kinds, str(acts))

# Module observed ACTIVE → KHÔNG bấm lại (bấm = toggle OFF = mất tank giữa room)
ALL_ON = {"high": {1: True, 2: True, 3: True, 4: True},
          "mid": {1: True, 2: None}, "low": {1: True, 2: True, 3: True}}
acts2 = fc.tick(hud(ALL_ON), hp=1.0, engagement="run1-room1")
ok("active_modules_never_repressed", acts2 == [], f"bấm lại = tắt module: {acts2}")

# State UNKNOWN (None) → bấm MỘT LẦN mỗi engagement, không lặp
UNKNOWN_STATE = {"high": {1: None, 2: None, 3: None, 4: None},
                 "mid": {1: None, 2: None}, "low": {1: None, 2: None, 3: None}}
fc2 = FitController(fit)
first = fc2.tick(hud(UNKNOWN_STATE), hp=1.0, engagement="run1-room1")
second = fc2.tick(hud(UNKNOWN_STATE), hp=1.0, engagement="run1-room1")
ok("unknown_state_pressed_once",
   len(first) > 0 and second == [], f"first={len(first)} second={len(second)}")

# fit hysteresis (rep_always_on=False): rep mở theo HP — cho fit HỤT cap
HYST = dict(fit, ship="PunisherHyst", rep_always_on=False,
            rep_open_hp=0.60, rep_close_hp=0.85)

# hp cao mà reps đang UNKNOWN-on → không mở thêm (chỉ mở khi hp thấp)
fc3 = FitController(fit)
fc3.tick(hud(UNKNOWN_STATE), hp=1.0, engagement="run1-room1")
no_rep = fc3.tick(hud(UNKNOWN_STATE), hp=0.95, engagement="run1-room1")
ok("high_hp_no_rep_request",
   not any(a["do"] in ("toggle_rep",) for a in no_rep), str(no_rep))

# [hysteresis] hp rơi dưới ngưỡng mà reps observed False → mở reps
fc4 = FitController(HYST)
fc4.tick(hud({"high": {1: True, 2: True, 3: True, 4: True},
              "mid": {1: True, 2: None}, "low": {1: False, 2: False, 3: False}}),
         hp=0.9, engagement="run1-room1")
low_acts = fc4.tick(hud({"high": {1: True, 2: True, 3: True, 4: True},
                         "mid": {1: True, 2: None}, "low": {1: False, 2: False, 3: False}}),
                    hp=0.5, engagement="run1-room1")
rep_slots = sorted(a["slot"] for a in low_acts if a["do"] == "toggle_rep")
ok("low_hp_opens_observed_off_reps", rep_slots == [1, 2], str(low_acts))

# [hysteresis] reps observed True + hp hồi trên ngưỡng đóng → đóng reps tiết kiệm cap
fc5 = FitController(HYST)
fc5.tick(hud({"high": {}, "mid": {}, "low": {1: True, 2: True, 3: True}}),
         hp=0.5, engagement="run1-room1")
close_acts = fc5.tick(hud({"high": {}, "mid": {}, "low": {1: True, 2: True, 3: True}}),
                      hp=0.9, engagement="run1-room1")
ok("recovered_hp_closes_reps",
   any(a["do"] == "close_rep" for a in close_acts), str(close_acts))
again = fc5.tick(hud({"high": {}, "mid": {}, "low": {1: True, 2: True, 3: True}}),
                 hp=0.9, engagement="run1-room1")
ok("close_rep_sent_once", again == [], str(again))

# [always-on] cap-stable fit: SAR bật NGAY từ đầu, hp cao hay thấp đều bật
fc7 = FitController(fit)
on_acts = fc7.tick(hud({"high": {}, "mid": {}, "low": {1: False, 2: False, 3: False}}),
                   hp=1.0, engagement="run1-room1")
rep_slots_on = sorted(a["slot"] for a in on_acts if a["do"] == "toggle_rep")
ok("always_on_tank_pressed_at_full_hp", rep_slots_on == [1, 2], str(on_acts))
hold = fc7.tick(hud({"high": {}, "mid": {}, "low": {1: True, 2: True, 3: True}}),
                hp=0.95, engagement="run1-room1")
ok("always_on_tank_never_closed",
   not any(a["do"] == "close_rep" for a in hold), str(hold))

# đổi engagement (room mới) → reset one-shot state
fc6 = FitController(fit)
fc6.tick(hud(UNKNOWN_STATE), hp=1.0, engagement="run1-room1")
new_room = fc6.tick(hud(UNKNOWN_STATE), hp=1.0, engagement="run1-room2")
ok("new_room_reissues_unknown_modules", len(new_room) > 0, str(new_room))

# ---------------- 3. solo Abyss wiring: Bot dùng fit, không drone ----------------
d = Path(tempfile.mkdtemp(prefix="fila_fit_"))
bus = FileBus(d)
ex = SimExecutor()
bot = Bot(bus, Config(), ex, fit_type="ab_punisher")
ok("bot_fit_passes_no_drones", bot.combat.has_drones is False,
   f"Punisher không drone nhưng brain vẫn bật: has_drones={bot.combat.has_drones}")

ex.phase = "ROOM1_FIGHT"
ex.overview_texts = lambda: ["Striking Kikimora", "Tangling Kikimora"]
bot.tick()
acts_all = ex.actions
ok("combat_brain_no_drone_actions",
   not any(a[0] in ("drone_engage", "recall_drones", "launch_drones") for a in acts_all),
   f"drone action phải vắng mặt với fit không drone: {acts_all}")

# ---------------- 4. trio tank_hp không bịa ----------------
d2 = Path(tempfile.mkdtemp(prefix="fila_fit2_"))
bus2 = FileBus(d2)
ex2 = SimExecutor()
logi_bot = Bot(bus2, Config(), ex2, role="logi")
ex2.phase = "ROOM1_FIGHT"
ex2.hp = 0.2   # HP CỦA LOGI — không phải của tank
logi_bot.tick()
trio = [e for e in events(d2) if e["type"] == "TRIO"]
ok("logi_does_not_read_own_hp_as_tank_hp",
   not any(e.get("do") == "all_reps_on_tank" for e in trio),
   f"tank_hp bịa từ hp logi 0.2 → mở reps sai người: {trio}")

# có fleet state thật (tank publish hp 0.5) → logi mới mở reps
from fila_bot.fleet import FleetState  # noqa: E402
d3 = Path(tempfile.mkdtemp(prefix="fila_fit3_"))
bus3 = FileBus(d3)
ex3 = SimExecutor()
logi2 = Bot(bus3, Config(), ex3, role="logi")
ex3.phase = "ROOM1_FIGHT"
ex3.hp = 0.9                       # HP của logi — khỏe, không phải lý do mở reps
# tank (instance khác trong fleet) publish HP thật qua cùng bus_dir
tank_fleet = FleetState(bus_dir=d3, role="tank")
tank_fleet.publish(hp=0.5)
logi2.fleet = FleetState(bus_dir=d3, role="logi")
logi2.tick()
trio2 = [e for e in events(d3) if e["type"] == "TRIO"]
ok("logi_uses_real_tank_hp_when_reported",
   any(e.get("do") == "all_reps_on_tank" for e in trio2),
   f"tank báo hp 0.5 mà logi vẫn không mở reps: {trio2}")

print(f"\n=> {PASS} test PASS (mọi [FAIL] exit(1) ngay)")
