"""Test mission runner — trên DUMP THẬT (docked + space), không fake schema.

Fixture:
- tests/fixtures/ui_tree_mission_docked.json — InfoPanelContainer (station/security/route) + AgentsPanel
- tests/fixtures/ui_tree_mission_space.json   — OverviewWindow (23 entry) + ShipUI + SelectedItemWnd

Nguyên tắc: chỉ khẳng định điều đọc được từ dump; chỗ chưa ground phải BLOCKED,
không được đoán.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.eye import Eye                    # noqa: E402
from fila_bot.mission import MissionEye, MissionRunner  # noqa: E402

PASS = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} — {msg}")
        sys.exit(1)


def eye_from(fixture: str) -> Eye:
    e = Eye.__new__(Eye)
    e.root = json.loads((ROOT / "tests/fixtures" / fixture).read_text(encoding="utf-8"))
    e._pos = None
    e._pos_root = None
    return e


# ---------------- DOCKED ----------------
ed = eye_from("ui_tree_mission_docked.json")
med = MissionEye(ed)
loc = med.location()
ok("loc_station", loc["station"] == "Jita III - Moon 1 - Tash-Murkon Family Trade Embassy", str(loc))
ok("loc_security", loc["security"] == 0.9, str(loc))
ok("loc_system_none", loc["system"] is None, "chưa ground alt= Current Solar System")

rt = med.route()
ok("route_no_destination", rt["destination"] is None and rt["markers"] == 0, str(rt))

ok("agent_dialogue_empty", med.agent_dialogue() == [], str(med.agent_dialogue()))
ok("mission_entries_empty", med.mission_entries() == [], str(med.mission_entries()))

st_d = med.state()
ok("docked_phase", st_d.phase == "DOCKED", st_d.phase)
ok("docked_in_station", st_d.in_station is True)
ok("docked_hp_none", st_d.hp is None, "không có ShipUI trong station")
ok("docked_overview_empty", st_d.overview_count == 0, str(st_d.overview_count))

# FSM: trong station, không có agent/dialog → phải là NEED_AGENT (không bấm mù), KHÔNG undock
runner = MissionRunner(med)
acts = runner.next_actions()
ok("docked_stage_need_agent", runner.stage == "NEED_AGENT", runner.stage)
ok("docked_blocked_not_undock", acts and acts[0]["do"] == "blocked", str(acts))
ok("docked_blocked_has_needs", "needs" in acts[0], str(acts[0]))

# ---------------- SPACE ----------------
es = eye_from("ui_tree_mission_space.json")
mes = MissionEye(es)
st_s = mes.state()
ok("space_phase", st_s.phase in ("AT_SITE", "IN_SPACE", "POCKET_CLEAR"), st_s.phase)
ok("space_hp_read", st_s.hp is not None and st_s.hp.get("shield") is not None, str(st_s.hp))
ok("space_cap_read", st_s.cap == 100.0, str(st_s.cap))
ok("space_overview", st_s.overview_count == 23, str(st_s.overview_count))
ok("space_not_in_station", st_s.in_station is False)
ok("space_no_gate", st_s.gates == [], str(st_s.gates))

# beacon: dump thật ở Jita (station/stargate), KHÔNG có beacon mission → rỗng, không bịa
ok("space_no_mission_beacon", st_s.mission_beacons == [], str(st_s.mission_beacons))

runner_s = MissionRunner(mes)
acts_s = runner_s.next_actions()
# ngoài space, không beacon, không route → BLOCKED với lý do rõ
ok("space_blocked_no_target", acts_s and acts_s[0]["do"] == "blocked", str(acts_s))
ok("space_blocked_reason", "beacon" in acts_s[0].get("why", "").lower(), str(acts_s[0]))

# ---------------- verify hooks ----------------
ok("verify_warp_speed_zero", mes.verify_warp() is False, str(es.speed_mps()))
ok("verify_docked_false_in_space", mes.verify_docked() is False)
ok("verify_docked_true_in_station", med.verify_docked() is True)

# ---------------- beacon giả lập từ dump THẬT: đổi tên 1 entry ----------------
import copy
e2 = Eye.__new__(Eye)
e2.root = copy.deepcopy(es.root)
e2._pos = None
e2._pos_root = None
ov = e2.overview_window()
entries = e2._find_by_type("OverviewScrollEntry", root=ov)
injected = 0
for ent in entries:
    for n in e2.walk(ent):
        a = n.get("attrs") or {}
        # đổi đúng cột Name (label chứa tên hệ/trạm), không phải Distance/Type
        if n.get("type") == "OverviewLabel" and isinstance(a.get("_text"), str) \
                and a["_text"].startswith("Jita"):
            a["_text"] = "Acceleration Gate"
            injected = 1
            break
    if injected:
        break
ok("gate_rename_injected", injected == 1, "không đổi được label Name trong dump")
me2 = MissionEye(e2)
gates = me2.gate_entries()
ok("gate_detected_after_rename", len(gates) == 1 and "gate" in (gates[0]["name"] or "").lower(),
   str(gates))
r2 = MissionRunner(me2)
a2 = r2.next_actions()
ok("gate_phase_after_rename", me2.state().phase in ("POCKET_CLEAR", "AT_SITE"), me2.state().phase)

print(f"\n=> {PASS} test PASS (mission runner, dump thật)")


# ---------------- STATION WINDOW + CONTEXT MENU (dump thật ui_dump_menu.json) ----------------
em = eye_from("ui_tree_station_menu.json")
ok("station_window_found", em.station_window() is not None)
sw = em.station_window()
ok("station_undock_button", sw["undock"] is not None and sw["undock"]["text"] == "Undock", str(sw["undock"]))
ok("station_undock_xy", sw["undock"]["center"] == (1145, 282), str(sw["undock"]["center"]))
ok("station_is_docked", em.is_docked() is True)
ok("station_tabs", {t["name"] for t in sw["tabs"]} >=
   {"guestsPanel", "stationInformationTabAgents", "Button_InventoryPanel"}, str(sw["tabs"]))

menus = em.context_menus()
ok("context_menu_found", len(menus) == 1, str(len(menus)))
ok("context_menu_entries", [e["text"] for e in menus[0]["entries"]] == ["Minimize", "Close"],
   str(menus[0]["entries"]))
ok("menu_entry_xy_by_text", em.menu_entry_xy("Close") == (1008, 323), str(em.menu_entry_xy("Close")))
ok("menu_entry_xy_missing", em.menu_entry_xy("Warp to Within") is None,
   "không được trả toạ độ khi menu không có entry đó")

print(f"=> {PASS} test PASS tổng (mission + station + menu)")
