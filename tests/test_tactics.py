"""Test lớp chiến thuật mới (merge 2026-11-10): lognormal/jitter input,
split-fire, hazard evaluate, bait gimmick, tactical orbit, drone proactive recall,
trio tactic mới, fit_type wiring.

Chạy: PYTHONPATH=src python tests/test_tactics.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot import rats                                     # noqa: E402
from fila_bot import rooms                                    # noqa: E402
from fila_bot.combat_brain import CombatBrain                 # noqa: E402
from fila_bot.drone import DroneManager                       # noqa: E402
from fila_bot.input import humanized_delay, jitter_xy         # noqa: E402
from fila_bot.reflex import Bot, SimExecutor                  # noqa: E402
from fila_bot.trio import TrioRole, _select_ammo              # noqa: E402

PASS = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} — {msg}")
        sys.exit(1)


# ---------------- 1. input: lognormal delay + jitter_xy ----------------
delays = [humanized_delay(1.0) for _ in range(500)]
assert all(0.75 <= d <= 1.45 for d in delays), (min(delays), max(delays))
ok("lognormal_delay_clamped", True, f"{min(delays):.2f}..{max(delays):.2f}")
mean = sum(delays) / len(delays)
ok("lognormal_delay_mean_below_uniform", mean < 1.15, f"mean={mean:.3f}")

for _ in range(200):
    jx, jy = jitter_xy(1000, 2000)
    assert -5 <= jx - 1000 <= 5 and -5 <= jy - 2000 <= 5, (jx, jy)
assert jitter_xy(10, 10, sigma_px=0.0) == (10, 10)
ok("jitter_xy_bounds", True)

# ---------------- 2. rats: classify giữ contract cũ + fields mới ----------------
c = rats.classify("Strikegrip Tessera")
ok("tessera_anti_drone", c["anti_drone"] is True and c["no_switch"] is True, str(c))
ok("tessera_optimal_15", c["optimal_km"] == 15, str(c["optimal_km"]))
c = rats.classify("Sparkneedle Tessella")
ok("spark_damage_em", c["damage_type"] == "em", str(c["damage_type"]))
c = rats.classify("Attacker Marshal Disparu Troop")
ok("marshal_is_bs_high_dps", c["is_bs"] and c["is_high_dps"], str(c))
ok("raw_key_preserved", c["raw"] == "Attacker Marshal Disparu Troop")

# cache/conduit giờ là SKIP (không phải quái)
c = rats.classify("Triglavian Bioadaptive Cache")
ok("cache_skip", c["skip"] is True, str(c))

# lock_order default: wiki thuần, skip cuối, có cả "raw" lẫn "name"
order = rats.lock_order(["Sparkneedle Tessella", "Karybdis Tyrannos",
                         "Snarecaster Tessella", "Vila Swarmer",
                         "Attacker Marshal Disparu Troop", "Fieldweaver Tessella"])
ok("default_order_web_first", order[0]["raw"] == "Snarecaster Tessella",
   str([x["raw"] for x in order]))
ok("default_swarmer_last", order[-1]["raw"] == "Vila Swarmer",
   str([x["raw"] for x in order]))
ok("items_have_name_key", all("name" in x for x in order))

# lock_order tactical (fit AB): scram thuần tụt ưu tiên; Kikimora được nâng
order = rats.lock_order(["Anchoring Vila Damavik", "Striking Kikimora"],
                        fit_type="ab_cruiser")
ok("tactical_kiki_before_scram", order[0]["raw"] == "Striking Kikimora",
   str([x["raw"] for x in order]))

# resist-hole: Spark (EM) trước khi fit trúng lỗ EM
order = rats.lock_order(["Blastneedle Tessella", "Sparkneedle Tessella"],
                        fit_type="ab_cruiser", resist_hole="em")
ok("resist_hole_spark_first", order[0]["raw"] == "Sparkneedle Tessella",
   str([x["raw"] for x in order]))

# split-fire: Karen + escort, EWAR sạch, có drone → drone cắn BS
plan = rats.split_fire_plan(["Karybdis Tyrannos", "Ephialtes Lancer"],
                            has_drones=True, fit_type="ab_cruiser")
ok("splitfire_drone_on_bs", plan["focus_fire"] is False
   and plan["drone_target"] == "Karybdis Tyrannos"
   and plan["weapon_target"] == "Ephialtes Lancer", str(plan))
# room có logi → focus fire
plan = rats.split_fire_plan(["Karybdis Tyrannos", "Fieldweaver Tessella"],
                            has_drones=True, fit_type="ab_cruiser")
ok("splitfire_logi_focus", plan["focus_fire"] is True, str(plan))

# ---------------- 3. rooms: contract + hazards ----------------
ok("entry_unknown_exists", len(rooms.ENTRY_MOVES["UNKNOWN"]) > 10)
ok("kill_orders_contract", "web" in rooms.KILL_ORDERS["KAREN"][0].lower()
   and rooms.KILL_ORDERS["MARSHAL"][0] == "Drainer Marshal"
   and rooms.KILL_ORDERS["LESHAK"][0] == "Starving")
ok("weather_notes_contract", "Firestorm" in rooms.WEATHER_NOTES["LESHAK"]
   and "Electrical" in rooms.WEATHER_NOTES["ANGEL"])
ok("gate_grace_contract", rooms.GATE_TRANSIT["grace_s"] == 18
   and rooms.EXIT_PROCEDURE["invul_s"] == 60)

hz = rooms.evaluate_hazards([{"name": "Bioluminescence Cloud", "dist_km": 8.0}],
                            "KAREN")
ok("hazard_blue_avoid", hz["avoid"] == ["Bioluminescence Cloud"], str(hz))
hz = rooms.evaluate_hazards([{"name": "Short-Range Deviant Automata Suppressor",
                              "dist_km": 10.0}], "SCYLLA", fit_type="ab_shield_drone")
ok("hazard_suppressor_recall", hz["recall_drones"] is True, str(hz))
hz = rooms.evaluate_hazards([{"name": "Tachyon Cloud", "dist_km": 5.0}],
                            "KAREN", fit_type="mwd_cruiser")
ok("hazard_tachyon_mwd_off", hz["disable_mwd"] is True, str(hz))
hz = rooms.evaluate_hazards([{"name": "Multibody Tracking Pylon", "dist_km": 10.0}],
                            "TESSERA")
ok("hazard_tracking_avoid", hz["avoid"] == ["Multibody Tracking Pylon"], str(hz))

p = rooms.loot_plan(room_n=2, timer_left_s=100, cache_dist_m=20000, nodes_dist_m=[])
ok("loot_panic_burn", p["emergency_burn_gate"] is True and p["cache"] is False, str(p))
p = rooms.loot_plan(room_n=2, timer_left_s=600, cache_dist_m=8000, nodes_dist_m=[5000, 30000])
ok("loot_plan_old_shape", p["cache"] is True and p["nodes"] == [0] and "reason" in p, str(p))

# ---------------- 4. combat_brain: tactical orbit + bait ----------------
class FakeEx:
    def __init__(self, names):
        self._names = names
        self.actions = []

    def overview_texts(self):
        return list(self._names)


brain = CombatBrain(fit_type="ab_cruiser")
ex = FakeEx(["Strikegrip Tessera", "Vila Swarmer"])
acts = brain.tick(ex, "ROOM1_FIGHT")
lock_acts = [a for a in acts if a[0] == "orbit"]
ok("tactical_orbit_tessera_22", lock_acts and lock_acts[0][1] == 22, str(acts))

brain = CombatBrain(fit_type="ab_cruiser")
ex = FakeEx(["Karybdis Tyrannos", "Ephialtes Lancer"])
acts = brain.tick(ex, "ROOM1_FIGHT")
orbit_acts = [a for a in acts if a[0] == "orbit"]
# Karen: orbit 2km under guns (ROOM_TACTICS) — dưới ~10km nó không track nổi
ok("tactical_orbit_karen_under_guns", orbit_acts and orbit_acts[0][1] == 2, str(acts))

# bait: giữ Lancer cuối làm mồi — Lancer phải ở CUỐI thứ tự ưu tiên trong plan
brain = CombatBrain(fit_type="ab_cruiser")
ex = FakeEx(["Ephialtes Lancer", "Karybdis Tyrannos", "Ephialtes Dissipator"])
brain.tick(ex, "ROOM1_FIGHT")
# gimmick giữ lại 1 Lancer — kiểm qua room tactics bait_token có giá trị
ok("karen_bait_token", rooms.ROOM_TACTICS["KAREN"]["bait_token"] == "Ephialtes Lancer")
ok("overmind_bait_token", rooms.ROOM_TACTICS["OVERMIND"]["bait_token"] == "needle Tessella")

# default fit giữ hành vi cũ: orbit 10km, không tactic
brain = CombatBrain()
ex = FakeEx(["Strikegrip Tessera", "Vila Swarmer"])
acts = brain.tick(ex, "ROOM1_FIGHT")
orbit_acts = [a for a in acts if a[0] == "orbit"]
ok("default_orbit_10", orbit_acts and orbit_acts[0][1] == 10, str(acts))

# ---------------- 5. drone: proactive recall mới ----------------
d = DroneManager(max_drones=5)
d.state = "ENGAGED"
d.in_space = 3
r = d.update({"drones_in_space": 3, "drones_hp_avg": 1.0, "room_cleared": True})
ok("drone_recall_room_cleared", r is not None and r["action"] == "recall"
   and d.state == "RECALLING", str(r))

d = DroneManager()
d.state = "ENGAGED"
r = d.update({"drones_in_space": 3, "drones_hp_avg": 1.0, "suppressor_dist_km": 10.0})
ok("drone_recall_suppressor", r is not None and r["action"] == "recall", str(r))

d = DroneManager()
d.state = "ENGAGED"
r = d.update({"drones_in_space": 3, "drones_hp_avg": 0.95,
              "yellowboxed_anti_drone": True})
ok("drone_recall_yellowbox", r is not None and r["action"] == "recall"
   and d.state == "RECALLING", str(r))

d = DroneManager()
allow, why = d.can_launch(redboxed=True, suppressor_close=True)
ok("drone_no_launch_suppressor", allow is False and "Suppressor" in why, why)

# hành vi cũ vẫn nguyên: không có tín hiệu mới → leash return_orbit, hp recall
d = DroneManager()
d.state = "ENGAGED"
d.in_space = 5
r = d.update({"drones_in_space": 5, "drones_hp_avg": 0.9, "dist_to_drone_target_km": 40})
ok("drone_leash_return_orbit_old", r is not None and r["action"] == "return_orbit", str(r))

# ---------------- 6. trio: tactic mới giữ contract cũ ----------------
t = TrioRole("tank")
acts = t.tick({"room_entry": True, "moved_this_room": False, "hp": 1.0})
ok("trio_tank_entry_old", acts[0]["do"] == "approach_cache", str(acts))

t = TrioRole("tank")
acts = t.tick({"room_entry": False, "moved_this_room": True, "hp": 1.0,
               "overview": ["Strikegrip Tessera", "Snarecaster Tessella"]})
ok("trio_tank_tessera_kite22", any(a["do"] == "keep_range" and a["km"] == 22 for a in acts),
   str(acts))

t = TrioRole("dps")
acts = t.tick({"dist_to_tank_km": 12.0})
ok("trio_dps_orbit_tank_old", acts[0]["do"] == "orbit_tank", str(acts))

t = TrioRole("dps")
acts = t.tick({"dist_to_tank_km": 2.0, "current_target": None,
               "overview": ["Strikegrip Tessera"], "target_dist_km": 9.0,
               "weapon": "laser"})
ok("trio_dps_tessera_orbit10", any(a["do"] == "orbit_target" and a["km"] == 10.0
                                   for a in acts), str(acts))
ok("trio_dps_ammo_conflag", any(a["do"] == "attack" and a["ammo"] == "conflagration"
                                for a in acts), str(acts))

ok("ammo_switch", _select_ammo(20.0, "rocket") == "javelin"
   and _select_ammo(9.0, "rocket") == "rage")

t = TrioRole("logi")
acts = t.tick({"kikimora_count": 2, "tank_hp": 0.95, "cap": 0.9,
               "logi_primaried": True})
ok("trio_logi_counter_orbit", any(a["do"] == "counter_orbit_transversal" for a in acts),
   str(acts))

t = TrioRole("tank")
t._vedmak_stopped = False
t.tick({"overview": ["Harrowing Vedmak"], "hp": 1.0})
ok("trio_vedmak_stop_once", True)
acts = t.tick({"overview": ["Harrowing Vedmak"], "hp": 1.0})
ok("trio_vedmak_stop_dedup", not any(a["do"] == "stop_ship" for a in acts), str(acts))

# ---------------- 7. Bot nhận fit_type (wiring LIVE) ----------------
from fila_bot.bus import FileBus          # noqa: E402
from fila_bot.config import Config        # noqa: E402
import tempfile                           # noqa: E402

bus = FileBus(Path(tempfile.mkdtemp(prefix="fila_tactics_bus_")))
bot = Bot(bus, Config(), SimExecutor(), fit_type="ab_cruiser", resist_hole="em")
ok("bot_fit_type_wired", bot.combat.fit_type == "ab_cruiser"
   and bot.combat.resist_hole == "em", str(bot.combat.fit_type))
bot_default = Bot(bus, Config(), SimExecutor())
ok("bot_default_fit", bot_default.combat.fit_type == "default")

# drone signals qua reflex tick (advisory, không crash)
bot_default.ex.phase = "ROOM1_CLEARED"
bot_default.ex.drones_in_space = 2
bot_default.tick()
ok("reflex_drone_cleared_advisory", True)

print(f"\n=> {PASS} test PASS (mọi [FAIL] exit(1) ngay)")
