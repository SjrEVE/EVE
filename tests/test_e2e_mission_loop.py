"""E2E mission loop — regression tren dump TQ THAT + vong lap SIM toi terminal state.

Khong phai bang chung chay live: day la replay offline qua dung pipeline san xuat
`LiveSecurityRunner.refresh() -> SecurityMode.tick() -> apply(dry)` va mot vong
Supervisor that (refresh -> tick -> execute). Xem `docs/MISSION_RESEARCH_DEEP_2026-11-11.md`.

Chay: PYTHONPATH=src python tests/test_e2e_mission_loop.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.agent import AgentEye  # noqa: E402
from fila_bot.eye import Eye  # noqa: E402
from fila_bot.missions_db import classify_security_mission, template_kind  # noqa: E402
from fila_bot.modes.live_security import LiveSecurityRunner  # noqa: E402
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


def eye_from(path: Path) -> Eye:
    e = Eye.__new__(Eye)
    e.root = json.loads(path.read_text(encoding="utf-8"))
    e._pos = None
    e._pos_root = None
    return e


FIX = ROOT / "tests" / "fixtures"
G1 = FIX / "ui_tree_e2e_01_docked_nodialog.json"        # docked, chi co agent Distribution
G2 = FIX / "ui_tree_e2e_02_offer_loaded.json"            # offer Rancorous Researcher (courier that)
G3 = FIX / "ui_tree_e2e_03_accepted_turnin.json"         # mission active + nut Complete
G4 = FIX / "ui_tree_e2e_04_connection_lost.json"         # dump TQ that co tin hieu Connection Lost
G10 = FIX / "ui_tree_e2e_05_security_cargo_delivery.json"  # Security L1 "Cargo Delivery" + Complete
G6 = FIX / "ui_tree_e2e_06_live_cannot_complete.json"       # dump LIVE 11-11: modal Cannot Complete Mission
G7 = FIX / "ui_tree_live_step2_offer.json"                   # dump LIVE 11-11: mission (2 of 5), Job Board chua mo

# ---------- 1. P0: "Cargo Delivery" la killMission co item objective, KHONG phai courier ----------
e10 = eye_from(G10)
off10 = AgentEye(e10).read_offer()
assert off10 is not None and off10["title"] == "Cargo Delivery"
assert off10["type"] != "courier", off10
assert off10["objective_kind"] == "item", off10
assert off10["template_kind"] == "kill_item", off10
assert template_kind("Cargo Delivery (1 of 5)") == "kill_item"
assert classify_security_mission("Cargo Delivery") == "item_objective"
ok("P0: offer Cargo Delivery doc tu dump TQ that -> kill + item objective, khong phai courier", True)

r10 = LiveSecurityRunner(e10, dry=True)
w10 = r10.refresh()
assert w10["mission_is_courier"] is False, w10["mission_is_courier"]
assert w10["mission_support"] == "item_objective", w10["mission_support"]
assert w10["drones_in_space"] is None, "khong duoc biạ so drone khi chua ground"
m10 = SecurityMode(max_missions=1)
# The dump is the client state RIGHT AFTER a Complete press was refused, so the
# mode must model that it pressed: otherwise the modal is indistinguishable from
# a box left over by an earlier run (ground 2026-11-12 19:42 run25).
m10._was_in_space = True
m10._await_turnin = True
a10 = m10.tick(w10)
# Dump that co modal "Cannot Complete Mission ... you must deliver 1 x Crates of
# Synthetic Oil" -> bot phai DUNG, khong dismiss OK roi bam Complete lai (loop),
# khong Quit mission (trai policy nhan offer).
assert a10 and a10[0]["do"] == "blocked" and "objective" in a10[0]["why"].lower(), a10
assert not any(x["do"] in ("quit_mission", "dismiss_modal", "complete_mission", "undock")
               for x in a10), a10
ok("P0 integration: modal EVE tu choi Complete -> BLOCKED co ly do that, khong Quit/retry mua", True)

# ---------- 1b. P0 goc: offer "Cargo Delivery" co nut Accept phai duoc NHAN ----------
# Shape offer lay tu docs/MISSION_RESEARCH_DEEP_2026-11-11.md (offline replay P0).
offer_shape = {"type": "encounter", "objective_kind": "item", "template_kind": "kill_item",
               "title": "Cargo Delivery", "cargo_m3": 0.1, "cargo_item": "Synthetic Oil",
               "buttons": {"accept": (343, 808), "decline": (434, 808), "delay": (525, 808),
                           "request": None, "complete": None, "quit": None, "close": None}}
w_offer = {"docked": True, "station": "Sobaseki VII", "home_station": "Sobaseki VII",
           "connection_lost": False, "modal": None, "agents": [], "agent_dialog_open": True,
           "offer": offer_shape, "missions": [], "has_active_mission": False,
           "mission_is_courier": False, "mission_support": "item_objective",
           "mission_panel_observed": True, "ship_health": None, "undock_xy": (999, 700)}
a_offer = SecurityMode().tick(w_offer)
assert a_offer and a_offer[0]["do"] == "accept_mission", a_offer
ok("P0: offer Cargo Delivery (killMission + item) -> accept_mission, khong block truoc Accept", True)

# ---------- 2. Courier that van duoc NHAN (policy: chi decline Anomic) ----------
e2 = eye_from(G2)
off2 = AgentEye(e2).read_offer()
assert off2 is not None
assert off2["type"] == "courier" and off2["objective_kind"] == "transport", off2
assert off2["title"] == "Rancorous Researcher (1 of 5)" and off2["cargo_m3"] == 0.1
r2 = LiveSecurityRunner(e2, dry=True)
w2 = r2.refresh()
assert w2["mission_is_courier"] is True
a2 = SecurityMode().tick(w2)
assert a2 and a2[0]["do"] == "accept_mission", a2
ok("offer courier that co cargo 0.1 m3 -> accept_mission (khong con block truoc Accept)", True)

# ---------- 3. Fail-closed: tram chi co agent Distribution -> block co ly do ----------
e1 = eye_from(G1)
w1 = LiveSecurityRunner(e1, dry=True).refresh()
clock0 = {"t": 500.0}
m1 = SecurityMode(clock=lambda: clock0["t"])
a1 = m1.tick(w1)
# Ground LIVE 2026-11-12 16:48: an empty agent list on the first docked tick is a
# render race, so the bot waits; the block must still arrive after the grace.
assert a1 and a1[0]["do"] == "wait", a1
clock0["t"] += 31.0
a1b = m1.tick(w1)
assert a1b[0]["do"] == "blocked" and "Security Agent" in (a1b[0]["why"]), a1b
ok("khong co Security Agent khả dụng -> BLOCKED ro ly do, khong click mua", True)

# ---------- 4. Replay that: offer -> accept -> set destination/undock, KHONG bam Complete som ----------
import fila_bot.modes.live_security as ls  # noqa: E402

ls.time.sleep = lambda *a, **k: None       # dry replay: bo thoi gian cho that cua executor
clock = {"t": 1000.0}


def virt_clock() -> float:
    return clock["t"]


eye = eye_from(G2)
runner = LiveSecurityRunner(eye, dry=True)
mode = SecurityMode(max_missions=1, clock=virt_clock)
stages = {
    "offer": G2,
    "accepted": G3,
}
stage = "offer"
trace: list[str] = []
for _ in range(60):
    w = runner.refresh()
    acts = mode.tick(w)
    runner.apply(acts)
    clock["t"] += 2.0
    for a in acts:
        d = a.get("do")
        if d:
            trace.append(d)
        if stage == "offer" and d == "accept_mission":
            eye.root = json.loads(stages["accepted"].read_text(encoding="utf-8"))
            stage = "accepted"
        elif stage == "accepted" and d == "undock":
            break
    if stage == "accepted" and any(a.get("do") == "undock" for a in acts):
        break
assert "accept_mission" in trace, trace
assert "set_destination" in trace and "undock" in trace, trace
assert "complete_mission" not in trace and "quit_mission" not in trace, trace
assert mode.completed_missions == 0, mode.status()
assert mode.blocked is None, mode.status()
ok("replay dump that: nhan -> set destination -> undock, KHONG bam Complete som", True)

# ---------- 4a. Dump LIVE 11-11: modal Cannot Complete Mission tu chinh client Boss ----------
e6 = eye_from(G6)
off6 = AgentEye(e6).read_offer()
assert off6 is not None and "What s in a Name" in (off6["title"] or ""), off6 and off6["title"]
w6 = LiveSecurityRunner(e6, dry=True).refresh()
assert w6["has_active_mission"] is True and w6["mission_panel_observed"] is True, w6
assert "Cannot Complete" in str((w6["modal"] or {}).get("text")), w6["modal"]
a6 = SecurityMode().tick(w6)
# G6 is the client state AFTER a Complete press was refused; model that press,
# otherwise the modal is indistinguishable from a box left over by an earlier run
# (ground 2026-11-12 19:42 run25). A refused Complete must still stop the run.
_m6 = SecurityMode(); _m6._was_in_space = True; _m6._await_turnin = True
a6 = _m6.tick(w6)
assert a6[0]["do"] == "blocked" and "objective" in a6[0]["why"].lower(), a6
# Sau khi dong modal: Boss yeu cau di lam mission -> set destination/undock,
# van KHONG bam Complete (objective chua xong) va KHONG Quit.
a6b = SecurityMode().tick(dict(w6, modal=None))
assert a6b[0]["do"] in ("set_destination", "undock"), a6b
assert not any(x["do"] in ("complete_mission", "quit_mission") for x in a6b), a6b
ok("dump LIVE 11-11: modal that -> sau khi dong thi DI LAM, khong bam Complete/Quit", True)

# ---------- 4b. Connection Lost (dump TQ that) -> E-STOP ngay ----------
e4 = eye_from(G4)
w4 = LiveSecurityRunner(e4, dry=True).refresh()
a4 = SecurityMode().tick(w4)
assert a4 and a4[0]["do"] == "estop", a4
assert "Connection Lost" in (a4[0]["why"]), a4
ok("Connection Lost tu dump TQ that -> estop, khong click Quit / khong tu login lai", True)

# ---------- 4c. AUTO: mission co bang chung combat objective -> duoc UNDOCK ----------
from fila_bot.missions_db import (authorize_security_targets,  # noqa: E402
                                  grounded_combat_objective, normalize_title)

live_title = "What s in a Name - Change of Address (1 of 5)"
g = grounded_combat_objective(live_title)
assert g is not None and "Engage any hostiles" in g["evidence"], g
assert normalize_title(live_title) == "what s in a name - change of address"
off_live = AgentEye(eye_from(G6)).read_offer()
assert off_live is not None and off_live["objective_kind"] == "combat", off_live
w_live = LiveSecurityRunner(eye_from(G6), dry=True).refresh()
assert w_live["mission_travel_support"] is True, w_live
assert w_live["mission_support"] == "unknown", w_live["mission_support"]
# Quyen BAN van bi tu choi du da duoc phep di chuyen (chua co faction ID + catalog).
assert authorize_security_targets(live_title, [
    {"name": "Guristas Frigate", "faction": "Guristas"}])[0] is False
ok("AUTO: bang chung objective live -> duoc di chuyen, nhung VAN khong duoc ban", True)

# Link toa do ground tu chinh dump live (Cell tablecell 0-3, dong "Location 0.9 Hirtamon").
from fila_bot.agent import mission_location_link  # noqa: E402
assert mission_location_link(eye_from(G6)) == (670, 352)
assert w_live["mission_link_xy"] == (670, 352), w_live["mission_link_xy"]
ok("ground: link Location trong briefing = (670,352), khong doan toa do", True)

# Cold start: dialog dong, mission active -> set destination (link) roi undock.
w_cold = dict(w_live, modal=None, agent_dialog_open=False, offer=None)
m_cold = SecurityMode()
a1 = m_cold.tick(w_cold)
assert a1 and a1[0]["do"] == "set_destination" and a1[0]["at"] == (670, 352), a1
w_route = dict(w_cold, travel={"system": "New Caldari", "docked": True,
                               "markers": [(100, 100)], "warping": False,
                               "menu": [], "route_panel": True})
a2 = m_cold.tick(w_route)
assert a2 and a2[0]["do"] == "undock", a2
assert not any(x["do"] in ("complete_mission", "quit_mission", "lock_target",
                           "fire_weapons") for x in a1 + a2)
ok("AUTO: nhan -> set destination -> undock (khong con dung im o tram)", True)

# Ngoai space con route marker -> di theo route (right-click marker -> Jump),
# khong warp beacon lung tung khi chua toi he cua mission.
m_route = SecurityMode(clock=lambda: 3000.0)
w_inspace = dict(w_route, docked=False, beacons=[], travel={
    "system": "New Caldari", "docked": False, "markers": [(100, 100)],
    "warping": False, "menu": [], "route_panel": True},
    ship_health={"shield": 1.0, "armor": 1.0, "structure": 1.0},
    hostiles=[], gates=[])
a3 = m_route.tick(w_inspace)
assert a3 and a3[0]["do"] == "open_menu", a3
ok("co route marker -> open_menu/Jump theo TravelTo, khong warp beacon som", True)

# ---------- 4c2. Job Board CHUA MO: dialog co Complete nhung van phai DI LAM ----------
w7 = LiveSecurityRunner(eye_from(G7), dry=True).refresh()
assert w7["has_active_mission"] is None, w7["has_active_mission"]  # panel missing is UNKNOWN, not observed-empty
assert w7["mission_travel_support"] is True and w7["mission_link_xy"] == (678, 352), w7
a7 = SecurityMode().tick(w7)
assert a7[0]["do"] == "set_destination" and a7[0]["at"] == (678, 352), a7
assert not any(x["do"] in ("complete_mission", "quit_mission", "blocked") for x in a7), a7
ok("Job Board chua mo -> van set destination/di lam, khong nham thanh turn-in", True)

# ---------- 4d. Khong spam warp toi beacon (bug live 11-11: TRAVEL_SITE dung 75s) ----------
clock2 = {"t": 2000.0}
m_warp = SecurityMode(clock=lambda: clock2["t"])
w_beacon = {"docked": False, "connection_lost": False, "modal": None,
            "ship_health": {"shield": 1.0, "armor": 1.0, "structure": 1.0},
            "has_active_mission": True, "missions": ["The Blockade"],
            "active_mission_title": "The Blockade", "mission_travel_support": True,
            "mission_support": "combat", "hostiles": [], "gates": [],
            "beacons": [{"name": "Avalon Flotilla", "center": (813, 396)}],
            "drones_out": False, "afterburner_on": True,
            "mission_panel_observed": True}
first = m_warp.tick(w_beacon)
assert first and first[0]["do"] == "warp_beacon", first
spam = []
for _ in range(12):
    clock2["t"] += 1.0
    spam += m_warp.tick(w_beacon)
assert not any(a["do"] == "warp_beacon" for a in spam), spam
assert all(a["do"] == "wait" for a in spam), spam
ok("warp toi beacon: 1 lenh roi CHO, khong bam S+click moi tick", True)
# Het cooldown -> toi da 3 lan roi BLOCKED co ly do (khong lap vo han).
for _ in range(3):
    clock2["t"] += 61.0
    tail = m_warp.tick(w_beacon)
assert tail[0]["do"] == "blocked" and "Warp" in (m_warp.blocked or ""), tail
ok("warp that bai sau 3 lan -> BLOCKED co ly do, khong lap vo han", True)

# ---------- 5. Vong lap E2E day du qua Supervisor that (SIM) toi IDLE_DONE ----------
from fila_bot.ui_model import build_supervisor  # noqa: E402

sup = build_supervisor("security", sim=True, dry=True, max_missions=1,
                       runs_dir=tempfile.mkdtemp(prefix="fila_e2e_"))
sim = sup.refresh.__self__
sup.send("START")
for _ in range(120):
    sup.step()
    if sup.mode.phase == "IDLE_DONE":
        break
assert sup.mode.phase == "IDLE_DONE", (sup.mode.phase, sup.mode.status(), sim.stage)
assert sup.mode.completed_missions == 1, sup.mode.status()
assert sup.mode.blocked is None, sup.mode.status()
for needed in ("open_agent_chat", "accept_mission", "undock", "warp_beacon",
               "lock_target", "fire_weapons", "recall_drones", "warp_home",
               "complete_mission"):
    assert needed in sim.trace, (needed, sim.trace)
ok("E2E SIM: refresh -> tick -> execute toi IDLE_DONE, completed=1, du 9 buoc hanh dong", True)

print(f"\n[PASS] test_e2e_mission_loop: {PASS} pass")
