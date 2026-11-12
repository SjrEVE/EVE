"""A successful turn-in where the tracker disappears must still be counted.

Ground LIVE 2026-11-12 15:02 (Piak, 'The Guristas Spies'): after Complete, EVE
removed the Job Board and the mission tracker entirely
(`mission_panel_observed == False`, all panel types absent) while the agent
dialog read "The Guristas Spies Objectives Complete ... Your accomplishment has
been noted" and showed a fresh 'Request Mission' with NO Complete button. The old
code waited forever for "panel observed AND mission absent" and never counted the
mission. That dialog state is the client confirming the turn-in.

The weaker path must stay strict: a missing panel with no such dialog evidence is
still UNVERIFIED — never counted.
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


DONE_TEXTS = [
    "Agent Conversation - Jitkavaja Ninsen Level 1",
    "Request Mission",
    "Close",
    ("Jitkavaja Ninsen Division: Security 0.7 ... Thank you. Your accomplishment "
     "has been noted and saved into our database."),
    "The Guristas Spies Objectives Complete The following objectives must be "
    "completed to finish the mission: Objective Eliminate the Guristas Spies.",
]


def docked_after(**kw):
    w = {"docked": True, "location_known": True, "snapshot_valid": True,
         "connection_lost": False, "has_active_mission": None,
         "mission_panel_observed": False, "missions": None,
         "ship_health": {"shield": 1.0, "armor": 1.0, "hull": 1.0},
         "agent_dialog_open": True, "agents": [],
         "offer": {"title": None, "texts": DONE_TEXTS,
                   "buttons": {"request": (723, 779), "close": (860, 779)}}}
    w.update(kw)
    return w


clock = {"t": 3000.0}
m = SecurityMode(clock=lambda: clock["t"])
m._was_in_space = True
m._await_turnin = True
m._turnin_title = "The Guristas Spies"
m._turnin_since = clock["t"]
m.door_since = clock["t"]
acts = m.tick(docked_after())
ok("turn-in counted from the agent dialog when the tracker vanished",
   m.completed_missions == 1 and not m._await_turnin, f"{m.completed_missions} {m.status()}")
ok("no click is fabricated to make the count happen",
   all(a["do"] == "wait" for a in acts), str(acts))
ok("status states the dialog evidence used",
   "Objectives Complete" in (m.status().get("detail") or ""), str(m.status().get("detail")))

# Missing panel + no dialog evidence must NOT be counted.
m2 = SecurityMode(clock=lambda: clock["t"])
m2._was_in_space = True
m2._await_turnin = True
m2._turnin_title = "The Guristas Spies"
m2._turnin_since = clock["t"]
m2.door_since = clock["t"]
acts = m2.tick(docked_after(agent_dialog_open=False, offer=None))
ok("missing panel with no dialog evidence is still unverified",
   m2.completed_missions == 0 and acts[0]["do"] == "wait", f"{m2.completed_missions} {acts}")

# The dialog must not be enough while a Complete button is still offered.
m3 = SecurityMode(clock=lambda: clock["t"])
m3._was_in_space = True
m3._await_turnin = True
m3._turnin_title = "The Guristas Spies"
m3._turnin_since = clock["t"]
m3.door_since = clock["t"]
acts = m3.tick(docked_after(offer={"title": "The Guristas Spies", "texts": DONE_TEXTS,
                                   "buttons": {"complete": (5, 6), "close": (7, 8)}}))
ok("a still-offered Complete button blocks the weaker path",
   m3.completed_missions == 0, f"{m3.completed_missions} {acts}")

print(f"\nKet qua: {PASS} PASS / {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
