"""CLI End-to-End cho fila-bot — Unified Launcher cho tat ca che do.

Usage:
    python -m fila_bot.cli status
    python -m fila_bot.cli distribution [--live] [--confirm-input] [--max-missions 5]
    python -m fila_bot.cli abyss [--live] [--confirm-input] [--filament "Tranquil Exotic Filament"]
    python -m fila_bot.cli inspect
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.eye import Eye  # noqa: E402
from fila_bot.ui_model import ModeUnavailable, build_supervisor  # noqa: E402
from fila_bot.version import banner, read_version  # noqa: E402
from fila_bot.win import find_client_window  # noqa: E402
from fila_bot.world_snapshot import parse_world  # noqa: E402


def _build(**kw):
    """build_supervisor + loi than thien. None = khong chay duoc (da in ly do)."""
    try:
        return build_supervisor(**kw)
    except ModeUnavailable as e:
        print(f"[KHONG CHAY] {e}")
        return None
    except (RuntimeError, FileNotFoundError, OSError) as e:
        print(f"[FATAL] Khong ket noi duoc EVE client: {e}")
        print("  -> Mo EVE Online, dang nhap nhan vat roi chay lai.")
        return None


def _watch(sup, *, abyss: bool, max_runs: int | None = None, tick: float = 0.5) -> int:
    """Vong theo doi co DIEU KIEN DUNG THAT (truoc day lap vo han vi Supervisor
    khong bao gio o trang thai STOPPED/BLOCKED).

    Tra ve: 0 xong viec, 3 bi chan (fail-closed), 130 nguoi dung Ctrl+C.
    """
    import logging
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    sup.start_thread(tick_interval=tick)
    sup.send("START")
    print("\nBot da bat dau. Nhan Ctrl+C de dung an toan...")
    last = ""
    last_detail = ""
    try:
        while True:
            time.sleep(1.0)
            st = sup.mode.status() if hasattr(sup.mode, "status") else {}
            phase = getattr(sup.mode, "phase", "?")
            runs = st.get("runs", 0)
            if abyss:
                line = (f"[{time.strftime('%H:%M:%S')}] {sup.state} | phase {phase} | "
                        f"run {runs} | room {st.get('room', 0)} | hp {st.get('hp')} | "
                        f"filament {st.get('filaments')}")
            else:
                # security: 'completed' (distribution dùng 'done'); runs fallback 0
                done = st.get("completed", st.get("done", runs))
                line = (f"[{time.strftime('%H:%M:%S')}] {sup.state} | phase {phase} | "
                        f"xong {done} | tu choi {st.get('declined', 0)}")
            detail = st.get("detail") or ""
            if line != last or detail != last_detail:   # chi in khi doi -> log khong bi spam
                print(line + (f" | {detail}" if detail else ""))
                last = line
                last_detail = detail

            # Ground LIVE 2026-11-12: the log printed only status text, so nobody
            # could tell whether ANY input was actually sent — the owner had to
            # ask "module ko bật lên à? drone thả ra ko lock target thì bắn kiểu
            # gì?". Print every executed action with its result, verbatim.
            try:
                while True:
                    evt = sup.evt_q.get_nowait()
                    if evt.get("type") != "TICK":
                        continue
                    acts = evt.get("acts") or []
                    results = evt.get("results") or []
                    for i, act in enumerate(acts):
                        if not isinstance(act, dict):
                            continue
                        kind = act.get("do")
                        if kind in ("wait",):
                            continue
                        res = results[i] if i < len(results) and isinstance(results[i], dict) else {}
                        status = res.get("status") or ("SENT" if res.get("ok") else "-")
                        note = res.get("note") or act.get("why") or ""
                        print(f"    · {kind} [{status}] {note}")
            except Exception:  # noqa: BLE001 — log khong duoc giet bot
                pass

            blocked = st.get("blocked")
            if blocked:
                print(f"\n[DUNG — fail-closed] {blocked}")
                sup.shutdown()
                return 3
            if not abyss and phase == "IDLE_DONE":
                # status cua Security/Distribution la 'completed'/'done', khong phai 'runs'
                print(f"\n[OK] Hoan tat: {done} nhiem vu, tu choi {st.get('declined', 0)}.")
                sup.shutdown()
                return 0
            if abyss and phase == "DOCKED":
                settled = sup.ticks > 20 or runs > 0
                if max_runs is not None and runs >= max_runs and settled:
                    print(f"\n[OK] Hoan tat {runs} run abyss.")
                    sup.shutdown()
                    return 0
                if settled and not st.get("filaments"):
                    print(f"\n[OK] Het filament sau {runs} run.")
                    sup.shutdown()
                    return 0
    except KeyboardInterrupt:
        print("\nNhan lenh dung tu nguoi dung... nha phim + dung sach.")
        sup.shutdown()
        return 130


def cmd_status(args) -> int:
    """Doc va in toan bo trang thai the gioi game qua WorldSnapshot."""
    print("=== DANG KET NOI EVE CLIENT... ===")
    win = find_client_window()
    if win:
        print(f"[OK] Cua so EVE: '{win['title']}' | Origin: {win['origin']} | Size: {win['size']}")
    else:
        print("[CANH BAO] Khong tim thay cua so exefile.exe (EVE Online).")

    try:
        eye = Eye(dll_path=args.dll)
        eye.refresh()
    except Exception as e:
        print(f"[LOI] Khong the khoi tao Eye reader: {e}")
        return 2

    snap = parse_world(eye)
    print("\n--- WORLD SNAPSHOT (observed values; UNKNOWN means not read) ---")
    print(f"Connection Lost (E-STOP) : {snap.connection_lost}")
    if snap.connection_lost:
        print("  -> Connection Lost popup detected; all bot actions must stop.")

    print(f"Location state           : {snap.location_state or 'UNKNOWN'}")
    print(f"Solar system             : {snap.system or 'UNKNOWN'}")
    print(f"Security status          : {snap.security if snap.security is not None else 'UNKNOWN'}")
    print(f"Station                  : {snap.station or 'UNKNOWN'}")
    if snap.active_ship:
        hull = snap.active_ship.get("hull") or "UNKNOWN"
        print(f"Active ship               : {hull}")
        print(f"  Ship name               : {snap.active_ship.get('name') or 'UNKNOWN'}")
    else:
        print("Active ship               : UNKNOWN")
    print(f"Ship panel observed      : {snap.ship_panel_observed}")
    print(f"Module activity          : {'KNOWN' if snap.module_activity_known else 'UNKNOWN'}")

    if snap.location_state == "IN_SPACE":
        print(f"Ship speed               : {snap.speed_mps if snap.speed_mps is not None else 'UNKNOWN'} m/s")
        print(f"Capacitor                : {f'{snap.capacitor_percent:.1f}%' if snap.capacitor_percent is not None else 'UNKNOWN'}")
        print(f"Maneuver                 : {snap.maneuver or 'UNKNOWN'}")
        if snap.ship_health:
            hp = snap.ship_health
            fmt_pct = lambda key: f"{hp[key] * 100:.1f}%" if key in hp else "UNKNOWN"
            print(f"Ship health              : Shield {fmt_pct('shield')} | "
                  f"Armor {fmt_pct('armor')} | Structure {fmt_pct('structure')}")
        print(f"Selected target          : {snap.selected_name or 'UNKNOWN'} | "
              f"Buttons: {list(snap.selected_buttons.keys())}")

    if snap.agents is None:
        agents_text = "UNKNOWN"
    elif not snap.agents:
        agents_text = "NONE (panel observed)"
    else:
        agents_text = "; ".join(a.get("name", "UNKNOWN") for a in snap.agents)
    print(f"Agents                   : {agents_text}")

    if snap.active_missions is None:
        missions_text = "UNKNOWN"
    elif not snap.active_missions:
        missions_text = "NONE (panel observed)"
    else:
        missions_text = "; ".join(snap.active_missions)
    print(f"Active missions           : {missions_text}")

    route_target = snap.route.destination or snap.route.next_system
    if route_target:
        route_text = f"{route_target} | Jumps: {snap.route.jumps if snap.route.jumps is not None else 'UNKNOWN'} | Markers: {snap.route.markers}"
    else:
        route_text = "UNKNOWN"
    print(f"Route                     : {route_text}")

    print(f"Agent Dialogue            : {'OPEN' if snap.agent_dialog.open else 'CLOSED'}")
    if snap.agent_dialog.open:
        ad = snap.agent_dialog
        print(f"  Title                  : {ad.title or 'UNKNOWN'}")
        print(f"  Available buttons      : {list(ad.buttons.keys())}")
        if ad.pickup:
            print(f"  Pickup                 : {ad.pickup.get('name')}")
        if ad.dropoff:
            print(f"  Dropoff                : {ad.dropoff.get('name')}")
        print(f"  Link coordinates       : Pickup {ad.pickup_link_xy} | Dropoff {ad.dropoff_link_xy}")

    print(f"Inventory                 : {'OPEN' if snap.inventory.open else 'CLOSED'}")
    if snap.inventory.open:
        inv = snap.inventory
        print(f"  Available hangars      : {list(inv.hangars.keys())}")
        if inv.capacity:
            print(f"  Capacity               : Used {inv.capacity.get('used')} m3 / Max {inv.capacity.get('max')} m3")
        print(f"  Items observed         : {len(inv.items)}")
        for it in inv.items[:5]:
            print(f"    - {it.get('name') or 'UNKNOWN'} at {it.get('center')}")

    return 0


def cmd_distribution(args) -> int:
    """Chay bot Distribution (Courier) end-to-end."""
    is_live = bool(args.live)
    is_dry = not bool(args.confirm_input)

    print("=" * 60)
    print(banner() + " — DISTRIBUTION COURIER MISSION RUNNER")
    print(f"Che do: {'LIVE (Client that)' if is_live else 'SIM (Gia lap test)'}")
    print(f"Thao tac: {'THUC THI PHIM/CHUOT THAT' if not is_dry else 'DRY-RUN (Chi log, an toan)'}")
    print(f"Gioi han: {args.max_missions or 'Vo han'} nhiem vu")
    print(f"Route sec: {'BO QUA kiem tra (--allow-unknown-sec)' if args.allow_unknown_sec else 'bat buoc hisec'}")
    print("=" * 60)

    if is_live and not is_dry:
        win = find_client_window()
        if not win:
            print("FATAL: Khong tim thay cua so EVE client. Khong the chay che do confirm-input.")
            return 2

    sup = _build(mode="distribution", sim=not is_live, dry=is_dry, dll=args.dll,
                 max_hours=args.max_hours, max_missions=args.max_missions,
                 allow_unknown_sec=bool(args.allow_unknown_sec))
    if sup is None:
        return 2
    return _watch(sup, abyss=False, tick=args.tick)


def cmd_abyss(args) -> int:
    """Chay bot Abyssal Deadspace end-to-end."""
    is_live = bool(args.live)
    is_dry = not bool(args.confirm_input)

    print("=" * 60)
    print(banner() + " — ABYSSAL DEADSPACE RUNNER")
    print(f"Che do: {'LIVE (Client that)' if is_live else 'SIM (Gia lap test)'}")
    print(f"Thao tac: {'THUC THI PHIM/CHUOT THAT' if not is_dry else 'DRY-RUN (Chi log, an toan)'}")
    print(f"Filament: {args.filament}   |   Engine: {args.engine}   |   So run: {args.max_runs or 'Vo han'}")
    if is_live:
        print("LUU Y: undock/filament/gate/dock cua Abyss CHUA ground tren client that —")
        print("        bot chi chay guards va se DUNG voi ly do thay vi bam mu.")
    print("=" * 60)

    sup = _build(mode="abyss", sim=not is_live, dry=is_dry, dll=args.dll,
                 max_hours=args.max_hours, filament=args.filament,
                 max_runs=args.max_runs, engine=args.engine)
    if sup is None:
        return 2
    return _watch(sup, abyss=True, max_runs=args.max_runs, tick=args.tick)


def cmd_security(args) -> int:
    """Chay bot Security PvE Mission Runner (Gila Combat Doctrine)."""
    is_live = bool(args.live)
    is_dry = not bool(args.confirm_input)

    if getattr(args, "preflight", False):
        return _security_preflight(args)

    print("=" * 60)
    print(banner() + " — SECURITY PVE MISSION RUNNER (GILA COMBAT DOCTRINE)")
    print(f"Che do: {'LIVE (Client that)' if is_live else 'SIM (Gia lap test)'}")
    print(f"Thao tac: {'THUC THI PHIM/CHUOT THAT' if not is_dry else 'DRY-RUN (Chi log, an toan)'}")
    print(f"Gioi han: {args.max_missions or 'Vo han'} nhiem vu")
    print("=" * 60)

    if is_live and not is_dry:
        win = find_client_window()
        if not win:
            print("FATAL: Khong tim thay cua so EVE client. Khong the chay che do confirm-input.")
            return 2

    sup = _build(mode="security", sim=not is_live, dry=is_dry, dll=args.dll,
                 max_hours=args.max_hours, max_missions=args.max_missions,
                 profile=getattr(args, 'profile', None))
    if sup is None:
        return 2
    return _watch(sup, abyss=False, tick=args.tick)


def _security_preflight(args) -> int:
    """Read-only preflight: profile, pinned build, window identity, world. No input."""
    from fila_bot.eye import DLL_PATH
    from fila_bot.mission_profile import (load_profile, preflight_world,
                                          verify_build)
    if not args.profile:
        print("[KHONG CHAY] --preflight can --profile <json>")
        return 2
    try:
        profile = load_profile(args.profile)
    except (OSError, ValueError) as exc:
        print(f"[KHONG CHAY] profile: {exc}")
        return 2
    win = find_client_window()
    try:
        eye = Eye(dll_path=args.dll)
        if eye.refresh() is None:
            print("[KHONG CHAY] reader returned no UI tree")
            return 2
    except Exception as exc:  # noqa: BLE001 — preflight reports, never starts bot
        print(f"[KHONG CHAY] reader: {exc}")
        return 2
    snap = parse_world(eye)
    world = {"location_known": snap.location_known,
             "connection_lost": snap.connection_lost}
    errors = verify_build(profile, args.client_exe, args.dll or DLL_PATH)
    errors += preflight_world(profile, world, win["title"] if win else None)
    print(json.dumps({"ok": not errors, "window": win["title"] if win else None,
                      "location_known": world["location_known"],
                      "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 3


def cmd_opportunities(args) -> int:
    """Doc panel Opportunities (AIR Career Program) — Freelance Jobs/Agent Missions."""
    print("=== DANG KET NOI EVE CLIENT... ===")
    win = find_client_window()
    if win:
        print(f"[OK] Cua so EVE: '{win['title']}' | Origin: {win['origin']} | Size: {win['size']}")
    else:
        print("[CANH BAO] Khong tim thay cua so exefile.exe (EVE Online).")

    try:
        eye = Eye(dll_path=args.dll)
        if eye.refresh() is None:
            print("[CANH BAO] Khong doc duoc UI tree (client khong tra JSON).")
    except Exception as e:
        print(f"[LOI] Khong the khoi tao Eye reader: {e}")
        return 2

    from fila_bot.opportunities import format_summary, parse_jobboard

    data = parse_jobboard(eye.root)
    if not data.get("opened") and args.open:
        win = find_client_window()
        print("[INFO] JobBoardWindow chua mo -> bam nut airCareerProgram (16,112)...")
        from fila_bot import control as ctl
        btn = eye._find_by_name("airCareerProgram")
        if not btn:
            print("[STOP] Khong thay nut airCareerProgram — ZID khong biet bam gi, khong bia.")
            return 3
        xy = eye.abs_center(btn[0])
        res = ctl.execute(ctl.act_menu_entry(xy), dry=False, win=win)
        print("[MT] click", xy, "->", res.get("ok"))
        time.sleep(2.5)
        if eye.refresh() is None:
            print("[CANH BAO] refresh that bai sau khi mo panel.")
        data = parse_jobboard(eye.root)

    print("\n=== OPPORTUNITIES (JobBoardWindow) ===")
    print(format_summary(data))
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[MT] da ghi JSON: {out_path}")
    return 0 if data.get("opened") else 3


def cmd_inspect(args) -> int:
    """Mo hoac in link toi Visual DOM Inspector."""
    p = ROOT / "tools" / "inspector.html"
    print("\nVisual EVE UI Tree Inspector:")
    print(f"Duong dan file: {p.resolve()}")
    print("\nDe xem truc quan cay DOM va bounding box cua EVE client:")
    print("1. Mo file tren bang bat ky trinh duyet nao (Chrome, Edge, Firefox).")
    print("2. Keo tha bat ky file dump .json nao trong thu muc 'dumps/' hoac 'tests/fixtures/' vao.")
    print("3. Hover chuot len canvas de xem type, _name, text, center toa do.")
    return 0


def main():
    p = argparse.ArgumentParser(description="fila-bot Unified End-to-End CLI")
    p.add_argument("--version", action="version",
                   version=f"fila-bot {read_version()}",
                   help="In phien ban roi thoat")
    p.add_argument("--dll", default=None, help="Duong dan DLL doc bo nho")
    sub = p.add_subparsers(dest="subcommand", required=True)

    # status
    p_stat = sub.add_parser("status", help="Xem trang thai the gioi game qua WorldSnapshot")
    p_stat.set_defaults(func=cmd_status)

    # distribution
    p_dist = sub.add_parser("distribution", help="Chay bot Distribution Courier mission")
    p_dist.add_argument("--live", action="store_true", help="Chay tren client EVE that (mac dinh la sim)")
    p_dist.add_argument("--confirm-input", action="store_true", help="Thuc thi click va phim that (mac dinh chi log)")
    p_dist.add_argument("--max-missions", type=int, default=None, help="So mission toi da")
    p_dist.add_argument("--max-hours", type=float, default=4.0, help="So gio chay toi da")
    p_dist.add_argument("--tick", type=float, default=0.5, help="Tick interval (giay)")
    p_dist.add_argument("--allow-unknown-sec", action="store_true",
                        help="Bo kiem tra sec route (mac dinh: khong ro sec -> DUNG, fail-closed)")
    p_dist.set_defaults(func=cmd_distribution)

    # abyss
    p_aby = sub.add_parser("abyss", help="Chay bot Abyssal Deadspace")
    p_aby.add_argument("--live", action="store_true", help="Chay tren client EVE that (mac dinh la sim)")
    p_aby.add_argument("--confirm-input", action="store_true", help="Thuc thi click va phim that (mac dinh chi log)")
    p_aby.add_argument("--filament", default="Tranquil Exotic Filament", help="Ten filament can chay")
    p_aby.add_argument("--max-runs", type=int, default=None, help="So run abyss toi da")
    p_aby.add_argument("--engine", choices=("fsm", "bt"), default="fsm",
                       help="Bo dieu khien: fsm (mac dinh) hoac bt (Behavior Tree)")
    p_aby.add_argument("--max-hours", type=float, default=4.0, help="So gio chay toi da")
    p_aby.add_argument("--tick", type=float, default=0.3, help="Tick interval (giay)")
    p_aby.set_defaults(func=cmd_abyss)

    # security
    p_sec = sub.add_parser("security", help="Chay bot Security PvE Mission Runner (Gila)")
    p_sec.add_argument("--live", action="store_true", help="Chay tren client EVE that (mac dinh la sim)")
    p_sec.add_argument("--confirm-input", action="store_true", help="Thuc thi click va phim that (mac dinh chi log)")
    p_sec.add_argument("--max-missions", type=int, default=None, help="So mission toi da")
    p_sec.add_argument("--max-hours", type=float, default=4.0, help="So gio chay toi da")
    p_sec.add_argument("--tick", type=float, default=0.5, help="Tick interval (giay)")
    p_sec.add_argument("--profile", default=None, help="Mission profile JSON; required for LIVE input")
    p_sec.add_argument("--preflight", action="store_true",
                       help="Read-only checks (profile/build/window/world) then exit; sends no input")
    p_sec.add_argument("--client-exe", default="C:/Fenris Creations/EVE/tq/bin64/exefile.exe",
                       help="Client binary whose SHA256 is pinned in the profile")
    p_sec.set_defaults(func=cmd_security)

    # inspect
    p_ins = sub.add_parser("inspect", help="Mo hoac in thong tin UI inspector")
    p_ins.set_defaults(func=cmd_inspect)

    # opportunities
    p_opp = sub.add_parser("opportunities", help="Doc panel Opportunities: Freelance Jobs/Agent Missions")
    p_opp.add_argument("--open", action="store_true",
                       help="Neu panel dang dong: bam nut airCareerProgram de mo (thao tác that)")
    p_opp.add_argument("--out", default=None, help="Ghi ket qua ra file JSON")
    p_opp.set_defaults(func=cmd_opportunities)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
