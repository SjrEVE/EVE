"""Regression: SecurityBrain decide() — não thuần Python (không LLM).

Mỗi test = 1 tình huống world thật (dump/probe shape) → quyết định đúng + why.
Chặn 4 loại sai Boss bắt gặp live 12-13/11: đứng im khi quái xa, bấm gate khi
pocket chưa clear, lock mù không kill-order, drone không leash.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.security_brain import SecurityBrain  # noqa: E402


def ok(n, cond):
    if not cond:
        print(f"[FAIL] {n}")
        raise SystemExit(1)
    print(f"[PASS] {n}")


def brain(title="Gone Berserk", level=1, **kw):
    return SecurityBrain(mission_title=title, mission_level=level, **kw)


HP_OK = {"shield": 1.0, "armor": 1.0, "structure": 1.0}


def world(overview, docked=False, hp=None, cap=None, drones=None):
    return {"docked": docked, "overview": overview,
            "ship_health": hp or HP_OK, "capacitor_percent": cap,
            "drones": drones or {"in_space": 0, "in_bay": 10}}


# --- 1. docked: không hành động, reset state ---
b = brain()
acts = b.decide(world([], docked=True))
ok("docked → không action", acts == [])
b.locked_names.add("x")
b.decide(world([], docked=True))
ok("docked reset locked_names", b.locked_names == set())

# --- 2. survival HP thấp: recall drone TRƯỚC khi FSM escape ---
b = brain()
acts = b.decide(world([
    {"Name": "EoM Imp", "Distance": "20 km", "center": (1, 1)},
], hp={"shield": 0.2, "armor": 1.0, "structure": 1.0},
    drones={"in_space": 2, "in_bay": 8}))
ok("hp<30% → recall_drones đầu tiên", acts and acts[0]["do"] == "recall_drones")
ok("hp<30% → orbit_out theo sau", len(acts) >= 2 and acts[1]["do"] == "orbit_out")

# --- 3. cap thấp: cap_save + recall ---
b = brain()
acts = b.decide(world([
    {"Name": "EoM Imp", "Distance": "20 km", "center": (1, 1)},
], cap=15.0, drones={"in_space": 2, "in_bay": 8}))
ok("cap<25% → cap_save", acts and acts[0]["do"] == "cap_save")

# --- 4. pocket sạch + gate xa → approach gate (KHÔNG bấm gate mù) ---
b = brain("Pirate Intrusion", level=2)
acts = b.decide(world([
    {"Name": "Acceleration Gate", "Distance": "26 km", "center": (2, 2)},
]))
ok("pocket sạch + gate 26km → approach", acts and acts[0]["do"] == "approach"
   and acts[0]["target"] == "Acceleration Gate")

# --- 5. pocket sạch + gate 0m trong tầm → activate gate ---
acts = b.decide(world([
    {"Name": "Acceleration Gate", "Distance": "0 m", "center": (2, 2)},
]))
ok("gate trong tầm → activate_gate", acts and acts[0]["do"] == "activate_gate")

# --- 6. pocket chưa clear (còn quái) → KHÔNG bấm gate dù gate có mặt ---
b = brain("Pirate Intrusion", level=2)
acts = b.decide(world([
    {"Name": "Acceleration Gate", "Distance": "0 m", "center": (2, 2)},
    {"Name": "Guristas Despoiler", "Distance": "20 km", "center": (3, 3)},
    {"Name": "Guristas Killer", "Distance": "22 km", "center": (4, 4)},
]))
gates = [a for a in acts if a["do"] == "activate_gate"]
ok("còn quái → KHÔNG activate_gate", not gates)

# --- 7. quái xa 1.5 AU → approach gần nhất (AU parse đúng) ---
b = brain()
acts = b.decide(world([
    {"Name": "EoM Succubus", "Distance": "1.5 AU", "center": (1, 1)},
    {"Name": "EoM Priest", "Distance": "2.0 AU", "center": (2, 2)},
]))
ok("quái AU xa → approach gần nhất (Succubus 1.5 AU)",
   acts and acts[0]["do"] == "approach" and acts[0]["target"] == "EoM Succubus")

# --- 8. quái trong range: lock theo kill-order + orbit + launch drone ---
b = brain("Gone Berserk")
acts = b.decide(world([
    {"Name": "EoM Fiend", "Distance": "15 km", "center": (1, 1)},   # trigger
    {"Name": "EoM Imp", "Distance": "18 km", "center": (2, 2)},     # kill_first
], drones={"in_space": 0, "in_bay": 10}))
does = [a["do"] for a in acts]
ok("launch drone khi có target", "launch_drones" in does)
locks = [a for a in acts if a["do"] == "lock"]
ok("lock đầu tiên = Imp (kill_first), KHÔNG phải trigger Fiend",
   locks and locks[0]["target"] == "EoM Imp")
ok("orbit 20km theo tactics", any(a["do"] == "orbit" and a.get("km") == 20 for a in acts))

# --- 9. trigger discipline: Fiend KHÔNG được lock khi còn Imp ---
lock_targets = [a.get("target") for a in acts if a["do"] == "lock"]
ok("trigger Fiend không nằm trong lock đầu tiên", "EoM Fiend" not in lock_targets[:1])

# --- 10. không spam re-lock target đã lock ---
acts2 = b.decide(world([
    {"Name": "EoM Fiend", "Distance": "15 km", "center": (1, 1)},
    {"Name": "EoM Imp", "Distance": "18 km", "center": (2, 2)},
], drones={"in_space": 2, "in_bay": 8}))
locks2 = [a.get("target") for a in acts2 if a["do"] == "lock"]
ok("tick sau: lock target MỚI (không re-lock Imp)", "EoM Imp" not in locks2)

# --- 11. drone leash: target > 25km → recall ---
b = brain()
b.locked_names.add("EoM Imp")
acts3 = b.decide(world([
    {"Name": "EoM Imp", "Distance": "40 km", "center": (1, 1)},
], drones={"in_space": 2, "in_bay": 8}))
ok("target 40km > leash → recall_drones", any(a["do"] == "recall_drones" for a in acts3))

# --- 12. station/gate/wreck KHÔNG phải quái ---
b = brain()
acts4 = b.decide(world([
    {"Name": "Nonni IV - Caldari Navy Assembly Plant", "Distance": "103 km", "center": (1, 1)},
    {"Name": "Wreck EoM Imp", "Distance": "5 km", "center": (2, 2)},
]))
ok("station/wreck không được lock/bắn", not any(a["do"] in ("lock", "orbit") for a in acts4))

print("\n[PASS] security brain: 15 checks")
