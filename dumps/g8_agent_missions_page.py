"""Probe G8 buoc 5: trong JobBoard chon 'Agent Missions' (side nav) -> dump trang + card.

PYTHONPATH=src python dumps/g8_agent_missions_page.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot import control as ctl  # noqa: E402
from fila_bot.eye import Eye  # noqa: E402
from fila_bot.win import find_client_window, focus  # noqa: E402

win = find_client_window()
if win:
    focus(win)
    time.sleep(0.3)

eye = Eye()
if eye.refresh() is None:
    print("refresh that bai — thu lai 1 lan sau 1 giay (UI dang chuyen canh)")
    time.sleep(1.0)
    if eye.refresh() is None:
        print("STOP: khong doc duoc UI tree")
        raise SystemExit(3)

# neu cua so job_board chua mo: mo AIR portal -> Freelance
jb = eye._find_by_type("JobBoardWindow")
if jb:
    print("JobBoardWindow da mo tu truoc — khong bam lai (an toan, tranh dong mo lung tung)")
else:
    btn = eye._find_by_name("airCareerProgram")
    if not btn:
        print("STOP: khong thay nut airCareerProgram")
        raise SystemExit(3)
    ctl.execute(ctl.act_menu_entry(eye.abs_center(btn[0])), dry=False, win=win)
    time.sleep(2.5)
    eye.refresh()
    freelance = None
    for n in eye.walk(eye.root):
        if n.get("type") == "Button":
            for c in n.get("children") or []:
                ca = c.get("attrs") or {}
                if ca.get("_name") == "label" and "freelance jobs" in str(ca.get("_setText") or "").lower():
                    freelance = n
    if not freelance:
        print("STOP: khong thay nut freelance")
        raise SystemExit(3)
    ctl.execute(ctl.act_menu_entry(eye.abs_center(freelance)), dry=False, win=win)
    time.sleep(2.5)
    eye.refresh()
    jb = eye._find_by_type("JobBoardWindow")
    if not jb:
        print("STOP: khong mo duoc JobBoardWindow")
        raise SystemExit(3)

# nut side-nav 'feature_agent_missions_entry'
nav = None
for n in eye.walk(jb[0]):
    if (n.get("attrs") or {}).get("_name") == "feature_agent_missions_entry":
        nav = n
        break
if not nav:
    print("STOP: khong thay feature_agent_missions_entry")
    raise SystemExit(3)
xy = eye.abs_center(nav)
print("click side nav agmissions tai:", xy)
res = ctl.execute(ctl.act_menu_entry(xy), dry=False, win=win)
print("click:", res)
time.sleep(2.5)

eye.refresh()
out = ROOT / "dumps" / "g8_agent_missions_page.json"
out.write_text(json.dumps(eye.root, ensure_ascii=False), encoding="utf-8")
print("dump:", out)

jb = eye._find_by_type("JobBoardWindow")
# in content_container (ben phai): page nao + card nao
content = None
for n in eye.walk(jb[0]):
    if (n.get("attrs") or {}).get("_name") == "content_container":
        content = n
        break
print("\n=== CONTENT CONTAINER ===")
def walk(n, depth=0):
    a = n.get("attrs") or {}
    nm = a.get("_name"); ty = n.get("type"); tx = a.get("_setText")
    if depth < 14:
        line = "  " * depth + f"{ty} name={nm!r}"
        if tx: line += f" text={str(tx)[:140]!r}"
        print(line)
    for c in n.get("children") or []:
        walk(c, depth + 1)
walk(content or {})
