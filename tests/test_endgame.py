"""Test P0-6 (timer endgame) + P1-2 (trio trong tick) + P1-3 (drone) + P2-4 (kill-switch)."""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.bus import FileBus            # noqa: E402
from fila_bot.config import Config         # noqa: E402
from fila_bot.input import kill_switch_pressed  # noqa: E402
from fila_bot.reflex import Bot, SimExecutor    # noqa: E402

PASS = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} — {msg}")
        sys.exit(1)


def make_bot(role: str = "solo") -> tuple[Bot, SimExecutor, FileBus, Path]:
    d = Path(tempfile.mkdtemp(prefix="fila_test_"))
    bus = FileBus(d)
    ex = SimExecutor()
    bot = Bot(bus, Config(), ex, role=role)
    return bot, ex, bus, d


def events(d: Path) -> list[dict]:
    p = d / "bot_to_fc.jsonl"
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def ev_types(d: Path) -> list[str]:
    return [e["type"] for e in events(d)]


# ---------------- P0-6: còn <=120s → ngừng loot ----------------
bot, ex, bus, d = make_bot()
ex.phase = "LOOT"
ex.room = 3
ex.want_loot = True
bot.abby_started = time.time() - 1090          # còn 110s
bot.tick()
ok("endgame_loot_stop_sets_flag", ex.want_loot is False, "want_loot vẫn True")
ok("endgame_loot_stop_event", "TIMER_LOOT_STOP" in ev_types(d), ",".join(ev_types(d)))

# loot đã dừng thì không emit lại mỗi tick
n1 = ev_types(d).count("TIMER_LOOT_STOP")
bot.tick()
ok("endgame_loot_stop_once", ev_types(d).count("TIMER_LOOT_STOP") == n1, "emit lặp")

# ---------------- P0-6: không vào room mới khi <180s ----------------
bot, ex, bus, d = make_bot()
ex.phase = "ROOM2_FIGHT"
ex.room = 1
bot.abby_started = time.time() - 1100          # còn 100s
bot.tick()
ok("endgame_room_guard_mayday", "MAYDAY" in ev_types(d), ",".join(ev_types(d)))
ok("endgame_room_guard_exit", ex.phase in ("WARP_HOME", "SURVIVAL", "EXIT"), f"phase={ex.phase}")

# còn nhiều thời gian → không chặn
bot, ex, bus, d = make_bot()
ex.phase = "ROOM2_FIGHT"
ex.room = 1
bot.abby_started = time.time() - 300           # còn 900s
bot.tick()
ok("endgame_room_ok_when_time", "MAYDAY" not in ev_types(d), ",".join(ev_types(d)))

# ---------------- P1-2: trio tank kêu logi khi hp thấp ----------------
bot, ex, bus, d = make_bot(role="tank")
ex.phase = "ROOM1_FIGHT"
ex.hp = 0.5
bot.tick()
trio = [e for e in events(d) if e["type"] == "TRIO"]
ok("trio_tank_signal", any(e.get("do") == "signal_logi_all_reps" for e in trio),
   f"trio={trio}")
ok("trio_role_in_event", all(e.get("role") == "tank" for e in trio), f"trio={trio}")

# ---------------- P1-2: logi thấy >6 kikimora → all reps ----------------
bot, ex, bus, d = make_bot(role="logi")
ex.phase = "ROOM1_FIGHT"
ex.overview_texts = lambda: ["Kikimora"] * 7 + ["Vila Swarmer"]
bot.tick()
trio = [e for e in events(d) if e["type"] == "TRIO"]
ok("trio_logi_kiki_swarm", any(e.get("do") == "all_reps_on_tank" for e in trio), f"trio={trio}")

# solo: không có event TRIO
bot, ex, bus, d = make_bot()
ex.phase = "ROOM1_FIGHT"
bot.tick()
ok("trio_solo_silent", "TRIO" not in ev_types(d), ",".join(ev_types(d)))

# ---------------- P1-2: new_room reset reps khi đổi room ----------------
bot, ex, bus, d = make_bot(role="logi")
bot.trio.reps_open = True
ex.room = 2
ex.phase = "ROOM2_FIGHT"
bot.tick()
ok("trio_new_room_reset", bot.trio.reps_open is False, "reps_open không reset")

# ---------------- P1-3: drone bị đánh → DRONE recall ----------------
bot, ex, bus, d = make_bot()
bot.drones.state = "ENGAGED"
bot.drones.in_space = 2
ex.drones_in_space = 2
ex.drones_hp_avg = 0.2             # < hp_floor 0.4
bot.tick()
dr = [e for e in events(d) if e["type"] == "DRONE"]
ok("drone_recall_on_damage", any(e.get("action") == "recall" for e in dr), f"drone={dr}")
ok("drone_state_transition", bot.drones.state == "RECALLING", bot.drones.state)

# ---------------- loop_watchdog không được bắn MAYDAY khi docked/idle ----------------
bot, ex, bus, d = make_bot()
ex.phase = "DOCKED"
for _ in range(8):
    bot.tick()
ok("watchdog_silent_docked", "MAYDAY" not in ev_types(d), ",".join(ev_types(d)))

# trong abyss thì vẫn phải bắt spam
bot, ex, bus, d = make_bot()
ex.phase = "ROOM1_FIGHT"
ex.last_action = "lock"
for _ in range(8):
    bot.tick()
ok("watchdog_fires_in_abyss", "MAYDAY" in ev_types(d), ",".join(ev_types(d)))

# ---------------- P2-4: kill-switch poll ----------------
DOWN = 0x8000


def fake_keys(pressed: set[int]):
    return lambda vk: DOWN if vk in pressed else 0


ok("killswitch_all_down", kill_switch_pressed(fake_keys({0x11, 0x10, 0x20})) is True)
ok("killswitch_missing_space", kill_switch_pressed(fake_keys({0x11, 0x10})) is False)
ok("killswitch_missing_ctrl", kill_switch_pressed(fake_keys({0x10, 0x20})) is False)

print(f"\n{PASS} PASS — endgame trio drone killswitch")
