"""Test rooms — playbook nhận diện room + kill order + loot plan + grace/exit facts."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.rooms import (  # noqa: E402
    ENTRY_MOVES, EXIT_PROCEDURE, GATE_TRANSIT, KILL_ORDERS, LOOT_VALUES,
    detect_room, loot_plan,
)

PASS = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} — {msg}")
        sys.exit(1)


# detect room
ok("detect_karen", detect_room(["Karybdis Tyrannos", "Ephialtes Lancer"]) == "KAREN", "")
ok("detect_les", detect_room(["Striking Leshak", "Blastlance Tessella"]) == "LESHAK", "")
ok("detect_marshal", detect_room(["Attacker Marshal", "Thunderchild"]) == "MARSHAL", "")
ok("detect_deep", detect_room(["Lucid Deepwatcher", "Lucid Escort"]) == "DEEPWATCHER", "")
ok("detect_kiki", detect_room(["Striking Kikimora", "Tangling Damavik"]) == "KIKI_SWARM", "")
ok("detect_vedmak", detect_room(["Harrowing Vedmak", "Striking Damavik"]) == "VEDMAK", "")
ok("detect_unknown", detect_room(["Vila Swarmer"]) == "UNKNOWN", "")

# entry moves tồn tại cho mọi room đã detect
for kind in ("KAREN", "LESHAK", "MARSHAL", "DEEPWATCHER", "KIKI_SWARM", "VEDMAK",
             "TESSERA", "OVERMIND", "SCYLLA", "SANSHA", "ANGEL", "UNKNOWN"):
    ok(f"entry_{kind}", kind in ENTRY_MOVES and len(ENTRY_MOVES[kind]) > 10, kind)

# kill orders: web-first nhất quán với rats doctrine
ok("karen_web_first", "web" in KILL_ORDERS["KAREN"][0].lower(), KILL_ORDERS["KAREN"][0])
ok("marshal_drainer_first", KILL_ORDERS["MARSHAL"][0] == "Drainer Marshal", KILL_ORDERS["MARSHAL"][0])
ok("les_starving_first", KILL_ORDERS["LESHAK"][0] == "Starving", KILL_ORDERS["LESHAK"][0])

# weather notes tồn tại cho combo quan trọng
from fila_bot.rooms import WEATHER_NOTES  # noqa: E402
ok("weather_les_firestorm", "Firestorm" in WEATHER_NOTES.get("LESHAK", {}), str(WEATHER_NOTES.get("LESHAK")))
ok("weather_angel_electrical", "Electrical" in WEATHER_NOTES.get("ANGEL", {}), str(WEATHER_NOTES.get("ANGEL")))

# loot plan: cache gần + timer dư → loot; xa + ngặt → skip
p = loot_plan(room_n=2, timer_left_s=600, cache_dist_m=8000, nodes_dist_m=[5000, 30000])
ok("loot_cache_yes", p["cache"] is True, str(p))
ok("loot_node_close_only", p["nodes"] == [0], str(p))

p = loot_plan(room_n=2, timer_left_s=120, cache_dist_m=25000, nodes_dist_m=[20000])
ok("loot_all_skip", p["cache"] is False and p["nodes"] == [], str(p))

# room 1 + run dài → bỏ node dù gần
p = loot_plan(room_n=1, timer_left_s=1100, cache_dist_m=3000, nodes_dist_m=[4000],
              run_avg_min=16)
ok("loot_room1_greedy_guard", p["nodes"] == [], str(p))

# loot values: red loot 100K NPC buy
ok("red_loot_value", LOOT_VALUES["Triglavian Survey Database"]["price_isk"] == 100_000
   and "NPC" in LOOT_VALUES["Triglavian Survey Database"]["sell"], "")

# gate grace + exit facts
ok("gate_grace", 15 <= GATE_TRANSIT["grace_s"] <= 20 and GATE_TRANSIT["keep_prop_on"], "")
ok("exit_invul", EXIT_PROCEDURE["invul_s"] == 60 and len(EXIT_PROCEDURE["steps"]) >= 3, "")

print(f"\n=> {PASS} test PASS (mọi [FAIL] exit(1) ngay)")
