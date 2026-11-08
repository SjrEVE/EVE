"""End-to-end test v1 — chạy KHÔNG cần EVE: full chu trình FC→bus→bot→events.

World model v1: FSM abyss thật (3 phòng / 20' / không warp out / survival).
Chạy: cd D:/fila-bot && python tests/test_all.py   (kỳ vọng tất cả PASS, exit 0)
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.bus import FileBus              # noqa: E402
from fila_bot.commands import validate, CommandError  # noqa: E402
from fila_bot.config import Config            # noqa: E402
from fila_bot.reflex import Bot, SimExecutor, IN_ABYSS  # noqa: E402

PASS = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} — {msg}")
        sys.exit(1)


# ---------- 1. DSL validate unit ----------
ok("dsl_orbit_ok", validate("ORBIT", 2800) == 2800)

try:
    validate("FLY_TO_MOON", None)
    ok("dsl_unknown_cmd_reject", False, "không raise")
except CommandError:
    ok("dsl_unknown_cmd_reject", True)

try:
    validate("ORBIT", 999999)
    ok("dsl_orbit_bounds", False, "999999 không raise")
except CommandError as e:
    ok("dsl_orbit_bounds", "out of bounds" in str(e), str(e))

try:
    validate("SET", "escape_hp 5.0")
    ok("dsl_set_bounds", False, "5.0 > 0.9 không raise")
except CommandError:
    ok("dsl_set_bounds", True)

ok("dsl_target_nearest", validate("TARGET", "nearest") == "nearest")
ok("dsl_keep_range", validate("KEEP_RANGE", 5000) == 5000)
ok("dsl_activate_8", validate("ACTIVATE", 8) == 8)

try:
    validate("ACTIVATE", 9)
    ok("dsl_activate_bounds", False, "9 > 8 không raise")
except CommandError:
    ok("dsl_activate_bounds", True)

# ---------- 2. bus round-trip ----------
tmp = Path(tempfile.mkdtemp(prefix="fila_test_"))
fc = FileBus(tmp)
(tmp / "fc_to_bot.jsonl").write_text("{corrupt!!}\n", encoding="utf-8")
fc._in_offset = 0
cmds = fc.poll()
ok("bus_corrupt_line", len(cmds) == 1 and "corrupt" in cmds[0], str(cmds))
ok("bus_corrupt_reject_event",
   any(e["type"] == "REJECT" for e in fc.read_outbox()), str(fc.read_outbox()))


def fc_send(cid: str, cmd, arg=None) -> None:
    import json
    with (tmp / "fc_to_bot.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"id": cid, "cmd": cmd, "arg": arg}) + "\n")


# ---------- 3. bot end-to-end: full mission flow theo world model ----------
fc = FileBus(tmp)
bot = Bot(fc, Config(escape_hp=0.25, unknown_timeout=0.25))
ex = bot.ex

# phase DOCKED
ok("flow_start_docked", ex.phase == "DOCKED", ex.phase)

# UNDOCK → TRAVEL_ENTRY
fc_send("u1", "UNDOCK")
bot.run(max_ticks=1, tick_sleep=0.01)
ok("flow_undock", ex.phase == "TRAVEL_ENTRY", ex.phase)

# FILA (còn 2 filament) → FILA_SPOOL, kho xuống 1
fc_send("f1", "FILA", "Dark Fierce Filament")
bot.run(max_ticks=1, tick_sleep=0.01)
ok("flow_fila_spool", ex.phase == "FILA_SPOOL", ex.phase)
ok("flow_fila_stash_decrement", ex.filaments == 1, f"filaments={ex.filaments}")
ok("flow_fila_weather_detected", ex.weather == "Dark", f"weather={ex.weather}")

# trong spool, GATE bị từ chối
fc_send("g0", "GATE")
bot.run(max_ticks=1, tick_sleep=0.01)
rej = [e for e in fc.read_outbox(50) if e["type"] == "REJECT" and e.get("cmd") == "GATE"]
ok("flow_gate_rejected_in_spool", len(rej) >= 1, str(rej))

# lệnh SAI vẫn REJECT đúng
fc_send("x1", "ORBIT", 999999)
fc_send("x2", "FLY_TO_MOON")
fc_send("x3", "SET", "escape_hp 0.5")
fc_send("x4", "STATUS")
bot.run(max_ticks=1, tick_sleep=0.01)
events = fc.read_outbox(100)
ok("flow_reject_bounds", any(e["type"] == "REJECT" and "out of bounds" in (e.get("reason") or "")
                             for e in events), str(events[-4:]))
ok("flow_reject_unknown", any(e["type"] == "REJECT" and "not in whitelist" in (e.get("reason") or "")
                              for e in events), str(events[-4:]))
ok("flow_set_applied", bot.cfg.escape_hp == 0.5, f"escape_hp={bot.cfg.escape_hp}")

# mô phỏng spool 15s: P0-1 — KHÔNG auto-confirm bằng timer.
# Không có xác minh eye/sim_confirm → hết timeout → MAYDAY + safe_exit (fail-closed)
bot.fila_started = time.time() - 16.0
bot.run(max_ticks=1, tick_sleep=0.01)
ok("flow_spool_no_confirm_without_eye", ex.phase == "SURVIVAL", ex.phase)   # fail-closed
may = [e for e in fc.read_outbox(50) if e["type"] == "MAYDAY" and "P0-1" in (e.get("reason") or "")]
ok("flow_spool_mayday_p01", len(may) >= 1, str(may))

# có sim_confirm=True (dialog xác nhận có thật) → AUTO_CONFIRM ok
fc2 = FileBus(tempfile.mkdtemp(prefix="fila_t2_"))
bot2 = Bot(fc2, Config(escape_hp=0.25, unknown_timeout=0.25))
bot2.ex.sim_confirm = True
fc2_send = lambda cid, cmd, arg=None: None   # không cần lệnh mới
bot2._do_undock(None)
bot2._do_fila("Gamma Fierce")
bot2.fila_started = time.time() - 16.0
bot2.run(max_ticks=1, tick_sleep=0.01)
ok("flow_auto_confirm_with_sim_flag", bot2.ex.phase == "ROOM1_FIGHT", bot2.ex.phase)
ok("flow_room1", bot2.ex.room == 1, f"room={bot2.ex.room}")

# phục hồi bot chính về ROOM1_FIGHT để test gate chain tiếp tục (đã chứng minh P0-1 ở trên)
ex.phase = "ROOM1_FIGHT"
ex.room = 1
ex.hp = 1.0

# clear room 1 (FC báo SET_PHASE vì thấy quái sạch) → GATE
fc_send("sp1", "SET_PHASE", "ROOM1_CLEARED")
fc_send("g1", "GATE")
bot.run(max_ticks=1, tick_sleep=0.01)
ok("flow_gate_to_room2", ex.phase == "ROOM2_FIGHT" and ex.room == 2, f"{ex.phase} room={ex.room}")

# room 2 clear → SET_PHASE → GATE → room 3
fc_send("sp2", "SET_PHASE", "ROOM2_CLEARED")
fc_send("g2", "GATE")
bot.run(max_ticks=1, tick_sleep=0.01)
ok("flow_gate_to_room3", ex.phase == "ROOM3_FIGHT" and ex.room == 3, f"{ex.phase} room={ex.room}")

# SET_PHASE sai phase (đang FIGHT→CLEARED mới hợp lệ) — dùng phase DOCKED để test reject
bot.ex.phase = "ROOM3_FIGHT"
fc_send("sp3", "SET_PHASE", "DOCKED")
bot.run(max_ticks=1, tick_sleep=0.01)
rej_sp = [e for e in fc.read_outbox(50) if e["type"] == "REJECT" and e.get("cmd") == "SET_PHASE"]
ok("flow_set_phase_reject_bad_target", len(rej_sp) >= 1, str(rej_sp))
bot.ex.phase = "ROOM3_FIGHT"   # khôi phục

# ---------- 4. hp thấp trong abyss → SURVIVAL (KHÔNG warp_home) ----------
ex.hp = 0.10
bot.run(max_ticks=2, tick_sleep=0.01)
sev = [e for e in fc.read_outbox(100) if e["type"] == "SAFE_EXIT"]
ok("safety_survival_in_abyss", ex.phase == "SURVIVAL" and sev and sev[-1].get("mode") == "survival",
   f"phase={ex.phase} sev={sev[-1] if sev else None}")

# ---------- 5. hp thấp NGOÀI abyss → warp_home ----------
bot.ex.phase = "TRAVEL_ENTRY"
bot.ex.hp = 0.10
bot.run(max_ticks=1, tick_sleep=0.01)
sev = [e for e in fc.read_outbox(100) if e["type"] == "SAFE_EXIT"]
ok("safety_warp_home_outside", ex.phase == "WARP_HOME" and sev and sev[-1].get("mode") == "warp_home",
   f"phase={ex.phase} sev={sev[-1] if sev else None}")

# ---------- 6. ABORT ngoài abyss → warp_home; ABORT trong abyss → survival ----------
bot.ex.phase = "TRAVEL_ENTRY"
bot.ex.hp = 1.0
fc_send("a1", "ABORT")
bot.run(max_ticks=1, tick_sleep=0.01)
ok("abort_outside_warp_home", ex.phase == "WARP_HOME", ex.phase)

bot.ex.phase = "ROOM2_FIGHT"
bot.ex.room = 2
bot.ex.hp = 1.0
fc_send("a2", "ABORT")
bot.run(max_ticks=1, tick_sleep=0.01)
ok("abort_inside_survival", ex.phase == "SURVIVAL", ex.phase)

# ---------- 7. FILA khi hết kho → FILA_MISSING + REJECT ----------
bot.ex.phase = "DOCKED"
bot.ex.filaments = 0
fc_send("f2", "FILA", "Gamma Raging")
bot.run(max_ticks=1, tick_sleep=0.01)
missing = [e for e in fc.read_outbox(100) if e["type"] == "FILA_MISSING"]
rej_f = [e for e in fc.read_outbox(100) if e["type"] == "REJECT" and e.get("cmd") == "FILA"]
ok("fila_missing_event", len(missing) >= 1, str(missing))
ok("fila_missing_reject", len(rej_f) >= 1, str(rej_f))
ok("fila_no_retry_phase_unchanged", ex.phase == "DOCKED", ex.phase)

# ---------- 8. UNKNOWN (trong abyss) → MAYDAY + safe_exit survival ----------
bot.ex.phase = "ROOM2_FIGHT"      # đang trong abyss
bot.ex.room = 2
bot.ex.hp = 1.0
bot.run(max_ticks=1, tick_sleep=0.01)   # 1 tick để _prev_phase = ROOM2_FIGHT
bot.ex.phase = "UNKNOWN"          # rồi overview "mất" → UNKNOWN
bot.run(max_ticks=8, tick_sleep=0.05)   # 0.40s > unknown_timeout 0.25s
evs = fc.read_outbox(100)
ok("unknown_mayday", any(e["type"] == "MAYDAY" for e in evs), "no MAYDAY")
sev = [e for e in evs if e["type"] == "SAFE_EXIT"]
ok("unknown_safe_exit", len(sev) >= 1 and sev[-1].get("mode") == "survival",
   f"UNKNOWN trong abyss (survival) → {sev[-1] if sev else None}")

# ---------- 9. TIMER_WARN: abyss đã 19.5 phút (còn 30s < warn 300s mặc định) ----------
bot.ex.phase = "ROOM3_FIGHT"
bot.ex.room = 3
bot.ex.hp = 1.0
bot.abby_started = time.time() - 1170.0   # còn 30s
bot.timer_warned = False
bot.run(max_ticks=1, tick_sleep=0.01)
tw = [e for e in fc.read_outbox(100) if e["type"] == "TIMER_WARN"]
ok("timer_warn_fires", len(tw) >= 1 and tw[-1].get("timer_left_s", 9999) <= 60, str(tw))

# ---------- 10. DEATH GUARDS qua tick thật ----------
# DEATH #3: GATE khi drone ngoài → REJECT
bot.ex.phase = "ROOM1_CLEARED"
bot.ex.room = 1
bot.ex.hp = 1.0
bot.ex.drones_in_space = 2
fc_send("dg1", "GATE")
bot.run(max_ticks=1, tick_sleep=0.01)
dg = [e for e in fc.read_outbox(50) if e["type"] == "REJECT" and e.get("cmd") == "GATE"]
ok("guard_gate_drone_block", len(dg) >= 1 and "drone" in (dg[-1].get("reason") or ""), str(dg))
# recall xong → gate thông
bot.ex.drones_in_space = 0
fc_send("dg2", "GATE")
bot.run(max_ticks=1, tick_sleep=0.01)
ok("guard_gate_after_recall", ex.phase == "ROOM2_FIGHT", ex.phase)

# guard action 'survival' từ OverviewEmpty (giả overview_count=0 qua ex attr)
bot.ex.phase = "ROOM2_FIGHT"
bot.ex.room = 2
bot.ex.hp = 1.0
bot.ex.overview_count = 0
bot.guards.guards[0].empty_since = None
bot.guards.guards[0].timeout_s = 0.05     # guard riêng trong bot
bot.run(max_ticks=3, tick_sleep=0.04)
gev = [e for e in fc.read_outbox(100) if e["type"] == "GUARD" or
       (e["type"] == "SAFE_EXIT" and "overview" in (e.get("reason") or ""))]
ok("guard_overview_empty_survival", len(gev) >= 1 and ex.phase == "SURVIVAL",
   f"phase={ex.phase} gev={gev[-2:]}")

print(f"\n=> {PASS} test PASS (mọi [FAIL] exit(1) ngay)")
