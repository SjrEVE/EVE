"""A stale refusal modal must not kill a freshly accepted mission.

Ground LIVE 2026-11-12 19:33 (run24): the bot accepted 'Seek and Destroy' from
agent 3016216, set a destination, and then hit a leftover
"One or more mission objectives have not been completed" box still in the UI tree
from an EARLIER turn-in attempt. The FSM treated any such text as EVE refusing
the current mission and stopped with OBJECTIVE_UNVERIFIED — killing a valid,
freshly accepted mission without ever undocking.

Rule: a refusal box is terminal evidence only for the turn-in we just attempted
(`_await_turnin`). Otherwise it is stale UI: dismiss it and continue.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.modes.security import SecurityMode

PASS = 0
FAIL = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name} {msg}")


REFUSAL = ("OK context_menu_Minimize One or more mission objectives have not been "
           "completed. Please check the mission s details via Opportunities or "
           "your info panel for further information.")

clock = {"t": 100.0}
m = SecurityMode(clock=lambda: clock["t"])
acts = m.tick({"docked": True, "has_active_mission": True,
               "missions": ["Seek and Destroy"],
               "mission_panel_observed": True,
               "modal": {"text": REFUSAL, "ok_xy": (640, 480)}})
ok("stale refusal modal is dismissed, not treated as a refusal",
   [a["do"] for a in acts] == ["dismiss_modal"], acts)

# While a turn-in is pending, the same text IS terminal evidence.
m2 = SecurityMode(clock=lambda: clock["t"])
m2._await_turnin = True
acts = m2.tick({"docked": True, "has_active_mission": True,
                "missions": ["Seek and Destroy"],
                "modal": {"text": REFUSAL, "ok_xy": (640, 480)}})
ok("refusal during a pending turn-in still blocks",
   [a["do"] for a in acts] == ["blocked"] and m2.phase == "OBJECTIVE_UNVERIFIED",
   (acts, m2.phase))

# And the fresh mission keeps running after the stale modal is gone.
m3 = SecurityMode(clock=lambda: clock["t"])
m3.tick({"docked": True, "has_active_mission": True,
         "missions": ["Seek and Destroy"],
         "modal": {"text": REFUSAL, "ok_xy": (640, 480)}})
acts = m3.tick({"docked": True, "has_active_mission": True,
                "missions": ["Seek and Destroy"],
                "modal": None, "offer": None,
                "agent_dialog_open": False,
                "agents": [{"name": "Jitkavaja Ninsen", "division": "security",
                            "available": True, "chat_xy": (400, 300)}]})
ok("the accepted mission still drives the undock/turn-in flow afterwards",
   m3.phase != "OBJECTIVE_UNVERIFIED", (m3.phase, acts))

print("\nKet qua: %d PASS / %d FAIL" % (PASS, FAIL))
sys.exit(0 if FAIL == 0 else 1)