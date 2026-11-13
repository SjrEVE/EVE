"""RouteAssist — autopilot HỖ TRỢ theo route đã set (Boss 14-11).

Contract: bot KHÔNG set destination, KHÔNG chọn hệ. Người set route trước;
bot thay tay: thấy marker → jump gate đúng tên hệ kế tiếp → chờ session change
→ chờ route panel CẬP NHẬT (chống nhảy ngược theo panel cũ) → lặp tới đích.
Fail-closed ở mọi điểm không có bằng chứng.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.autopilot import RouteAssist  # noqa: E402

PASS = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} — {msg}")
        sys.exit(1)


class FakeClock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t

    def advance(self, s: float) -> None:
        self.t += s


def world(system="Nonni", next_system=None, jumps=None, markers=0, gates=None,
          stations=None, docked=False, undock_xy=(889, 282), location_known=True,
          connection_lost=False, destination=None):
    return {
        "docked": docked, "undock_xy": undock_xy,
        "system": system if location_known else None,
        "location_known": location_known,
        "connection_lost": connection_lost,
        "route": {"destination": destination, "next_system": next_system,
                  "jumps": jumps, "markers": markers},
        "gates": gates or [], "stations": stations or [],
    }


def gate(name, xy=(500, 300)):
    return {"name": name, "type": "Stargate", "center": xy}


# ---------------- 1. route rỗng → done, không bấm gì ----------------
ra = RouteAssist()
acts = ra.tick(world())
ok("no_route_done", acts == [{"do": "done", "why": acts[0]["why"]}] and ra.state == "DONE",
   str(acts))

# ---------------- 2. có route + gate đúng tên → jump ----------------
ra = RouteAssist()
acts = ra.tick(world(next_system="Josameto", jumps=1, markers=1,
                     gates=[gate("Josameto")]))
ok("jump_sent_when_gate_matches",
   len(acts) == 1 and acts[0]["do"] == "jump" and acts[0]["at"] == (500, 300)
   and ra.state == "JUMPING", str(acts))
# resend không xảy ra ngay
clock = FakeClock()
ra2 = RouteAssist(clock=clock)
ra2.tick(world(next_system="Josameto", markers=1, gates=[gate("Josameto")]))
clock.advance(10)
same = ra2.tick(world(next_system="Josameto", markers=1, gates=[gate("Josameto")]))
ok("jump_not_resent_within_cooldown",
   same[0]["do"] == "wait", str(same))

# ---------------- 3. gate sai tên / nhiều gate → KHÔNG bấm mù ----------------
ra = RouteAssist()
acts = ra.tick(world(next_system="Josameto", markers=1, gates=[gate("Piak")]))
ok("wrong_gate_name_waits", acts[0]["do"] == "wait" and ra.state == "WAIT_GATE", str(acts))

ra2 = RouteAssist()
clock2 = FakeClock()
ra2clock = RouteAssist(clock=clock2)
ra2clock.tick(world(next_system="Josameto", markers=1, gates=[gate("Josameto A"), gate("Josameto B")]))
clock2.advance(61)
blocked = ra2clock.tick(world(next_system="Josameto", markers=1,
                              gates=[gate("Josameto A"), gate("Josameto B")]))
ok("ambiguous_gate_blocks", blocked[0]["do"] == "blocked" and "đúng một gate" in blocked[0]["why"],
   str(blocked))

# ---------------- 4. jump xong: system đổi → chờ route panel cập nhật ----------------
clock3 = FakeClock()
ra3 = RouteAssist(clock=clock3)
ra3.tick(world(system="Piak", next_system="Josameto", jumps=1, markers=1,
               gates=[gate("Josameto")]))
# client đổi hệ sau jump (transition: location UNKNOWN một lúc)
clock3.advance(2)
w = world(system=None, location_known=False, next_system="Josameto", jumps=1, markers=1)
acts = ra3.tick(w)
ok("transition_after_jump_waits", acts[0]["do"] == "wait" and ra3.jumps_done == 0, str(acts))
# vào hệ mới, UI đọc lại được nhưng route panel CŨ (next_system=Josameto còn treo)
clock3.advance(5)
acts = ra3.tick(world(system="Josameto", next_system="Josameto", jumps=1, markers=1,
                      gates=[gate("Josameto"), gate("Nourvukaiken")]))
ok("stale_route_panel_waits_no_backjump",
   acts[0]["do"] == "wait" and not any(a["do"] == "jump" for a in acts)
   and ra3._await_route_update, str(acts))
# route panel CẬP NHẬT (next_system đổi) → mới jump tiếp
acts = ra3.tick(world(system="Josameto", next_system="Nourvukaiken", jumps=2, markers=2,
                      gates=[gate("Nourvukaiken")]))
ok("updated_route_then_jump",
   acts[0]["do"] == "jump" and acts[0]["name"] == "Nourvukaiken", str(acts))
ok("jump_counted_once", ra3.jumps_done == 1, str(ra3.jumps_done))

# ---------------- 5. jumps giảm cũng là bằng chứng cập nhật ----------------
clock4 = FakeClock()
ra4 = RouteAssist(clock=clock4)
ra4.tick(world(system="A", next_system="B", jumps=3, markers=3, gates=[gate("B")]))
ra4.tick(world(system="B", next_system="B", jumps=3, markers=3, gates=[gate("B")]))
# jumps giảm 3→2 (panel cập nhật theo chiều giảm) dù next_system chưa đổi chuỗi —
# guard stale bị xoá, và gate B vẫn khớp next_system='B' → jump tiếp là ĐÚNG
# (panel đã cập nhật = đã clear hệ cũ; còn 2 jump, gate B vẫn là lối đi).
acts = ra4.tick(world(system="B", next_system="B", jumps=2, markers=2, gates=[gate("B")]))
ok("jumps_drop_clears_stale_guard_then_jump",
   not ra4._await_route_update and acts[0]["do"] == "jump",
   f"await={ra4._await_route_update} acts={acts}")
# panel cập nhật hẳn (next_system=C) + có gate C → jump tiếp
# (clock phải qua resend cooldown trước — pending jump B vừa gửi ở tick trước)
clock4.advance(125)
acts = ra4.tick(world(system="B", next_system="C", jumps=2, markers=2, gates=[gate("C")]))
ok("jumps_drop_then_next_jump", acts[0]["do"] == "jump" and acts[0].get("name") == "C",
   str(acts))

# ---------------- 6. docked + route → undock ----------------
ra5 = RouteAssist()
acts = ra5.tick(world(docked=True, markers=2, undock_xy=(889, 282)))
ok("docked_with_route_undocks",
   acts[0]["do"] == "undock" and acts[0]["at"] == (889, 282), str(acts))
# docked + không route → done
ra6 = RouteAssist()
acts = ra6.tick(world(docked=True, markers=0))
ok("docked_no_route_done", acts[0]["do"] == "done", str(acts))

# ---------------- 7. connection lost → estop ----------------
ra7 = RouteAssist()
acts = ra7.tick(world(connection_lost=True))
ok("connection_lost_estop", acts[0]["do"] == "estop", str(acts))

# ---------------- 8. max-jumps guard ----------------
clock8 = FakeClock()
ra8 = RouteAssist(clock=clock8, max_jumps=1)
ra8.tick(world(system="A", next_system="B", markers=2, gates=[gate("B")]))
ra8.tick(world(system="B", next_system="C", jumps=1, markers=1, gates=[gate("C")]))
done = ra8.tick(world(system="B", next_system="C", jumps=1, markers=1, gates=[gate("C")]))
ok("max_jumps_stops", done[0]["do"] == "done" and ra8.jumps_done == 1, str(done))

# ---------------- 9. dock_at_end ----------------
ra9 = RouteAssist(dock_at_end=True)
acts = ra9.tick(world(system="Nonni", markers=0,
                      stations=[{"name": "Nonni IV - Plant", "type": "Station",
                                 "center": (700, 400)}],
                      destination="Nonni IV - Plant"))
ok("dock_at_end_docks_exact_station",
   acts[0]["do"] == "dock" and acts[0]["at"] == (700, 400), str(acts))
# station không khớp → không dock mù
ra10 = RouteAssist(dock_at_end=True)
acts = ra10.tick(world(system="Nonni", markers=0,
                       stations=[{"name": "Other Plant", "type": "Station",
                                  "center": (700, 400)}],
                       destination="Nonni IV - Plant"))
ok("dock_at_end_no_match_waits", acts[0]["do"] == "wait", str(acts))

# ---------------- 10. transition quá lâu → block ----------------
clock11 = FakeClock()
ra11 = RouteAssist(clock=clock11)
ra11.tick(world(system="A", next_system="B", markers=1, gates=[gate("B")]))
ra11.tick(world(system=None, location_known=False))
clock11.advance(46)
blocked = ra11.tick(world(system=None, location_known=False))
ok("long_transition_blocks", blocked[0]["do"] == "blocked", str(blocked))

print(f"\n=> {PASS} test PASS (mọi [FAIL] exit(1) ngay)")
