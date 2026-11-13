"""Regression G10 (11-11): vòng mission ĐÓNG KÍN qua sim — nhận -> undock -> combat
-> về trạm -> TRẢ mission (không undock lại vô hạn).

Tình huống thật 11-11: bot kill xong về trạm, has_active_mission=TRUE (chưa Complete)
-> FSM cũ undock lại ngay -> vòng vô hạn, không bao giờ nhận thưởng.

Chạy: PYTHONPATH=src python tests/test_g10_mission_loop.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.modes.security import SecurityMode  # noqa: E402

PASS = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} — {msg}")
        sys.exit(1)


def world(**kw) -> dict:
    w = {
        "docked": True, "station": "Sobaseki VII - CN Logistic Support",
        "home_station": "Sobaseki VII - CN Logistic Support",
        "system": "Sobaseki", "security": 0.9, "connection_lost": False,
        "agents": [{"name": "Jukosoni Kauniki", "level": 1, "division": "Security",
                    "available": True, "chat_xy": (640, 400)}],
        "agent_dialog_open": False, "offer": None,
        "missions": [], "has_active_mission": False,
        "hostiles": [], "gates": [], "beacons": [],
        "ship_health": None, "speed_mps": None, "maneuver": None,
        "undock_xy": (999, 700), "drones_in_space": 0, "drones_out": False,
        "weapons_firing": False, "afterburner_on": False, "_agent_eye": None,
        "mission_panel_observed": True, "mission_support": None,
        "active_mission_title": None,
    }
    w.update(kw)
    return w


loaded_offer = {"type": "courier", "title": "Cargo Delivery", "chain": None,
                "cargo_m3": 0.1, "cargo_item": "Chip", "cargo_qty": 1,
                "pickup": None, "dropoff": None, "isk": [21000],
                "buttons": {"accept": (343, 808), "decline": (434, 808),
                            "delay": (525, 808), "request": None,
                            "complete": None, "quit": None, "close": None}}
complete_offer = {"type": None, "title": "The Blockade", "chain": None,
                  "cargo_m3": None, "cargo_item": None, "cargo_qty": None,
                  "pickup": None, "dropoff": None, "isk": [],
                  "buttons": {"accept": None, "decline": None, "delay": None,
                              "request": None, "complete": (400, 808),
                              "quit": (500, 808), "close": (600, 808)}}

# ---------- 1. Nhận mission ----------
m = SecurityMode()
assert m.tick(world(agent_dialog_open=True, offer=loaded_offer))[0]["do"] == "accept_mission"
ok("nhận mission -> accept_mission", True)

# ---------- 2. ĐÃ accept (door grace) nhưng has_active_mission chưa kịp TRUE:
#              sau grace 6s, KHÔNG undock khi chưa thấy panel mission — chờ/hành động hợp lệ
for i in range(10):
    m.tick(world(agent_dialog_open=True, offer=loaded_offer))
# client đã nhận: dialog chuyển sang trạng thái khác (không còn offer) — bot phải chờ
a = m.tick(world(agent_dialog_open=True, offer=None))
assert a[0]["do"] in ("wait", "request_mission", "undock", "open_agent_chat"), a
ok("sau accept: hành động hợp lệ, không block oan", True)

# ---------- 3. VỪA NHẬN mission (chưa ra space) -> UNDOCK, không mở lại chat agent ----------
m2 = SecurityMode()
a = m2.tick(world(has_active_mission=True, missions=["The Blockade"],
                  mission_support="combat", active_mission_title="The Blockade"))
assert a[0]["do"] == "undock", a
ok("vừa nhận mission + chưa ra space -> undock (không deadlock mở lại hội thoại)", True)

# ---------- 3b. ĐÃ ĐI LÀM VỀ (từng ở space) + mission active -> mở chat trả, KHÔNG undock lặp ----------
m2b = SecurityMode()
m2b.tick(world(docked=False, has_active_mission=True, missions=["The Blockade"],
               mission_support="combat", hostiles=[], beacons=[]))
a = m2b.tick(world(has_active_mission=True, missions=["The Blockade"],
                   mission_support="combat", active_mission_title="The Blockade"))
assert a[0]["do"] == "open_agent_chat", a
ok("đi làm về + mission active -> open_agent_chat (chống undock vô hạn, G10)", True)

# ---------- 4. Complete KHÔNG tính theo click — phải READ-BACK mission entry biến mất ----------
m3 = SecurityMode()
m3._was_in_space = True          # mô phỏng "đã đi làm về" (live 11-11: chưa rời trạm thì KHÔNG bấm Complete)
a = m3.tick(world(has_active_mission=True, agent_dialog_open=True, offer=complete_offer,
                  mission_is_courier=False, mission_support="combat"))
assert a[0]["do"] == "complete_mission" and a[0]["at"] == (400, 808), a
assert m3.completed_missions == 0, "counter tăng trước khi xác nhận là bịa"
ok("nút Complete -> phát lệnh, CHƯA tăng counter", True)

# client chưa cập nhật: mission vẫn active -> chờ, không kết luận xong
a = m3.tick(world(has_active_mission=True, agent_dialog_open=True, offer=complete_offer,
                  mission_is_courier=False, mission_support="combat"))
assert a[0]["do"] == "wait", a
assert m3.completed_missions == 0
# panel mission ĐÃ quan sát + entry biến mất -> turn-in xác nhận
a = m3.tick(world(has_active_mission=False, missions=[], mission_panel_observed=True,
                  mission_is_courier=False))
assert m3.completed_missions == 1, m3.status()
assert m3._await_turnin is False
ok("read-back: mission entry biến mất -> completed=1 duy nhất 1 lần", True)

# panel KHÔNG quan sát được -> không tự xác nhận (fail-closed)
m3b = SecurityMode()
m3b._was_in_space = True
m3b.tick(world(has_active_mission=True, agent_dialog_open=True, offer=complete_offer,
               mission_is_courier=False, mission_support="combat"))
a = m3b.tick(world(has_active_mission=False, missions=[], mission_panel_observed=False))
assert a[0]["do"] == "wait" and m3b.completed_missions == 0, a
ok("panel mission không đọc được -> chờ, KHÔNG tự nhận turn-in", True)

# ---------- 4b. Courier có nút Complete (objective ĐÃ xong theo EVE) -> vẫn trả được ----------
m3c = SecurityMode()
m3c._was_in_space = True
courier_turnin = dict(complete_offer, title="Rancorous Researcher (1 of 5)")
a = m3c.tick(world(has_active_mission=True, agent_dialog_open=True, offer=courier_turnin,
                   mission_is_courier=True, mission_support="courier", cargo_loaded=False))
assert a[0]["do"] == "complete_mission", a
ok("courier có nút Complete thật -> complete_mission (không Quit, không block oan)", True)

# ---------- 4c. Courier CHƯA có nút Complete: giữ tàu ở trạm, báo rõ, không Quit/bắn ----------
m3d = SecurityMode()
no_complete = dict(loaded_offer, type="courier", title="Rancorous Researcher (1 of 5)")
a = m3d.tick(world(has_active_mission=True, agent_dialog_open=True, offer=no_complete,
                   mission_is_courier=True, mission_support="courier", cargo_empty_now=True))
assert a[0]["do"] == "blocked" and "giữ tàu" in a[0]["why"], a
assert not any(x["do"] in ("quit_mission", "undock", "lock_target", "fire_weapons") for x in a)
ok("courier chưa xong objective -> accepted_but_unsupported, KHÔNG Quit/bắn mù", True)

# ---------- 4d. Mission item-objective (Cargo Delivery) chưa ground objective ship ----------
m3e = SecurityMode()
a = m3e.tick(world(has_active_mission=True, mission_is_courier=False,
                   mission_support="item_objective", active_mission_title="Cargo Delivery",
                   missions=["Cargo Delivery"]))
assert a[0]["do"] == "blocked" and "execution support" in a[0]["why"], a
ok("Cargo Delivery (killMission + item) -> giữ tàu, không tự undock/bắn", True)

# ---------- 4e. LIVE 11-11: vừa nhận mà đã có nút Complete -> KHÔNG bấm ----------
# EVE hiện Complete ngay sau Accept ("What's in a Name - Change of Address (1 of 5)");
# bấm vào ra modal "Cannot Complete Mission". Chưa rời trạm = chưa có bằng chứng.
m3f = SecurityMode()
a = m3f.tick(world(has_active_mission=True, agent_dialog_open=True, offer=complete_offer,
                   mission_is_courier=False, mission_support="unknown"))
assert a[0]["do"] == "blocked" and "chưa rời trạm" in a[0]["why"], a
assert not any(x["do"] in ("complete_mission", "quit_mission", "dismiss_modal") for x in a)
assert m3f.completed_missions == 0
ok("LIVE 11-11: nút Complete ngay sau Accept -> BLOCKED, không bấm Complete/Quit", True)

# ---------- 5. Mission active + dialog mở ĐANG LOAD (offer=None) -> chờ, KHÔNG undock ----------
m4 = SecurityMode()
a = m4.tick(world(has_active_mission=True, agent_dialog_open=True, offer=None))
assert a[0]["do"] == "wait", a
ok("mission active + dialog đang load -> chờ render (không undock/klai click)", True)

# ---------- 6. Mission active + KHÔNG thấy agent panel nào -> undock (trường hợp biên) ----------
m5 = SecurityMode()
a = m5.tick(world(has_active_mission=True, agents=[]))
assert a[0]["do"] == "undock", a
ok("mission active + không có agent trong trạm -> undock (không kẹt)", True)

# ---------- 7. Fire authorization: protected/unknown target MUST block before any action ----------
for bad_faction in ("CONCORD", "CaldariNavy", "GallenteNavy", "AmarrNavy", "MissionNPC", None):
    m_safe = SecurityMode()
    unsafe_world = world(docked=False, has_active_mission=True, missions=["The Blockade"],
                         hostiles=[{"name": "untrusted target", "faction": bad_faction,
                                    "priority": 1, "distance": 1000, "center": (500, 500)}],
                         ship_health={"shield": 1.0, "armor": 1.0, "structure": 1.0})
    acts_safe = m_safe.tick(unsafe_world)
    assert acts_safe[0]["do"] == "blocked" and not any(
        a["do"] in ("lock_target", "fire_weapons", "engage_drones", "launch_drones")
        for a in acts_safe), (bad_faction, acts_safe)
# Even a known Guristas target is not attacked under an unknown mission title.
m_unknown = SecurityMode()
a_unknown = m_unknown.tick(world(docked=False, has_active_mission=True, missions=["Unknown Encounter"],
    hostiles=[{"name": "Guristas Frigate", "faction": "Guristas", "priority": 1,
               "distance": 1000, "center": (500, 500)}],
    ship_health={"shield": 1.0, "armor": 1.0, "structure": 1.0}))
assert a_unknown[0]["do"] == "blocked", a_unknown
ok("fire authorization: CONCORD/Empire/unknown faction or mission -> BLOCKED, zero weapon actions", True)

# ---------- 8. Combat: no offense until the client confirms the exact itemID ----------
m6 = SecurityMode()
w_combat = world(docked=False, has_active_mission=True, missions=["The Blockade"],
                 locked_target=None, target_bar_supported=True,
                 hostiles=[{"name": "Angel Cartel Frigate", "object_id": 101,
                            "faction": "Angel", "priority": 5,
                            "distance": 15000, "center": (500, 500)}],
                 ship_health={"shield": 1.0, "armor": 1.0, "structure": 1.0})
a1 = m6.tick(w_combat)
k1 = [x["do"] for x in a1]
assert "lock_target" in k1 and "launch_drones" in k1, a1
assert "fire_weapons" not in k1 and "engage_drones" not in k1, a1
# Tick 2: exact object ID is now active in the client's target bar.
readback = {"object_id": 101, "is_active": True,
            "texts": ["Angel Cartel Frigate"]}
a2 = m6.tick(dict(w_combat, afterburner_on=True, drones_out=True,
                  locked_target=readback))
k2 = [x["do"] for x in a2]
assert "lock_target" not in k2 and "fire_weapons" in k2 and "engage_drones" in k2, a2
# Tick 3: neither weapon activation nor drone order is repeated for this identity.
a2b = m6.tick(dict(w_combat, afterburner_on=True, drones_out=True,
                   locked_target=readback))
k2b = [x["do"] for x in a2b]
assert "fire_weapons" not in k2b and "engage_drones" not in k2b, a2b
ok("combat waits for exact itemID lock readback, then acts once", True)

# ---------- 9. Quái đổi -> lock lại; hết quái -> recall drone rồi về ----------
a3 = m6.tick(dict(w_combat, afterburner_on=True,
                  hostiles=[{"name": "Guristas Kappa Cruiser", "object_id": 202,
                             "faction": "Guristas", "priority": 6,
                             "distance": 20000, "center": (510, 505)}]))
assert a3[0]["do"] == "lock_target", a3
ok("đổi mục tiêu -> lock lại đúng object ID", True)

a4 = m6.tick(dict(w_combat, afterburner_on=True, hostiles=[], drones_out=True))
assert a4[0]["do"] == "wait", a4     # 18s wave-wait bắt đầu
m6.clock = lambda: 10**9             # tua thời gian qua 18s
a5 = m6.tick(dict(w_combat, afterburner_on=True, hostiles=[], drones_out=True))
assert a5[0]["do"] == "recall_drones", a5
ok("hết quái -> recall drone trước khi rời pocket", True)

# ---------- 9. Sau recall: warp_home 1 lần, các tick sau KHÔNG spam lệnh ----------
a6 = m6.tick(dict(w_combat, afterburner_on=True, hostiles=[], drones_out=False))
assert a6[0]["do"] == "warp_home", a6
a7 = m6.tick(dict(w_combat, afterburner_on=True, hostiles=[], drones_out=False))
assert a7[0]["do"] == "warp_home" or a7[0]["do"] == "wait", a7
# phát lại tối đa: sau 120s chỉ wait
m6.clock = lambda: 10**9 + 500
a8 = m6.tick(dict(w_combat, afterburner_on=True, hostiles=[], drones_out=False))
assert a8[0]["do"] == "wait", a8
ok("warp_home không spam vô hạn (giới hạn 120s rồi chỉ chờ)", True)

print(f"\n=> {PASS} test PASS (G10 mission-loop regression)")
