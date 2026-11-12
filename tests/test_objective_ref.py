"""Syntax regression only; synthetic coordinates below are NOT live evidence.

Ground truth (client source V24.02 + dump TQ 11-11):
  * scratch/probe_firecloud.txt — trong pocket Josameto:
        EveLabelMedium 'You need to approach <a href= showinfo:10131//9002321446000117567 >Fire Cloud</a>'
    cung dump co 'MissionBracket' name="('agentmissions', 3010986, 'dungeon', 0)"
  * ui_dump_space.json — bracket that ten '__inflightbracket_<itemID>'
    (client bracketMgr.py: name='__inflightbracket_%s' % itemID)
  * scratch/live_current_tree.json — 'You need to travel to <a href= showinfo:5//30000156 >Josameto</a>'
  * scratch/live_after_panel_fix.json — 'You need to activate the Acceleration Gate' (khong anchor)

Truoc day bot dung im o buoc nay (docs/EVEMASTER_ARCHITECTURE §6: objective
KHONG PHAI KILL -> authorize tu choi ban la dung, nhung khong co duong 'approach').
Module objective_ref.py giai phan parse; runner dung no o buoc sau.

Chay: PYTHONPATH=src python tests/test_objective_ref.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.objective_ref import (  # noqa: E402
    ACTIVATE,
    APPROACH,
    TRAVEL,
    UNKNOWN,
    bracket_name_for,
    match_bracket,
    objective_reference,
)

PASS = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} {msg}")
        raise SystemExit(1)


FIRE_CLOUD = ("You need to approach <a href= showinfo:10131//9002321446000117567 "
              ">Fire Cloud</a>")
TRAVEL_JOSAMETO = ("You need to travel to <a href= showinfo:5//30000156 "
                   ">Josameto</a> <color=#ff72e755>0.6</color>")
GATE_PLAIN = "You need to activate the Acceleration Gate"

# ---- parse objective text ----

ref = objective_reference(FIRE_CLOUD)
ok("Fire Cloud: verb=approach", bool(ref) and ref["verb"] == APPROACH, repr(ref))
ok("Fire Cloud: type_id=10131", bool(ref) and ref["type_id"] == 10131, repr(ref))
ok("Fire Cloud: item_id doc duoc",
   bool(ref) and ref["item_id"] == 9002321446000117567, repr(ref))
ok("Fire Cloud: label sach markup", bool(ref) and ref["label"] == "Fire Cloud",
   repr(ref))

ref_j = objective_reference(TRAVEL_JOSAMETO)
ok("Josameto: verb=travel", bool(ref_j) and ref_j["verb"] == TRAVEL, repr(ref_j))
ok("Josameto: he 0.6 bo markup, label chi ten he",
   bool(ref_j) and ref_j["label"] == "Josameto", repr(ref_j))
ok("Josameto: type_id=5 (SolarSystem)", bool(ref_j) and ref_j["type_id"] == 5,
   repr(ref_j))

ref_g = objective_reference(GATE_PLAIN)
ok("Gate plain: verb=activate", bool(ref_g) and ref_g["verb"] == ACTIVATE,
   repr(ref_g))
ok("Gate plain: khong co item_id (khong anchor)",
   bool(ref_g) and ref_g["item_id"] is None, repr(ref_g))

ref_u = objective_reference("You need to do something unrecognised")
ok("Cau la: verb=unknown (khong cap quyen di chuyen)",
   bool(ref_u) and ref_u["verb"] == UNKNOWN, repr(ref_u))

ok("None -> None", objective_reference(None) is None)
ok("empty -> None", objective_reference("") is None)
ok("whitespace -> None", objective_reference("   ") is None)

# ---- bracket naming + matching ----

ok("bracket name theo client",
   bracket_name_for(60003460) == "__inflightbracket_60003460")
ok("bracket name tu string id",
   bracket_name_for("9002321446000117567") ==
   "__inflightbracket_9002321446000117567")
ok("bracket name: None -> None", bracket_name_for(None) is None)
ok("bracket name: non-digit -> None", bracket_name_for("abc") is None)

brackets = [
    {"name": "__inflightbracket_60003460", "center": (813, 588), "label": None},
    {"name": "__inflightbracket_9002321446000117567", "center": (700, 400),
     "label": None},
]
hit = match_bracket(brackets, 9002321446000117567)
ok("match theo item_id", hit is not None and hit["center"] == (700, 400), repr(hit))

hit_label = match_bracket(
    [{"name": "__inflightbracket_1", "center": (10, 20), "label": "Fire Cloud"}],
    999, label="fire cloud")
ok("label cannot override a mismatched item ID", hit_label is None,
   repr(hit_label))

ok("khong match -> None",
   match_bracket([{"name": "__inflightbracket_1", "center": (1, 1),
                   "label": "Other"}], 12345, label="Fire Cloud") is None)
ok("list rong -> None", match_bracket([], None, None) is None)

# ---- synthetic matcher chain, NOT a production/live action trace ----
chain = None
parsed = objective_reference(FIRE_CLOUD)
if parsed and parsed.get("item_id"):
    chain = match_bracket(brackets, parsed["item_id"], parsed.get("label"))
ok("synthetic syntax/matcher composition (not clickable proof)",
   chain is not None and chain["center"] == (700, 400), repr(chain))

print(f"\n{PASS} PASS")
