"""Regression G9 (2026-11-11): bot KHÔNG nhận mission — block "Không tìm thấy nút Decline".

Root cause (đ ground trên dump THẬT, không fake):
- Dump TQ 2026-11-10 16:02 (dumps/g8_dialog_160238.json): ngay sau khi click chat,
  AgentDialogueWindow chỉ 60 node + LoadingWheel, KHÔNG có Edit/Button — offer chưa
  render. FSM cũ đọc offer trên cây rỗng -> title=None -> evaluate_offer(None) trả
  DECLINE -> không có nút Decline -> block vĩnh viễn (runs/2026-11-11.jsonl 05:43).
- Fixture G2 (tests/fixtures/ui_tree_agent_offer.json): dialog đã load = 588 node,
  2 Edit briefing/objective + Accept/Decline/DeferMission_Button.

Quy tắc mới:
1. evaluate_offer(None) -> BLOCKED (không decline mù).
2. Dialog mở nhưng chưa render (AgentEye.loaded()=False) -> chờ có hạn, không quyết.
3. Dialog đã load mà không có nút nào -> bấm Request Mission (hội thoại lần đầu).
4. Sau khi bấm nút door (Accept/Decline/Complete) -> chờ 6s chuyển cảnh.

Chạy: PYTHONPATH=src python tests/test_g9_dialog.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.agent import AgentEye  # noqa: E402
from fila_bot.eye import Eye  # noqa: E402
from fila_bot.missions_db import evaluate_offer  # noqa: E402
from fila_bot.modes.security import SecurityMode  # noqa: E402

PASS = 0
DUMP_LOADING = ROOT / "dumps/g8_dialog_160238.json"
if not DUMP_LOADING.is_file():
    print("[SKIP] local-only EVE loading dump is not included in portable artifacts")
    raise SystemExit(0)


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} — {msg}")
        sys.exit(1)


def eye_from(path: Path) -> Eye:
    e = Eye.__new__(Eye)
    e.root = json.loads(path.read_text(encoding="utf-8"))
    e._pos = None
    e._pos_root = None
    return e


# ---------- 1. evaluate_offer(None) = BLOCKED, KHÔNG DECLINE ----------
d, why = evaluate_offer(None)
assert (d, why) == ("BLOCKED", "không đọc được tiêu đề mission (dialog chưa render offer)"), (d, why)
d2, _ = evaluate_offer("")
assert d2 == "BLOCKED", d2
ok("evaluate_offer(None) -> BLOCKED (khong decline mu — bug 05:43)", True)

# blacklist: CHỈ anomic DECLINE; counter-attack/navy/encounter đều NHẬN hết
d3, why3 = evaluate_offer("Counterattack (Caldari Navy)")
assert d3 == "ACCEPT", (d3, why3)
d3a, _ = evaluate_offer("Counter-Attack")
assert d3a == "ACCEPT", d3a
d3b, why3b = evaluate_offer("Gallente Navy Tower Defense")
assert d3b == "ACCEPT", (d3b, why3b)
d3f, why3f = evaluate_offer("Cargo Delivery")
assert d3f == "ACCEPT", (d3f, why3f)  # chỉ anomic bị decline; type-risk gate nằm trước firing
d3e, _ = evaluate_offer("The Encounter")
assert d3e == "ACCEPT", d3e
d3c, _ = evaluate_offer("Anomic Base Team")
assert d3c == "DECLINE", d3c
ok("blacklist: CHI anomic DECLINE — con lai nhan het (ca counter-attack)", True)

# Offer acceptance policy != authorization to fire. Unknown mission / protected target
# must fail closed even when the offer itself was accepted.
from fila_bot.missions_db import classify_security_mission, authorize_security_targets  # noqa: E402
assert classify_security_mission("The Blockade") == "combat"
# P0 11-11: CCP SDE build 3682781 xep "Cargo Delivery" vao killMission co
# item objective; dump TQ g10_turnin_dialog.json la agent SECURITY L1 co nut
# Complete. KHONG duoc gan thanh courier theo keyword title/cargo.
assert classify_security_mission("Cargo Delivery") == "item_objective"
assert classify_security_mission("Counterattack") == "unknown"
assert classify_security_mission("Counter-Attack") == "unknown"
assert classify_security_mission("The Encounter") == "unknown"  # 'counter' la infix, khong duoc khop
assert classify_security_mission("Anomic Team") == "burner"
assert classify_security_mission("Rancorous Researcher (1 of 5)") == "unknown"
assert classify_security_mission("The Blockade (3 of 5)") == "combat"  # cat chain
assert authorize_security_targets("The Blockade", [
    {"name": "Guristas Frigate", "faction": "Guristas"}])[0] is True
for protected in ("CONCORD", "AmarrNavy", "CaldariNavy", "GallenteNavy", "MinmatarNavy"):
    allowed, reason = authorize_security_targets("The Blockade", [
        {"name": "protected NPC", "faction": protected}])
    assert not allowed and protected in reason, (protected, allowed, reason)
assert not authorize_security_targets("Counterattack", [
    {"name": "Guristas Frigate", "faction": "Guristas"}])[0]
assert not authorize_security_targets("The Blockade", [
    {"name": "unknown NPC", "faction": "MissionNPC"}])[0]
ok("fire policy: mission+faction must be known; Empire/CONCORD/unknown fail closed", True)

# ---------- 2. AgentEye.loaded(): dump THẬT đã load vs đang load ----------
FIX_LOAD = ROOT / "tests/fixtures/ui_tree_agent_offer.json"

ae_ok = AgentEye(eye_from(FIX_LOAD))
assert ae_ok.loaded() is True
off_ok = ae_ok.read_offer()
assert off_ok and off_ok["title"] == "Rancorous Researcher (1 of 5)", off_ok and off_ok["title"]
ok("AgentEye.loaded(): dialog da render (fixture G2) -> True + doc duoc title", True)

ae_loading = AgentEye(eye_from(DUMP_LOADING))
assert ae_loading.loaded() is False
off_loading = ae_loading.read_offer()
assert off_loading is not None and off_loading["title"] is None
assert not any(off_loading["buttons"].values()), off_loading["buttons"]
ok("AgentEye.loaded(): dialog DANG load (dump TQ 16:02: wheel, 0 Edit) -> False", True)

# ---------- 3. FSM: dialog đang load -> WAIT, không decline, không block ----------
clock = {"t": 100.0}


def mk(world: dict) -> SecurityMode:
    m = SecurityMode(clock=lambda: clock["t"])
    m.request_safe_stop = lambda: None  # không dùng trong test này
    return m


def world_loading(**kw) -> dict:
    """Mirror world của LiveSecurityRunner khi dialog vừa mở (dump 16:02)."""
    w = {
        "docked": True, "station": "Tunttaras IX - Moon 11 - Ytiri Storage",
        "home_station": "Tunttaras IX - Moon 11 - Ytiri Storage",
        "system": "Isaziwa", "security": 0.9, "connection_lost": False,
        "agents": [{"name": "Iji Kiyura", "level": 1, "division": "Security",
                    "available": True, "chat_xy": (640, 400)}],
        "agent_dialog_open": True,
        "offer": None,             # read_offer() trên cây đang load: title None
        "missions": [], "has_active_mission": False,
        "hostiles": [], "gates": [], "beacons": [],
        "ship_health": None, "speed_mps": None, "maneuver": None,
        "undock_xy": (999, 700), "drones_in_space": 0, "drones_out": False,
        "weapons_firing": False, "afterburner_on": False, "_agent_eye": None,
    }
    w.update(kw)
    return w


# tick 1: dialog mở, chưa load -> wait (nhưng nếu chưa từng open_agent_chat
# và chưa thấy dialog thì tick đầu vẫn phải chờ load, KHÔNG click chat lại)
m = mk({})
a1 = m.tick(world_loading())
assert a1 and a1[0]["do"] == "wait" and "load" in a1[0]["why"], a1
ok("dialog mo chua render -> wait (khong decline/blocked/klai click chat)", True)

# ... và sau 25 tick (25s) không load -> BLOCKED có lý do rõ
for i in range(1, 26):
    clock["t"] += 1.0
    acts = m.tick(world_loading())
assert acts[0]["do"] == "blocked" and "20s" in (m.blocked or ""), (acts, m.blocked)
ok("dialog 20s khong render -> blocked ro ly do (khong treo vo han)", True)

# ---------- 4. FSM: offer đã load nhưng title không đọc được -> WAIT 12s rồi block ----------
clock["t"] = 100.0
m = mk({})
loaded_offer = {"type": None, "title": None, "cargo_m3": None, "cargo_item": None,
                "cargo_qty": None, "pickup": None, "dropoff": None, "isk": [],
                "buttons": {"accept": (503, 808), "decline": (594, 808),
                            "delay": (685, 808), "request": None, "complete": None,
                            "quit": None, "close": None}}
a = m.tick(world_loading(offer=loaded_offer))
assert a[0]["do"] == "wait" and "tiêu đề" in a[0]["why"], a
clock["t"] += 13.0
a = m.tick(world_loading(offer=loaded_offer))
assert a[0]["do"] == "blocked" and "12s" in (m.blocked or ""), (a, m.blocked)
ok("offer co nut nhung title=None -> wait 12s roi block (KHONG decline)", True)

# ---------- 5. FSM: offer chuẩn -> accept_mission đúng toạ độ nút ----------
clock["t"] = 100.0
m = mk({})
good = dict(loaded_offer, type="courier", title="Rancorous Researcher (1 of 5)", cargo_m3=0.1)
a = m.tick(world_loading(offer=good))
assert a[0]["do"] == "accept_mission" and a[0]["at"] == (503, 808), a
ok("offer chuân -> accept_mission tai AcceptMission_Button (503,808)", True)

# ---------- 6. FSM: dialog đã load, KHÔNG có nút nào -> request_mission ----------
clock["t"] = 100.0
m = mk({})
empty_btns = dict(loaded_offer, buttons={k: None for k in loaded_offer["buttons"]})
a = m.tick(world_loading(offer=empty_btns))
assert a[0]["do"] == "request_mission", a
# sau 3s vẫn chờ; sau 9s chưa có nút -> block
clock["t"] += 3.0
a = m.tick(world_loading(offer=empty_btns))
assert a[0]["do"] == "wait", a
clock["t"] += 6.0
a = m.tick(world_loading(offer=empty_btns))
assert a[0]["do"] == "blocked" and "Request" in (m.blocked or ""), (a, m.blocked)
ok("dialog load khong co nut -> request_mission, roi block neu 8s trong", True)

# ---------- 7. FSM: sau khi bấm door (accept) -> chờ 6s chuyển cảnh ----------
clock["t"] = 100.0
m = mk({})
good2 = dict(loaded_offer, type="courier", title="Rancorous Researcher (1 of 5)", cargo_m3=0.1)
assert m.tick(world_loading(offer=good2))[0]["do"] == "accept_mission"
# ngay sau đó offer vẫn còn trong world (client chưa cập nhật) -> KHÔNG accept lần 2
clock["t"] += 1.0
a = m.tick(world_loading(offer=good2))
assert a[0]["do"] == "wait" and "bấm nút" in a[0]["why"], a
clock["t"] += 7.0
a = m.tick(world_loading(offer=good2))     # hết grace -> quyết lại bình thường
assert a[0]["do"] == "accept_mission", a
ok("sau khi bam Accept -> grace 6s khong click nua (anti double-click)", True)

# ---------- 8. FSM: không có dialog, có agent security -> open_agent_chat (giữ hành vi cũ) ----------
clock["t"] = 100.0
m = mk({})
a = m.tick(world_loading(agent_dialog_open=False, offer=None))
assert a[0]["do"] == "open_agent_chat" and a[0]["at"] == (640, 400), a
ok("chua mo dialog + co agent -> open_agent_chat (khong thoat hanh vi cu)", True)

print(f"\n=> {PASS} test PASS (G9 dialog-load regression)")
