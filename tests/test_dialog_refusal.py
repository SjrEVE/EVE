"""A Complete button plus "objectives have not been completed" is a REFUSAL.

Ground LIVE 2026-11-12 18:19 (Piak, 'Eliminate the Pirate Campers'): the agent
dialog showed Complete/Quit/Close buttons AND the sentence "One or more mission
objectives have not been completed. Please check the mission's details ...".
Clicking Complete produced that sentence as a modal, the run ended on
OBJECTIVE_UNVERIFIED, and the mission stayed active in the ledger — so the next
run could not accept anything new.

Rule: the dialog's own text is evidence. Refusal text means do not click, and do
not count or keep anything as completed.
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


REFUSAL = ("One or more mission objectives have not been completed. Please check "
           "the mission s details via Opportunities or your info panel")


def docked(offer):
    return {"docked": True, "location_known": True, "snapshot_valid": True,
            "connection_lost": False, "has_active_mission": True,
            "mission_panel_observed": True, "missions": ["Eliminate the Pirate Campers"],
            "active_mission_title": "Eliminate the Pirate Campers",
            "ship_health": {"shield": 1.0, "armor": 1.0, "hull": 1.0},
            "agent_dialog_open": True, "agents": [], "offer": offer}


clock = {"t": 900.0}

# 1. Refusal text + Complete button -> block, never click.
m = SecurityMode(clock=lambda: clock["t"])
m._was_in_space = True
offer = {"title": "Eliminate the Pirate Campers", "objective_kind": "combat",
         "texts": ["Agent Conversation - Jitkavaja Ninsen Level 1", "Complete Mission",
                   "Quit Mission", "Close", REFUSAL],
         "buttons": {"complete": (358, 779), "quit": (502, 779), "close": (646, 779)}}
acts = m.tick(docked(offer))
kinds = [a["do"] for a in acts]
ok("refusal text blocks instead of clicking Complete",
   "complete_mission" not in kinds and acts[0]["do"] == "blocked", str(acts))
ok("the block names the real reason (objective not finished)",
   "objective" in (m.blocked or "").lower(), m.blocked or "")
ok("phase marks the objective as still open",
   m.phase == "OBJECTIVE_IN_PROGRESS", m.phase)

# 2. Same dialog without the refusal text -> the normal turn-in path stays.
m2 = SecurityMode(clock=lambda: clock["t"])
m2._was_in_space = True
clean = {"title": "Eliminate the Pirate Campers", "objective_kind": "combat",
         "texts": ["Agent Conversation - Jitkavaja Ninsen Level 1", "Complete Mission"],
         "buttons": {"complete": (358, 779), "close": (646, 779)}}
acts = m2.tick(docked(clean))
ok("a clean dialog still allows the turn-in click",
   acts and acts[0]["do"] == "complete_mission", str(acts))

# 3. Modal form of the same refusal: ground 11-11 dump g10_turnin_dialog is a
#    Complete press EVE refused, and ground 2026-11-12 19:42 showed the same box
#    surviving in the tree on a later run that pressed nothing. The FSM must not
#    guess which one it is: it dismisses once, and if the box survives, stops.
m3 = SecurityMode(clock=lambda: clock["t"])
w = docked(clean)
w["modal"] = {"text": REFUSAL, "ok_xy": (5, 5)}
first = m3.tick(w)
ok("a refusal modal without a pending turn-in is dismissed once, not called terminal",
   first and first[0]["do"] == "dismiss_modal", str(first))
second = m3.tick(w)
ok("if it survives the dismiss the run stops instead of looping",
   second and second[0]["do"] == "blocked", str(second))

# With a turn-in actually pending, the same text IS terminal.
m4 = SecurityMode(clock=lambda: clock["t"])
m4._await_turnin = True
acts = m4.tick(w)
ok("a refusal right after this run's own Complete stays terminal",
   acts[0]["do"] == "blocked" and m4.phase == "OBJECTIVE_UNVERIFIED", str(acts))

print(f"\nKet qua: {PASS} PASS / {FAIL} FAIL")
sys.exit(1 if FAIL else 0)