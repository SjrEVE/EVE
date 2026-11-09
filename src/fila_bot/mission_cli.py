"""CLI mission runner — xem trạng thái + chạy action (dry mặc định).

    python -m fila_bot.mission_cli status         # chỉ đọc, in JSON trạng thái
    python -m fila_bot.mission_cli plan           # FSM quyết gì tiếp (không bấm)
    python -m fila_bot.mission_cli run --go       # bấm THẬT (cần --go)

Mặc định KHÔNG bấm gì. `run` không có --go = chỉ in action sẽ bấm.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.mission import MissionEye, MissionRunner   # noqa: E402
from fila_bot.win import find_client_window, focus             # noqa: E402


def _open_eye(dll: str | None):
    from fila_bot.eye import Eye
    e = Eye(dll_path=dll)
    e.refresh()
    return e


def _print(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def cmd_status(args) -> int:
    e = _open_eye(args.dll)
    st = MissionEye(e).state()
    _print(st.as_dict())
    return 0


def cmd_plan(args) -> int:
    e = _open_eye(args.dll)
    me = MissionEye(e)
    runner = MissionRunner(me, orbit_km=args.orbit)
    st = me.state()
    acts = runner.next_actions()
    _print({"stage": runner.stage, "phase": st.phase, "actions": acts})
    return 0


def cmd_run(args) -> int:
    from fila_bot import control as ctl

    e = _open_eye(args.dll)
    me = MissionEye(e)
    runner = MissionRunner(me, orbit_km=args.orbit)
    dry = not args.go
    win = None
    if not dry:
        win = find_client_window()
        if win is None:
            print("FATAL: không tìm thấy cửa sổ EVE (exefile.exe) — không bấm mù")
            return 2
        focus(win)
        print(f"window: {win['title']} origin={win['origin']} size={win['size']}")
        time.sleep(0.5)
    rounds = 0
    while rounds < args.max_rounds:
        rounds += 1
        st = me.state()
        acts = runner.next_actions()
        print(f"\n[{rounds}] phase={st.phase} stage={runner.stage}")
        _print(acts)
        if not args.go:
            print("(dry — thêm --go để bấm thật)")
            return 0
        did = False
        for a in acts:
            name = a.get("do")
            if name == "blocked":
                print(f"BLOCKED: {a.get('why')}")
                continue
            if name == "undock":
                at = a.get("at")
                if not at:
                    print("BLOCKED: action undock thiếu toạ độ từ eye")
                    continue
                r = ctl.execute(ctl.act_undock_at(at), dry=dry, win=win)
                print("undock:", r.get("ok"))
                did = True
            elif name == "open_menu":
                at = a.get("at")
                if not at:
                    print("BLOCKED: open_menu thiếu toạ độ entry")
                    continue
                r = ctl.execute(ctl.act_open_context_menu(at), dry=dry, win=win)
                print(f"open_menu on '{a.get('label')}':", r.get("ok"))
                did = True
            elif name == "menu_entry":
                at = a.get("at")
                if not at:
                    print("BLOCKED: menu_entry thiếu toạ độ (menu không có entry đó)")
                    continue
                r = ctl.execute(ctl.act_menu_entry(at), dry=dry, win=win)
                print(f"menu_entry '{a.get('text')}':", r.get("ok"))
                did = True
            elif name == "hover_menu":
                # hover để submenu bung ra; dùng click nhẹ vào chính entry cấp 1
                xy = e.menu_entry_xy(a.get("text") or "", exact=False)
                if xy is None:
                    print(f"BLOCKED: không thấy entry menu '{a.get('text')}'")
                    continue
                r = ctl.execute(ctl.act_menu_entry(xy), dry=dry, win=win)
                print(f"hover_menu '{a.get('text')}':", r.get("ok"))
                did = True
            elif name in ("warp_to", "warp_route"):
                label = a.get("label")
                if name == "warp_to" and label:
                    xy = _entry_xy(e, label)
                    if xy is None:
                        print(f"BLOCKED: không thấy entry '{label}' trong overview")
                        continue
                    r = ctl.execute(ctl.act_warp_to(xy), dry=dry, win=win)
                else:
                    r = ctl.execute(ctl.act_warp_route(), dry=dry, win=win)
                print(f"{name}: {r.get('ok')}")
                did = True
        if not did:
            print("không có action nào chạy được — dừng")
            return 1
        if args.go:
            time.sleep(args.wait)
    return 0


def _entry_xy(eye, label: str):
    """Toạ độ entry overview theo TÊN đã verify (P0-5: không bấm mù)."""
    if not label:
        return None
    want = label.strip().lower()
    for e in eye.overview_entries():
        if (e.get("Name") or "").strip().lower() == want:
            return e.get("center")
    for e in eye.overview_entries():
        if want in (e.get("Name") or "").lower():
            return e.get("center")
    return None


def _find_button_xy(eye, text: str):
    """Toạ độ button theo text (EveLabelMedium._setText trong ButtonWindow)."""
    want = text.strip().lower()
    for n in eye.walk(eye.root or {}):
        a = n.get("attrs", {}) or {}
        txt = (a.get("_setText") or "").strip().lower()
        if txt == want:
            return eye.abs_center(n)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="mission runner (security missions)")
    ap.add_argument("cmd", choices=["status", "plan", "run"])
    ap.add_argument("--dll", default=None)
    ap.add_argument("--orbit", type=float, default=2500)
    ap.add_argument("--go", action="store_true", help="bấm THẬT (mặc định dry)")
    ap.add_argument("--wait", type=float, default=3.0, help="giây giữa các vòng")
    ap.add_argument("--max-rounds", type=int, default=20)
    args = ap.parse_args()
    return {"status": cmd_status, "plan": cmd_plan, "run": cmd_run}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
